# SPDX-License-Identifier: GPL-3.0-only
# Nano 6 Theme Studio - Copyright (C) 2026 sharphatman-ux and contributors. See LICENSE.
"""AI prompt builder (offline: just text) and importer for the images an AI tool returns."""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw

from .cropper import initial_placement, render_placement

GLYPHS = {
    "Now Playing": "a play triangle inside a sound-wave or spinning-disc motif",
    "Music": "a pair of musical eighth notes",
    "Radio": "a radio tower / antenna sending broadcast waves",
    "Fitness": "a running figure or sneaker",
    "Clock": "a round analog clock face with two hands",
    "Photos": "a flower or a small stack of photos",
    "Audiobooks": "an open book with headphones",
    "Podcasts": "a studio microphone with broadcast rings",
    "iTunes U": "a graduation mortarboard cap",
    "Voice Memos": "a sound waveform or small handheld microphone",
    "Settings": "a mechanical gear / cog",
    "Genius Mixes": "an atom-like swirl or sparkle of merging streams",
    "Playlists": "a list of horizontal lines with a small music note",
    "Artists": "a person silhouette with a microphone",
    "Albums": "a square album cover with a record peeking out",
    "Songs": "a single musical note",
    "Genres": "a guitar",
    "Composers": "a grand piano or a conductor's baton over sheet music",
}
ICON_W, ICON_H = 154, 164  # native large home icon
ICON_SMALL = 105  # native small home icon
ICON_GEN = 512  # square artwork size to ask for (scaled down cleanly)
FACE = 240
SCOPES = ("All home icons", "Single icon", "Clock face", "Wallpaper", "Everything")


@dataclass
class Slot:
    kind: str  # "icon" | "face" | "hands" | "digits" | "wallpaper"
    name: str
    w: int
    h: int


def _ratio(w, h):
    g = math.gcd(w, h)
    return f"{w // g}:{h // g}"


SHORT = {  # a few plain words per icon, for the short prompts
    "Now Playing": "a play button",
    "Music": "music notes",
    "Radio": "a radio tower",
    "Fitness": "a running shoe",
    "Clock": "a clock",
    "Photos": "a flower",
    "Audiobooks": "an open book",
    "Podcasts": "a microphone",
    "iTunes U": "a graduation cap",
    "Voice Memos": "a sound wave",
    "Settings": "a gear",
    "Genius Mixes": "a sparkle",
    "Playlists": "a list with a music note",
    "Artists": "a singer",
    "Albums": "a record",
    "Songs": "a music note",
    "Genres": "a guitar",
    "Composers": "a piano",
}


def slots_for(
    scope: str,
    apps: Sequence[str],
    icon: str | None = None,
    hands: list[tuple[int, int]] | None = None,
    digits=None,
    extras: bool = False,
) -> list[Slot]:
    """digits is accepted for compatibility but ignored: digit/date glyphs are static."""
    out: list[Slot] = []
    if scope in ("All home icons", "Everything"):
        out += [Slot("icon", a, ICON_GEN, ICON_GEN) for a in apps]
    if scope == "Single icon":
        out.append(Slot("icon", icon or apps[0], ICON_GEN, ICON_GEN))
    if scope in ("Clock face", "Everything"):
        out.append(Slot("face", "Clock face background", FACE, FACE))
        if extras:
            for n, (w, h) in enumerate(hands or []):
                out.append(Slot("hands", f"Clock hand {n + 1}", w, h))
    if scope in ("Wallpaper", "Everything"):
        out.append(Slot("wallpaper", "Wallpaper", FACE, FACE))
    return out


def _style(idea):
    return (idea.strip() or "clean modern minimal").rstrip(".")


def _slot_text(s: Slot, idea: str = "") -> str:
    """One short, plain prompt for one image (works well in Gemini and other chat tools)."""
    st = _style(idea)
    if s.kind == "icon":
        return (
            f"A square app icon of {SHORT.get(s.name, s.name.lower())}, {s.w}x{s.h} pixels. "
            f"Style: {st}. One bold centred symbol on a transparent background. No text or labels."
        )
    if s.kind == "face":
        return (
            f"A square clock face background, {s.w}x{s.h} pixels. Style: {st}. "
            "No clock hands, no numbers, no text."
        )
    if s.kind == "hands":
        return (
            f"One clock hand pointing straight up, {s.w}x{s.h} pixels, on a transparent background. "
            f"Style: {st}. No text."
        )
    return f"A square wallpaper, {s.w}x{s.h} pixels. Style: {st}. Soft and low contrast. No text or icons."


NO_TEXT = "No text or labels."


def build_prompt(idea: str, slots: list[Slot], sheet: bool = False) -> str:
    """All prompts as one text (for saving / tests); the dialog shows and copies one at a time."""
    return (
        "\n".join(
            f"=== Prompt {k}: {t} ===\n{body}\n"
            for k, (t, body, _) in enumerate(build_prompts(idea, slots, sheet), 1)
        ).rstrip()
        + "\n"
    )


def build_prompts(idea: str, slots: list[Slot], sheet: bool = False) -> list[tuple]:
    """[(title, prompt text, slots)]: one image per prompt by default. sheet=True puts the icons
    on one small grid image (the smallest spec that still slices reliably)."""
    icons = [s for s in slots if s.kind == "icon"]
    out: list[tuple] = []
    if icons and sheet and len(icons) > 1:
        cols, rows, cw, ch = sheet_layout(icons)
        names = ", ".join(SHORT.get(s.name, s.name.lower()) for s in icons)
        out.append(
            (
                "home icon sheet",
                f"One image, {cols * cw}x{rows * ch} pixels: a grid of {cols} columns x {rows} rows of "
                f"square app icons, {cw}x{ch} each, with white gaps between. Style: {_style(idea)}. "
                f"No text or labels. Left to right, top to bottom: {names}.",
                icons,
            )
        )
    else:
        out += [(f"{s.name} icon", _slot_text(s, idea), [s]) for s in icons]
    for s in slots:
        if s.kind != "icon":
            out.append((s.name, _slot_text(s, idea), [s]))
    return out


def sheet_layout(slots: list[Slot]) -> tuple[int, int, int, int]:
    n = len(slots)
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)
    cw = min(256, max(s.w for s in slots))
    ch = min(256, max(s.h for s in slots))
    cw = ch = max(cw, ch)
    return cols, rows, cw, ch


def slice_sheet(im: Image.Image, cols: int, rows: int) -> list[Image.Image]:
    """Cut a sprite sheet into cells, left-to-right, top-to-bottom."""
    cw, ch = im.width / cols, im.height / rows
    return [
        im.crop((round(c * cw), round(r * ch), round((c + 1) * cw), round((r + 1) * ch)))
        for r in range(rows)
        for c in range(cols)
    ]


def remove_plain_background(im: Image.Image, tol: int = 24) -> Image.Image:
    """If the four corners share one solid colour, flood it away from the edges."""
    im = im.convert("RGBA")
    W, H = im.size
    corners = [im.getpixel(p) for p in ((0, 0), (W - 1, 0), (0, H - 1), (W - 1, H - 1))]
    if any(c[3] < 250 for c in corners):
        return im  # already transparent
    ref = corners[0]
    if min(ref[:3]) < 200:
        return im  # dark/colour tile fill is part of the design
    if any(max(abs(a - b) for a, b in zip(c[:3], ref[:3])) > tol for c in corners):
        return im  # not a plain background
    rgb = im.convert("RGB")
    mark = (255, 0, 255)
    probe = rgb.copy()
    for p in ((0, 0), (W - 1, 0), (0, H - 1), (W - 1, H - 1)):
        if probe.getpixel(p) != mark:
            ImageDraw.floodfill(probe, p, mark, thresh=tol)
    out = im.copy()
    px = out.load()
    pp = probe.load()
    for y in range(H):
        for x in range(W):
            if pp[x, y] == mark and rgb.getpixel((x, y)) != mark:
                px[x, y] = px[x, y][:3] + (0,)
    return out


def fit(im: Image.Image, w: int, h: int) -> Image.Image:
    """No-stretch framing: scale to fit inside w x h, centred."""
    p = initial_placement(im.width, im.height, w, h, mode="fit")
    return render_placement(im, w, h, p)


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def detect_tiles(im: Image.Image, slots: list[Slot]) -> list:
    """Smart sheet import: find tiles on any layout, assign by reading order."""
    from . import sheet_detect as D

    tiles = D.detect(im)
    D.assign_slots(tiles, [s.name for s in slots if s.kind == "icon"] or [s.name for s in slots])
    return tiles


def assign(
    images: list[tuple[str, Image.Image]], slots: list[Slot]
) -> list[tuple[Slot, Image.Image]]:
    """Match by file name when a slot name appears in it, otherwise fill remaining slots in order.
    A single image for several slots is a sheet: tiles are detected (any layout); a strict grid
    is the fallback when nothing sensible is found."""
    if len(images) == 1 and len(slots) > 1:
        tiles = detect_tiles(images[0][1], slots)
        by = {s.name: s for s in slots}
        got = [(by[t.slot], t.image) for t in tiles if t.slot in by]
        if len(got) >= 2:
            return got
        cols, rows, *_ = sheet_layout(slots)
        return list(zip(slots, slice_sheet(images[0][1], cols, rows)))
    free = list(slots)
    res = []
    rest = []
    for fn, im in images:
        stem = _norm(Path(fn).stem)
        hit = max(
            (s for s in free if _norm(s.name) and _norm(s.name) in stem),
            key=lambda s: len(s.name),
            default=None,
        )
        if hit:
            free.remove(hit)
            res.append((hit, im))
        else:
            rest.append(im)
    res += list(zip(free, rest))
    order = {id(s): n for n, s in enumerate(slots)}
    return sorted(res, key=lambda t: order[id(t[0])])


def prompt_for(kind: str, name: str, w: int, h: int, style: str = "") -> str:
    """One short prompt for the single selected item (kind: icon | face | hand | wallpaper | image)."""
    st = _style(style)
    if kind == "icon":
        return _slot_text(Slot("icon", name, ICON_GEN, ICON_GEN), st)
    if kind == "face":
        return _slot_text(Slot("face", name, w, h), st)
    if kind == "hand":
        return (
            f"One {name.lower()} for a watch, pointing straight up, {w}x{h} pixels, on a transparent "
            f"background. Style: {st}. No text."
        )
    if kind == "wallpaper":
        return _slot_text(Slot("wallpaper", name, w, h), st)
    return f"An image of {w}x{h} pixels. Style: {st}. No text or labels."


# ---- quick options (the AI prompt window) ----
OPTIONS = ("Everything", "Just icons", "Just backgrounds", "Watch face + hands")
OPTION_HINTS = {
    "Everything": "icons + wallpaper + watch face + hands on one sheet (for more advanced AIs)",
    "Just icons": "all 18 home icons on one sheet",
    "Just backgrounds": "one home-screen wallpaper",
    "Watch face + hands": "one clock background + hour, minute and second hands",
}
HAND_NAMES = ("Hour hand", "Minute hand", "Second hand")


def option_slots(option: str, apps: Sequence[str]) -> list[Slot]:
    icons = [Slot("icon", a, ICON_GEN, ICON_GEN) for a in apps]
    watch = [Slot("face", "Clock face background", FACE, FACE)] + [
        Slot("hands", n, 256, 256) for n in HAND_NAMES
    ]
    wall = [Slot("wallpaper", "Wallpaper", FACE, FACE)]
    return {
        "Everything": icons + wall + watch,
        "Just icons": icons,
        "Just backgrounds": wall,
        "Watch face + hands": watch,
    }[option]


def option_grid(option: str, n: int) -> tuple[int, int]:
    """(cols, rows) of equal square cells for a multi-item sheet."""
    if option == "Watch face + hands":
        return 4, 1
    if option == "Everything":
        return 6, 4  # 18 icons + wallpaper + face + 3 hands (+1 empty)
    return sheet_layout([Slot("icon", "", ICON_GEN, ICON_GEN)] * n)[:2]


def _what(s: Slot) -> str:
    if s.kind == "icon":
        return f"{SHORT.get(s.name, s.name.lower())} icon"
    if s.kind == "face":
        return "round clock face background (no hands, no numbers)"
    if s.kind == "hands":
        return f"{s.name.lower()} pointing straight up, centred"
    return "dark low-contrast wallpaper"


def option_prompt(option: str, apps: Sequence[str], style: str = "") -> str:
    """One concise prompt for the chosen option (sheets get an exact grid spec)."""
    st = _style(style)
    slots = option_slots(option, apps)
    if len(slots) == 1:
        return _slot_text(slots[0], st)
    cols, rows = option_grid(option, len(slots))
    cell = 256
    items = "; ".join(f"{k + 1} {_what(s)}" for k, s in enumerate(slots))
    spare = cols * rows - len(slots)
    return (
        f"One image, {cols * cell}x{rows * cell} pixels, a grid of {cols} columns x {rows} rows of equal "
        f"{cell}x{cell} square cells with thin white gaps. Style: {st}, consistent across all cells. "
        f"One item per cell, centred, on a plain background. No text, labels or numbers anywhere. "
        f"Left to right, top to bottom: {items}."
        + (f" Leave the last {spare} cell(s) empty." if spare else "")
    )
