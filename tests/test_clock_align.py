# SPDX-License-Identifier: GPL-3.0-only
# Nano 6 Theme Studio - Copyright (C) 2026 sharphatman-ux and contributors. See LICENSE.
"""Clock hand placement: preview pivots are project data, not firmware fields."""

from __future__ import annotations

import json
import zipfile

from PIL import Image

from nano6studio.core import home_render as H
from nano6studio.core.catalog import ClockFace
from nano6studio.core.project import ThemeProject


def _hand():
    im = Image.new("RGBA", (5, 30), (0, 0, 0, 0))
    for y in range(30):
        im.putpixel((2, y), (0, 255, 0, 255))
    return im


def test_pivot_pixel_stays_on_the_centre_when_rotated():
    hand = Image.new("RGBA", (11, 21), (0, 0, 0, 0))
    hand.putpixel((3, 15), (255, 0, 0, 255))
    for ang in (0, 90, 180, 270):
        out = H.place_hand(hand, ang, (3, 15), (120, 120))
        # Bicubic resampling can move a one-pixel dot by a pixel; the pin stays on centre.
        best = max(
            ((out.getpixel((x, y))[0], x, y) for y in range(110, 131) for x in range(110, 131)),
        )
        assert best[0] > 200 and abs(best[1] - 120) <= 1 and abs(best[2] - 120) <= 1, ang


def test_changing_pivot_or_centre_moves_the_hand():
    hand = _hand()
    pinned = H.place_hand(hand, 0, (2, 20), (120, 120))
    assert pinned.getpixel((120, 112))[1] > 200  # bitmap row 12, eight pixels above the pin
    shifted = H.place_hand(hand, 0, (2, 10), (120, 120))
    assert shifted.getpixel((120, 130))[1] > 200  # bitmap row 20 is now below the centre
    assert pinned.tobytes() != shifted.tobytes()
    off = H.place_hand(hand, 0, (2, 20), (80, 40))
    assert off.getpixel((80, 40))[1] > 200
    assert off.getpixel((120, 120))[3] == 0


def test_clock_align_roundtrip_and_defaults_are_omitted(tmp_path):
    face = ClockFace("Clock face 1", preview=5, parts=[])
    proj = ThemeProject(name="align")
    proj.set_hand_pivot(face, 9, 3, 10, default=(3, 10))
    proj.set_face_centre(face, 120, 120)
    assert proj.clock_align == {}
    proj.set_hand_pivot(face, 9, 1, 4, default=(3, 10))
    proj.set_face_centre(face, 100, 110)
    path = tmp_path / "t.n6theme"
    proj.save_n6theme(path)
    loaded = ThemeProject.load_n6theme(path)
    place = loaded.clock_placement(face)
    assert place.centre == (100, 110)
    assert place.pivots[9] == (1, 4)
    loaded.clear_clock_align(face)
    assert loaded.clock_align == {}
    assert loaded.clock_placement(face).centre == H.DEFAULT_FACE_CENTRE


def test_stock_preview_uses_placement_without_touching_the_database():
    """Needs the stock IPSW. Skipped in CI when NANO6_IPSW is unset."""
    from firmware import stock_silver

    from nano6studio.core import catalog as C
    from nano6studio.core.silverimages import SilverImagesDB

    raw = stock_silver()
    db = SilverImagesDB.parse(raw)
    faces = C.clock_faces(db)
    two = next(f for f in faces if len(f.hands()) == 2)
    plain = H.hands_overlay(db, two.hands())
    explicit = H.hands_overlay(db, two.hands(), placement=H.ClockPlacement())
    assert plain.tobytes() == explicit.tobytes()
    moved = H.ClockPlacement(pivots={two.hands()[0]: (0, 0)})
    assert H.hands_overlay(db, two.hands(), placement=moved).tobytes() != plain.tobytes()
    extra = next(f for f in faces if len(f.hands()) >= 3)
    assert (
        H.hands_overlay(db, extra.hands()).tobytes()
        != H.hands_overlay(db, extra.hands()[:2]).tobytes()
    )
    assert db.rebuild() == raw  # placement is not a SilverImagesDB field


def test_project_without_clock_align_still_loads(tmp_path):
    path = tmp_path / "old.n6theme"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(
            "project.json",
            json.dumps({"name": "old", "version": 1, "edits": {}, "replacements": {}}),
        )
    loaded = ThemeProject.load_n6theme(path)
    face = ClockFace("Clock face 1", preview=7, parts=[])
    assert loaded.clock_align == {}
    assert loaded.clock_placement(face).pivots == {}
    assert loaded.clock_placement(face).centre == (120, 120)
