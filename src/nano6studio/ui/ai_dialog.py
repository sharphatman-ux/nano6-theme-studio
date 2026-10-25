# SPDX-License-Identifier: GPL-3.0-only
# Nano 6 Theme Studio - Copyright (C) 2026 sharphatman-ux and contributors. See LICENSE.
"""Small dialog: build copy-ready prompts for any AI image tool, then import the results."""

from __future__ import annotations

from PIL import Image
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from nano6studio.core import ai_prompts as P
from nano6studio.core import home_render as H
from nano6studio.core.icons import ART, apply_app_art


class AIQuickDialog(QDialog):
    """Quick AI prompt: pick one of 4 options, set a Style, Copy prompt, Import."""

    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.setWindowTitle("AI prompt")
        self.resize(520, 430)
        self.setAcceptDrops(True)
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QButtonGroup, QRadioButton

        self._st = QSettings("Nano6ThemeStudio", "Nano6ThemeStudio")
        v = QVBoxLayout(self)
        self.group = QButtonGroup(self)
        self.radios = []
        for k, o in enumerate(P.OPTIONS):
            r = QRadioButton(f"{o}  –  {P.OPTION_HINTS[o]}")
            r.setStyleSheet("font-size:14px;padding:5px")
            self.group.addButton(r, k)
            self.radios.append(r)
            v.addWidget(r)
        last = int(self._st.value("ai_option", 1) or 1)
        self.radios[min(max(last, 0), 3)].setChecked(True)
        h = QHBoxLayout()
        v.addLayout(h)
        h.addWidget(QLabel("Style"))
        self.style = QLineEdit(str(self._st.value("ai_style", "") or ""))
        self.style.setPlaceholderText("e.g. rockabilly tattoo flash")
        h.addWidget(self.style, 1)
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        v.addWidget(self.text, 1)
        b = QHBoxLayout()
        v.addLayout(b)
        self.copy_button = QPushButton("Copy prompt")
        self.copy_button.setObjectName("primary")
        b.addWidget(self.copy_button)
        self.import_button = QPushButton("Import…")
        b.addWidget(self.import_button)
        self.status = QLabel(
            "Copy the prompt into your AI tool, then import its sheet or images (or drop them here)."
        )
        self.status.setObjectName("hint")
        self.status.setWordWrap(True)
        v.addWidget(self.status)
        self.group.idToggled.connect(lambda *_: self.rebuild())
        self.style.textChanged.connect(self.rebuild)
        self.copy_button.clicked.connect(self.copy)
        self.import_button.clicked.connect(lambda: self.import_files())
        self._helper = AIPromptDialog(win)  # slot appliers / review (not shown)
        self.rebuild()

    # ---- state ----
    def option(self) -> str:
        return P.OPTIONS[max(0, self.group.checkedId())]

    def set_option(self, name: str):
        self.radios[P.OPTIONS.index(name)].setChecked(True)

    def apps(self):
        return [a.name for a in self.win.all_apps]

    def face(self):
        """Selected clock face, else the Clock Faces tab's selection, else Face 1."""
        w = self.win
        if w.sel and w.sel[0] == "face":
            return w.sel[1]
        it = w.clock_grid.currentItem()
        if it is not None:
            return it.data(256)[1]
        return w.cat["clock_faces"][0]

    def slots(self):
        return P.option_slots(self.option(), self.apps())

    def prompt(self) -> str:
        return P.option_prompt(self.option(), self.apps(), self.style.text())

    def rebuild(self, *_):
        self._st.setValue("ai_style", self.style.text())
        self._st.setValue("ai_option", max(0, self.group.checkedId()))
        self.text.setPlainText(self.prompt())

    def copy(self):
        QApplication.clipboard().setText(self.prompt())
        self.status.setText("Prompt copied.")

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        if paths:
            self.import_files(paths)

    # ---- import ----
    def match(self, images):
        """[(slot, image)] plus a 'sure' flag. One image for several slots = a sheet: smart tile
        detection first, then the exact grid the prompt asked for; several images = by name/order."""
        slots = self.slots()
        if len(images) == 1 and len(slots) > 1:
            im = images[0][1]
            tiles = P.detect_tiles(im, slots)
            by = {s.name: s for s in slots}
            got = [(by[t.slot], t.image) for t in tiles if t.slot in by and not t.clipped]
            if len(got) == len(slots):
                return got, True
            cols, rows = P.option_grid(self.option(), len(slots))
            cells = P.slice_sheet(im, cols, rows)[: len(slots)]
            sure = abs(im.width / im.height - cols / rows) < 0.06 * cols / rows
            return list(zip(slots, cells)), sure
        pairs = P.assign(images, slots)
        return pairs, len(images) == len(slots)

    def import_files(self, paths=None, review=True):
        if not paths:
            paths, _ = QFileDialog.getOpenFileNames(
                self, "AI sheet or images", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)"
            )
        if not paths:
            return 0
        return self.import_images([(p, Image.open(p).convert("RGBA")) for p in paths], review)

    def import_images(self, images, review=True):
        pairs, sure = self.match(images)
        if not sure and review:
            rev = ImportReviewDialog(self, [(im, s.name, False) for s, im in pairs], self.slots())
            if not rev.exec():
                return 0
            by = {s.name: s for s in self.slots()}
            pairs = [(by[n], im) for n, im in rev.result_pairs() if n in by]
        n = self._apply(pairs)
        self.status.setText(f"Imported {n} image(s). Use 'Edit framing…' on any item to adjust.")
        return n

    def _apply(self, pairs):
        w = self.win
        proj = w.proj
        db = proj._db
        f = self.face()
        out = []
        labels = {v: k for k, v in H.hand_labels(db, f).items()} if f else {}
        rest = []
        for s, im in pairs:
            if s.kind == "hands":
                iid = labels.get(s.name)
                if iid is None:
                    continue  # face without that hand
                im = P.remove_plain_background(im)
                bb = im.getchannel("A").getbbox()
                if bb:
                    im = im.crop(bb)
                t = db.images[iid]
                proj.apply_replacement(iid, P.fit(im, t.width, t.height), "clock")
                out.append(s)
            else:
                rest.append((s, im))
        old = w.face
        w.face = f
        self._helper._face = lambda: f
        n = self._helper._apply(rest) + len(out)
        if out and f:
            H.sync_face_thumbnail(proj, f)
        w.face = old if old is not None else f
        w.fill_tabs()
        w.refresh_preview()
        return n


class AIPromptDialog(QDialog):
    """Advanced sheet / multi-file importer (not shown in the default UI)."""

    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.setWindowTitle("AI prompt builder")
        self.resize(620, 520)
        v = QVBoxLayout(self)
        v.addWidget(
            QLabel(
                "1. Describe your theme, pick what to make, copy the prompt into ChatGPT, Gemini, Grok, Midjourney…"
            )
        )
        self.idea = QLineEdit()
        self.idea.setPlaceholderText("e.g. cyberpunk neon")
        v.addWidget(self.idea)
        r = QHBoxLayout()
        v.addLayout(r)
        self.scope = QComboBox()
        self.scope.addItems(P.SCOPES)
        r.addWidget(self.scope)
        self.icon = QComboBox()
        self.icon.addItems([a.name for a in win.all_apps])
        r.addWidget(self.icon)
        self.mode = QComboBox()
        self.mode.addItems(["One image per prompt", "Icons on one sheet (optional)"])
        r.addWidget(self.mode)
        self.extras = QCheckBox("+ hands")
        r.addWidget(self.extras)
        self.notes = QLabel()
        self.notes.setWordWrap(True)
        self.notes.setObjectName("notes")
        self.notes.setStyleSheet("color:#9aa3ad")
        v.addWidget(self.notes)
        pr = QHBoxLayout()
        v.addLayout(pr)
        pr.addWidget(QLabel("Prompt:"))
        self.which = QComboBox()
        pr.addWidget(self.which, 1)
        self.which.currentIndexChanged.connect(self._show_prompt)
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        v.addWidget(self.text, 1)  # prompt text only
        b = QHBoxLayout()
        v.addLayout(b)
        self.copy_button = QPushButton("Copy prompt")
        self.copy_button.setObjectName("primary")
        b.addWidget(self.copy_button)
        self.import_one_button = QPushButton("Import image for this prompt…")
        b.addWidget(self.import_one_button)
        self.import_button = QPushButton("2. Import AI results / sheet…")
        b.addWidget(self.import_button)
        self.import_one_button.clicked.connect(lambda: self.import_for_current())
        self.setAcceptDrops(True)
        self.status = QLabel("")
        v.addWidget(self.status)
        for w in (
            self.idea.textChanged,
            self.scope.currentIndexChanged,
            self.icon.currentIndexChanged,
            self.mode.currentIndexChanged,
            self.extras.toggled,
        ):
            w.connect(self.rebuild)
        self.copy_button.clicked.connect(self.copy)
        self.import_button.clicked.connect(self.import_files)
        self.rebuild()

    def _face(self):
        return self.win.face or (self.win.cat["clock_faces"][0] if self.win.cat else None)

    def slots(self):
        db = self.win.proj._db
        f = self._face()
        hands = [(db.images[i].width, db.images[i].height) for i in (f.hands() if f else [])]
        return P.slots_for(
            self.scope.currentText(),
            [a.name for a in self.win.all_apps],
            self.icon.currentText(),
            hands,
            None,
            self.extras.isChecked(),
        )

    def rebuild(self):
        self.icon.setVisible(self.scope.currentText() == "Single icon")
        self.extras.setVisible(self.scope.currentText() in ("Clock face", "Everything"))
        self.prompts = P.build_prompts(
            self.idea.text(), self.slots(), self.mode.currentIndex() == 1
        )
        keep = self.which.currentIndex()
        self.which.blockSignals(True)
        self.which.clear()
        self.which.addItems([f"{k}. {t}" for k, (t, *_) in enumerate(self.prompts, 1)])
        self.which.setCurrentIndex(min(max(keep, 0), len(self.prompts) - 1))
        self.which.blockSignals(False)
        n = len(self.prompts)
        self.notes.setText(
            f"{n} short prompts, one image each. Pick one, Copy prompt, paste it into the AI tool, then "
            "use 'Import image for this prompt…' (or drop the file here). Any size works; images are fitted on import."
            if n > 1
            else "Copy prompt, paste it into the AI tool, then import the image (or drop it here)."
        )
        self.which.setVisible(n > 1)
        self._show_prompt()

    def _show_prompt(self, *_):
        i = self.which.currentIndex()
        self.text.setPlainText(self.prompts[i][1] if 0 <= i < len(self.prompts) else "")

    def prompt_text(self) -> str:
        return self.text.toPlainText()

    def copy(self):
        QApplication.clipboard().setText(self.prompt_text())
        self.status.setText(
            f"Prompt {self.which.currentIndex() + 1} of {len(self.prompts)} copied."
        )

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        if len(paths) == 1 and self.current_slots() and len(self.current_slots()) == 1:
            self.import_for_current(paths[0])
        elif paths:
            self.import_files(paths)

    def current_slots(self):
        i = self.which.currentIndex()
        return self.prompts[i][2] if 0 <= i < len(self.prompts) else []

    def import_for_current(self, path=None):
        """One image for the selected prompt: a single slot gets it directly; a sheet prompt
        goes through the normal sheet detection and review."""
        sl = self.current_slots()
        if not sl:
            return 0
        if not path:
            path, _ = QFileDialog.getOpenFileName(
                self,
                f"Image for {self.prompts[self.which.currentIndex()][0]}",
                "",
                "Images (*.png *.jpg *.jpeg *.webp *.bmp)",
            )
        if not path:
            return 0
        im = Image.open(path).convert("RGBA")
        if len(sl) > 1:
            return self.import_files([path])
        n = self._apply([(sl[0], im)])
        self.status.setText(f"Imported into {sl[0].name}. Use 'Edit framing…' to adjust.")
        return n

    def import_files(self, paths=None):
        if not paths:
            paths, _ = QFileDialog.getOpenFileNames(
                self, "AI images", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)"
            )
        if not paths:
            return
        imgs = [(p, Image.open(p).convert("RGBA")) for p in paths]
        rev = ImportReviewDialog(self, self.review_items(imgs), self.all_slots())
        if not rev.exec():
            return
        n = self.import_pairs(rev.result_pairs())
        self.status.setText(
            f"Imported {n} image(s). Select any slot and use 'Edit framing…' to adjust."
        )

    def all_slots(self):
        """Every target a tile may be sent to (independent of the prompt scope)."""
        self._face()
        out = [P.Slot("icon", a.name, P.ICON_GEN, P.ICON_GEN) for a in self.win.all_apps]
        out += [
            P.Slot("face", "Clock face background", P.FACE, P.FACE),
            P.Slot("wallpaper", "Wallpaper", P.FACE, P.FACE),
        ]
        return out

    def review_items(self, images):
        """[(thumbnail image, pre-filled slot name or None, clipped)] for the review dialog."""
        slots = self.all_slots()
        if len(images) == 1:
            tiles = P.detect_tiles(images[0][1], slots)
            if len(tiles) >= 2:
                return [(t.image, t.slot, t.clipped) for t in tiles]
        pairs = P.assign(images, [s for s in self.slots()] or slots)
        return [(im, s.name, False) for s, im in pairs]

    def import_images(self, images):
        """Non-interactive import (tests/self-test): auto assignments, no review."""
        return self.import_pairs([(n, im) for im, n, _ in self.review_items(images) if n])

    def import_pairs(self, pairs):
        by = {s.name: s for s in self.all_slots()}
        return self._apply([(by[n], im) for n, im in pairs if n in by])

    def _apply(self, pairs):
        w = self.win
        proj = w.proj
        db = proj._db
        apps = {a.name: a for a in w.all_apps}
        f = self._face()
        n = 0
        clock = False
        for slot, im in pairs:
            im = (
                P.remove_plain_background(im)
                if slot.kind != "wallpaper" and slot.kind != "face"
                else im
            )
            if slot.kind == "icon":
                apply_app_art(proj, apps[slot.name], P.fit(im, ART, ART))
            elif slot.kind == "face" and f:
                clock = True
                for b in f.backgrounds():
                    proj.apply_replacement(b, P.fit(im, P.FACE, P.FACE), "clock")
            elif slot.kind == "hands" and f:
                clock = True
                ids = f.hands()
                k = int(slot.name.split()[-1]) - 1
                t = db.images[ids[k]]
                proj.apply_replacement(ids[k], P.fit(im, t.width, t.height), "clock")
            elif slot.kind == "wallpaper":
                wid, th = (w.proj.wallpaper_id or w.cat["wallpapers"][0][1], None)
                for _nm, i, t in w.cat["wallpapers"]:
                    if i == wid:
                        th = t
                from nano6studio.core.catalog import wallpaper_copies

                for c in wallpaper_copies(wid):
                    proj.apply_replacement(c, P.fit(im, P.FACE, P.FACE), "wallpaper")
                if th:
                    proj.apply_replacement(th, P.fit(im, 79, 79), "wallpaper")
            n += 1
        if f and clock:
            H.sync_face_thumbnail(proj, f)
        w.fill_tabs()
        w.refresh_preview()
        return n


class ImportReviewDialog(QDialog):
    """Thumbnail per detected tile + a pre-filled slot dropdown; clipped tiles get a badge."""

    def __init__(self, parent, items, slots):
        super().__init__(parent)
        self.setWindowTitle("Review AI import")
        self.resize(760, 560)
        from PySide6.QtWidgets import QGridLayout, QScrollArea, QWidget

        from nano6studio.ui.qtutil import pil_to_pixmap

        v = QVBoxLayout(self)
        v.addWidget(QLabel(f"{len(items)} image(s) found. Check each assignment, then Apply."))
        area = QScrollArea()
        area.setWidgetResizable(True)
        inner = QWidget()
        g = QGridLayout(inner)
        area.setWidget(inner)
        v.addWidget(area, 1)
        self.items = items
        self.combos = []
        names = ["(skip)"] + [s.name for s in slots]
        for k, (im, name, clipped) in enumerate(items):
            box = QVBoxLayout()
            cell = QWidget()
            cell.setLayout(box)
            th = QLabel()
            th.setPixmap(pil_to_pixmap(im.convert("RGBA").resize((88, 88))))
            box.addWidget(th)
            if clipped:
                b = QLabel("⚠ clipped")
                b.setStyleSheet("color:#e0a000;font-weight:bold")
                b.setToolTip("This tile was cut off on the sheet; check it or regenerate it.")
                box.addWidget(b)
            c = QComboBox()
            c.addItems(names)
            c.setCurrentText(name or "(skip)")
            box.addWidget(c)
            self.combos.append(c)
            g.addWidget(cell, k // 6, k % 6)
        b = QHBoxLayout()
        v.addLayout(b)
        ok = QPushButton("Apply")
        ok.setObjectName("primary")
        ok.clicked.connect(self.accept)
        no = QPushButton("Cancel")
        no.clicked.connect(self.reject)
        b.addStretch(1)
        b.addWidget(no)
        b.addWidget(ok)

    def result_pairs(self):
        return [
            (c.currentText(), im)
            for c, (im, _, _) in zip(self.combos, self.items)
            if c.currentText() != "(skip)"
        ]
