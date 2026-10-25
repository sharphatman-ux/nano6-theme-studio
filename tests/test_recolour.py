# SPDX-License-Identifier: GPL-3.0-only
"""Recolour tools and the clock framing overlay."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import colorsys
import time

import pytest
from firmware import require_ipsw, stock_silver  # noqa: E402
from PIL import Image
from PySide6.QtWidgets import QApplication

from nano6studio.core import recolor as R


def _grad():
    im = Image.new("RGBA", (64, 64))
    for x in range(64):
        for y in range(64):
            im.putpixel((x, y), (200, 40 + x, 30, 255 if y < 48 else 0))
    return im


def _hue(p):
    return colorsys.rgb_to_hsv(*(c / 255 for c in p[:3]))[0] * 360


def test_tint_keeps_shading_and_alpha():
    im = _grad()
    out = R.tint(im, (0, 120, 255), 1.0)
    a, b = out.getpixel((2, 10)), out.getpixel((60, 10))
    assert 180 < _hue(a) < 240 and 180 < _hue(b) < 240  # now blue
    assert sum(b[:3]) > sum(a[:3])  # shading kept (left darker)
    assert out.getchannel("A").tobytes() == im.getchannel("A").tobytes()
    half = R.tint(im, (0, 120, 255), 0.5).getpixel((30, 10))
    assert half != out.getpixel((30, 10)) and half != im.getpixel((30, 10))


def test_replace_colour_only_hits_matching_pixels():
    im = Image.new("RGBA", (40, 20), (255, 0, 0, 255))
    im.paste((0, 0, 255, 128), (20, 0, 40, 20))
    out = R.replace_colour(im, (255, 0, 0), (0, 200, 0), 30)
    assert out.getpixel((5, 5)) == (0, 200, 0, 255)
    assert out.getpixel((30, 5)) == (0, 0, 255, 128)


def test_hue_shift_visibly_changes_colour():
    im = Image.new("RGBA", (8, 8), (220, 40, 40, 200))
    for deg in (60, 120, -120, 180):
        out = R.shift_hue(im, deg).getpixel((1, 1))
        d = (_hue(out) - _hue(im.getpixel((1, 1)))) % 360
        assert abs(d - deg % 360) < 8 and out[3] == 200


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_editor_recolour_live_eyedropper_and_cancel(app):
    from nano6studio.ui.editor import ImageEditorDialog

    src = Image.new("RGBA", (200, 200), (230, 30, 30, 255))
    src.paste((20, 20, 200, 255), (100, 0, 200, 200))
    dlg = ImageEditorDialog(src, 154, 164)
    dlg.show()
    app.processEvents()
    p0 = dlg.canvas.p
    before = dlg.result_image()
    # Tint
    dlg.r_mode.setCurrentIndex(0)
    dlg.set_recolour_colour((0, 200, 0))
    t = time.time()
    while time.time() - t < 1:
        app.processEvents()
    px = dlg.result_image().getpixel((20, 80))
    assert px[1] > px[0] and dlg.canvas.p == p0
    # Replace with eyedropper on the blue half
    dlg._reset_recolour()
    dlg.r_mode.setCurrentIndex(1)
    f = dlg.canvas.frame_rect()
    d = dlg.canvas.display_scale()
    from PySide6.QtCore import QPointF

    sx, sy = dlg.canvas.source_pixel(QPointF(f.x() + 140 * d, f.y() + 80 * d))
    assert sx >= 100
    dlg._picked(sx, sy)
    dlg.set_recolour_colour((250, 250, 0))
    t = time.time()
    while time.time() - t < 1:
        app.processEvents()
    out = dlg.result_image()
    assert (
        out.getpixel((140, 80))[:3] == (250, 250, 0)
        or sum(abs(a - b) for a, b in zip(out.getpixel((140, 80))[:3], (250, 250, 0))) < 20
    )
    assert out.getpixel((10, 80))[:3] == before.getpixel((10, 80))[:3]  # red untouched
    dlg.reject()  # nothing applied


def test_recolour_all_icons_preview_cancel_and_apply_validates(app):
    from nano6studio.core.loader import load_ipsw, make_project
    from nano6studio.core.validate import check
    from nano6studio.ui.main_window import MainWindow
    from nano6studio.ui.recolour_all import RecolourAllDialog

    fw = load_ipsw(require_ipsw())
    w = MainWindow()
    w.attach(fw, make_project(fw))
    db = w.proj._db
    music = next(a for a in w.all_apps if a.name == "Music")
    stock_px = db.images[music.large].to_pil().convert("RGBA").getpixel((77, 82))
    d = RecolourAllDialog(w)
    d.colour = (0, 90, 255)
    d.preview()
    live = db.images[music.large].to_pil().convert("RGBA").getpixel((77, 82))
    assert live != stock_px and not w.proj.is_manual(music.large)  # previewed, not written
    d.reject()
    assert db.images[music.large].to_pil().convert("RGBA").getpixel((77, 82)) == stock_px
    d = RecolourAllDialog(w)
    d.colour = (0, 90, 255)
    d.accept()
    for a in w.all_apps:
        assert all(w.proj.is_manual(i) for i in a.ids)
    raw = stock_silver()
    assert check(db.rebuild(), raw) == []  # palette formats within limits


def test_clock_overlay_per_face(app):
    from nano6studio.core import catalog as C
    from nano6studio.core import home_render as H
    from nano6studio.core.silverimages import SilverImagesDB

    db = SilverImagesDB.parse(stock_silver())
    faces = C.clock_faces(db)
    for f in faces:
        ov = H.clock_overlay(db, f)
        assert ov.size == (240, 240)
        a = ov.getchannel("A")
        if f.hands():
            assert a.getbbox() is not None, f.name
            assert a.getextrema()[1] < 255  # see-through
    analog = next(f for f in faces if f.hands())
    bb = H.clock_overlay(db, analog).getchannel("A").getbbox()
    assert bb[0] < 120 < bb[2] and bb[1] < 120 < bb[3]  # hands about the centre


def _preview_for(w, app, n):
    w.select_face(n)
    w.tabs.setCurrentWidget(w.clock_grid)
    app.processEvents()
    return w.face


@pytest.mark.parametrize("n", [10, 8])  # 10 = digital, 8 = analog with a digital readout
def test_no_digit_overlay_and_digits_not_editable(app, n):
    from PIL import ImageChops

    from nano6studio.core import catalog as C
    from nano6studio.core import home_render as H
    from nano6studio.core.loader import load_ipsw, make_project
    from nano6studio.ui.main_window import MainWindow

    fw = load_ipsw(require_ipsw())
    w = MainWindow()
    w.attach(fw, make_project(fw))
    w.show()
    w.tabs.setCurrentWidget(w.clock_grid)
    app.processEvents()
    assert w.view.currentIndex() == 2 and w.preview.mode == "clock"
    assert w.overlay_toggle.text() == "Show clock hands" and w.overlay_toggle.isChecked()
    assert not hasattr(H, "_digit_strip")
    f = _preview_for(w, app, n)
    db = w.proj._db
    # digits/date glyphs never offered for editing
    static = C.static_glyphs(db, f)
    assert len(static) >= 10
    listed = {w.parts.item(k).data(256) for k in range(w.parts.count())}
    assert not (listed & static) and f.background in listed
    # overlay = hands only: identical to the bare hands layer (or empty for a hand-less face)
    ov = H.clock_overlay(db, f).getchannel("A")
    if f.hands():
        hands = H.hands_overlay(db, f.hands()).getchannel("A")
        extra = ImageChops.subtract(
            ov.point(lambda v: 255 if v else 0), hands.point(lambda v: 255 if v else 0)
        )
        extra.paste(0, (114, 114, 127, 127))  # centre pivot cross
        assert extra.getbbox() is None
    else:
        assert ov.getbbox() is None
    # replaced background: preview draws no digits (only the flat colour + hands)
    flat = Image.new("RGB", (240, 240), (90, 0, 90))
    w.proj.apply_replacement(f.background, flat, "clock")
    w.refresh_preview()
    w.preview.show_overlay = False
    im = w.preview.render().convert("RGB")
    mask = (
        H.hands_overlay(db, f.hands()).getchannel("A")
        if f.hands()
        else Image.new("L", (240, 240), 0)
    )
    diff = ImageChops.difference(im, Image.new("RGB", (240, 240), (90, 0, 90))).convert("L")
    diff.paste(0, mask=mask.point(lambda v: 255 if v else 0))
    assert diff.point(lambda v: 255 if v > 30 else 0).getbbox() is None


def test_thumbnail_hidden_auto_regenerated_and_reverted(app):
    from nano6studio.core import home_render as H
    from nano6studio.core.loader import load_ipsw, make_project
    from nano6studio.core.validate import check
    from nano6studio.ui.main_window import MainWindow

    fw = load_ipsw(require_ipsw())
    w = MainWindow()
    w.attach(fw, make_project(fw))
    w.show()
    w.tabs.setCurrentWidget(w.clock_grid)
    app.processEvents()
    f = _preview_for(w, app, 1)
    db = w.proj._db
    thumbs = H.face_thumbnails(f)
    assert thumbs
    listed = [w.parts.item(k).data(256) for k in range(w.parts.count())]
    labels = [w.parts.item(k).text() for k in range(w.parts.count())]
    assert not set(thumbs) & set(listed) and "Preview" not in labels
    assert sorted(l.split(" ×")[0] for l in labels) == ["Background", "Hour hand", "Minute hand"]
    assert w.sel[2] == f.background and w.detail_title.text().endswith("Background")
    assert (
        w.detail_image.pixmap() is not None and not w.detail_image.pixmap().isNull()
    )  # 220x220 panel thumb
    stock = {i: db.images[i].to_pil().convert("RGB").tobytes() for i in thumbs}
    # edit the background through the normal apply path
    *_, apply = w._target()
    apply(Image.new("RGB", (240, 240), (0, 160, 0)))
    w._after_edit()
    for i in thumbs:
        px = db.images[i].to_pil().convert("RGB").getpixel((5, 5))
        assert px[1] > 120 and px[0] < 60 and w.proj.is_manual(i)
    assert check(db.rebuild(), stock_silver()) == []
    # revert restores the stock thumbnail
    w.revert_selected()
    for i in thumbs:
        assert i not in w.proj.edits and db.images[i].to_pil().convert("RGB").tobytes() == stock[i]


def test_hand_labels(app):
    from nano6studio.core import catalog as C
    from nano6studio.core import home_render as H
    from nano6studio.core.silverimages import SilverImagesDB

    db = SilverImagesDB.parse(stock_silver())
    F = C.clock_faces(db)
    lab = H.hand_labels(db, F[0])
    assert sorted(lab.values()) == ["Hour hand", "Minute hand"]
    lab = H.hand_labels(db, F[17])
    assert sorted(lab.values()) == ["Hour hand", "Minute hand", "Second hand"]


def test_clock_tab_matches_ipod_picker(app):
    from nano6studio.core import catalog as C
    from nano6studio.core.loader import load_ipsw, make_project
    from nano6studio.ui.main_window import MainWindow

    fw = load_ipsw(require_ipsw())
    w = MainWindow()
    w.attach(fw, make_project(fw))
    ent = C.picker_entries(38)
    assert len(ent) == 18 and sum(map(len, ent)) == 38
    assert [e for e in ent if len(e) > 1] == [
        list(range(3, 9)),
        list(range(11, 17)),
        list(range(21, 27)),
        list(range(27, 33)),
    ]
    assert w.clock_grid.count() == 18
    assert [w.clock_grid.item(k).text() for k in range(18)] == [f"Face {k}" for k in range(1, 19)]
    assert (
        C.picker_position(20) == 10 and C.picker_position(38) == 18 and C.picker_position(25) == 11
    )
    w.adv.setChecked(True)
    assert w.clock_grid.count() == 38
    w.adv.setChecked(False)
    assert w.clock_grid.count() == 18
