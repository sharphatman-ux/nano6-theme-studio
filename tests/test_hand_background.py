# SPDX-License-Identifier: GPL-3.0-only
# Nano 6 Theme Studio - Copyright (C) 2026 sharphatman-ux and contributors. See LICENSE.
"""Flat backdrops on imported clock hands are cleared to transparency."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import random

from PIL import Image

from nano6studio.core import ai_prompts as P
from nano6studio.core.silverimages import SilverImage, ensure_alpha_format


def _hand_on(bg, size=(80, 100), bar=(34, 16, 46, 88), ink=(230, 230, 230, 255)):
    im = Image.new("RGBA", size, bg)
    im.paste(ink, bar)
    return im


def test_clears_white_black_and_green_backdrops():
    white = P.clear_flat_background(_hand_on((255, 255, 255, 255), ink=(40, 40, 40, 255)))
    assert white.getpixel((0, 0))[3] == 0
    assert white.getpixel((40, 40))[:3] == (40, 40, 40)

    black = P.clear_flat_background(_hand_on((0, 0, 0, 255), ink=(240, 40, 40, 255)))
    assert black.getpixel((0, 0))[3] == 0
    assert black.getpixel((40, 40))[:3] == (240, 40, 40)

    rng = random.Random(1)
    green = _hand_on((0, 0, 0, 0))
    px = green.load()
    for y in range(green.height):
        for x in range(green.width):
            j = rng.randint(-12, 12)
            px[x, y] = (10 + j, 170 + j, 40, 255)
    for y in range(16, 88):
        for x in range(34, 46):
            px[x, y] = (230, 230, 230, 255)
    cut = P.clear_flat_background(green)
    assert cut.getpixel((1, 1))[3] == 0
    assert cut.getpixel((40, 40))[3] == 255


def test_clears_an_inset_flat_mat_and_keeps_the_hand():
    im = Image.new("RGBA", (90, 120), (0, 180, 40, 255))
    im.paste((250, 250, 250, 255), (8, 8, 82, 112))
    im.paste((20, 20, 20, 255), (40, 12, 52, 100))
    cut = P.clear_flat_background(im)
    assert cut.getpixel((0, 0))[3] == 0
    assert cut.getpixel((12, 20))[3] == 0  # the white mat
    assert cut.getpixel((46, 50))[:3] == (20, 20, 20)
    assert cut.getpixel((46, 50))[3] == 255


def test_leaves_a_nonuniform_picture_and_an_already_keyed_hand():
    im = Image.new("RGBA", (40, 40), (0, 0, 0, 255))
    px = im.load()
    for y in range(40):
        for x in range(40):
            px[x, y] = (255, 0, 0, 255) if x < 20 else (0, 0, 255, 255)
    px[20, 20] = (0, 255, 0, 255)
    assert P.clear_flat_background(im).getpixel((0, 0))[3] == 255

    keyed = Image.new("RGBA", (30, 40), (0, 0, 0, 0))
    keyed.putpixel((15, 20), (255, 255, 255, 255))
    out = P.clear_flat_background(keyed)
    assert out.getpixel((0, 0))[3] == 0
    assert out.getpixel((15, 20))[3] == 255


def test_bgra_encoding_keeps_cleared_pixels_transparent():
    slot = SilverImage(
        image_id=1,
        fmt=0x0565,
        bpp=0x10,
        stride=4,
        width=2,
        height=2,
        raw_payload=b"\x00" * 8,
        header32=b"\x00" * 32,
    )
    ensure_alpha_format(slot)
    im = Image.new("RGBA", (2, 2), (0, 0, 0, 0))
    im.putpixel((0, 0), (10, 20, 30, 255))
    slot.set_pil(im)
    out = slot.to_pil()
    assert slot.fmt == 0x1888
    assert out.getpixel((0, 0))[3] == 255
    assert out.getpixel((1, 1))[3] == 0

    kept = SilverImage(
        image_id=2,
        fmt=0x1888,
        bpp=0x20,
        stride=8,
        width=2,
        height=2,
        raw_payload=b"",
        header32=b"",
    )
    ensure_alpha_format(kept)
    assert kept.fmt == 0x1888


def test_hand_editor_clears_backdrop_and_uncheck_restores():
    from PySide6.QtWidgets import QApplication

    from nano6studio.ui.editor import ImageEditorDialog

    app = QApplication.instance() or QApplication([])
    src = _hand_on((0, 170, 40, 255), size=(60, 90), bar=(24, 8, 36, 80), ink=(240, 240, 240, 255))
    dlg = ImageEditorDialog(src, 34, 148, clear_background=True)
    try:
        assert dlg.clear_bg.isChecked()
        assert dlg.orig.getpixel((0, 0))[3] == 0
        assert dlg.orig.getpixel((30, 40))[3] == 255
        framed = dlg.result_image()
        assert framed.mode == "RGBA" and framed.getchannel("A").getextrema()[0] == 0
        dlg.clear_bg.setChecked(False)
        app.processEvents()
        assert dlg.orig.getpixel((0, 0))[3] == 255
        assert dlg.result_image().getchannel("A").getextrema()[0] == 255
    finally:
        dlg.close()
        app.processEvents()
