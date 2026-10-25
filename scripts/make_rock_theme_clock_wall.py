# SPDX-License-Identifier: GPL-3.0-only
"""Add the Rock Theme clock face (face 20) and wallpaper (Settings row 1, col 1) to the pack.

usage: python make_rock_theme_clock_wall.py <out_dir> <fw.ipsw>
<out_dir> must hold rock-theme.n6theme from make_rock_theme_icons.py."""

import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageOps

from nano6studio.core import catalog as C
from nano6studio.core import firmware_pack as F
from nano6studio.core import home_render as H
from nano6studio.core.loader import load_ipsw
from nano6studio.core.project import ThemeProject
from nano6studio.core.validate import check

OUT = Path(sys.argv[1])
PACK = OUT / "rock-theme.n6theme"
FW = Path(sys.argv[2])
ART = Path(__file__).resolve().parents[1] / "samples" / "rock-theme"
fw = load_ipsw(FW)
db = fw.db
stock = fw.stock_silver
proj = ThemeProject.load_n6theme(PACK, db=db)
BONE, BLACK, RED, GOLD = (
    (236, 224, 196, 255),
    (12, 10, 10, 255),
    (178, 22, 26, 255),
    (201, 158, 74, 255),
)

# ---- clock: face 20 (background + hour/minute/second hands, no digit readout) ----
face = C.clock_faces(db)[19]
assert face.name == "Clock face 20"
dial = ImageOps.fit(
    Image.open(ART / "clock-dial-art.jpg").convert("RGB"), (1024, 1024), Image.Resampling.LANCZOS
)
dial = dial.crop((0, 0, 1024, 1024)).resize((240, 240), Image.Resampling.LANCZOS)
dial.save(OUT / "clock-dial-240.png")
for b in face.backgrounds():
    proj.apply_replacement(b, dial, "clock")

# hands drawn on the exact stock canvases (34x148) with the stock geometry:
# hour y48-120, minute y0-120, second y28-139 with its pivot dot at y116, all centred on x=17.
SS = 4


def hand(kind):
    W, Hh = 34, 148
    im = Image.new("RGBA", (W * SS, Hh * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx = 17 * SS
    s = lambda v: int(v * SS)
    if kind in ("hour", "minute"):
        top = 48 if kind == "hour" else 2
        bot = 120
        hw = 6.5 if kind == "hour" else 5.0
        # spade-tipped tattoo hand: black outline, bone fill
        poly = [
            (cx, s(top)),
            (cx + s(hw + 1.5), s(top + 9)),
            (cx + s(hw * 0.55), s(top + 12)),
            (cx + s(hw * 0.75), s(bot)),
            (cx - s(hw * 0.75), s(bot)),
            (cx - s(hw * 0.55), s(top + 12)),
            (cx - s(hw + 1.5), s(top + 9)),
        ]
        d.polygon(poly, fill=BLACK)
        inner = [(x + (cx - x) * 0.38 / (1 + abs(cx - x) / s(6)) * 0, y) for x, y in poly]
        sh = s(1.2)
        inner = [
            (cx, s(top) + sh * 2),
            (cx + s(hw + 1.5) - sh * 1.6, s(top + 9)),
            (cx + s(hw * 0.55) - sh * 0.4, s(top + 12) - sh * 0.2),
            (cx + s(hw * 0.75) - sh, s(bot) - sh),
            (cx - s(hw * 0.75) + sh, s(bot) - sh),
            (cx - s(hw * 0.55) + sh * 0.4, s(top + 12) - sh * 0.2),
            (cx - s(hw + 1.5) + sh * 1.6, s(top + 9)),
        ]
        d.polygon(inner, fill=BONE)
        d.line(
            (cx, s(top + 14), cx, s(bot - 4)), fill=(150, 20, 24, 255), width=s(0.6)
        )  # thin red inlay
    else:
        d.rectangle((cx - s(1.4), s(28), cx + s(1.4), s(139)), fill=BLACK)
        d.rectangle((cx - s(0.7), s(29), cx + s(0.7), s(138)), fill=RED)
        d.ellipse((cx - s(6), s(110), cx + s(6), s(122)), fill=BLACK)  # pivot dot at y116
        d.ellipse((cx - s(4.8), s(111.2), cx + s(4.8), s(120.8)), fill=RED)
        d.ellipse((cx - s(1.6), s(114.4), cx + s(1.6), s(117.6)), fill=GOLD)
        d.polygon(
            [(cx, s(30)), (cx + s(4), s(42)), (cx, s(39)), (cx - s(4), s(42))], fill=BLACK
        )  # arrow tip
        d.polygon(
            [(cx, s(32)), (cx + s(2.6), s(40.5)), (cx, s(38)), (cx - s(2.6), s(40.5))], fill=RED
        )
    return im.resize((W, Hh), Image.Resampling.LANCZOS)


labels = H.hand_labels(db, face)
for i in face.hands():
    kind = labels[i].split()[0].lower()
    assert (db.images[i].width, db.images[i].height) == (34, 148)
    h = hand(kind)
    h.save(OUT / f"clock-hand-{kind}-34x148.png")
    proj.apply_replacement(i, h, "clock")
H.sync_face_thumbnail(proj, face)
proj.clock_id = face.background

# ---- wallpaper: Settings row 1, column 1 (+ its twin copy) ----
walls = C.wallpapers(db)
name, wid, thumb = walls[0]
w = ImageOps.fit(
    Image.open(ART / "wallpaper-art.jpg").convert("RGB"), (240, 240), Image.Resampling.LANCZOS
)
w = ImageEnhance.Brightness(w).enhance(0.9)
w.save(OUT / "wallpaper-240.png")
for c in C.wallpaper_copies(wid):
    proj.apply_replacement(c, w, "wallpaper")
if thumb:
    proj.apply_replacement(thumb, w.resize((79, 79), Image.Resampling.LANCZOS), "wallpaper")
proj.wallpaper_id = wid
proj.save_n6theme(PACK)
print(
    "wallpaper",
    name,
    hex(wid),
    "copies",
    [hex(c) for c in C.wallpaper_copies(wid)],
    "thumb",
    hex(thumb or 0),
)

# ---- previews through the app's renderer ----
H.render_clock(db, face).save(OUT / "preview-clock-1009.png")
apps = H.order_apps(fw.catalog["apps"], include_hidden=True)
H.render_home(db, wid, apps, 0, True, 0).save(OUT / "preview-home-wallpaper.png")
H.render_home(db, wid, apps, 0, False, 0).save(OUT / "preview-home-wallpaper-large.png")
db.images[face.preview].to_pil().save(OUT / "preview-clock-thumb-79.png")

# ---- validator + test export (deleted, never shipped) ----
data = db.rebuild()
print("validator:", check(data, stock) or "OK")
with tempfile.TemporaryDirectory() as scratch:
    t = Path(scratch) / "rock_theme_test.ipsw"
    F.build_themed_ipsw(FW, data, t)
    print(F.verify_themed_ipsw(t, data))
print("edits", len(proj.edits))
