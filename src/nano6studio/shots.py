# SPDX-License-Identifier: GPL-3.0-only
# Nano 6 Theme Studio - Copyright (C) 2026 sharphatman-ux and contributors. See LICENSE.
"""Headless self-test + screenshots (used by --selftest and the GUI tests)."""

from __future__ import annotations

import shutil
import traceback
from pathlib import Path

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication


def mouse(w, kind, x, y):
    t = {
        "press": QEvent.Type.MouseButtonPress,
        "move": QEvent.Type.MouseMove,
        "release": QEvent.Type.MouseButtonRelease,
    }[kind]
    btn = Qt.MouseButton.NoButton if kind == "move" else Qt.MouseButton.LeftButton
    ev = QMouseEvent(
        t,
        QPointF(x, y),
        w.mapToGlobal(QPointF(x, y)),
        btn,
        Qt.MouseButton.LeftButton if kind != "release" else Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(w, ev)


def run(ipsw: Path, report: Path, theme: Path = None, shots: Path = None) -> int:
    lines = []
    try:
        from nano6studio.core.fat16 import FatImage
        from nano6studio.core.loader import load_ipsw, make_project
        from nano6studio.core.project import ThemeProject
        from nano6studio.core.rsrc_fs import SILVER_IMAGES

        lines.append(f"mcopy_on_path={shutil.which('mcopy')}")
        fw = load_ipsw(ipsw)
        lines.append(f"images={len(fw.db.images)}")
        fat = fw.fat_bytes
        img = FatImage(fat)
        img.write(SILVER_IMAGES, fw.db.rebuild())
        lines.append(f"fat_roundtrip_identical={img.tobytes() == fat}")
        lines.append(
            f"apps={len(fw.catalog['apps'])} faces={len(fw.catalog['clock_faces'])} "
            f"wallpapers={len(fw.catalog['wallpapers'])} other={len(fw.catalog['other'])}"
        )
        app = QApplication.instance() or QApplication([])
        app.setStyle("Fusion")
        from nano6studio.ui.main_window import MainWindow

        w = MainWindow()
        w.resize(1180, 740)
        w.show()
        app.processEvents()
        if shots:
            shots.mkdir(parents=True, exist_ok=True)
            w.grab().save(str(shots / "00_welcome.png"))
        proj = ThemeProject.load_n6theme(theme, db=fw.db) if theme else make_project(fw)
        w.attach(fw, proj)
        app.processEvents()
        lines.append(f"project={proj.name} edited={len(proj.replacements)}")
        if shots:
            for k, (g, name) in enumerate(
                [
                    (w.home_grid, "home_icons"),
                    (w.clock_grid, "clock_faces"),
                    (w.wallpaper_grid, "wallpapers"),
                ],
                1,
            ):
                w.tabs.setCurrentWidget(g)
                g.setCurrentRow(0 if k != 1 else 1)
                app.processEvents()
                w.grab().save(str(shots / f"0{k}_tab_{name}.png"))
            w.view.setCurrentIndex(1)
            app.processEvents()
            w.grab().save(str(shots / "04_home_small_icons.png"))
            w.view.setCurrentIndex(0)
            w.adv.setChecked(True)
            app.processEvents()
            w.grab().save(str(shots / "05_advanced_all_images.png"))
            w.adv.setChecked(False)
            # editor mid-drag on a clock face background
            w.tabs.setCurrentWidget(w.clock_grid)
            w.clock_grid.setCurrentRow(1)
            app.processEvents()
            from nano6studio.ui.editor import ImageEditorDialog

            src, tw, th, shape, ov, _ = w._target()
            dlg = ImageEditorDialog(src, tw, th, shape, ov, "Edit – clock background", w)
            dlg.resize(640, 640)
            dlg.show()
            app.processEvents()
            c = dlg.canvas
            f0 = c.frame_rect()
            p0 = (c.p.ox, c.p.oy)
            c.set_zoom(c.p.scale * 1.6)
            p0 = (c.p.ox, c.p.oy)
            cx, cy = c.width() / 2, c.height() / 2
            mouse(c, "press", cx, cy)
            for s in range(1, 11):
                mouse(c, "move", cx + 6 * s, cy + 3 * s)
                app.processEvents()
            dlg.grab().save(str(shots / "06_editor_mid_drag.png"))
            mouse(c, "release", cx + 60, cy + 30)
            lines.append(
                f"drag_frame_fixed={c.frame_rect() == f0} moved={(round(c.p.ox - p0[0], 1), round(c.p.oy - p0[1], 1))}"
            )
            dlg.close()
            w.tabs.setCurrentWidget(w.home_grid)
            w.home_grid.setCurrentRow(2)
            app.processEvents()
            lines.append(f"icon_sel={w.sel[0]}:{getattr(w.sel[1], 'name', '')}")
            src, tw, th, shape, ov, _ = w._target()
            d2 = ImageEditorDialog(src, tw, th, shape, ov, "Edit – Radio icon", w)
            d2.resize(640, 640)
            d2.show()
            app.processEvents()
            c2 = d2.canvas
            mouse(c2, "press", 320, 300)
            mouse(c2, "move", 280, 330)
            app.processEvents()
            d2.grab().save(str(shots / "07_editor_icon_mid_drag.png"))
            mouse(c2, "release", 280, 330)
            d2.close()
        # themed IPSW export (same code path as the Export button)
        w._headless = True
        out = report.parent / "selftest_themed.ipsw"
        got = w._export_ipsw(str(out))
        from nano6studio.core.firmware_pack import verify_themed_ipsw

        v = verify_themed_ipsw(out, proj._db.rebuild())
        lines.append(
            f"themed_ipsw={got is not None} sections={','.join(v['sections'])} "
            f"disk_swap={v['disk_swap']} silver_matches={v['silver_matches']}"
        )
        if shots:
            from PySide6.QtCore import QTimer

            def _grab_export():
                for x in app.topLevelWidgets():
                    if x.windowTitle() == "Export" and x.isVisible():
                        x.grab().save(str(shots / "08_export_dialog.png"))
                        x.reject()

            QTimer.singleShot(400, _grab_export)
            w.export_dialog()
        lines.append("RESULT=OK" if v["silver_matches"] else "RESULT=FAIL")
    except Exception:
        lines.append(traceback.format_exc())
        lines.append("RESULT=FAIL")
    report.write_text("\n".join(lines), encoding="utf-8")
    return 0 if lines[-1] == "RESULT=OK" else 1
