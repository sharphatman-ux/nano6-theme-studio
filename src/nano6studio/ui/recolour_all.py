# SPDX-License-Identifier: GPL-3.0-only
# Nano 6 Theme Studio - Copyright (C) 2026 sharphatman-ux and contributors. See LICENSE.
"""Recolour every home icon at once (tint or hue). Live preview; Cancel reverts."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QPushButton,
    QSlider,
)

from nano6studio.core import recolor as R
from nano6studio.core.icons import app_art_from_db, apply_app_art, compose_variant


class RecolourAllDialog(QDialog):
    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.setWindowTitle("Recolour all home icons")
        self.db = win.proj._db
        self.apps = list(win.all_apps)
        self.art = {a.name: app_art_from_db(self.db, a) for a in self.apps}  # current artwork
        self.colour = (255, 140, 0)
        f = QFormLayout(self)
        f.addRow(QLabel("Applies the same recolour to all 18 icons (large and small)."))
        self.mode = QComboBox()
        self.mode.addItems([R.MODES[0], R.MODES[2]])
        f.addRow("Mode", self.mode)
        self.colour_button = QPushButton()
        self._swatch()
        self.colour_button.clicked.connect(self._pick)
        f.addRow("Colour", self.colour_button)
        self.strength = QSlider(Qt.Orientation.Horizontal)
        self.strength.setRange(0, 100)
        self.strength.setValue(80)
        f.addRow("Strength", self.strength)
        self.hue = QSlider(Qt.Orientation.Horizontal)
        self.hue.setRange(-180, 180)
        f.addRow("Hue", self.hue)
        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        bb.button(QDialogButtonBox.StandardButton.Ok).setText("Apply to all icons")
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        f.addRow(bb)
        self._t = QTimer(self)
        self._t.setSingleShot(True)
        self._t.setInterval(80)
        self._t.timeout.connect(self.preview)
        for s in (self.mode.currentIndexChanged, self.strength.valueChanged, self.hue.valueChanged):
            s.connect(lambda *_: self._t.start())
        self.preview()

    def _swatch(self):
        c = self.colour
        self.colour_button.setText(f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}")
        self.colour_button.setStyleSheet(
            f"background: rgb{tuple(c)}; color: {'#000' if sum(c) > 380 else '#fff'}"
        )

    def _pick(self):
        c = QColorDialog.getColor(QColor(*self.colour), self, "Icon colour")
        if c.isValid():
            self.colour = (c.red(), c.green(), c.blue())
            self._swatch()
            self._t.start()

    def params(self):
        return {
            "mode": self.mode.currentText(),
            "colour": self.colour,
            "strength": self.strength.value() / 100,
            "hue": self.hue.value(),
        }

    def recoloured(self, name):
        return R.apply(self.art[name], self.params())

    def preview(self):
        """Show the result without encoding: temporary decoded overrides on the bitmaps."""
        for a in self.apps:
            art = self.recoloured(a.name)
            for iid in a.ids:
                im = self.db.images[iid]
                im._pil = compose_variant(self.db, art, (im.width, im.height))
        self.win.preview.refresh()
        self.win.home_grid.viewport().update()

    def _clear(self):
        for a in self.apps:
            for iid in a.ids:
                self.db.images[iid]._pil = None

    def accept(self):
        self._t.stop()
        self._clear()
        for a in self.apps:
            apply_app_art(self.win.proj, a, self.recoloured(a.name))
        super().accept()
        self.win.fill_tabs()
        self.win.refresh_preview()

    def reject(self):
        self._t.stop()
        self._clear()
        self.win.refresh_preview()
        super().reject()
