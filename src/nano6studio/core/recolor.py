# SPDX-License-Identifier: GPL-3.0-only
# Nano 6 Theme Studio - Copyright (C) 2026 sharphatman-ux and contributors. See LICENSE.
"""Recolour operations (Pillow only). All keep the alpha channel untouched."""

from __future__ import annotations

from PIL import Image, ImageChops, ImageOps

RGB = tuple[int, int, int]
MODES = ("Tint / Colourize", "Replace colour", "Hue shift")


def _split(im):
    im = im.convert("RGBA")
    return im.convert("RGB"), im.getchannel("A")


def tint(im: Image.Image, colour: RGB, strength: float = 1.0) -> Image.Image:
    """Recolour to `colour` keeping the shading: dark stays dark, highlights stay light."""
    rgb, a = _split(im)
    col = ImageOps.colorize(
        rgb.convert("L"), black=(0, 0, 0), mid=tuple(colour), white=(255, 255, 255)
    )
    out = Image.blend(rgb, col, max(0.0, min(1.0, strength))).convert("RGBA")
    out.putalpha(a)
    return out


def replace_colour(im: Image.Image, src: RGB, dst: RGB, tolerance: int = 40) -> Image.Image:
    """Pixels within `tolerance` of `src` move to `dst` (same offset, so shading survives),
    with a soft edge over the last third of the tolerance."""
    rgb, a = _split(im)
    d = ImageChops.difference(rgb, Image.new("RGB", rgb.size, tuple(src)))
    r, g, b = d.split()
    dist = ImageChops.lighter(ImageChops.lighter(r, g), b)
    tol = max(1, int(tolerance))
    soft = max(1, tol // 3)
    mask = dist.point(
        lambda v: 255 if v <= tol - soft else (0 if v >= tol else int(255 * (tol - v) / soft))
    )
    chans = [
        c.point(lambda v, k=k: max(0, min(255, v + k)))
        for c, k in zip(rgb.split(), (dst[0] - src[0], dst[1] - src[1], dst[2] - src[2]))
    ]
    out = Image.composite(Image.merge("RGB", chans), rgb, mask).convert("RGBA")
    out.putalpha(a)
    return out


def shift_hue(im: Image.Image, deg: int) -> Image.Image:
    """Rotate hue by deg (-180..180)."""
    if not deg:
        return im
    rgb, a = _split(im)
    h, s, v = rgb.convert("HSV").split()
    off = int(round(deg / 360 * 256)) % 256
    out = (
        Image.merge("HSV", (h.point(lambda x: (x + off) % 256), s, v))
        .convert("RGB")
        .convert("RGBA")
    )
    out.putalpha(a)
    return out


def apply(im: Image.Image, p: dict | None) -> Image.Image:
    """p = {mode, colour, strength, src, tolerance, hue}; None/empty = unchanged."""
    if not p or not p.get("on", True):
        return im
    m = p.get("mode", MODES[0])
    if m == MODES[0] and p.get("colour") is not None and p.get("strength", 0) > 0:
        return tint(im, p["colour"], p.get("strength", 1.0))
    if m == MODES[1] and p.get("src") is not None and p.get("colour") is not None:
        return replace_colour(im, p["src"], p["colour"], p.get("tolerance", 40))
    if m == MODES[2]:
        return shift_hue(im, int(p.get("hue", 0)))
    return im
