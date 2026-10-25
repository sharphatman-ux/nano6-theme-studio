# SPDX-License-Identifier: GPL-3.0-only
"""AI prompt builder: sizes per slot, sprite-sheet import order, filename matching."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path

from firmware import require_ipsw  # noqa: E402
from PIL import Image

from nano6studio.core import ai_prompts as P

APPS = list(P.GLYPHS)
FIX = Path(__file__).parent / "fixtures"


def test_prompts_are_short_one_image_each():
    slots = P.slots_for(
        "Everything", APPS, hands=[(14, 110), (10, 120)], digits=(30, 60), extras=True
    )
    ps = P.build_prompts("cyberpunk neon", slots)  # default: one image per prompt
    assert len(ps) == 18 + 1 + 2 + 1  # icons, face, 2 hands, wallpaper
    for title, text, sl in ps:
        assert len(sl) == 1 and len(text) < 260, title  # short, plain, one asset
        assert "cyberpunk neon" in text and "No text" in text or "no text" in text
    icon = dict((t, x) for t, x, _ in ps)["Music icon"]
    assert "512x512 pixels" in icon and "transparent background" in icon and "music notes" in icon
    face = dict((t, x) for t, x, _ in ps)["Clock face background"]
    assert "240x240 pixels" in face and "No clock hands" in face
    assert "14x110 pixels" in dict((t, x) for t, x, _ in ps)["Clock hand 1"]
    assert not any(s.kind == "digits" for s in slots)  # digits are static: never prompted
    single = P.build_prompts("x", P.slots_for("Single icon", APPS, "Podcasts"))
    assert len(single) == 1 and "microphone" in single[0][1]


def test_sheet_mode_is_one_small_prompt():
    ps = P.build_prompts("pastel", P.slots_for("Everything", APPS), sheet=True)
    assert [t for t, *_ in ps] == ["home icon sheet", "Clock face background", "Wallpaper"]
    sheet = ps[0][1]
    assert "1280x1024 pixels" in sheet and "5 columns x 4 rows" in sheet and len(sheet) < 600
    assert sheet.index("a play button") < sheet.index("a piano") and len(ps[0][2]) == 18


def _gutter_sheet(cols, rows, cell=200, gut=12):
    sheet = Image.new("RGBA", (cols * (cell + gut) + gut, rows * (cell + gut) + gut), "white")
    for n in range(cols * rows):
        x = gut + (n % cols) * (cell + gut)
        y = gut + (n // cols) * (cell + gut)
        sheet.paste((n * 10, 200 - n * 8, 7, 255), (x, y, x + cell, y + cell))
    return sheet


def test_sprite_sheet_import_order():
    slots = P.slots_for("All home icons", APPS)
    got = P.assign([("sheet.png", _gutter_sheet(5, 4))], slots)
    assert [
        s.name for s, _ in got
    ] == APPS  # 18 cells used, 2 unused stay plain (and the rest ignored)
    for n, (s, im) in enumerate(got):
        assert im.getpixel((im.width // 2, im.height // 2))[:2] == (n * 10, 200 - n * 8)


def test_real_ai_sheet():
    sheet = Image.open(FIX / "sample_ai_sheet.jpg")
    tiles = P.detect_tiles(sheet, P.slots_for("Everything", APPS))
    icons = [t for t in tiles if t.kind == "icon"]
    assert [t.slot for t in icons] == APPS
    assert [t.slot for t in icons if t.clipped] == ["Composers"]
    assert [t.kind for t in tiles if t.kind != "icon"] == ["face", "wallpaper"]
    face = next(t for t in tiles if t.kind == "face")
    wall = next(t for t in tiles if t.kind == "wallpaper")
    assert face.box[0] > 500 and wall.box[0] > face.box[0] and min(face.w, face.h) > 200
    for t in icons:
        assert 150 <= t.h <= 170 and (t.clipped or 150 <= t.w <= 170)  # labels trimmed off


def test_filename_matching_and_background_removal():
    slots = P.slots_for("All home icons", APPS)
    red = Image.new("RGBA", (300, 200), (255, 255, 255, 255))
    red.paste((200, 0, 0, 255), (100, 50, 200, 150))
    got = P.assign([("my_settings.png", red), ("a.png", red), ("Voice-Memos_v2.png", red)], slots)
    names = [s.name for s, _ in got]
    assert names == ["Now Playing", "Voice Memos", "Settings"]
    cut = P.remove_plain_background(red)
    assert cut.getpixel((0, 0))[3] == 0 and cut.getpixel((150, 100)) == (200, 0, 0, 255)
    fitted = P.fit(cut, 256, 256)
    assert fitted.size == (256, 256)
    bb = fitted.getchannel("A").getbbox()  # 100x100 square stays square (no stretch)
    assert abs((bb[2] - bb[0]) - (bb[3] - bb[1])) <= 2


def test_dialog_imports_into_project():

    from PySide6.QtWidgets import QApplication

    from nano6studio.core.loader import load_ipsw, make_project
    from nano6studio.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    fw = load_ipsw(require_ipsw())
    w = MainWindow()
    w.attach(fw, make_project(fw))
    from nano6studio.ui.ai_dialog import AIPromptDialog

    d = AIPromptDialog(w)
    d.idea.setText("neon")
    d.scope.setCurrentText("All home icons")
    assert d.mode.currentIndex() == 0 and len(d.prompts) == 18  # single-image prompts by default
    d.mode.setCurrentIndex(1)
    assert "1280x1024" in d.text.toPlainText()
    d.copy()
    assert QApplication.clipboard().text() == d.text.toPlainText()
    assert d.import_images([("s.png", _gutter_sheet(5, 4))]) == 18
    a = w.all_apps[0]
    assert all(w.proj.is_manual(i) for i in a.ids)
    d.scope.setCurrentText("Clock face")
    d.import_images([("face.png", Image.new("RGBA", (512, 512), (9, 9, 200, 255)))])
    f = d._face()
    assert all(
        w.proj._db.images[b].to_pil().convert("RGB").getpixel((120, 120)) == (9, 9, 200)
        for b in f.backgrounds()
    )


def test_sample_sheet_applies_everything(tmp_path):
    """All 18 apps (large + small bitmaps) and every clock-dial copy are written and previewed."""
    from PySide6.QtWidgets import QApplication

    from nano6studio.core import home_render as H
    from nano6studio.core.loader import load_ipsw, make_project
    from nano6studio.ui.ai_dialog import AIPromptDialog
    from nano6studio.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    fw = load_ipsw(require_ipsw())
    w = MainWindow()
    w.attach(fw, make_project(fw))
    db = w.proj._db
    face = w.cat["clock_faces"][0]
    before_home = [
        H.render_home(db, w.proj.wallpaper_id or w.cat["wallpapers"][0][1], w.apps, p, s, 0)
        for s in (False, True)
        for p in range(H.page_count(w.apps, s))
    ]
    before_clock = H.render_clock(db, face)
    d = AIPromptDialog(w)
    d.scope.setCurrentText("Everything")
    items = d.review_items([("sheet.jpg", Image.open(FIX / "sample_ai_sheet.jpg").convert("RGBA"))])
    assert [n for _, n, _ in items] == APPS + ["Clock face background", "Wallpaper"]
    assert d.import_pairs([(n, im) for im, n, _ in items]) == 20
    for a in w.all_apps:
        sizes = {(db.images[i].width, db.images[i].height) for i in a.ids}
        assert all(w.proj.is_manual(i) for i in a.ids), a.name
        assert (154, 164) in sizes and (105, 105) in sizes, (a.name, sizes)
    for b in face.backgrounds():
        assert w.proj.is_manual(b)
    assert w.proj.is_manual(face.preview)
    assert H.render_clock(db, face).tobytes() != before_clock.tobytes()
    wid = w.proj.wallpaper_id or w.cat["wallpapers"][0][1]
    after_home = [
        H.render_home(db, wid, w.apps, p, s, 0)
        for s in (False, True)
        for p in range(H.page_count(w.apps, s))
    ]
    assert all(a.tobytes() != b.tobytes() for a, b in zip(after_home, before_home))


def test_no_copyright_wording_in_any_prompt():
    import re

    for scope in P.SCOPES:
        for sheet in (False, True):
            t = P.build_prompt(
                "green phosphor terminal",
                P.slots_for(scope, APPS, "Music", [(34, 148)] * 2, (20, 33), True),
                sheet,
            )
            assert not re.search(r"copyright|trademark|original art|logo", t, re.I), scope
            assert "x" in t and "pixels" in t


def _win():
    from PySide6.QtWidgets import QApplication

    from nano6studio.core.loader import load_ipsw, make_project
    from nano6studio.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    fw = load_ipsw(require_ipsw())
    w = MainWindow()
    w.attach(fw, make_project(fw))
    w.show()
    app.processEvents()
    return app, w


def _pick(w, app, tab, row):
    w.tabs.setCurrentWidget(tab)
    tab.setCurrentRow(row)
    app.processEvents()


def test_quick_options_prompts_and_copy():
    import re

    from PySide6.QtWidgets import QApplication

    from nano6studio.ui.ai_dialog import AIQuickDialog

    app, w = _win()
    d = AIQuickDialog(w)
    d.style.setText("rockabilly tattoo flash")
    assert [r.text().split("  –")[0] for r in d.radios] == list(P.OPTIONS)
    seen = {}
    for o in P.OPTIONS:
        d.set_option(o)
        app.processEvents()
        t = d.text.toPlainText()
        seen[o] = t
        assert t == d.prompt() and "rockabilly tattoo flash" in t and len(t) < 1100
        assert not re.search(r"copyright|trademark|original art|logo|===", t, re.I)
        d.copy()
        assert QApplication.clipboard().text() == t
    assert "1536x1024" in seen["Everything"] and "6 columns x 4 rows" in seen["Everything"]
    assert (
        "hour hand" in seen["Everything"]
        and "wallpaper" in seen["Everything"]
        and "music notes icon" in seen["Everything"]
    )
    assert "1280x1024" in seen["Just icons"] and "hand" not in seen["Just icons"]
    assert seen["Just backgrounds"].startswith("A square wallpaper, 240x240")
    wf = seen["Watch face + hands"]
    assert (
        "1024x256" in wf and "4 columns x 1 rows" in wf and "second hand" in wf and "No text" in wf
    )
    assert AIQuickDialog(w).style.text() == "rockabilly tattoo flash"  # remembered


def _grid(cols, rows, colours, cell=256, gap=8):
    im = Image.new("RGBA", (cols * cell, rows * cell), "white")
    for k, c in enumerate(colours):
        x, y = (k % cols) * cell, (k // cols) * cell
        im.paste(c, (x + gap, y + gap, x + cell - gap, y + cell - gap))
    return im


def test_quick_import_watch_sheet_to_selected_face(tmp_path):
    from nano6studio.core import home_render as H
    from nano6studio.ui.ai_dialog import AIQuickDialog

    app, w = _win()
    w.select_face(20)
    app.processEvents()
    f = w.sel[1]
    d = AIQuickDialog(w)
    d.set_option("Watch face + hands")
    sheet = _grid(
        4, 1, [(10, 200, 30, 255), (200, 0, 0, 255), (0, 0, 200, 255), (200, 200, 0, 255)]
    )
    sheet.paste(
        (255, 255, 255, 255), (256 + 8, 8, 256 + 100, 248)
    )  # hand cells: tall bars on white
    for k in (1, 2, 3):
        sheet.paste((255, 255, 255, 255), (k * 256 + 8, 8, k * 256 + 248, 248))
        sheet.paste(
            [(200, 0, 0, 255), (0, 0, 200, 255), (200, 200, 0, 255)][k - 1],
            (k * 256 + 118, 30, k * 256 + 138, 230),
        )
    assert d.import_images([("s.png", sheet)], review=False) == 4
    db = w.proj._db
    assert all(w.proj.is_manual(b) for b in f.backgrounds()) and w.proj.is_manual(f.preview)
    assert db.images[f.background].to_pil().convert("RGB").getpixel((120, 120))[1] > 150
    lab = {v: k for k, v in H.hand_labels(db, f).items()}
    for name in P.HAND_NAMES:
        assert w.proj.is_manual(lab[name]), name


def test_quick_import_icons_sheet_and_separate_backgrounds(tmp_path):
    from nano6studio.ui.ai_dialog import AIQuickDialog

    app, w = _win()
    d = AIQuickDialog(w)
    d.set_option("Just icons")
    assert d.import_images([("sheet.png", _gutter_sheet(5, 4))], review=False) == 18
    assert all(w.proj.is_manual(i) for a in w.all_apps for i in a.ids)
    d.set_option("Just backgrounds")
    wid = w.proj.wallpaper_id or w.cat["wallpapers"][0][1]
    assert (
        d.import_images(
            [("wall.png", Image.new("RGBA", (500, 500), (9, 9, 200, 255)))], review=False
        )
        == 1
    )
    assert w.proj._db.images[wid].to_pil().convert("RGB").getpixel((120, 120)) == (9, 9, 200)
