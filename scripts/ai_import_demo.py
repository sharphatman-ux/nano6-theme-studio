"""Before/after of importing tests/fixtures/sample_ai_sheet.jpg -> nano6-shots/ai_import_test.png"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path

from PIL import Image, ImageDraw
from PySide6.QtWidgets import QApplication

from nano6studio.core import home_render as H
from nano6studio.core.loader import load_ipsw, make_project
from nano6studio.ui.ai_dialog import AIPromptDialog
from nano6studio.ui.main_window import MainWindow

app = QApplication([])
fw = load_ipsw(Path(sys.argv[1]))
w = MainWindow()
w.attach(fw, make_project(fw))
db = w.proj._db
face = w.cat["clock_faces"][0]
wid = w.proj.wallpaper_id or w.cat["wallpapers"][0][1]


def shots():
    out = [H.render_home(db, wid, w.apps, p, True, 0) for p in range(H.page_count(w.apps, True))]
    out += [
        H.render_home(db, wid, w.apps, p, False, 0) for p in range(H.page_count(w.apps, False))
    ][-6:]
    return out + [H.render_clock(db, face)]


before = shots()
sheet = Image.open(Path(__file__).parents[1] / "tests/fixtures/sample_ai_sheet.jpg").convert("RGBA")
d = AIPromptDialog(w)
d.scope.setCurrentText("Everything")
items = d.review_items([("sheet.jpg", sheet)])
d.import_pairs([(n, im) for im, n, _ in items])
after = shots()
n = len(before)
W = 250 * n + 10
S = Image.new("RGB", (W, 260 + 520 + 40), "white")
dr = ImageDraw.Draw(S)
for k, (im, name, clip) in enumerate(items):
    x = 10 + k * 120 % (W - 120)
    y = 10 + (k * 120 // (W - 120)) * 130
    S.paste(im.convert("RGB").resize((96, 96)), (x, y + 14))
    dr.text((x, y), ("! " if clip else "") + name, fill="red" if clip else "black")
for r, row in enumerate((before, after)):
    dr.text((10, 280 + r * 265), "BEFORE" if r == 0 else "AFTER", fill="black")
    for k, im in enumerate(row):
        S.paste(im.convert("RGB"), (10 + k * 250, 295 + r * 265))
S.save(sys.argv[2])
print("saved", sys.argv[2], len(items))
