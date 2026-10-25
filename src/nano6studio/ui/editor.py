# SPDX-License-Identifier: GPL-3.0-only
# Nano 6 Theme Studio - Copyright (C) 2026 sharphatman-ux and contributors. See LICENSE.
"""Framing editor: the frame stays fixed and centred; the image moves under it."""

from __future__ import annotations

from PIL import Image, ImageEnhance
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from nano6studio.core.cropper import Placement, initial_placement, render_placement, zoom_about
from nano6studio.core.recolor import MODES as RECOLOUR_MODES
from nano6studio.core.recolor import apply as apply_recolour
from nano6studio.core.recolor import shift_hue
from nano6studio.ui.qtutil import pil_to_pixmap

MARGIN = 56


class FrameCanvas(QWidget):
    """shape: 'rect' | 'rounded' | 'clock'."""

    changed = Signal()
    picked = Signal(int, int)  # source-image pixel under an eyedropper click

    def __init__(
        self,
        src: Image.Image,
        tw: int,
        th: int,
        shape: str = "rect",
        overlay: Image.Image | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setMinimumSize(420, 420)
        self.setMouseTracking(False)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.tw, self.th, self.shape = tw, th, shape
        self.overlay_pm = pil_to_pixmap(overlay) if overlay is not None else None
        self._drag: QPointF | None = None
        self.show_overlay = True
        self.picking = False
        self.set_source(src)

    # ---- model ----
    def set_source(self, src: Image.Image, mode: str = "fill"):
        self.src = src.convert("RGBA")
        self.pm = pil_to_pixmap(self.src)
        self.p = initial_placement(self.src.width, self.src.height, self.tw, self.th, mode)
        self.update()
        self.changed.emit()

    def reset(self, mode: str):
        self.p = initial_placement(self.src.width, self.src.height, self.tw, self.th, mode)
        self.update()
        self.changed.emit()

    def frame_rect(self) -> QRectF:
        d = self.display_scale()
        w, h = self.tw * d, self.th * d
        return QRectF((self.width() - w) / 2, (self.height() - h) / 2, w, h)

    def display_scale(self) -> float:
        return max(
            0.1, min((self.width() - 2 * MARGIN) / self.tw, (self.height() - 2 * MARGIN) / self.th)
        )

    def to_target(self, pt: QPointF):
        f, d = self.frame_rect(), self.display_scale()
        return (pt.x() - f.x()) / d, (pt.y() - f.y()) / d

    def set_zoom(self, scale: float):
        self.p = zoom_about(self.p, scale / self.p.scale, self.tw / 2, self.th / 2)
        self.update()
        self.changed.emit()

    def result(self) -> Image.Image:
        return render_placement(self.src, self.tw, self.th, self.p)

    # ---- interaction ----
    def source_pixel(self, pt: QPointF):
        tx, ty = self.to_target(pt)
        x, y = int((tx - self.p.ox) / self.p.scale), int((ty - self.p.oy) / self.p.scale)
        return max(0, min(self.src.width - 1, x)), max(0, min(self.src.height - 1, y))

    def mousePressEvent(self, e):
        if self.picking and e.button() == Qt.MouseButton.LeftButton:
            self.picking = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self.picked.emit(*self.source_pixel(e.position()))
            return
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag = e.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, e):
        if self._drag is not None:
            d = self.display_scale()
            delta = e.position() - self._drag
            self._drag = e.position()
            self.p = Placement(self.p.scale, self.p.ox + delta.x() / d, self.p.oy + delta.y() / d)
            self.update()
            self.changed.emit()

    def mouseReleaseEvent(self, e):
        self._drag = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def wheelEvent(self, e):
        steps = e.angleDelta().y() / 120.0
        if steps:
            fx, fy = self.to_target(e.position())
            self.p = zoom_about(self.p, 1.1**steps, fx, fy)
            self.update()
            self.changed.emit()

    # ---- painting ----
    def _frame_path(self) -> QPainterPath:
        f = self.frame_rect()
        path = QPainterPath()
        if self.shape == "rounded":
            r = f.width() * 0.18
            path.addRoundedRect(f, r, r)
        else:
            path.addRect(f)
        return path

    def paintEvent(self, _):
        qp = QPainter(self)
        qp.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        qp.setRenderHint(QPainter.RenderHint.Antialiasing)
        qp.fillRect(self.rect(), QColor("#0e0f12"))
        f, d = self.frame_rect(), self.display_scale()
        img_rect = QRectF(
            f.x() + self.p.ox * d,
            f.y() + self.p.oy * d,
            self.src.width * self.p.scale * d,
            self.src.height * self.p.scale * d,
        )
        qp.drawPixmap(img_rect, self.pm, QRectF(self.pm.rect()))
        # dim everything outside the frame
        outside = QPainterPath()
        outside.addRect(QRectF(self.rect()))
        frame = self._frame_path()
        qp.fillPath(outside.subtracted(frame), QColor(0, 0, 0, 175))
        if self.shape == "clock":
            circ = QPainterPath()
            circ.addEllipse(f.adjusted(2, 2, -2, -2))
            qp.fillPath(frame.subtracted(circ), QColor(0, 0, 0, 70))
            qp.setPen(QPen(QColor(255, 255, 255, 120), 1, Qt.PenStyle.DashLine))
            qp.drawEllipse(f.adjusted(2, 2, -2, -2))
        if self.overlay_pm is not None and self.show_overlay:
            qp.drawPixmap(f, self.overlay_pm, QRectF(self.overlay_pm.rect()))
        qp.setPen(QPen(QColor("#3a7afe"), 2))
        qp.drawPath(frame)
        qp.setPen(QColor("#9aa0a6"))
        qp.drawText(
            QRectF(0, f.bottom() + 8, self.width(), 20),
            Qt.AlignmentFlag.AlignHCenter,
            f"{self.tw}×{self.th}  ·  drag to move · wheel to zoom",
        )


class AdjustDialog(QDialog):
    """Colour sliders that preview live on the editor canvas (debounced); Cancel reverts."""

    def __init__(self, vals, parent=None, on_preview=None):
        super().__init__(parent)
        self.setWindowTitle("Adjust colours")
        self._start = dict(vals)
        self._cb = on_preview
        lay = QFormLayout(self)
        self.sliders = {}
        for k in ("Brightness", "Contrast", "Saturation"):
            s = QSlider(Qt.Orientation.Horizontal)
            s.setRange(20, 200)
            s.setValue(int(round(vals.get(k, 1.0) * 100)))
            lay.addRow(k, s)
            self.sliders[k] = s
        s = QSlider(Qt.Orientation.Horizontal)
        s.setRange(-180, 180)
        s.setValue(int(vals.get("Hue", 0)))
        lay.addRow("Hue", s)
        self.sliders["Hue"] = s
        from PySide6.QtCore import QTimer

        self._t = QTimer(self)
        self._t.setSingleShot(True)
        self._t.setInterval(60)
        self._t.timeout.connect(self._fire)
        for s in self.sliders.values():
            s.valueChanged.connect(lambda _=0: self._t.start())
        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        b = QPushButton("Reset")
        bb.addButton(b, QDialogButtonBox.ButtonRole.ResetRole)
        b.clicked.connect(self.reset)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addRow(bb)

    def reset(self):
        for k, s in self.sliders.items():
            s.setValue(0 if k == "Hue" else 100)

    def _fire(self):
        if self._cb:
            self._cb(self.values())

    def values(self):
        return {k: (s.value() if k == "Hue" else s.value() / 100) for k, s in self.sliders.items()}

    def accept(self):
        self._t.stop()
        self._fire()
        super().accept()

    def reject(self):
        self._t.stop()
        if self._cb:
            self._cb(self._start)  # revert the live preview
        super().reject()


class ImageEditorDialog(QDialog):
    live = Signal()  # framing / colours changed: result_image() is new

    def __init__(
        self,
        src: Image.Image,
        tw: int,
        th: int,
        shape: str = "rect",
        overlay: Image.Image | None = None,
        title: str = "Edit",
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(640, 640)
        self.orig = src.convert("RGBA")
        self.adjustments = {"Brightness": 1.0, "Contrast": 1.0, "Saturation": 1.0, "Hue": 0}
        self.recolour = {
            "mode": RECOLOUR_MODES[0],
            "colour": None,
            "strength": 0.8,
            "src": None,
            "tolerance": 40,
            "hue": 0,
        }
        self.rot = 0
        lay = QVBoxLayout(self)
        self.canvas = FrameCanvas(self.orig, tw, th, shape, overlay)
        lay.addWidget(self.canvas, 1)
        row = QHBoxLayout()
        b_fill = QPushButton("Fill")
        b_fit = QPushButton("Fit inside")
        b_fill.clicked.connect(lambda: self.canvas.reset("fill"))
        b_fit.clicked.connect(lambda: self.canvas.reset("fit"))
        row.addWidget(b_fill)
        row.addWidget(b_fit)
        row.addWidget(QLabel("Zoom"))
        self.zoom = QSlider(Qt.Orientation.Horizontal)
        self.zoom.setRange(5, 800)
        self.zoom.valueChanged.connect(self._zoom_slider)
        row.addWidget(self.zoom, 1)
        b_rot = QPushButton("Rotate 90°")
        b_rot.clicked.connect(self._rotate)
        b_adj = QPushButton("Colours…")
        b_adj.clicked.connect(self._adjust)
        row.addWidget(b_rot)
        row.addWidget(b_adj)
        lay.addLayout(row)
        if overlay is not None:
            self.overlay_toggle = QCheckBox("Show clock hands")
            self.overlay_toggle.setChecked(True)
            self.overlay_toggle.setToolTip("Where this face's hands turn (about the screen centre)")
            self.overlay_toggle.toggled.connect(self._toggle_overlay)
            lay.addWidget(self.overlay_toggle)
        lay.addWidget(self._recolour_box())
        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        bb.button(QDialogButtonBox.StandardButton.Ok).setText("Apply")
        bb.button(QDialogButtonBox.StandardButton.Ok).setObjectName("primary")
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self._base_scale = self.canvas.p.scale
        self.canvas.changed.connect(self._sync_slider)
        self.canvas.changed.connect(self.live.emit)
        self._sync_slider()

    # ---- recolour panel (live) ----
    def _recolour_box(self):
        from PySide6.QtCore import QTimer

        box = QGroupBox("Recolour")
        g = QFormLayout(box)
        self.r_mode = QComboBox()
        self.r_mode.addItems(RECOLOUR_MODES)
        g.addRow("Mode", self.r_mode)
        crow = QHBoxLayout()
        self.r_colour = QPushButton("Choose colour…")
        self.r_colour.clicked.connect(self._choose_colour)
        crow.addWidget(self.r_colour)
        self.r_src = QPushButton("Pick from image")
        self.r_src.setToolTip("Eyedropper: then click the image")
        self.r_src.clicked.connect(self._start_pick)
        crow.addWidget(self.r_src)
        g.addRow("Colour", crow)
        self.r_strength = QSlider(Qt.Orientation.Horizontal)
        self.r_strength.setRange(0, 100)
        self.r_strength.setValue(80)
        g.addRow("Strength", self.r_strength)
        self.r_tol = QSlider(Qt.Orientation.Horizontal)
        self.r_tol.setRange(1, 200)
        self.r_tol.setValue(40)
        g.addRow("Tolerance", self.r_tol)
        self.r_hue = QSlider(Qt.Orientation.Horizontal)
        self.r_hue.setRange(-180, 180)
        self.r_hue.setValue(0)
        g.addRow("Hue", self.r_hue)
        b = QPushButton("Reset recolour")
        b.clicked.connect(self._reset_recolour)
        g.addRow(b)
        self._rt = QTimer(self)
        self._rt.setSingleShot(True)
        self._rt.setInterval(60)
        self._rt.timeout.connect(self._recolour_changed)
        for sgl in (
            self.r_mode.currentIndexChanged,
            self.r_strength.valueChanged,
            self.r_tol.valueChanged,
            self.r_hue.valueChanged,
        ):
            sgl.connect(lambda *_: self._rt.start())
        self.r_mode.currentIndexChanged.connect(self._mode_ui)
        self._mode_ui()
        self.canvas.picked.connect(self._picked)
        return box

    def _mode_ui(self, *_):
        m = self.r_mode.currentText()
        self.r_strength.setEnabled(m == RECOLOUR_MODES[0])
        self.r_tol.setEnabled(m == RECOLOUR_MODES[1])
        self.r_src.setEnabled(m == RECOLOUR_MODES[1])
        self.r_hue.setEnabled(m == RECOLOUR_MODES[2])
        self.r_colour.setEnabled(m != RECOLOUR_MODES[2])

    @staticmethod
    def _swatch(btn, rgb, label):
        btn.setText(f"{label} #{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}")
        txt = "#000" if sum(rgb) > 380 else "#fff"
        btn.setStyleSheet(f"background: rgb{tuple(rgb)}; color: {txt}")

    def set_recolour_colour(self, rgb):
        self.recolour["colour"] = tuple(rgb)
        self._swatch(self.r_colour, rgb, "Target")
        self._rt.start()

    def _choose_colour(self):
        from PySide6.QtGui import QColor as _QC

        c = QColorDialog.getColor(
            _QC(*(self.recolour["colour"] or (255, 140, 0))), self, "Target colour"
        )
        if c.isValid():
            self.set_recolour_colour((c.red(), c.green(), c.blue()))

    def _start_pick(self):
        self.canvas.picking = True
        self.canvas.setCursor(Qt.CursorShape.CrossCursor)

    def _picked(self, x, y):
        rgb = self._pre_recolour().convert("RGB").getpixel((x, y))
        self.recolour["src"] = tuple(rgb)
        self._swatch(self.r_src, rgb, "Source")
        if self.recolour["colour"] is None:
            self.set_recolour_colour(rgb)
        self._rt.start()

    def _recolour_changed(self):
        self.recolour.update(
            mode=self.r_mode.currentText(),
            strength=self.r_strength.value() / 100,
            tolerance=self.r_tol.value(),
            hue=self.r_hue.value(),
        )
        self._show_adj(self.adjustments)

    def _reset_recolour(self):
        self.recolour.update(colour=None, src=None)
        self.r_hue.setValue(0)
        self.r_strength.setValue(80)
        self.r_tol.setValue(40)
        self.r_colour.setText("Choose colour…")
        self.r_colour.setStyleSheet("")
        self.r_src.setText("Pick from image")
        self.r_src.setStyleSheet("")
        self._show_adj(self.adjustments)

    def _toggle_overlay(self, on):
        self.canvas.show_overlay = on
        self.canvas.update()

    def _sync_slider(self):
        self.zoom.blockSignals(True)
        self.zoom.setValue(int(round(100 * self.canvas.p.scale / self._base_scale)))
        self.zoom.blockSignals(False)

    def _zoom_slider(self, v):
        self.canvas.set_zoom(self._base_scale * v / 100)

    def _processed(self):
        return apply_recolour(self._pre_recolour(), getattr(self, "recolour", None))

    def _pre_recolour(self):
        im = self.orig.rotate(-self.rot, expand=True) if self.rot else self.orig
        for k, fn in (
            ("Brightness", ImageEnhance.Brightness),
            ("Contrast", ImageEnhance.Contrast),
            ("Saturation", ImageEnhance.Color),
        ):
            if self.adjustments[k] != 1.0:
                im = fn(im).enhance(self.adjustments[k])
        return shift_hue(im, self.adjustments.get("Hue", 0))

    def _rotate(self):
        self.rot = (self.rot + 90) % 360
        self.canvas.set_source(self._processed())
        self._base_scale = self.canvas.p.scale

    def _show_adj(self, vals):
        """Swap the canvas image in place: pan/zoom (placement) stay as they are."""
        self.adjustments = dict(vals)
        p = self.canvas.p
        self.canvas.src = self._processed()
        self.canvas.pm = pil_to_pixmap(self.canvas.src)
        self.canvas.p = p
        self.canvas.update()
        self.live.emit()

    def _adjust(self):
        self._adj_dlg = d = AdjustDialog(self.adjustments, self, on_preview=self._show_adj)
        d.exec()

    def result_image(self) -> Image.Image:
        return self.canvas.result()
