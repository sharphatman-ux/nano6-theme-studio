"""Diagnostic IPSW: stamp every candidate wallpaper image (all non-clock 240x240 images and the
79x79 wallpaper thumbnails) with its own hex ID, so the iPod shows which asset it really draws."""

import sys
from pathlib import Path

from PIL import ImageDraw, ImageFont

from nano6studio.core.firmware_pack import build_themed_ipsw, verify_themed_ipsw
from nano6studio.core.loader import load_ipsw
from nano6studio.core.validate import check

B = 0x0DAD0000
ipsw, out = Path(sys.argv[1]), Path(sys.argv[2])
fw = load_ipsw(ipsw)
db = fw.db
stock = db.raw
try:
    font = (
        ImageFont.truetype(str(Path(sys.argv[3])), 64)
        if len(sys.argv) > 3
        else ImageFont.load_default(size=64)
    )
except Exception:
    font = ImageFont.load_default()
targets = [
    i
    for i, im in db.images.items()
    if ((im.width, im.height) == (240, 240) and not (0x349 <= i - B <= 0x4EC))
    or ((im.width, im.height) == (79, 79) and 0x322 <= i - B <= 0x342)
]
for i in sorted(targets):
    im = db.images[i]
    if im.fmt == 0x0004:
        continue
    base = im.to_pil().convert("RGBA")
    d = ImageDraw.Draw(base)
    s = im.width
    tag = f"{i - B:X}"
    f = font if s >= 200 else ImageFont.load_default(size=26)
    box = d.textbbox((0, 0), tag, font=f)
    tw, th = box[2] - box[0], box[3] - box[1]
    x, y = (s - tw) // 2, (s - th) // 2
    d.rectangle((x - 6, y - 6, x + tw + 6, y + th + 10), fill=(255, 255, 0, 255))
    d.text((x - box[0], y - box[1]), tag, font=f, fill=(0, 0, 0, 255))
    im.set_pil(base)
new = db.rebuild()
probs = check(new, stock)
assert not probs, probs[:5]
build_themed_ipsw(ipsw, new, out)
assert verify_themed_ipsw(out, new)["silver_matches"]
print(out, "stamped", len(targets), "images:", " ".join(f"{i - B:X}" for i in sorted(targets)))
