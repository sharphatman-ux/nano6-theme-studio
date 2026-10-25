# SPDX-License-Identifier: GPL-3.0-only
"""Build the 'Rock Theme' sample home icons from original art.

usage: python make_rock_theme_icons.py samples/rock-theme/source <out_dir> <fw.ipsw>"""

import sys
from pathlib import Path

from PIL import Image, ImageOps

from nano6studio.core import home_render as H
from nano6studio.core.icons import ART, apply_app_art
from nano6studio.core.loader import load_ipsw, make_project
from nano6studio.core.validate import check

src, out = Path(sys.argv[1]), Path(sys.argv[2])
fw = load_ipsw(Path(sys.argv[3]))
proj = make_project(fw)
db = proj._db
proj.name = "Rock Theme"
apps = H.order_apps(fw.catalog["apps"], include_hidden=True)
(out / "art").mkdir(parents=True, exist_ok=True)
(out / "native").mkdir(exist_ok=True)
for a in apps:
    im = Image.open(src / f"{a.name}.jpg").convert("RGB")
    art = ImageOps.fit(im, (1024, 1024), Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    art.save(out / "art" / f"{a.name}.png")  # importable by name (AI import)
    res = apply_app_art(proj, a, art.resize((ART, ART), Image.Resampling.LANCZOS))
    for iid, v in res.items():
        v.save(out / "native" / f"{a.name}_{v.width}x{v.height}_{iid:08x}.png")
print("apps", len(apps))
data = db.rebuild()
probs = check(data, fw.stock_silver)
print("validator:", probs or "OK")
proj.save_n6theme(out / "rock-theme.n6theme")
# contact sheet
cell = 180
cols = 6
rows = (len(apps) + cols - 1) // cols
sheet = Image.new("RGBA", (cols * cell, rows * (cell + 10)), (24, 24, 26, 255))
for k, a in enumerate(apps):
    v = db.images[a.large or a.ids[0]].to_pil().convert("RGBA")
    sheet.alpha_composite(
        v, ((k % cols) * cell + (cell - v.width) // 2, (k // cols) * (cell + 10) + 8)
    )
sheet.save(out / "contact-sheet.png")
home = H.render_home(db, proj.wallpaper_id, apps, 0, True, 0)
home.save(out / "home-preview-240.png")
H.render_home(db, proj.wallpaper_id, apps, 0, False, 0).save(out / "home-preview-240-large.png")
