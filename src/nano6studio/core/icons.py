# SPDX-License-Identifier: GPL-3.0-only
# Nano 6 Theme Studio - Copyright (C) 2026 sharphatman-ux and contributors. See LICENSE.
"""Write one piece of app artwork into every native bitmap of that app."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image, ImageChops, ImageDraw

from . import catalog as C

if TYPE_CHECKING:
    from nano6studio.core.project import ThemeProject
    from nano6studio.core.silverimages import SilverImagesDB


ART = 256  # editor works on a square artwork canvas


def _mask_for(db: SilverImagesDB, size):
    if size == (154, 164) and C.MASK_LARGE in db.images:
        m = db.images[C.MASK_LARGE].to_pil().getchannel("A")
    elif size == (105, 105) and C.MASK_SMALL in db.images:
        m = db.images[C.MASK_SMALL].to_pil().getchannel("A")
    else:
        m = Image.new("L", size, 0)
        r = max(4, size[0] // 6)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), r, fill=255)
    hi = m.getextrema()[1] or 255  # tap-down masks are semi-transparent: normalise to a shape
    return m.point(lambda v: min(255, v * 255 // hi))


def compose_variant(
    db: SilverImagesDB, art: Image.Image, size, keep_shadow_from: Image.Image = None
) -> Image.Image:
    """Fit square art into the visible rounded square of a native icon bitmap."""
    x0, y0, x1, y1 = C.VISIBLE.get(size, (0, 0) + size)
    w, h = x1 - x0, y1 - y0
    a = art.convert("RGBA").resize((w, h), Image.Resampling.LANCZOS)
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    out.paste(a, (x0, y0), a)
    mask = _mask_for(db, size)
    alpha = ImageChops.multiply(out.getchannel("A"), mask)
    out.putalpha(alpha)
    return out


def apply_app_art(
    proj: ThemeProject, app: C.HomeApp, art: Image.Image, manual: bool = True
) -> dict[int, Image.Image]:
    res = {}
    for iid in app.ids:
        slot = proj._db.images[iid]
        im = compose_variant(proj._db, art, (slot.width, slot.height))
        proj.apply_replacement(iid, im, "icon", manual=manual)
        if proj.edits.get(iid):
            proj.edits[iid].label = app.name
        res[iid] = im
    return res


def app_art_from_db(db: SilverImagesDB, app: C.HomeApp) -> Image.Image:
    """Current artwork of an app (from its large bitmap's visible area)."""
    iid = app.large or app.ids[0]
    im = db.images[iid].to_pil().convert("RGBA")
    box = C.VISIBLE.get(im.size, (0, 0) + im.size)
    return im.crop(box).resize((ART, ART), Image.Resampling.LANCZOS)
