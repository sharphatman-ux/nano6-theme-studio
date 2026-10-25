# SPDX-License-Identifier: GPL-3.0-only
# Nano 6 Theme Studio - Copyright (C) 2026 sharphatman-ux and contributors. See LICENSE.
"""GUI tests: tabs only show their own items; editor frame stays fixed while dragging."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from firmware import require_ipsw  # noqa: E402
from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from nano6studio.core.loader import load_ipsw, make_project
from nano6studio.shots import mouse


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def win(app):
    from nano6studio.ui.main_window import MainWindow

    fw = load_ipsw(require_ipsw())
    w = MainWindow()
    w.resize(1180, 740)
    w.show()
    w.attach(fw, make_project(fw))
    app.processEvents()
    return w


def test_tabs_are_separate(win):
    assert win.tabs.count() == 3
    names = [win.home_grid.item(i).toolTip() for i in range(win.home_grid.count())]
    assert len(names) == 18 and "Music" in names and "Settings" in names
    assert win.clock_grid.count() == 18
    assert win.wallpaper_grid.count() == 24
    win.adv.setChecked(True)
    assert win.tabs.count() == 4 and win.all_images_grid.count() == len(win.cat["other"])
    win.adv.setChecked(False)
    assert win.tabs.count() == 3


def test_selecting_app_swipes_preview(win, app):
    win.tabs.setCurrentWidget(win.home_grid)
    row = [win.home_grid.item(i).toolTip() for i in range(win.home_grid.count())].index("Clock")
    win.home_grid.setCurrentRow(row)
    app.processEvents()
    assert win.preview.mode == "home"
    assert win.preview.apps[win.preview.page].name == "Clock"
    # swipe by drag on the preview
    pv = win.preview
    r = pv.screen_rect()
    p0 = pv.page
    mouse(pv, "press", r.center().x(), r.center().y())
    mouse(pv, "move", r.center().x() - r.width() * 0.4, r.center().y())
    mouse(pv, "release", r.center().x() - r.width() * 0.4, r.center().y())
    assert pv.page == p0 + 1


def test_editor_drag_moves_image_not_frame(win, app):
    from nano6studio.ui.editor import ImageEditorDialog

    win.tabs.setCurrentWidget(win.clock_grid)
    win.clock_grid.setCurrentRow(0)
    app.processEvents()
    src, tw, th, shape, ov, apply = win._target()
    assert (tw, th, shape) == (240, 240, "clock") and ov is not None
    big = Image.new("RGBA", (800, 400), (0, 0, 255, 255))
    big.paste((255, 0, 0, 255), (0, 0, 400, 400))
    dlg = ImageEditorDialog(big, tw, th, shape, ov)
    dlg.resize(640, 640)
    dlg.show()
    app.processEvents()
    c = dlg.canvas
    f0 = c.frame_rect()
    d = c.display_scale()
    p0 = c.p
    assert p0.scale == pytest.approx(240 / 400)  # Fill start
    cx, cy = c.width() / 2, c.height() / 2
    mouse(c, "press", cx, cy)
    for k in range(1, 6):
        mouse(c, "move", cx + 20 * k, cy + 10 * k)
        app.processEvents()
        assert c.frame_rect() == f0  # frame never moves
    mouse(c, "release", cx + 100, cy + 50)
    assert c.p.ox - p0.ox == pytest.approx(100 / d, abs=0.01)
    assert c.p.oy - p0.oy == pytest.approx(50 / d, abs=0.01)
    assert c.p.scale == p0.scale
    # wheel-zoom via slider keeps frame centre over the same source pixel
    before = ((120 - c.p.ox) / c.p.scale, (120 - c.p.oy) / c.p.scale)
    dlg.zoom.setValue(200)
    after = ((120 - c.p.ox) / c.p.scale, (120 - c.p.oy) / c.p.scale)
    assert before == pytest.approx(after) and c.frame_rect() == f0
    out = dlg.result_image()
    assert out.size == (240, 240)
    # dragging right by 100px revealed the left (red) part more: centre pixel colour from source
    sx, sy = after
    exp = (255, 0, 0) if sx < 400 else (0, 0, 255)
    assert out.getpixel((120, 120))[:3] == exp
    # fill/fit buttons reset placement
    c.reset("fit")
    assert c.p.scale == pytest.approx(240 / 800)
    apply(out)
    assert win.proj.is_manual(win.sel[2])
    dlg.close()


def test_all_6g_apps_shown(win):
    names = [win.home_grid.item(i).toolTip() for i in range(win.home_grid.count())]
    assert len(names) == 18 and {"iTunes U", "Audiobooks", "Voice Memos"} <= set(names)
    assert [a.name for a in win.preview.apps] == names
    assert all("\n" not in win.home_grid.item(i).text() for i in range(win.home_grid.count()))


@pytest.fixture()
def fresh(app):
    from nano6studio.ui.main_window import MainWindow

    fw = load_ipsw(require_ipsw())
    w = MainWindow()
    w.resize(1180, 740)
    w.show()
    w.attach(fw, make_project(fw))
    app.processEvents()
    yield w
    w.close()


def _near(p, c, tol):
    return max(abs(a - b) for a, b in zip(p, c)) < tol


def test_every_face_background_edit_updates_preview(fresh, app):
    """Regression (sharphatman-ux, face 11): replacing any face's background must change the live
    preview, the 79x79 thumbnail and every stored copy of that dial."""
    w = fresh
    db = w.proj._db
    w.adv.setChecked(True)
    w.tabs.setCurrentWidget(w.clock_grid)
    n = w.clock_grid.count()
    assert n == 38
    for row in range(n):
        w.clock_grid.setCurrentRow(row)
        app.processEvents()
        kind, face, iid = w.sel
        assert kind == "face" and iid == face.background, f"face {row + 1}: wrong part selected"
        before = w.preview.render().convert("RGB").tobytes()
        colour = ((row * 53) % 200 + 30, 255 - row * 5, (row * 97) % 255)
        _, tw, th, *_rest, apply = w._target()
        apply(Image.new("RGBA", (tw, th), colour + (255,)))
        w._after_edit()
        app.processEvents()
        assert w.sel[2] == iid
        for b in face.backgrounds():
            assert db.images[b].to_pil().convert("RGB").getpixel((120, 4)) == colour, (
                f"face {row + 1}: copy {b:x} not written"
            )
        shown = w.preview.render().convert("RGB")
        assert shown.tobytes() != before, f"face {row + 1}: preview did not change"
        small = shown.resize((60, 60))
        hits = sum(_near(small.getpixel((x, y)), colour, 16) for x in range(60) for y in range(60))
        assert hits >= 20, f"face {row + 1}: new background not visible in preview ({hits})"
        thumb = db.images[face.preview].to_pil().convert("RGB")
        assert (
            sum(_near(thumb.getpixel((x, y)), colour, 40) for x in range(79) for y in range(79))
            >= 20
        ), f"face {row + 1}: thumbnail stale"


def test_hand_edit_updates_preview(fresh, app):
    w = fresh
    w.select_face(11)
    app.processEvents()
    before = w.preview.render().tobytes()
    rows = [r for r in range(w.parts.count()) if w.parts.item(r).text().endswith("hand")]
    assert rows
    w.parts.setCurrentRow(rows[0])
    _, tw, th, *_rest, apply = w._target()
    apply(Image.new("RGBA", (tw, th), (255, 0, 0, 255)))
    w._after_edit()
    app.processEvents()
    assert w.preview.render().tobytes() != before


def test_colour_sliders_preview_live_and_cancel_reverts(app):
    import time

    from nano6studio.ui.editor import AdjustDialog, ImageEditorDialog

    src = Image.new("RGBA", (200, 200), (200, 60, 30, 255))
    dlg = ImageEditorDialog(src, 154, 164)
    dlg.show()
    app.processEvents()
    dlg.canvas.set_zoom(dlg.canvas.p.scale * 1.5)
    p0 = dlg.canvas.p
    before = dlg.result_image().getpixel((77, 82))
    d = AdjustDialog(dlg.adjustments, dlg, on_preview=dlg._show_adj)
    d.show()
    d.sliders["Hue"].setValue(120)
    d.sliders["Brightness"].setValue(150)
    t = time.time()
    while time.time() - t < 1 and dlg.adjustments.get("Hue") != 120:
        app.processEvents()
    assert dlg.adjustments["Hue"] == 120 and dlg.canvas.p == p0  # live, pan/zoom kept
    live = dlg.result_image().getpixel((77, 82))
    assert live != before and live[1] > live[0]  # red-orange -> greenish
    d.reject()
    app.processEvents()
    assert dlg.result_image().getpixel((77, 82)) == before and dlg.canvas.p == p0
    d = AdjustDialog(dlg.adjustments, dlg, on_preview=dlg._show_adj)
    d.sliders["Hue"].setValue(-90)
    d.accept()
    assert dlg.adjustments["Hue"] == -90 and dlg.result_image().getpixel((77, 82)) != before


def test_wallpaper_grid_row1_col3_and_all_copies_written(fresh, app):
    """sharphatman-ux: edited 'row 1, third' in the tab, selected the same spot in Settings; must be
    the same wallpaper, and every stock copy + the Settings thumbnail must change."""
    from nano6studio.core import catalog as C

    w = fresh
    db = w.proj._db
    B = C.BASE
    w.tabs.setCurrentWidget(w.wallpaper_grid)
    app.processEvents()
    rects = [w.wallpaper_grid.visualItemRect(w.wallpaper_grid.item(i)) for i in range(4)]
    assert rects[0].y() == rects[1].y() == rects[2].y() < rects[3].y()  # 3 per row at 344 px
    for row, copies in (
        (2, [0x30F]),
        (0, [0x30D, 0x30C]),
        (7, [0x315, 0x314, 0x316]),
        (16, [0x334, 0x335]),
    ):
        w.wallpaper_grid.setCurrentRow(row)
        app.processEvents()
        kind, obj, iid = w.sel
        assert kind == "wall" and C.wallpaper_copies(iid) == [B + c for c in copies]
        _, tw, th, *_r, apply = w._target()
        col = (10 + row * 9, 200, 90, 255)
        apply(Image.new("RGBA", (tw, th), col))
        w._after_edit()
        app.processEvents()
        for c in copies:
            px = db.images[B + c].to_pil().convert("RGB").getpixel((100, 100))
            assert max(abs(a - b) for a, b in zip(px, col[:3])) <= 16, hex(c)
        tpx = db.images[obj[2]].to_pil().convert("RGB").getpixel((40, 40))
        assert max(abs(a - b) for a, b in zip(tpx, col[:3])) <= 16
        assert w.preview.render().convert("RGB").getpixel((120, 5))[:3] != (0, 0, 0)
    assert w.wallpaper_grid.item(2).data(Qt.ItemDataRole.UserRole)[1][1] == B + 0x30F


def test_open_twice_and_close_leaves_no_scratch_dirs(app, isolated_tempdir):
    from nano6studio.core import session
    from nano6studio.ui.main_window import MainWindow

    window = MainWindow()
    window.open_ipsw(str(require_ipsw()))
    session.session_dir()  # simulate something that needed scratch space
    window.open_ipsw(str(require_ipsw()))
    session.session_dir()
    assert len(list(isolated_tempdir.glob("n6ts_*"))) == 1  # one per session, not per open
    window.close()
    app.processEvents()
    assert list(isolated_tempdir.glob("n6ts_*")) == []
