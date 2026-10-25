# SPDX-License-Identifier: GPL-3.0-only
# Nano 6 Theme Studio - Copyright (C) 2026 sharphatman-ux and contributors. See LICENSE.
"""Main window: tabs (left) · live device preview (centre) · context panel (right).
First launch guides through 1 Open firmware → 2 Customize → 3 Export."""

from __future__ import annotations

from pathlib import Path

from PIL import Image
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from nano6studio.core import catalog as C
from nano6studio.core import home_render as H
from nano6studio.core.export import export_asset_pack, export_silver_db, write_install_guide
from nano6studio.core.icons import ART, app_art_from_db, apply_app_art
from nano6studio.core.loader import LoadedFirmware, load_ipsw, make_project
from nano6studio.core.project import ThemeProject
from nano6studio.ui.credits import CreditsDialog
from nano6studio.ui.editor import ImageEditorDialog
from nano6studio.ui.install_wizard import InstallWizard
from nano6studio.ui.preview import DevicePreview
from nano6studio.ui.qtutil import pil_to_pixmap
from nano6studio.ui.styles import DARK_QSS

IMG_FILTER = "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif)"


def _thumb(im: Image.Image, size=72, edited=False) -> QIcon:
    from PIL import ImageDraw

    im = im.convert("RGBA").copy()
    im.thumbnail((size, size), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.paste(im, ((size - im.width) // 2, (size - im.height) // 2), im)
    if edited:  # small "edited by you" badge instead of cluttering the name
        d = ImageDraw.Draw(canvas)
        d.ellipse((size - 18, 0, size - 1, 17), fill=(255, 196, 0, 255))
        d.text((size - 13, 2), "*", fill=(0, 0, 0, 255))
    return QIcon(pil_to_pixmap(canvas))


def _grid() -> QListWidget:
    g = QListWidget()
    g.setViewMode(QListWidget.ViewMode.IconMode)
    g.setIconSize(QSize(64, 64))
    g.setGridSize(QSize(104, 124))
    f = g.font()
    f.setPointSizeF(max(7.5, f.pointSizeF() - 1.5))
    g.setFont(f)
    g.setTextElideMode(Qt.TextElideMode.ElideNone)
    g.setResizeMode(QListWidget.ResizeMode.Adjust)
    g.setMovement(QListWidget.Movement.Static)
    g.setWordWrap(True)
    g.setUniformItemSizes(False)  # uniform sizes clipped 2-line names
    return g


CALM_NOTE = "Back up your music first. If it ever gets stuck, see How to install, If it gets stuck."


class MainWindow(QMainWindow):
    TABS = ["Home Icons", "Clock Faces", "Wallpapers"]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Nano 6 Theme Studio")
        self.resize(1180, 740)
        self.setStyleSheet(DARK_QSS)
        self.fw: LoadedFirmware | None = None
        self.proj: ThemeProject | None = None
        self.cat = None
        self.sel = None  # ("app", HomeApp) | ("face", ClockFace, part_id) | ("wall", (name,id,thumb)) | ("img", id)
        self.face: C.ClockFace | None = None
        self._build_menu()
        self._build_ui()
        self._set_step(1)

    # ---------- layout ----------
    def _build_menu(self):
        m = self.menuBar()
        f = m.addMenu("&File")
        f.addAction("Open firmware (.ipsw)…", self.open_ipsw)
        f.addAction("Open theme project…", self.load_project)
        f.addAction("Save theme project…", self.save_project)
        f.addSeparator()
        f.addAction("Export…", self.export_dialog)
        f.addSeparator()
        f.addAction("Quit", self.close)
        t = m.addMenu("&Tools")
        t.addAction("AI prompt…", self.ai_prompts)
        f.addAction("Export themed firmware (.ipsw)…", lambda: self._export_ipsw())
        t.addAction("How to install on the iPod…", lambda: InstallWizard(self).exec())
        m.addMenu("&Help").addAction("Credits…", lambda: CreditsDialog(self).exec())

    def _build_ui(self):
        root = QWidget()
        v = QVBoxLayout(root)
        v.setContentsMargins(12, 8, 12, 8)
        # step bar
        steps = QHBoxLayout()
        self.step_btns = []
        for _n, (txt, fn) in enumerate(
            [
                ("1  Open firmware", self.open_ipsw),
                ("2  Customize", lambda: None),
                ("3  Export", self.export_dialog),
            ],
            1,
        ):
            b = QPushButton(txt)
            b.setCheckable(True)
            b.clicked.connect(fn)
            b.setMinimumHeight(34)
            steps.addWidget(b)
            self.step_btns.append(b)
        v.addLayout(steps)
        self.stack = QStackedWidget()
        v.addWidget(self.stack, 1)
        # welcome page
        wel = QWidget()
        wl = QVBoxLayout(wel)
        wl.addStretch()
        t = QLabel(
            "<h2>Nano 6 Theme Studio</h2>Open your own stock iPod nano 6G firmware (.ipsw) to start.<br>"
            "Nothing is flashed. You export a theme and install it with ipod_theme."
        )
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        wl.addWidget(t)
        b = QPushButton("Open firmware (.ipsw)…")
        b.setObjectName("primary")
        b.setMinimumHeight(44)
        b.clicked.connect(self.open_ipsw)
        wl.addWidget(b, 0, Qt.AlignmentFlag.AlignHCenter)
        wl.addStretch()
        self.stack.addWidget(wel)
        # editor page
        ed = QWidget()
        h = QHBoxLayout(ed)
        h.setContentsMargins(0, 0, 0, 0)
        left = QVBoxLayout()
        self.tabs = QTabWidget()
        self.tabs.setFixedWidth(344)
        self.home_grid, self.clock_grid, self.wallpaper_grid, self.all_images_grid = (
            _grid(),
            _grid(),
            _grid(),
            _grid(),
        )
        for g, name in (
            (self.home_grid, "Home Icons"),
            (self.clock_grid, "Clock Faces"),
            (self.wallpaper_grid, "Wallpapers"),
        ):
            self.tabs.addTab(g, name)
            g.currentItemChanged.connect(self._on_pick)
        self.all_images_grid.currentItemChanged.connect(self._on_pick)
        self.tabs.currentChanged.connect(self._on_tab)
        left.addWidget(self.tabs, 1)
        self.recolour_all_button = QPushButton("Recolour all home icons…")
        self.recolour_all_button.clicked.connect(self.recolour_all_icons)
        left.addWidget(self.recolour_all_button)
        self.ai_button = QPushButton("AI prompt…")
        self.ai_button.clicked.connect(self.ai_prompts)
        self.ai_button.setToolTip(
            "Prompt for an AI image tool (icons, backgrounds, watch face) and import the result"
        )
        left.addWidget(self.ai_button)
        self.adv = QCheckBox("Advanced: all images")
        self.adv.toggled.connect(self._toggle_adv)
        left.addWidget(self.adv)
        h.addLayout(left)
        # centre
        mid = QVBoxLayout()
        self.preview = DevicePreview()
        mid.addWidget(self.preview, 1)
        row = QHBoxLayout()
        self.prev_button = QPushButton("◀")
        self.next_button = QPushButton("▶")
        self.prev_button.clicked.connect(lambda: self.preview.go(self.preview.page - 1))
        self.next_button.clicked.connect(lambda: self.preview.go(self.preview.page + 1))
        self.view = QComboBox()
        self.view.addItems(["Home – large icons", "Home – small icons (2×2)", "Clock"])
        self.view.currentIndexChanged.connect(self._on_view)
        self.page_lbl = QLabel("")
        self.preview.pageChanged.connect(lambda p: self._update_page_lbl())
        for w in (self.prev_button, self.view, self.page_lbl, self.next_button):
            row.addWidget(w)
        mid.addLayout(row)
        self.overlay_toggle = QCheckBox("Show clock hands")
        self.overlay_toggle.setChecked(True)
        self.overlay_toggle.setToolTip(
            "Tinted: where this face's hands turn (about the screen centre)"
        )
        self.overlay_toggle.toggled.connect(
            lambda on: (setattr(self.preview, "show_overlay", on), self.preview.refresh())
        )
        mid.addWidget(self.overlay_toggle)

        h.addLayout(mid, 1)
        # right context panel
        panel = QFrame()
        panel.setFixedWidth(250)
        pr = QVBoxLayout(panel)
        self.detail_title = QLabel("Select an item")
        self.detail_title.setStyleSheet("font-size:16px;font-weight:600")
        self.detail_image = QLabel()
        self.detail_image.setFixedSize(220, 220)
        self.detail_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail_image.setStyleSheet("background:#121316;border-radius:8px")
        self.detail_info = QLabel("")
        self.detail_info.setObjectName("hint")
        self.detail_info.setWordWrap(True)
        self.parts = QListWidget()
        self.parts.setViewMode(QListWidget.ViewMode.IconMode)
        self.parts.setIconSize(QSize(40, 40))
        self.parts.setGridSize(QSize(56, 64))
        self.parts.setMaximumHeight(140)
        self.parts.setMovement(QListWidget.Movement.Static)
        self.parts.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.parts.currentItemChanged.connect(self._on_part)
        self.replace_button = QPushButton("Replace…")
        self.replace_button.setObjectName("primary")
        self.edit_button = QPushButton("Edit framing…")
        self.revert_button = QPushButton("Revert")
        self.replace_button.clicked.connect(self.replace_selected)
        self.edit_button.clicked.connect(self.edit_selected)
        self.revert_button.clicked.connect(self.revert_selected)
        for w in (
            self.detail_title,
            self.detail_image,
            self.detail_info,
            self.parts,
            self.replace_button,
            self.edit_button,
            self.revert_button,
        ):
            pr.addWidget(w)
        pr.addStretch()
        h.addWidget(panel)
        self.stack.addWidget(ed)
        self.setCentralWidget(root)
        self._enable_ctx(False)

    def _set_step(self, n):
        for k, b in enumerate(self.step_btns, 1):
            b.setChecked(k == n)
            b.setEnabled(k == 1 or self.proj is not None)
        self.stack.setCurrentIndex(0 if self.proj is None else 1)

    def _enable_ctx(self, on):
        for b in (self.replace_button, self.edit_button, self.revert_button):
            b.setEnabled(on)

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        from nano6studio.core import session

        session.cleanup()
        super().closeEvent(event)

    # ---------- loading ----------
    def open_ipsw(self, path: str | None = None):
        if not path:
            path, _ = QFileDialog.getOpenFileName(
                self, "Open iPod nano 6G firmware", "", "IPSW (*.ipsw);;All (*.*)"
            )
            if not path:
                self._set_step(1 if self.proj is None else 2)
                return
        try:
            self.fw = load_ipsw(Path(path))
        except Exception as e:
            QMessageBox.critical(self, "Could not open firmware", str(e))
            return
        self.proj = make_project(self.fw)
        self._after_load()
        self.statusBar().showMessage(f"Loaded {Path(path).name}")

    def attach(self, fw: LoadedFirmware, proj: ThemeProject):
        self.fw, self.proj = fw, proj
        self._after_load()

    def _after_load(self):
        self.cat = self.fw.catalog
        self.all_apps = H.order_apps(self.cat["apps"], include_hidden=True)  # tab: every app
        self.apps = H.order_apps(self.cat["apps"], include_hidden=True)  # every app that can appear
        f0 = self.cat["clock_faces"]
        self.face = next(
            (f for f in f0 if f.background == self.proj.clock_id), f0[0] if f0 else None
        )
        self.fill_tabs()
        self._set_step(2)
        self.refresh_preview()

    def fill_tabs(self):
        db = self.proj._db

        def ed(ids) -> bool:
            """True when any of these images was edited (marks the thumbnail)."""
            return any(self.proj.is_manual(i) or i in self.proj.replacements for i in ids)

        for g in (self.home_grid, self.clock_grid, self.wallpaper_grid):
            g.blockSignals(True)
            g.clear()
        for a in self.all_apps:
            it = QListWidgetItem(
                _thumb(db.images[a.large or a.ids[0]].to_pil(), edited=ed(a.ids)), a.name
            )
            it.setToolTip(a.name)
            it.setData(Qt.ItemDataRole.UserRole, ("app", a))
            self.home_grid.addItem(it)
        faces = self.cat["clock_faces"]
        adv = self.adv.isChecked()
        for pos, nums in enumerate(C.picker_entries(len(faces)), 1):
            for v, n in enumerate(nums):
                if v and not adv:
                    continue  # other case-colour variants: Advanced only
                f = faces[n - 1]
                label = f"Face {pos}" + (f" · colour {v + 1}" if len(nums) > 1 and adv else "")
                it = QListWidgetItem(
                    _thumb(
                        db.images[f.preview or f.background].to_pil(),
                        edited=ed([i for _, i in f.parts]),
                    ),
                    label,
                )
                tip = f"Clock Face picker position {pos} on the iPod (app face #{n})"
                if len(nums) > 1:
                    tip += f". Matches the iPod's case colour: {len(nums)} colour variants (Advanced shows all)"
                it.setToolTip(tip)
                it.setData(Qt.ItemDataRole.UserRole, ("face", f))
                self.clock_grid.addItem(it)
        for w in self.cat["wallpapers"]:
            it = QListWidgetItem(_thumb(db.images[w[1]].to_pil(), edited=ed([w[1]])), w[0])
            it.setData(Qt.ItemDataRole.UserRole, ("wall", w))
            self.wallpaper_grid.addItem(it)
        for g in (self.home_grid, self.clock_grid, self.wallpaper_grid):
            g.blockSignals(False)
        if self.adv.isChecked():
            self._fill_all()

    def _fill_all(self):
        db = self.proj._db
        self.all_images_grid.clear()
        for i in self.cat["other"]:
            im = db.images[i]
            it = QListWidgetItem(
                _thumb(im.to_pil(), 48), f"{i & 0xFFFF:04x}\n{im.width}×{im.height}"
            )
            it.setData(Qt.ItemDataRole.UserRole, ("img", i))
            self.all_images_grid.addItem(it)

    def select_face(self, face_no: int):
        """Select app face #face_no in the Clock Faces tab (helper for tests / self-test)."""
        self.tabs.setCurrentWidget(self.clock_grid)
        for k in range(self.clock_grid.count()):
            if (
                self.clock_grid.item(k).data(Qt.ItemDataRole.UserRole)[1].name
                == f"Clock face {face_no}"
            ):
                self.clock_grid.setCurrentRow(k)
                return True
        if not self.adv.isChecked():  # a hidden colour variant: show them all
            self.adv.setChecked(True)
            return self.select_face(face_no)
        return False

    def _toggle_adv(self, on):
        if self.proj:
            cur = self.tabs.currentIndex()
            self.fill_tabs()
            self.tabs.setCurrentIndex(cur)
        idx = self.tabs.indexOf(self.all_images_grid)
        if on and idx < 0 and self.proj:
            self._fill_all()
            self.tabs.addTab(self.all_images_grid, "All images")
            self.tabs.setCurrentWidget(self.all_images_grid)
        elif not on and idx >= 0:
            self.tabs.removeTab(idx)

    # ---------- selection ----------
    def _on_tab(self, idx):
        w = self.tabs.widget(idx)
        if hasattr(self, "recolour_all_button"):
            self.recolour_all_button.setVisible(w is self.home_grid)
        if w is self.clock_grid:
            self.view.setCurrentIndex(2)
        elif self.view.currentIndex() == 2:
            self.view.setCurrentIndex(0)

    def _on_view(self, i):
        if hasattr(self, "overlay_toggle"):
            self.overlay_toggle.setVisible(i == 2)
        self.preview.set_mode("clock" if i == 2 else "home", small=(i == 1) if i < 2 else None)
        self._update_page_lbl()

    def _update_page_lbl(self):
        self.page_lbl.setText(
            f"page {self.preview.page + 1}/{self.preview.pages()}"
            if self.preview.mode == "home"
            else ""
        )

    def _on_pick(self, cur, _prev=None):
        if cur is None or self.proj is None:
            return
        data = cur.data(Qt.ItemDataRole.UserRole)
        kind = data[0]
        self.parts.clear()
        self.parts.setVisible(kind == "face")
        db = self.proj._db
        if kind == "app":
            a = data[1]
            self.sel = ("app", a, None)
            self.preview.show_app(a.name)
            self._show(
                a.name,
                db.images[a.large or a.ids[0]].to_pil(),
                f"{len(a.ids)} bitmaps (large, small, list) are written together at their native sizes.",
            )
        elif kind == "face":
            f = data[1]
            self.face = f
            self.proj.clock_id = f.background
            self.parts.blockSignals(True)
            bgs = f.backgrounds()
            primary_row = 0
            static = C.static_glyphs(db, f) | set(H.face_thumbnails(f))
            hl = H.hand_labels(db, f)
            for role, i in f.parts:
                if i in static or role == "Preview":
                    continue  # digit/date glyphs (static) and the 79x79 picker thumbnail (auto-generated)
                if role == "Background" and i != f.background:
                    continue  # extra copies are edited together with the main one
                label = hl.get(i, role.split()[0])
                tip = f"{hl.get(i, role)} · {db.images[i].width}×{db.images[i].height}"
                if role == "Background" and len(bgs) > 1:
                    label = f"Background ×{len(bgs)}"
                    tip += f" · {len(bgs)} copies, all replaced together"
                if i == f.background:
                    primary_row = self.parts.count()
                it = QListWidgetItem(_thumb(db.images[i].to_pil(), 40), label)
                it.setData(Qt.ItemDataRole.UserRole, i)
                it.setToolTip(tip)
                self.parts.addItem(it)
            self.parts.blockSignals(False)
            self.sel = ("face", f, f.background)
            if f.background:
                self.parts.setCurrentRow(primary_row)
            self.view.setCurrentIndex(2)
            self.refresh_preview()
            self._show_part()
        elif kind == "wall":
            w = data[1]
            self.sel = ("wall", w, w[1])
            self.proj.wallpaper_id = w[1]
            if self.view.currentIndex() == 2:
                self.view.setCurrentIndex(0)
            self.refresh_preview()
            self._show(w[0], db.images[w[1]].to_pil(), "240×240 home-screen wallpaper.")
        else:
            i = data[1]
            self.sel = ("img", None, i)
            im = db.images[i]
            self._show(
                f"Image {i:08x}", im.to_pil(), f"{im.width}×{im.height} · format {im.fmt:04x}"
            )
        self._enable_ctx(True)

    def _on_part(self, cur, _p=None):
        if cur is None or not self.sel or self.sel[0] != "face":
            return
        self.sel = ("face", self.sel[1], cur.data(Qt.ItemDataRole.UserRole))
        self._show_part()

    def _show_part(self):
        f, i = self.sel[1], self.sel[2]
        if i is None:
            return
        im = self.proj._db.images[i]
        role = H.hand_labels(self.proj._db, f).get(i) or next((r for r, j in f.parts if j == i), "")
        self._show(f"{f.name} – {role}", im.to_pil(), f"{im.width}×{im.height}. Pick a part below.")

    def _show(self, title, im, info):
        self.detail_title.setText(title)
        self.detail_info.setText(info)
        im = im.convert("RGBA").copy()
        im.thumbnail((210, 210))
        self.detail_image.setPixmap(pil_to_pixmap(im))

    def recolour_all_icons(self):
        if not self.proj:
            return
        from nano6studio.ui.recolour_all import RecolourAllDialog

        self._recol = RecolourAllDialog(self)
        self._recol.exec()

    def ai_prompts(self):
        if not self.proj:
            self.statusBar().showMessage("Open a firmware first.")
            return
        from nano6studio.ui.ai_dialog import AIQuickDialog

        self._ai = AIQuickDialog(self)
        self._ai.exec()

    def refresh_preview(self):
        if not self.proj:
            return
        self.preview.set_state(self.proj._db, self.apps, self.proj.wallpaper_id, self.face)
        self._update_page_lbl()

    # ---------- editing ----------
    def _target(self):
        """(source image for 'Edit', tw, th, shape, overlay, apply_fn)."""
        kind, obj, iid = self.sel
        db = self.proj._db
        if kind == "app":
            return (
                app_art_from_db(db, obj),
                ART,
                ART,
                "rounded",
                None,
                lambda im: apply_app_art(self.proj, obj, im),
            )
        im = db.images[iid]
        role = next((r for r, j in obj.parts if j == iid), "") if kind == "face" else ""
        overlay = None
        shape = "rect"
        if kind == "face" and role == "Background":
            shape = "clock"
            overlay = H.clock_overlay(db, obj)

        def apply(new, kind=kind, iid=iid, obj=obj, role=role):
            cat = {"face": "clock", "wall": "wallpaper"}.get(kind, "other")
            targets = [iid]
            if kind == "face" and role == "Background":
                targets = [iid] + [
                    j for j in obj.backgrounds() if j != iid
                ]  # every copy of the dial
            if kind == "wall":
                targets = C.wallpaper_copies(iid)  # every copy of the wallpaper
            for t in targets:
                self.proj.apply_replacement(t, new, cat)
            if kind == "face":
                H.sync_face_thumbnail(self.proj, obj)  # 79x79 picker thumbnail, every copy
            if kind == "wall" and obj[2]:
                self.proj.apply_replacement(
                    obj[2], new.resize((79, 79), Image.Resampling.LANCZOS), "wallpaper"
                )

        return im.to_pil(), im.width, im.height, shape, overlay, apply

    def _run_editor(self, src):
        _, tw, th, shape, overlay, apply = self._target()
        dlg = ImageEditorDialog(
            src, tw, th, shape, overlay, f"Edit – {self.detail_title.text()}", self
        )
        self._last_editor = dlg
        if shape == "clock":  # mirror the editor in the live 240x240 preview
            from PySide6.QtCore import QTimer

            t = QTimer(dlg)
            t.setSingleShot(True)
            t.setInterval(80)

            def push():
                self.preview.bg_override = dlg.result_image()
                self.preview.refresh()

            t.timeout.connect(push)
            dlg.live.connect(t.start)
            if self.view.currentIndex() != 2:
                self.view.setCurrentIndex(2)
            push()
        try:
            ok = dlg.exec()
        finally:
            self.preview.bg_override = None
        if ok:
            apply(dlg.result_image())
            self._after_edit()
        else:
            self.preview.refresh()

    def replace_selected(self):
        if not self.sel:
            return
        p, _ = QFileDialog.getOpenFileName(self, "Choose image", "", IMG_FILTER)
        if p:
            self._run_editor(Image.open(p).convert("RGBA"))

    def edit_selected(self):
        if self.sel:
            self._run_editor(self._target()[0])

    def revert_selected(self):
        if not self.sel:
            return
        kind, obj, iid = self.sel
        extra = (
            [j for j in obj.backgrounds() if j != iid]
            if kind == "face" and iid in obj.backgrounds()
            else []
        )
        ids = (
            obj.ids
            if kind == "app"
            else [iid]
            + extra
            + ([obj[2]] if kind == "wall" and obj[2] else [])
            + ([j for j in C.wallpaper_copies(iid) if j != iid] if kind == "wall" else [])
        )
        for i in ids:
            self.proj.revert(i)
        if kind == "face":
            H.sync_face_thumbnail(self.proj, obj)  # stock thumb if nothing else is edited
        self._after_edit()

    def _after_edit(self):
        tab, row = self.tabs.currentIndex(), self.tabs.currentWidget().currentRow()
        sel = self.sel
        self.fill_tabs()
        self.tabs.setCurrentIndex(tab)
        g = self.tabs.currentWidget()
        g.blockSignals(True)
        g.setCurrentRow(row)
        g.blockSignals(False)
        self.sel = sel
        self.refresh_preview()
        if sel[0] == "app":
            self._show(
                sel[1].name,
                self.proj._db.images[sel[1].large or sel[1].ids[0]].to_pil(),
                self.detail_info.text(),
            )
        elif sel[0] == "face":
            self._show_part()

    # ---------- project / export ----------
    def save_project(self):
        if not self.proj:
            return
        p, _ = QFileDialog.getSaveFileName(
            self, "Save theme project", "theme.n6theme", "Theme (*.n6theme)"
        )
        if p:
            self.proj.save_n6theme(Path(p))
            self.statusBar().showMessage(f"Saved {p}")

    def load_project(self, path: str | None = None):
        if not self.fw:
            QMessageBox.information(
                self, "Open theme project", "Open the stock firmware first (step 1)."
            )
            return
        if not path:
            path, _ = QFileDialog.getOpenFileName(
                self, "Open theme project", "", "Theme (*.n6theme)"
            )
            if not path:
                return
        # start from pristine images so projects don't stack
        self.fw = load_ipsw(self.fw.ipsw_path)
        self.proj = ThemeProject.load_n6theme(Path(path), db=self.fw.db)
        self._after_load()

    def export_dialog(self):
        if not self.proj:
            return
        self._set_step(3)
        d = QDialog(self)
        d.setWindowTitle("Export")
        l = QVBoxLayout(d)
        l.addWidget(
            QLabel(
                "Build a ready-to-install firmware from your stock IPSW and your edits.\n"
                "This app never flashes your iPod. Install it with iTunes Shift+Update."
            )
        )
        note = QLabel(CALM_NOTE)
        note.setWordWrap(True)
        note.setStyleSheet("color:#9aa3ad")
        l.addWidget(note)
        b0 = QPushButton("Export themed firmware (.ipsw)")
        b0.setObjectName("primary")
        b0.setMinimumHeight(40)
        b1 = QPushButton("Asset pack (.zip) for ipod_theme")
        b2 = QPushButton("SilverImagesDB.LE.bin only")
        b3 = QPushButton("How to install…")
        b0.clicked.connect(lambda: (d.accept(), self._export_ipsw()))
        b1.clicked.connect(lambda: (d.accept(), self._export_pack()))
        b2.clicked.connect(lambda: (d.accept(), self._export_db()))
        b3.clicked.connect(lambda: InstallWizard(self).exec())
        for b in (b0, b1, b2, b3):
            l.addWidget(b)
        d.exec()
        self._set_step(2)

    def _export_ipsw(self, path: str | None = None):
        from nano6studio.core.firmware_pack import build_themed_ipsw, verify_themed_ipsw

        if not path:
            path, _ = QFileDialog.getSaveFileName(
                self, "Export themed firmware", "iPod_1.2_36B10147_themed.ipsw", "IPSW (*.ipsw)"
            )
            if not path:
                return None
        silver = self.proj._db.rebuild()
        try:
            build_themed_ipsw(self.fw.ipsw_path, silver, Path(path))
            v = verify_themed_ipsw(Path(path), silver)
            if not v["silver_matches"]:
                raise RuntimeError("verification failed: rsrc does not contain the edited images")
        except Exception as e:
            QMessageBox.critical(self, "Export failed", str(e))
            return None
        self.statusBar().showMessage(f"Built and verified {path}")
        if self.isVisible() and not getattr(self, "_headless", False):
            QMessageBox.information(
                self,
                "Themed firmware ready",
                f"Saved {Path(path).name} (validated and verified).\n\nBack up your music first. Then in iTunes: click the "
                "iPod icon, HOLD Shift and click 'Check for Update' (not Restore), choose this file, click Open.\n"
                "The full steps and the recovery steps follow.",
            )
            InstallWizard(self).exec()
        return path

    def _export_pack(self):
        p, _ = QFileDialog.getSaveFileName(
            self, "Export asset pack", "theme_pack.zip", "ZIP (*.zip)"
        )
        if p:
            export_asset_pack(self.proj, Path(p))
            self.statusBar().showMessage(f"Exported {p}")

    def _export_db(self):
        p, _ = QFileDialog.getSaveFileName(
            self, "Export SilverImagesDB", "SilverImagesDB.LE.bin", "BIN (*.bin)"
        )
        if p:
            export_silver_db(self.proj._db, Path(p))
            write_install_guide(Path(p).with_name("FLASH_INSTRUCTIONS.txt"))
            self.statusBar().showMessage(f"Exported {p}")
