# SPDX-License-Identifier: GPL-3.0-only
# Nano 6 Theme Studio - Copyright (C) 2026 sharphatman-ux and contributors. See LICENSE.
"""Pixel renderer for the nano 6G 240x240 home screen and clock (used by the
live preview, tests and exported preview PNGs)."""

from __future__ import annotations

import io
import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

from . import catalog as C

if TYPE_CHECKING:
    from nano6studio.core.catalog import ClockFace
    from nano6studio.core.project import ThemeProject
    from nano6studio.core.silverimages import SilverImagesDB


# Helvetica Bold read from the user's own firmware: a path or the raw font bytes
_FONT_PATH: str | bytes | None = None

# Preview pin for a hand bitmap when the user has not set one. Not a firmware field:
# horizontal centre of the bitmap, 82% of the way down (the previous studio preview).
DEFAULT_PIVOT_FRAC = 0.82
DEFAULT_FACE_CENTRE = (C.SCREEN // 2, C.SCREEN // 2)

# Shown in the Clock Faces panel. Positions are not editable; see docs/CLOCK_FACES.md.
GLYPH_HELP = (
    "Bitmap only. The iPod draws this glyph at a fixed position compiled into the OS. "
    "That position is not stored in SilverImagesDB or any other firmware file this app can edit. "
    "Replacing the picture keeps the original width and height."
)
PIVOT_HELP = (
    "Preview only — saved in the theme project, not written into the IPSW. "
    "The iPod turns every hand about the screen centre (120, 120) and stores no pivot. "
    "The pivot is the bitmap pixel this preview pins to that centre. "
    "Default: horizontal centre, 82% down. Draw the hand's pin on that pixel "
    "so a centre-pivoted hand matches the device."
)


def default_hand_pivot(size: tuple[int, int]) -> tuple[int, int]:
    """Bitmap pixel the preview pins to the face centre when no override is set."""
    w, h = size
    return (w // 2, int(h * DEFAULT_PIVOT_FRAC))


@dataclass
class ClockPlacement:
    """Studio-only hand placement. Defaults match a centre-pivoted hand.

    ``centre`` is the point on the 240×240 screen that hands turn about.
    ``pivots`` maps a hand image id to the bitmap pixel that lands on ``centre``.
    Missing hands use :func:`default_hand_pivot`. Nothing here is written to the IPSW.
    """

    centre: tuple[int, int] = DEFAULT_FACE_CENTRE
    pivots: dict[int, tuple[int, int]] = field(default_factory=dict)

    def pivot_for(self, image_id: int, size: tuple[int, int]) -> tuple[int, int]:
        return self.pivots.get(image_id) or default_hand_pivot(size)


def set_font(path: str | bytes | None) -> None:
    global _FONT_PATH
    _FONT_PATH = path


def _font(size: int):
    try:
        if _FONT_PATH:
            source = io.BytesIO(_FONT_PATH) if isinstance(_FONT_PATH, bytes) else _FONT_PATH
            return ImageFont.truetype(source, size)
    except OSError:
        pass
    for f in ("arialbd.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


def order_apps(
    apps: list[C.HomeApp], include_hidden: bool = False, include_conditional: bool | None = None
) -> list[C.HomeApp]:
    """Stock home order. Default: only always-present apps. include_conditional adds
    Audiobooks/iTunes U/Voice Memos in their stock slots; include_hidden adds everything."""
    by = {a.name: a for a in apps}
    cond = include_hidden if include_conditional is None else include_conditional
    names = [n for n in C.DEFAULT_ORDER if cond or include_hidden or n not in C.CONDITIONAL]
    names += [n for n in C.APPS if n not in C.DEFAULT_ORDER] if include_hidden else []
    return [by[n] for n in names if n in by]


def page_count(apps, small: bool) -> int:
    per = 4 if small else 1
    return max(1, math.ceil(len(apps) / per))


def _status_bar(d: ImageDraw.ImageDraw, im: Image.Image) -> None:
    # translucent black strip with battery at the right (stock look)
    strip = Image.new("RGBA", (C.SCREEN, C.STATUS_H), (0, 0, 0, 110))
    im.alpha_composite(strip)
    x, y = 210, 5
    d.rectangle((x, y, x + 20, y + 9), outline=(235, 235, 235, 255))
    d.rectangle((x + 21, y + 3, x + 22, y + 6), fill=(235, 235, 235, 255))
    d.rectangle((x + 2, y + 2, x + 15, y + 7), fill=(235, 235, 235, 255))


def _label(d, text, cx, y, size):
    f = _font(size)
    w = d.textlength(text, font=f)
    d.text((cx - w / 2 + 1, y + 1), text, font=f, fill=(0, 0, 0, 160))
    d.text((cx - w / 2, y), text, font=f, fill=(255, 255, 255, 255))


def _dots(d, n, cur):
    gap = 10
    x0 = C.SCREEN / 2 - (n - 1) * gap / 2
    for k in range(n):
        x = x0 + k * gap
        col = (255, 255, 255, 255) if k == cur else (255, 255, 255, 90)
        d.ellipse((x - 2.5, C.DOTS_Y - 2.5, x + 2.5, C.DOTS_Y + 2.5), fill=col)


def render_home(
    db: SilverImagesDB,
    wallpaper_id: int | None,
    apps: list[C.HomeApp],
    page: int = 0,
    small: bool = False,
    offset_px: float = 0.0,
) -> Image.Image:
    """offset_px: horizontal swipe offset (for drag animation)."""
    S = C.SCREEN
    im = Image.new("RGBA", (S, S), (0, 0, 0, 255))
    if wallpaper_id and wallpaper_id in db.images:
        im.alpha_composite(db.images[wallpaper_id].to_pil().convert("RGBA").resize((S, S)))
    n = page_count(apps, small)
    layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    for p in (page - 1, page, page + 1):
        if not 0 <= p < n:
            continue
        dx = round((p - page) * S + offset_px)
        if small:
            for k, app in enumerate(apps[p * 4 : p * 4 + 4]):
                x, y = C.SMALL_POS[k]
                if app.small:
                    ic = db.images[app.small].to_pil().convert("RGBA")
                    layer.alpha_composite(ic, (x + dx, y))
                _label(ld, app.name, x + dx + 52.5, y + C.SMALL_LABEL_DY, 12)
        else:
            if p < len(apps):
                app = apps[p]
                x, y = C.LARGE_POS
                if app.large:
                    ic = db.images[app.large].to_pil().convert("RGBA")
                    layer.alpha_composite(ic, (x + dx, y))
                _label(ld, app.name, S / 2 + dx, C.LARGE_LABEL_Y + 32, 17)
    im.alpha_composite(layer)
    d = ImageDraw.Draw(im)
    _status_bar(d, im)
    _dots(d, n, page)
    return im


def _hand(len_px, w, color):
    h = Image.new("RGBA", (w * 2 + 2, len_px + 10), (0, 0, 0, 0))
    ImageDraw.Draw(h).polygon(
        [(w + 1, 0), (2 * w + 1, len_px), (w + 1, len_px + 8), (1, len_px)], fill=color
    )
    return h


def _rotate_hand(hand: Image.Image, angle_deg: float, pivot: tuple[int, int] | None = None):
    """Rotate a vertical hand bitmap (pointing up) so ``pivot`` stays fixed.

    ``pivot`` is a pixel of ``hand``. The default is :func:`default_hand_pivot`.
    """
    w, h = hand.size
    px, py = pivot if pivot is not None else default_hand_pivot((w, h))
    big = Image.new("RGBA", (max(w, h) * 2 + 4, max(w, h) * 2 + 4), (0, 0, 0, 0))
    cx, cy = big.width // 2, big.height // 2
    big.alpha_composite(hand, (cx - int(px), cy - int(py)))
    return big.rotate(-angle_deg, resample=Image.Resampling.BICUBIC, center=(cx, cy)), (cx, cy)


def place_hand(
    hand: Image.Image,
    angle_deg: float,
    pivot: tuple[int, int],
    centre: tuple[int, int],
    size: int = 240,
) -> Image.Image:
    """Paint ``hand`` so ``pivot`` sits on ``centre`` after rotation (0° points up)."""
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    rotated, (cx, cy) = _rotate_hand(hand, angle_deg, pivot)
    out.alpha_composite(rotated, (int(centre[0]) - cx, int(centre[1]) - cy))
    return out


def pivot_marker(w: int, h: int, pivot: tuple[int, int], colour=(0, 230, 255, 230)) -> Image.Image:
    """A crosshair on the pivot pixel of a hand bitmap (editor / detail view)."""
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    x, y = int(pivot[0]), int(pivot[1])
    d = ImageDraw.Draw(im)
    d.line((x - 7, y, x + 7, y), fill=colour)
    d.line((x, y - 7, x, y + 7), fill=colour)
    return im


def hands_overlay(
    db: SilverImagesDB,
    hand_ids: list[int],
    size: int = 240,
    hh: int = 10,
    mm: int = 9,
    placement: ClockPlacement | None = None,
) -> Image.Image:
    """Hands at 10:09. The first two bitmaps are the hour and minute hands (shorter one
    is the hour hand, same as before). Any further bitmaps are second hands, drawn
    pointing up so their pivot can be checked. Digits are not drawn."""
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    place = placement or ClockPlacement()
    centre = place.centre if placement is not None else (size // 2, size // 2)
    ids = [i for i in hand_ids if i in db.images]
    primary = [(db.images[i].to_pil().convert("RGBA"), i) for i in ids[:2]]
    if len(primary) < 2:
        primary = [
            (_hand(60, 5, (255, 255, 255, 230)), None),
            (_hand(90, 3, (255, 255, 255, 230)), None),
        ]
    primary.sort(key=lambda t: t[0].height)
    angles = [(hh % 12 + mm / 60) * 30, mm * 6]
    drawn: list[tuple[Image.Image, int | None, float]] = [
        (hand, iid, ang) for (hand, iid), ang in zip(primary, angles)
    ]
    for iid in ids[2:]:
        drawn.append((db.images[iid].to_pil().convert("RGBA"), iid, 0.0))
    for hand, iid, ang in drawn:
        pivot = (
            place.pivot_for(iid, hand.size) if iid is not None else default_hand_pivot(hand.size)
        )
        out.alpha_composite(place_hand(hand, ang, pivot, centre, size))
    return out


def clock_overlay(
    db: SilverImagesDB,
    face,
    colour=(0, 230, 255),
    opacity: float = 0.7,
    placement: ClockPlacement | None = None,
) -> Image.Image:
    """The face's hands (10:09, pinned at ``placement``) plus its full-screen overlay
    bitmaps, as a tinted see-through layer. Digits / date are NOT drawn: their positions
    differ per face and live in the encrypted OS (see docs/CLOCK_FACES.md)."""
    S = C.SCREEN
    lay = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    if not face:
        return lay
    for r, i in face.parts:
        if r == "Overlay":
            lay.alpha_composite(db.images[i].to_pil().convert("RGBA").resize((S, S)))
    if face.hands():
        lay.alpha_composite(hands_overlay(db, face.hands(), placement=placement))
    a = lay.getchannel("A").point(lambda v: int(v * opacity))
    out = Image.new("RGBA", (S, S), tuple(colour) + (0,))
    out.putalpha(a)
    if face.hands():
        d = ImageDraw.Draw(out)
        cx, cy = placement.centre if placement is not None else DEFAULT_FACE_CENTRE
        d.line((cx - 6, cy, cx + 6, cy), fill=tuple(colour) + (200,))
        d.line((cx, cy - 6, cx, cy + 6), fill=tuple(colour) + (200,))
    return out


def render_clock(
    db: SilverImagesDB,
    face: C.ClockFace | None,
    background: Image.Image | None = None,
    placement: ClockPlacement | None = None,
) -> Image.Image:
    S = C.SCREEN
    im = Image.new("RGBA", (S, S), (0, 0, 0, 255))
    bg = background
    if bg is None and face and face.background:
        bg = db.images[face.background].to_pil()
    if bg is not None:
        im.alpha_composite(bg.convert("RGBA").resize((S, S)))
    if face:
        for r, i in face.parts:
            if r == "Overlay":
                im.alpha_composite(db.images[i].to_pil().convert("RGBA").resize((S, S)))
        if face.hands():
            im.alpha_composite(hands_overlay(db, face.hands(), placement=placement))
    return im


def digit_set(db: SilverImagesDB, face) -> list:
    """First run of >=10 same-size glyph bitmaps in a face = digits 0-9 (largest set)."""
    runs, cur = [], []
    for _r, i in face.parts:
        im = db.images[i]
        if cur and (im.width, im.height) == (db.images[cur[-1]].width, db.images[cur[-1]].height):
            cur.append(i)
        else:
            if len(cur) >= 10:
                runs.append(cur)
            cur = [i]
    if len(cur) >= 10:
        runs.append(cur)
    runs = [r for r in runs if db.images[r[0]].height >= 15 and db.images[r[0]].width < 120]
    return max(runs, key=lambda r: db.images[r[0]].height)[:10] if runs else []


def face_thumbnails(face: ClockFace) -> list:
    """Every 79x79 clock-picker thumbnail copy of a face."""
    out = [i for r, i in face.parts if r == "Preview"]
    if face.preview and face.preview not in out:
        out.append(face.preview)
    return out


def sync_face_thumbnail(proj: ThemeProject, face) -> None:
    """Keep the firmware's 79x79 clock-picker thumbnail in step with the face: if the
    background, overlays or hands are edited, re-render it (background + overlays + hands at
    10:09, LANCZOS downscale) into every copy; if nothing is edited, restore the stock one."""
    db = proj._db
    thumbs = face_thumbnails(face)
    if not thumbs:
        return
    src = [i for r, i in face.parts if r in ("Background", "Overlay") or r.startswith("Hand")]
    if any(i in proj.edits for i in src):
        t = render_clock(db, face, placement=proj.clock_placement(face)).resize(
            (79, 79), Image.Resampling.LANCZOS
        )
        for i in thumbs:
            proj.apply_replacement(i, t, "clock", manual=True)
    else:
        for i in thumbs:
            proj.revert(i)


def hand_labels(db: SilverImagesDB, face) -> dict:
    """id -> 'Hour hand' / 'Minute hand' / 'Second hand'. The firmware lists hour, minute, then
    second hand(s); the hour hand's visible length is checked to be the shorter of the first two."""
    hs = face.hands()
    lab = {}

    def vis(i):
        bb = db.images[i].to_pil().convert("RGBA").getchannel("A").getbbox()
        return (bb[3] - bb[1]) if bb else 0

    if len(hs) >= 2:
        h, m = (hs[0], hs[1]) if vis(hs[0]) <= vis(hs[1]) else (hs[1], hs[0])
        lab[h], lab[m] = "Hour hand", "Minute hand"
    elif hs:
        lab[hs[0]] = "Hand"
    rest = hs[2:]
    for k, i in enumerate(rest):
        lab[i] = "Second hand" + (f" {k + 1}" if len(rest) > 1 else "")
    return lab
