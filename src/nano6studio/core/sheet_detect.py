# SPDX-License-Identifier: GPL-3.0-only
# Nano 6 Theme Studio - Copyright (C) 2026 sharphatman-ux and contributors. See LICENSE.
"""Find the picture tiles on an AI-made sheet, whatever its layout (pure Pillow, no numpy).

Background-colour mask -> morphological close/open -> connected components ->
drop text labels -> reading order -> classify icon / clock face / wallpaper."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from statistics import median

from PIL import Image, ImageChops, ImageFilter

STEP = 4  # analyse at 1/4 resolution


@dataclass
class Tile:
    box: tuple[int, int, int, int]  # full-resolution x0,y0,x1,y1
    kind: str = "icon"  # icon | face | wallpaper
    clipped: bool = False
    slot: str | None = None
    image: Image.Image | None = None

    @property
    def w(self) -> int:
        return self.box[2] - self.box[0]

    @property
    def h(self) -> int:
        return self.box[3] - self.box[1]

    @property
    def cx(self):
        return (self.box[0] + self.box[2]) / 2

    @property
    def cy(self):
        return (self.box[1] + self.box[3]) / 2


def _bg_colour(im):
    W, H = im.size
    pts = [im.getpixel((x, y)) for x in (0, W // 2, W - 1) for y in (0, H - 1)] + [
        im.getpixel((0, H // 2)),
        im.getpixel((W - 1, H // 2)),
    ]
    return tuple(sorted(p[c] for p in pts)[len(pts) // 2] for c in range(3))


def _mask(im, tol=48):
    rgb = im.convert("RGB")
    small = rgb.resize(
        (max(1, rgb.width // STEP), max(1, rgb.height // STEP)), Image.Resampling.BOX
    )
    diff = ImageChops.difference(small, Image.new("RGB", small.size, _bg_colour(rgb)))
    r, g, b = diff.split()
    m = ImageChops.lighter(ImageChops.lighter(r, g), b).point(lambda v: 255 if v > tol else 0)
    m = m.filter(ImageFilter.MaxFilter(3)).filter(
        ImageFilter.MinFilter(3)
    )  # close: fill strokes' gaps
    m = m.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))  # open: drop specks
    return m


def _components(m) -> list[tuple[int, int, int, int, int]]:
    W, H = m.size
    px = m.load()
    seen = bytearray(W * H)
    out = []
    for y in range(H):
        for x in range(W):
            if px[x, y] and not seen[y * W + x]:
                q = deque([(x, y)])
                seen[y * W + x] = 1
                x0 = x1 = x
                y0 = y1 = y
                n = 0
                while q:
                    a, b = q.popleft()
                    n += 1
                    x0, x1, y0, y1 = min(x0, a), max(x1, a), min(y0, b), max(y1, b)
                    for c, d in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
                        if 0 <= c < W and 0 <= d < H and px[c, d] and not seen[d * W + c]:
                            seen[d * W + c] = 1
                            q.append((c, d))
                out.append((x0, y0, x1 + 1, y1 + 1, n))
    return out


def _fill_holes(m):
    """Background reachable from the border stays background; enclosed gaps (white strokes
    inside a dark tile) become part of the tile."""
    W, H = m.size
    px = m.load()
    out = Image.new("L", m.size, 255)
    po = out.load()
    q = deque((x, y) for x in range(W) for y in (0, H - 1))
    q.extend((x, y) for y in range(H) for x in (0, W - 1))
    while q:
        x, y = q.popleft()
        if 0 <= x < W and 0 <= y < H and not px[x, y] and po[x, y]:
            po[x, y] = 0
            q.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    return out


def _runs(vals, frac, minlen):
    out = []
    start = None
    for i, v in enumerate(list(vals) + [0]):
        if v >= frac and start is None:
            start = i
        if v < frac and start is not None:
            if i - start >= minlen:
                out.append((start, i))
            start = None
    return out


def _solid_cores(m, c, minlen, frac=0.55, depth=0):
    """Split a component into solid rectangles: rows that are mostly filled, then columns.
    Text labels glued to a tile (thin, sparse rows) fall away."""
    x0, y0, x1, y1, _ = c
    px = m.load()
    res = []
    for a, b in _runs(
        [sum(1 for x in range(x0, x1) if px[x, y]) / (x1 - x0) for y in range(y0, y1)], frac, minlen
    ):
        ya, yb = y0 + a, y0 + b
        for p, q in _runs(
            [sum(1 for y in range(ya, yb) if px[x, y]) / (yb - ya) for x in range(x0, x1)],
            frac,
            minlen,
        ):
            box = (x0 + p, ya, x0 + q, yb, (q - p) * (yb - ya))
            if depth < 2 and box[:4] != (x0, y0, x1, y1):
                res += _solid_cores(m, box, minlen, frac, depth + 1)
            else:
                res.append(box)
    return res


def detect(im: Image.Image) -> list[Tile]:
    im = im.convert("RGBA")
    m = _fill_holes(_mask(im))
    minlen = max(6, min(m.size) // 30)  # ~1/30 of the sheet: smaller is text
    comps = [k for c in _components(m) for k in _solid_cores(m, c, minlen)]
    if not comps:
        return []
    big = max(max(c[2] - c[0], c[3] - c[1]) for c in comps)
    # labels/text: short blobs, or sparse (letters), much smaller than real tiles
    cand = [
        c
        for c in comps
        if (c[3] - c[1]) >= 0.3 * big and c[4] >= 0.45 * (c[2] - c[0]) * (c[3] - c[1])
    ]
    tiles = [
        Tile((c[0] * STEP, c[1] * STEP, min(im.width, c[2] * STEP), min(im.height, c[3] * STEP)))
        for c in cand
    ]
    if not tiles:
        return []
    # typical icon size = most common tile height
    hs = sorted(t.h for t in tiles)
    icon = median(hs[: max(1, (len(hs) * 3 + 3) // 4)])
    for t in tiles:
        if max(t.w, t.h) > 1.25 * icon:
            t.kind = "large"
        elif min(t.w, t.h) < 0.8 * max(t.w, t.h):
            t.clipped = True  # same height as icons but cut short by an overlapping tile
    tiles = reading_order(tiles, icon)
    larges = [t for t in tiles if t.kind == "large"]
    for n, t in enumerate(larges):  # prompt order: clock face first, then wallpaper
        t.kind = "face" if n == 0 else "wallpaper"
    bg = _bg_colour(im.convert("RGB"))
    for t in tiles:
        t.box = _refine(im, t.box, bg)
    side = median([t.w for t in tiles if t.kind == "icon" and not t.clipped] or [icon])
    for t in tiles:
        if t.clipped:  # labels sit below tiles: keep the top icon-sized part
            x0, y0, x1, y1 = t.box
            t.box = (x0, y0, x1, min(y1, y0 + int(side)))
        elif t.kind == "icon" and t.h > t.w:
            x0, y0, x1, y1 = t.box
            t.box = (x0, y0, x1, y0 + t.w)
        t.image = _trim(im.crop(t.box), t)
    return tiles


def _refine(im, box, bg, tol=60):
    """Snap a box to its tile edges at full resolution (first/last mostly-filled rows/cols,
    from the top-left, so a label under the tile is excluded)."""
    x0, y0, x1, y1 = box
    x0, y0 = max(0, x0 - STEP), max(0, y0 - STEP)
    x1, y1 = min(im.width, x1 + STEP), min(im.height, y1 + STEP)
    c = im.convert("RGB").crop((x0, y0, x1, y1))
    w, h = c.size
    d = (
        ImageChops.difference(c, Image.new("RGB", c.size, bg))
        .convert("L")
        .point(lambda v: 1 if v > tol // 3 else 0)
    )
    px = d.load()
    rows = [sum(px[x, y] for x in range(w)) / w for y in range(h)]
    runs = _runs(rows, 0.5, 4)
    if not runs:
        return box
    a, b = max(runs, key=lambda r: r[1] - r[0])
    cols = [sum(px[x, y] for y in range(a, b)) / (b - a) for x in range(w)]
    cr = _runs(cols, 0.5, 4)
    if not cr:
        return box
    p, q = max(cr, key=lambda r: r[1] - r[0])
    return (x0 + p, y0 + a, x0 + q, y0 + b)


def reading_order(tiles: list[Tile], icon: float) -> list[Tile]:
    """Rows by y-centre clustering (half an icon height), then left to right."""
    rows: list[list[Tile]] = []
    for t in sorted(tiles, key=lambda t: t.cy):
        if rows and abs(t.cy - median(r.cy for r in rows[-1])) < icon * 0.6:
            rows[-1].append(t)
        else:
            rows.append([t])
    return [t for r in rows for t in sorted(r, key=lambda t: t.cx)]


def _trim(tile: Image.Image, t: Tile) -> Image.Image:
    """Square content: unclipped tiles crop to their centred square; clipped ones are padded
    (never stretched) so the visible part keeps its proportions."""
    w, h = tile.size
    if t.clipped:
        s = max(w, h)
        out = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        out.paste(tile, (0, (s - h) // 2))
        return out
    s = min(w, h)
    return tile.crop(((w - s) // 2, 0, (w - s) // 2 + s, s))  # top-anchored: labels go below


def assign_slots(tiles: list[Tile], app_order: list[str]) -> list[Tile]:
    """Icons take the prompt's app order; first large tile = clock face, next = wallpaper."""
    icons = [t for t in tiles if t.kind == "icon"]
    for t, name in zip(icons, app_order):
        t.slot = name
    for t in tiles:
        if t.kind == "face":
            t.slot = "Clock face background"
        if t.kind == "wallpaper":
            t.slot = "Wallpaper"
    return tiles
