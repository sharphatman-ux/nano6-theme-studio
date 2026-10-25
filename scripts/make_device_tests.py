"""Two device-test IPSWs: (a) stock DB rebuilt with no edits, (b) one home icon recoloured.
Both go through the full pipeline (rebuild -> validator -> FAT -> MSE -> read-back) and are
checked against the upstream ipodhax encoder."""

import hashlib
import io
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parents[1] / "tests" / "upstream"))
from ipodhax.silverdb.pack import encode_image

from nano6studio.core import home_render as H
from nano6studio.core.firmware_pack import build_themed_ipsw, verify_themed_ipsw
from nano6studio.core.icons import app_art_from_db, apply_app_art
from nano6studio.core.loader import load_ipsw, make_project
from nano6studio.core.validate import check

ipsw, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
fw = load_ipsw(ipsw)
stock = fw.db.raw
rep = []
# (a)
a = fw.db.rebuild(force=True)
assert a == stock and check(a, stock) == []
pa = out / "test_a_stock_rebuild_no_edits.ipsw"
build_themed_ipsw(ipsw, a, pa)
assert verify_themed_ipsw(pa, a)["silver_matches"]
rep.append(f"(a) {pa.name}: DB == stock bytes: True; validator: pass")
# (b) recolour Music
fw = load_ipsw(ipsw)
proj = make_project(fw)
db = proj._db
app = next(x for x in H.order_apps(fw.catalog["apps"], include_hidden=True) if x.name == "Music")
art = app_art_from_db(db, app).convert("RGBA")
r, g, b, al = art.split()
art = Image.merge("RGBA", (b, r, g, al))  # hue swap: orange -> purple-ish
apply_app_art(proj, app, art)
bdb = db.rebuild()
probs = check(bdb, stock)
assert probs == [], probs
same = []
for iid in app.ids:
    im = db.images[iid]
    tmp = out / f"_{iid}_{im.fmt:04x}.png"
    im.to_pil().convert("RGBA").save(tmp)
    s = io.BytesIO()
    encode_image(iid, im.fmt, tmp, s)
    tmp.unlink()
    # re-encode the decoded pixels with ours too, so both encoders see identical input
    from nano6studio.core.silverimages import build_header, encode_pixels

    p = encode_pixels(im.to_pil(), im.fmt, im.bpp, im.width, im.height, im.stride)
    mine = build_header(im.fmt, im.bpp, im.width, im.height, iid, im.stride, len(p)) + p
    same.append((iid, f"{im.fmt:04x}", f"{im.width}x{im.height}", mine == s.getvalue()))
pb = out / "test_b_music_icon_recolor.ipsw"
build_themed_ipsw(ipsw, bdb, pb)
assert verify_themed_ipsw(pb, bdb)["silver_matches"]
rep.append(f"(b) {pb.name}: Music icon bitmaps {len(app.ids)} edited; validator: pass")
rep += [f"    {i} fmt {f} {s}: identical to upstream encode_image: {ok}" for i, f, s, ok in same]
for p in (pa, pb):
    rep.append(f"{p.name} sha256 {hashlib.sha256(p.read_bytes()).hexdigest()}")
(out / "README.txt").write_text(
    "Device test builds (EXPERIMENTAL). Install (a) first; if it boots, try (b).\n"
    "Recovery: hold Volume Down + Sleep/Wake through the logo until black, 1-2 s more, release;\n"
    "in iTunes Shift+click Restore iPod and choose the stock iPod_1.2_36B10147.ipsw.\n\n"
    + "\n".join(rep)
    + "\n"
)
print("\n".join(rep))
