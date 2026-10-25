# SPDX-License-Identifier: GPL-3.0-only
# Nano 6 Theme Studio - Copyright (C) 2026 sharphatman-ux and contributors. See LICENSE.
"""No-stretch framing crop math for nano assets."""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageEnhance


@dataclass
class CropParams:
    target_w: int
    target_h: int
    mode: str = "fill"  # fill | fit
    zoom: float = 1.0
    pan_x: float = 0.5  # 0..1 center of crop in source
    pan_y: float = 0.5
    rotation: float = 0.0  # degrees
    brightness: float = 1.0
    contrast: float = 1.0
    saturation: float = 1.0
    bg_color: tuple[int, int, int, int] = (0, 0, 0, 255)


def apply_adjustments(im: Image.Image, p: CropParams) -> Image.Image:
    if p.rotation:
        im = im.rotate(p.rotation, expand=True, resample=Image.Resampling.BICUBIC)
    if p.brightness != 1.0:
        im = ImageEnhance.Brightness(im).enhance(p.brightness)
    if p.contrast != 1.0:
        im = ImageEnhance.Contrast(im).enhance(p.contrast)
    if p.saturation != 1.0:
        im = ImageEnhance.Color(im).enhance(p.saturation)
    return im


def framed_crop(src: Image.Image, p: CropParams) -> Image.Image:
    """Return an image exactly target_w x target_h with no stretching of content."""
    im = apply_adjustments(src.convert("RGBA"), p)
    tw, th = p.target_w, p.target_h
    sw, sh = im.size
    if sw == 0 or sh == 0:
        return Image.new("RGBA", (tw, th), p.bg_color)

    if p.mode == "fit":
        # scale so entire image fits inside; letterbox
        scale = min(tw / sw, th / sh) * p.zoom
        nw, nh = max(1, int(sw * scale)), max(1, int(sh * scale))
        resized = im.resize((nw, nh), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (tw, th), p.bg_color)
        # pan within leftover margin
        max_x = tw - nw
        max_y = th - nh
        x = int(max_x * p.pan_x) if max_x > 0 else 0
        y = int(max_y * p.pan_y) if max_y > 0 else 0
        canvas.paste(resized, (x, y), resized)
        return canvas

    # fill: shorter side fills; crop the overhang
    scale = max(tw / sw, th / sh) * p.zoom
    nw, nh = max(1, int(sw * scale)), max(1, int(sh * scale))
    resized = im.resize((nw, nh), Image.Resampling.LANCZOS)
    # crop window of tw x th
    max_x = max(0, nw - tw)
    max_y = max(0, nh - th)
    left = int(max_x * p.pan_x)
    top = int(max_y * p.pan_y)
    return resized.crop((left, top, left + tw, top + th))


def aspect_ok(result: Image.Image, tw: int, th: int) -> bool:
    return result.size == (tw, th)


# ---------------------------------------------------------------------------
# Placement model used by the drag-under-frame editor.
# The output frame is fixed (tw x th). The source image is scaled by `scale`
# (output px per source px) and its top-left sits at (ox, oy) in output px.
# Dragging changes ox/oy; zooming changes scale about a fixed point.
# ---------------------------------------------------------------------------
@dataclass
class Placement:
    scale: float
    ox: float
    oy: float


def initial_placement(sw: int, sh: int, tw: int, th: int, mode: str = "fill") -> Placement:
    s = (max if mode == "fill" else min)(tw / sw, th / sh)
    return Placement(s, (tw - sw * s) / 2, (th - sh * s) / 2)


def zoom_about(
    p: Placement,
    factor: float,
    fx: float,
    fy: float,
    min_scale: float = 1e-3,
    max_scale: float = 64.0,
) -> Placement:
    """Zoom by factor keeping output point (fx, fy) fixed over the same source pixel."""
    ns = min(max(p.scale * factor, min_scale), max_scale)
    k = ns / p.scale
    return Placement(ns, fx - (fx - p.ox) * k, fy - (fy - p.oy) * k)


def render_placement(
    src: Image.Image, tw: int, th: int, p: Placement, bg=(0, 0, 0, 0)
) -> Image.Image:
    """Exact output: affine sample of src under the fixed frame (no stretching)."""
    src = src.convert("RGBA")
    inv = 1.0 / p.scale
    # output (x,y) -> source ((x - ox)/s, (y - oy)/s)
    out = src.transform(
        (tw, th),
        Image.Transform.AFFINE,
        (inv, 0, -p.ox * inv, 0, inv, -p.oy * inv),
        resample=Image.Resampling.BICUBIC if p.scale >= 1 else Image.Resampling.BILINEAR,
        fillcolor=(0, 0, 0, 0),
    )
    if p.scale < 1:  # downscale cleanly: resample via LANCZOS path
        nw, nh = max(1, round(src.width * p.scale)), max(1, round(src.height * p.scale))
        small = src.resize((nw, nh), Image.Resampling.LANCZOS)
        out = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
        out.paste(small, (round(p.ox), round(p.oy)), small)
    canvas = Image.new("RGBA", (tw, th), bg)
    canvas.alpha_composite(out)
    return canvas
