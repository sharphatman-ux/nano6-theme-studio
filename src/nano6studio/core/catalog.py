# SPDX-License-Identifier: GPL-3.0-only
# Nano 6 Theme Studio - Copyright (C) 2026 sharphatman-ux and contributors. See LICENSE.
"""Semantic catalog of the nano 6G (fw 1.2, 36B10147) SilverImagesDB.

Icon IDs were mapped by rendering every candidate bitmap and identifying each
glyph against the stock home screen (Apple iPod nano 6G user guide app list),
not by ordering heuristics. Layout facts:
  * fw 1.2 default home screen = ONE large icon per page (154x164 bitmaps);
    Settings > General > Home Screen > Small Icons = 2x2 per page (105x105).
  * 50x50 = list-size icons (Settings > Home Screen list).
  * 0x0DAD02BF / 0x0DAD02C0 = tap-down shape masks (large / small), per ipod_theme
    ("the artwork right before the first icon").
  * Each size ships two copies of every icon (set A and set B; set B moves
    Music to the end). Both are used by the OS, so edits are written to both.

Clock faces: each face style is a 79x79 picker thumbnail with the 240x240
background(s), hands and glyphs stored around it (see clock_faces). The DB has 38
styles: 14 single faces plus 4 groups of 6 case-colour variants, which the
Settings picker shows as 18 faces (picker_entries).

Wallpapers: SETTINGS_WALLPAPERS lists the 240x240 images (plus near-identical
copies) and their 79x79 thumbnails in Settings > Wallpaper order, 3 per row.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from PIL import Image

if TYPE_CHECKING:
    from nano6studio.core.silverimages import SilverImagesDB


BASE = 0x0DAD0000

APPS = [
    "Music",
    "Now Playing",
    "Radio",
    "Fitness",
    "Clock",
    "Photos",
    "Podcasts",
    "Audiobooks",
    "iTunes U",
    "Voice Memos",
    "Settings",
    "Genius Mixes",
    "Playlists",
    "Artists",
    "Albums",
    "Songs",
    "Genres",
    "Composers",
]

# Stock default home-screen order (user guide, fw 1.2 "icons you see when you first turn on")
DEFAULT_ORDER = [
    "Now Playing",
    "Music",
    "Radio",
    "Fitness",
    "Clock",
    "Photos",
    "Audiobooks",
    "Podcasts",
    "iTunes U",
    "Voice Memos",
    "Settings",
]

_ORDER_A = [
    "Albums",
    "Artists",
    "Audiobooks",
    "Composers",
    "Genius Mixes",
    "Music",
    "Now Playing",
    "Playlists",
    "Podcasts",
    "Photos",
    "Settings",
    "Songs",
    "Fitness",
    "Voice Memos",
    "Radio",
    "Clock",
    "iTunes U",
    "Genres",
]
_ORDER_B = [
    "Albums",
    "Artists",
    "Audiobooks",
    "Composers",
    "Genius Mixes",
    "Now Playing",
    "Playlists",
    "Podcasts",
    "Photos",
    "Settings",
    "Songs",
    "Fitness",
    "Voice Memos",
    "Radio",
    "Clock",
    "iTunes U",
    "Genres",
    "Music",
]
_ORDER_LIST = [
    "Radio",
    "Fitness",
    "Clock",
    "Photos",
    "Podcasts",
    "iTunes U",
    "Voice Memos",
    "Music",
    "Albums",
    "Artists",
    "Audiobooks",
    "Composers",
    "Genres",
    "Genius Mixes",
    "Playlists",
    "Songs",
]

# Visibility per the Apple iPod nano (6th generation) User Guide, fw 1.2 edition
# (ma1551, "The Home screen" table, ch. 1):
#   Audiobooks - "it doesn't appear if you have no audiobooks"
#   iTunes U   - "it doesn't appear if you have no collections"
#   Voice Memos - "visible only if a microphone is connected ... or if there are voice memo recordings"
CONDITIONAL = {
    "Audiobooks": "Shows only when audiobooks are synced",
    "iTunes U": "Shows only when iTunes U is synced",
    "Voice Memos": "Shows only with a mic or recordings",
}
# Same guide: "You can add these icons to your Home screen by turning them on in Settings"
OPTIONAL = {
    n: "Off by default (turn on in Settings)"
    for n in ("Genius Mixes", "Playlists", "Artists", "Albums", "Songs", "Genres", "Composers")
}

MASK_LARGE = BASE + 0x2BF
MASK_SMALL = BASE + 0x2C0


def _seq(start: int, names: list[str]) -> dict[str, int]:
    return {n: BASE + start + i for i, n in enumerate(names)}


LARGE_A = _seq(0x2C1, _ORDER_A)  # 154x164
LARGE_B = _seq(0x2F9, _ORDER_B)
SMALL_A = _seq(0x2D5, _ORDER_A)  # 105x105
SMALL_B = _seq(0x2E7, _ORDER_B)
LIST_50 = _seq(0x6C8, _ORDER_LIST)  # 50x50

# visible rounded-square area inside each bitmap (from tap-down mask alpha bbox)
VISIBLE = {(154, 164): (14, 11, 140, 137), (105, 105): (14, 5, 91, 82), (50, 50): (0, 0, 50, 50)}

# Home-screen geometry on the 240x240 panel (measured from stock bitmaps/masks
# and stock screenshots; status bar 18 px, page dots at y~228).
SCREEN = 240
STATUS_H = 18
LARGE_POS = (43, 20)  # 154x164 bitmap origin; label baseline below
LARGE_LABEL_Y = 166
SMALL_POS = [(7, 20), (128, 20), (7, 122), (128, 122)]  # 105x105 origins, 2x2
SMALL_LABEL_DY = 84  # label top relative to icon origin
DOTS_Y = 229

WALLPAPER_RANGE = (BASE + 0x30C, BASE + 0x343)
CLOCK_RANGE = (BASE + 0x349, BASE + 0x4EC)  # 0x344-0x348 = picker chrome


@dataclass
class HomeApp:
    name: str
    ids: list[int]  # every bitmap of this app (all sizes/sets)
    large: int | None = None
    small: int | None = None
    list_icon: int | None = None


@dataclass
class ClockFace:
    name: str
    preview: int | None
    parts: list[tuple[str, int]] = field(default_factory=list)  # (role, id)

    primary: int | None = None  # background the preview shows (closest to the 79x79 thumbnail)

    @property
    def background(self) -> int | None:
        if self.primary is not None:
            return self.primary
        bgs = self.backgrounds()
        return bgs[-1] if bgs else None

    def backgrounds(self) -> list[int]:
        """Every full-screen background copy of this face (all are written on edit)."""
        return [i for r, i in self.parts if r == "Background"]

    def glyphs(self) -> list[int]:
        return [i for r, i in self.parts if r in ("Digits / detail", "Dial detail")]

    def hands(self) -> list[int]:
        return [i for r, i in self.parts if r.startswith("Hand")]


ALWAYS = [n for n in DEFAULT_ORDER if n not in CONDITIONAL]  # the 8 always-present apps


# Apps that never appear on a nano 6G (true leftovers). None of the 18 mapped apps
# qualifies: the fw 1.2 user guide lists all 18 as Home screen icons (11 shown by
# default, Audiobooks/iTunes U/Voice Memos conditionally, 7 addable in Settings).
LEFTOVERS: set = set()


def home_apps(db: SilverImagesDB, include_hidden: bool = True) -> list[HomeApp]:
    """Every app that can appear on a nano 6G home screen."""
    out = []
    for n in (n for n in APPS if include_hidden or n in ALWAYS):
        if n in LEFTOVERS:
            continue
        ids = [t[n] for t in (LARGE_A, LARGE_B, SMALL_A, SMALL_B, LIST_50) if n in t]
        ids = [i for i in ids if i in db.images]
        if ids:
            out.append(HomeApp(n, ids, LARGE_A.get(n), SMALL_A.get(n), LIST_50.get(n)))
    return out


def _role(w: int, h: int) -> str:
    if (w, h) == (240, 240):
        return "Background"
    if (w, h) == (79, 79):
        return "Preview"
    if h >= 90 and h >= 2.4 * w and w <= 60:
        return "Hand"
    if w >= 60 and h >= 60:
        return "Dial detail"
    return "Digits / detail"


def clock_faces(db: SilverImagesDB) -> list[ClockFace]:
    """One style per 79x79 preview. The 240x240 right before a preview is its
    background. Hands/digits/overlays that follow a run of N styles are split at
    each 240x240 overlay and dealt out to those N styles in order (this is how
    the colour variants are laid out); otherwise they go to the last style."""
    lo, hi = CLOCK_RANGE
    ids = [i for i in sorted(db.images) if lo <= i <= hi]
    role = {i: _role(db.images[i].width, db.images[i].height) for i in ids}
    faces: list[ClockFace] = []
    run: list[ClockFace] = []  # faces since last leftover block
    pending: list[int] = []

    def flush():
        nonlocal pending, run
        if not pending:
            return
        tgt = run or faces[-1:]
        chunks, cur = [], []
        for i in pending:
            if role[i] == "Background" and cur:
                chunks.append(cur)
                cur = []
            cur.append(i)
        if cur:
            chunks.append(cur)
        if len(chunks) > 1 and role[chunks[0][0]] != "Background":
            chunks[1] = chunks[0] + chunks[1]
            chunks.pop(0)
        if tgt and len(chunks) == len(tgt) and len(tgt) > 1:
            for f, ch in zip(tgt, chunks):
                f.parts += [("Overlay" if role[i] == "Background" else role[i], i) for i in ch]
        elif tgt:
            tgt[-1].parts += [
                ("Overlay" if role[i] == "Background" and tgt[-1].background else role[i], i)
                for i in pending
            ]
        pending = []
        run = []

    for i in ids:
        if role[i] == "Preview":
            # background(s) = trailing 240s right before this preview
            bgs = []
            while pending and role[pending[-1]] == "Background":
                bgs.insert(0, pending.pop())
            head = []
            while bgs and pending and role[pending[-1]] == "Hand":
                head.insert(0, pending.pop())  # hands right before a bg block = this face
            if pending and role[pending[0]] == "Background":
                head, pending = pending + head, []  # bg + its parts before preview = this face
            if pending:
                flush()
            f = ClockFace(
                f"Clock face {len(faces) + 1}",
                i,
                [("Background" if role[h] == "Background" else role[h], h) for h in head]
                + [("Background", b) for b in bgs]
                + [("Preview", i)],
            )
            faces.append(f)
            run.append(f)
        else:
            pending.append(i)
    flush()
    _assign_backgrounds_by_look(db, faces)
    _opaque_overlays_are_backgrounds(db, faces)
    _share_hands(db, faces)
    return faces


def _opaque_overlays_are_backgrounds(db: SilverImagesDB, faces) -> None:
    """A fully opaque 240x240 'overlay' hides everything under it, so it is really another
    copy/state of the dial. Treat it as a Background copy and re-pick the copy that
    matches the face thumbnail as the one the preview shows."""
    for f in faces:
        changed = False
        for n, (r, i) in enumerate(f.parts):
            if (
                r == "Overlay"
                and db.images[i].to_pil().convert("RGBA").getchannel("A").getextrema()[0] == 255
            ):
                f.parts[n] = ("Background", i)
                changed = True
        if changed and f.preview:
            ps = _sig(db, f.preview)
            f.primary = min(f.backgrounds(), key=lambda i: _dist(_sig(db, i), ps))


def _assign_hands_to_their_background(db: SilverImagesDB, faces, role) -> None:
    """Hands stored right after a background (at most 2 small images in between)
    belong to that background's face."""
    {i: k for k, f in enumerate(faces) for r, i in f.parts}
    bg_owner = {i: k for k, f in enumerate(faces) for i in f.backgrounds()}
    for k, f in enumerate(faces):
        for r, i in list(f.parts):
            if r != "Hand":
                continue
            j, gap = i - 1, 0
            while j in role and role[j] != "Background" and gap <= 4:
                j -= 1
                gap += 1
            if j in bg_owner and bg_owner[j] != k and gap <= 4:
                # count only non-hand items in the gap
                between = [x for x in range(j + 1, i) if role.get(x) != "Hand"]
                if len(between) <= 2:
                    f.parts = [(rr, ii) for rr, ii in f.parts if ii != i]
                    faces[bg_owner[j]].parts.append(("Hand", i))


def _shape_dist(db: SilverImagesDB, a, b) -> float:
    """Colour-blind layout difference of two thumbnails (0 = same design)."""

    def g(i):
        im = db.images[i].to_pil().convert("L").resize((16, 16), Image.Resampling.BILINEAR)
        v = list(im.getdata())
        m = sum(v) / len(v)
        d = [x - m for x in v]
        n = (sum(x * x for x in d) ** 0.5) or 1
        return [x / n for x in d]

    x, y = g(a), g(b)
    return 1 - sum(p * q for p, q in zip(x, y))


def _share_hands(db: SilverImagesDB, faces) -> None:
    """Colour variants share one hand set (e.g. the pastel faces): an analog-looking
    face without hands or digits borrows the nearest earlier face's hands."""
    from .home_render import digit_set

    for k, f in enumerate(faces):
        if f.hands() or digit_set(db, f):
            continue
        for j in range(k - 1, max(-1, k - 6), -1):
            own = [i for r, i in faces[j].parts if r == "Hand"]
            if own and _shape_dist(db, f.preview, faces[j].preview) < 0.35:
                f.parts += [("Hand (shared)", i) for i in own]
                break


def _sig(db: SilverImagesDB, iid):
    im = db.images[iid].to_pil().convert("RGB").resize((12, 12), Image.Resampling.BILINEAR)
    return list(im.getdata())


def _dist(a, b):
    return sum((x[0] - y[0]) ** 2 + (x[1] - y[1]) ** 2 + (x[2] - y[2]) ** 2 for x, y in zip(a, b))


def _assign_backgrounds_by_look(db: SilverImagesDB, faces) -> None:
    """ID order alone mis-groups some backgrounds (e.g. the pastel faces store all
    their backgrounds in one block). Move every opaque 240x240 background to the
    face whose own 79x79 thumbnail it resembles most (searching nearby faces), and
    pick each face's primary background the same way."""
    psig = {k: _sig(db, f.preview) for k, f in enumerate(faces) if f.preview}
    moves = []
    for k, f in enumerate(faces):
        for r, i in list(f.parts):
            if r != "Background":
                continue
            bs = _sig(db, i)
            near = [j for j in range(max(0, k - 1), min(len(faces), k + 6)) if j in psig]
            best = min(near, key=lambda j: _dist(bs, psig[j]))
            db_, dk = _dist(bs, psig[best]), _dist(bs, psig.get(k, psig[best]))
            # only clear matches: near-identical to the other thumbnail, far from ours
            prev = faces[k - 1].preview if k > 0 else None
            if (
                prev is not None
                and i == prev + 1
                and (k - 1) in psig
                and _dist(bs, psig[k - 1]) < dk
            ):
                moves.append((k, k - 1, i))  # alternate background stored right after its preview
            elif best != k and db_ < 600_000 and db_ < 0.2 * dk:
                moves.append((k, best, i))
    for k, best, i in moves:
        # the background moves together with the parts stored right after it
        ids = {j for _, j in faces[k].parts}
        roles = dict((j, r) for r, j in faces[k].parts)
        grp, j = [i], i + 1
        while j in ids and roles[j] not in ("Background", "Preview", "Overlay"):
            grp.append(j)
            j += 1
        faces[k].parts = [(r, x) for r, x in faces[k].parts if x not in grp]
        faces[best].parts = (
            [("Background", i)] + [(roles[x], x) for x in grp[1:]] + faces[best].parts
        )
    for k, f in enumerate(faces):
        bgs = f.backgrounds()
        if bgs and k in psig:
            f.primary = min(bgs, key=lambda i: _dist(_sig(db, i), psig[k]))


def _thumb_key(db: SilverImagesDB, iid):
    im = db.images[iid].to_pil().convert("RGB").resize((12, 12))
    return list(im.getdata())


# Settings > General > Wallpaper on nano 6G 1.2 (36B10147): one entry per 79x79 picker
# thumbnail, in thumbnail-ID order (3 per row). Each maps to the full-screen 240x240
# image(s) it stands for. Textured thumbnails are zoomed crops, so they were matched by a
# multi-scale crop search (scripts in docs/WALLPAPERS.md) plus visual check; where two stock
# images are equally good matches (near-twins) both are written.
SETTINGS_WALLPAPERS = [
    (0x322, (0x30D, 0x30C)),  # chalkboard (two near-identical copies)
    (0x323, (0x30E,)),  # blossoms
    (0x324, (0x30F,)),  # denim
    (0x325, (0x310,)),  # green triangles
    (0x326, (0x311,)),  # red triangles
    (0x327, (0x312,)),  # water drops
    (0x328, (0x313,)),  # ripples
    (0x329, (0x315, 0x314, 0x316)),  # dark weave (three near-identical copies)
    (0x32A, (0x319,)),  # purple pattern
    (0x32B, (0x31A,)),  # crumpled
    (0x32C, (0x31C,)),  # pink pattern
    (0x32D, (0x31D,)),  # red pattern
    (0x32E, (0x31F,)),  # blue dots
    (0x32F, (0x320,)),  # pink dots
    (0x330, (0x321,)),  # orange dots
    (0x331, (0x332,)),
    (0x333, (0x334, 0x335)),
    (0x336, (0x337,)),
    (0x338, (0x339,)),
    (0x33A, (0x33B,)),
    (0x33C, (0x33D,)),
    (0x33E, (0x33F,)),
    (0x340, (0x341,)),
    (0x342, (0x343,)),
]
WALL_COLS = 3  # Settings picker and the app's Wallpapers tab both show 3 per row


def _settings_table(db: SilverImagesDB):
    out = []
    for t, fulls in SETTINGS_WALLPAPERS:
        t = BASE + t
        fulls = [BASE + f for f in fulls]
        if t not in db.images or (db.images[t].width, db.images[t].height) != (79, 79):
            return None
        if any(
            f not in db.images or (db.images[f].width, db.images[f].height) != (240, 240)
            for f in fulls
        ):
            return None
        out.append((t, fulls))
    return out


_COPIES: dict = {}


def wallpaper_copies(full_id: int) -> list[int]:
    """Every stock image written when this wallpaper is edited (main one first)."""
    return list(_COPIES.get(full_id, [full_id]))


def wallpapers(db: SilverImagesDB) -> list[tuple[str, int, int | None]]:
    """(name, main 240x240 id, 79x79 Settings thumbnail id), in Settings order."""
    table = _settings_table(db)
    if table is None:  # unknown firmware layout: old heuristic
        return _wallpapers_by_look(db)
    res = []
    for n, (t, fulls) in enumerate(table):
        _COPIES[fulls[0]] = fulls
        res.append(
            (f"Wallpaper {n + 1} (row {n // WALL_COLS + 1}, col {n % WALL_COLS + 1})", fulls[0], t)
        )
    return res


def _wallpapers_by_look(db: SilverImagesDB) -> list[tuple[str, int, int | None]]:
    """(friendly name, 240x240 id, matching 79x79 picker thumbnail id or None)."""
    lo, hi = WALLPAPER_RANGE
    walls = [
        i
        for i in sorted(db.images)
        if lo <= i <= hi and (db.images[i].width, db.images[i].height) == (240, 240)
    ]
    thumbs = [
        i
        for i in sorted(db.images)
        if lo <= i <= hi and (db.images[i].width, db.images[i].height) == (79, 79)
    ]
    tk = {t: _thumb_key(db, t) for t in thumbs}
    res, used = [], set()
    for n, w in enumerate(walls, 1):
        wk = _thumb_key(db, w)
        best, bd = None, 1e18
        for t, k in tk.items():
            d = sum(
                (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2 for a, b in zip(wk, k)
            )
            if d < bd:
                best, bd = t, d
        thumb = best if best is not None and bd < 144 * 3 * 900 and best not in used else None
        if thumb:
            used.add(thumb)
        res.append((f"Wallpaper {n}", w, thumb))
    return res


def static_glyphs(db: SilverImagesDB, face) -> set:
    """Digit / date glyphs of a face (small "Digits / detail" bitmaps and any run of 10+
    same-size dial bitmaps). The OS draws them at per-face positions we cannot read, so the
    Clock Faces tab hides them from editing (Advanced: all images still lists them)."""
    out = {i for r, i in face.parts if r == "Digits / detail"}
    run = []
    for r, i in face.parts + [("", None)]:
        im = db.images.get(i) if i is not None else None
        if run and im is not None and r == "Dial detail" and (im.width, im.height) == run[0][1]:
            run.append((i, run[0][1]))
            continue
        if len(run) >= 10:
            out |= {j for j, _ in run}
        run = [(i, (im.width, im.height))] if (im is not None and r == "Dial detail") else []
    return out


# Settings > Date & Time > Clock Face on fw 1.2 offers 18 faces (Apple: 9 analog, 4 digital,
# 1 analog/digital, Mickey, Minnie, Kermit, Animal; some "reflect the colour of your iPod nano").
# The DB holds 38 face styles: 14 single faces + 4 case-colour groups of 6 variants
# (app faces 3-8, 11-16, 21-26, 27-32); 14 + 4 = 18. The picker order is assumed to be the DB
# order with each colour group collapsed to one entry (not device-verified for every position).
COLOUR_GROUPS = [(3, 8), (11, 16), (21, 26), (27, 32)]


def picker_entries(n_faces: int = 38) -> list[list[int]]:
    """[[app face numbers]] per Clock Face picker position (1-based numbers, in picker order)."""
    if n_faces != 38:
        return [[k] for k in range(1, n_faces + 1)]
    out, k = [], 1
    while k <= n_faces:
        g = next((g for g in COLOUR_GROUPS if g[0] == k), None)
        if g:
            out.append(list(range(g[0], g[1] + 1)))
            k = g[1] + 1
        else:
            out.append([k])
            k += 1
    return out


def picker_position(face_no: int, n_faces: int = 38) -> int:
    for pos, nums in enumerate(picker_entries(n_faces), 1):
        if face_no in nums:
            return pos
    return 0
