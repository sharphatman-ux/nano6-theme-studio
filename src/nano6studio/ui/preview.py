# SPDX-License-Identifier: GPL-3.0-only
# Nano 6 Theme Studio - Copyright (C) 2026 sharphatman-ux and contributors. See LICENSE.
"""Live 240x240 device preview with page swiping (drag or arrows)."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget

from nano6studio.core import home_render as H
from nano6studio.ui.qtutil import pil_to_pixmap


class DevicePreview(QWidget):
    pageChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(300, 300)
        self.db = None
        self.apps: list = []
        self.wall = None
        self.face = None
        self.mode = "home"
        self.small = False
        self.page = 0
        self._drag_x = None
        self._off = 0.0
        self._pm = None
        self.show_overlay = True
        self.bg_override = None  # live image from an open clock-background editor

    def set_state(self, db, apps, wallpaper_id, face):
        self.db, self.apps, self.wall, self.face = db, apps, wallpaper_id, face
        self.page = min(self.page, self.pages() - 1)
        self.refresh()

    def pages(self):
        return H.page_count(self.apps, self.small) if self.mode == "home" else 1

    def set_mode(self, mode=None, small=None):
        if mode is not None:
            self.mode = mode
        if small is not None:
            self.small = small
            self.page = 0
        self.refresh()

    def go(self, page):
        self.page = max(0, min(self.pages() - 1, page))
        self._off = 0
        self.refresh()
        self.pageChanged.emit(self.page)

    def show_app(self, name):
        names = [a.name for a in self.apps]
        if name in names:
            self.mode = "home"
            self.go(names.index(name) // (4 if self.small else 1))

    def render(self):
        if self.db is None:
            return None
        if self.mode == "clock":
            im = H.render_clock(self.db, self.face, self.bg_override)
            if self.show_overlay and self.face:
                im.alpha_composite(H.clock_overlay(self.db, self.face))
            return im
        return H.render_home(self.db, self.wall, self.apps, self.page, self.small, self._off)

    def refresh(self):
        im = self.render()
        self._pm = pil_to_pixmap(im) if im is not None else None
        self.update()

    def screen_rect(self) -> QRectF:
        s = min(self.width(), self.height()) - 40
        s = max(240, (s // 240) * 240) if s >= 240 else s
        return QRectF((self.width() - s) / 2, (self.height() - s) / 2, s, s)

    def mousePressEvent(self, e):
        if self.mode == "home":
            self._drag_x = e.position().x()

    def mouseMoveEvent(self, e):
        if self._drag_x is not None:
            k = 240 / self.screen_rect().width()
            self._off = (e.position().x() - self._drag_x) * k
            self.refresh()

    def mouseReleaseEvent(self, e):
        if self._drag_x is None:
            return
        off = self._off
        self._drag_x = None
        self._off = 0
        if off < -40:
            self.go(self.page + 1)
        elif off > 40:
            self.go(self.page - 1)
        else:
            self.refresh()

    def paintEvent(self, _):
        qp = QPainter(self)
        qp.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.screen_rect()
        body = r.adjusted(-14, -14, 14, 14)
        qp.setPen(Qt.PenStyle.NoPen)
        qp.setBrush(QColor("#2b2d33"))
        qp.drawRoundedRect(body, 22, 22)
        if self._pm is None:
            qp.fillRect(r, QColor("#000"))
            qp.setPen(QColor("#777"))
            qp.drawText(r, Qt.AlignmentFlag.AlignCenter, "No firmware loaded")
            return
        qp.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)  # crisp pixels
        qp.drawPixmap(r, self._pm, QRectF(self._pm.rect()))
