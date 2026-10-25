# SPDX-License-Identifier: GPL-3.0-only
# Nano 6 Theme Studio - Copyright (C) 2026 sharphatman-ux and contributors. See LICENSE.
"""Build the original 'Phosphor Terminal' sample theme (green CRT terminal look).
All artwork is drawn procedurally here: no third-party assets, logos or fonts.
usage: python make_phosphor_terminal_theme.py <fw.ipsw> <out.n6theme> <preview_dir>"""

import math
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from nano6studio.core import catalog as C
from nano6studio.core import home_render as H
from nano6studio.core.icons import apply_app_art
from nano6studio.core.loader import load_ipsw, make_project

G = (20, 255, 106)
GD = (8, 120, 50)
BG = (4, 12, 7)
N = 256


def crt(im, strength=70, vig_k=0.6):
    im = im.convert("RGBA")
    glow = im.filter(ImageFilter.GaussianBlur(4))
    im = Image.alpha_composite(Image.blend(im, glow, 0.0), im)
    a0 = ImageChops.lighter(im.getchannel("A"), glow.getchannel("A"))
    im = ImageChops.add(im.convert("RGB"), glow.convert("RGB"), scale=1.0).convert("RGBA")
    im.putalpha(a0)
    w, h = im.size
    lines = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(lines)
    for y in range(0, h, 2 if h <= 260 else 3):
        d.line((0, y, w, y), fill=(0, 0, 0, strength))
    lines.putalpha(ImageChops.multiply(lines.getchannel("A"), a0))
    im = Image.alpha_composite(im, lines)
    vig = Image.new("L", (w, h), 0)
    ImageDraw.Draw(vig).ellipse((-w * 0.25, -h * 0.25, w * 1.25, h * 1.25), fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(w / 6))
    dark = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    dark.putalpha(ImageChops.invert(vig).point(lambda v: int(v * vig_k)))
    return Image.alpha_composite(im, dark)


def base_tile():
    im = Image.new("RGBA", (N, N), BG + (255,))
    d = ImageDraw.Draw(im)
    for k in range(0, N, 32):
        d.line((k, 0, k, N), fill=(10, 40, 20))
        d.line((0, k, N, k), fill=(10, 40, 20))
    d.rounded_rectangle((10, 10, N - 11, N - 11), 34, outline=G, width=5)
    return im, d


W = 13  # stroke


def glyph(name):
    im, d = base_tile()
    c = N / 2
    L = lambda *p: d.line(p, fill=G, width=W, joint="curve")
    E = lambda b, **k: d.ellipse(b, outline=G, width=W, **k)
    R = lambda b: d.rectangle(b, outline=G, width=W)
    if name == "Music":
        E((70, 160, 118, 200))
        E((140, 140, 188, 180))
        L(114, 180, 114, 70, 184, 52, 184, 160)
    elif name == "Now Playing":
        d.polygon([(100, 70), (100, 186), (190, 128)], outline=G, width=W)
        L(70, 70, 70, 186)
    elif name == "Radio":
        R((52, 104, 204, 196))
        L(80, 104, 170, 56)
        E((70, 124, 118, 172))
        for x in (140, 160, 180):
            L(x, 124, x, 176)
    elif name == "Fitness":
        E((112, 46, 144, 78))
        L(128, 82, 118, 140, 150, 196)
        L(118, 140, 84, 196)
        L(80, 110, 128, 96, 176, 116)
    elif name == "Clock":
        E((52, 52, 204, 204))
        L(c, c, c, 82)
        L(c, c, 166, 150)
        for a in range(12):
            r = math.radians(a * 30)
            d.line(
                (
                    c + 66 * math.sin(r),
                    c - 66 * math.cos(r),
                    c + 76 * math.sin(r),
                    c - 76 * math.cos(r),
                ),
                fill=G,
                width=4,
            )
    elif name == "Photos":
        R((48, 68, 208, 188))
        L(64, 176, 110, 118, 140, 150, 166, 126, 196, 176)
        E((150, 82, 178, 110))
    elif name == "Podcasts":
        E((108, 86, 148, 126))
        L(128, 130, 128, 196)
        d.arc((72, 50, 184, 162), 200, 340, fill=G, width=W)
        d.arc((46, 24, 210, 188), 205, 335, fill=G, width=W)
    elif name == "Audiobooks":
        L(c, 70, c, 196)
        d.polygon([(c, 70), (56, 56), (56, 182), (c, 196)], outline=G, width=W)
        d.polygon([(c, 70), (200, 56), (200, 182), (c, 196)], outline=G, width=W)
    elif name == "iTunes U":
        d.polygon([(c, 70), (214, 112), (c, 154), (42, 112)], outline=G, width=W)
        L(80, 128, 80, 176, c, 196, 176, 176, 176, 128)
    elif name == "Voice Memos":
        d.rounded_rectangle((104, 46, 152, 146), 24, outline=G, width=W)
        d.arc((76, 90, 180, 176), 0, 180, fill=G, width=W)
        L(c, 176, c, 206)
        L(96, 206, 160, 206)
    elif name == "Settings":
        for a in range(8):
            r = math.radians(a * 45)
            d.line(
                (
                    c + 46 * math.cos(r),
                    c + 46 * math.sin(r),
                    c + 80 * math.cos(r),
                    c + 80 * math.sin(r),
                ),
                fill=G,
                width=16,
            )
        E((76, 76, 180, 180))
        E((110, 110, 146, 146))
    elif name == "Genius Mixes":
        E((110, 110, 146, 146), fill=G)
        for a in (0, 60, 120):
            o = Image.new("RGBA", (N, N))
            ImageDraw.Draw(o).ellipse((40, 96, 216, 160), outline=G, width=6)
            im.alpha_composite(o.rotate(a, center=(c, c)))
    elif name == "Playlists":
        for y in (72, 108, 144, 180):
            L(52, y, 150, y)
        E((166, 162, 200, 192))
        L(198, 176, 198, 80)
    elif name == "Artists":
        E((92, 48, 164, 120))
        d.arc((56, 128, 200, 272), 180, 360, fill=G, width=W)
    elif name == "Albums":
        R((72, 52, 204, 184))
        L(52, 72, 52, 204, 184, 204)
        E((112, 92, 164, 144))
        E((132, 112, 144, 124))
    elif name == "Songs":
        E((84, 164, 136, 204))
        L(132, 184, 132, 56, 176, 92)
    elif name == "Genres":
        E((60, 128, 140, 208))
        L(118, 150, 196, 60)
        L(184, 50, 210, 76)
    elif name == "Composers":
        for y in (86, 110, 134, 158, 182):
            d.line((48, y, 208, y), fill=GD, width=4)
        E((84, 150, 120, 186))
        L(118, 168, 118, 64)
        E((150, 102, 186, 138))
        L(184, 120, 184, 40)
    return crt(im, 22, 0.15)


def wallpaper():
    S = 240
    im = Image.new("RGBA", (S, S), BG + (255,))
    d = ImageDraw.Draw(im)
    for k in range(0, S, 20):
        d.line((k, 0, k, S), fill=(9, 34, 17))
        d.line((0, k, S, k), fill=(9, 34, 17))
    for k in range(6):
        d.arc(
            (20 - k * 30, 20 - k * 30, 220 + k * 30, 220 + k * 30),
            0,
            360,
            fill=(12, 60 - 6 * k, 28),
        )
    d.line((120, 0, 120, S), fill=(14, 70, 34))
    d.line((0, 120, S, 120), fill=(14, 70, 34))
    for x, y in ((8, 8), (232, 8), (8, 232), (232, 232)):
        sx, sy = (1 if x < 120 else -1), (1 if y < 120 else -1)
        d.line((x, y, x + 18 * sx, y), fill=G, width=2)
        d.line((x, y, x, y + 18 * sy), fill=G, width=2)
    return crt(im, 80)


def analog_face():
    S = 240
    im = Image.new("RGBA", (S, S), BG + (255,))
    d = ImageDraw.Draw(im)
    c = 120
    d.ellipse((8, 8, 232, 232), outline=G, width=4)
    d.ellipse((22, 22, 218, 218), outline=GD, width=2)
    for k in range(60):
        r = math.radians(k * 6)
        a = 96 if k % 5 else 84
        d.line(
            (
                c + a * math.sin(r),
                c - a * math.cos(r),
                c + 104 * math.sin(r),
                c - 104 * math.cos(r),
            ),
            fill=G,
            width=4 if k % 5 == 0 else 1,
        )
    for n, (x, y) in {"12": (120, 50), "3": (190, 120), "6": (120, 190), "9": (50, 120)}.items():
        _seg(d, n, x, y, 9)
    _segtext(d, "CLK//LOCAL", 120, 160, 3)
    return crt(im, 80)


SEG = {
    "0": "abcedf",
    "1": "bc",
    "2": "abged",
    "3": "abgcd",
    "4": "fgbc",
    "5": "afgcd",
    "6": "afgedc",
    "7": "abc",
    "8": "abcdefg",
    "9": "abcdfg",
    ":": "",
}


def _seg(d, s, cx, cy, u, col=G):
    w = u * 2
    x = cx - (len(s) * (w + u)) / 2
    for ch in s:
        segs = SEG.get(ch, "")
        P = {
            "a": (x, cy - 2 * u, x + w, cy - 2 * u),
            "b": (x + w, cy - 2 * u, x + w, cy),
            "c": (x + w, cy, x + w, cy + 2 * u),
            "d": (x, cy + 2 * u, x + w, cy + 2 * u),
            "e": (x, cy, x, cy + 2 * u),
            "f": (x, cy - 2 * u, x, cy),
            "g": (x, cy, x + w, cy),
        }
        for sname in segs:
            d.line(P[sname], fill=col, width=max(2, u // 2))
        if ch == ":":
            d.rectangle((x + u - 1, cy - u - 1, x + u + 1, cy - u + 1), fill=col)
            d.rectangle((x + u - 1, cy + u - 1, x + u + 1, cy + u + 1), fill=col)
        x += w + u


def _segtext(d, s, cx, cy, u):  # tiny blocky terminal letters (original)
    x = cx - len(s) * u * 2.2 / 2
    for ch in s:
        d.rectangle((x, cy - u, x + u * 1.4, cy + u), outline=GD) if ch.isalpha() else (
            _seg(d, ch, x + u, cy, u // 2 + 1, GD) if ch in SEG else None
        )
        if ch == "/":
            d.line((x, cy + u, x + u * 1.4, cy - u), fill=GD, width=1)
        x += u * 2.2


def digital_face():
    S = 240
    im = Image.new("RGBA", (S, S), BG + (255,))
    d = ImageDraw.Draw(im)
    d.rectangle((10, 40, 230, 200), outline=G, width=3)
    for y in range(52, 196, 12):
        d.line((16, y, 224, y), fill=(10, 36, 18))
    d.rectangle((24, 168, 216, 186), outline=GD, width=2)
    d.rectangle((26, 170, 150, 184), fill=GD)
    return crt(im, 80)


def digit_glyph(ch, w, h):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    u = int(min(w / 3.2, h / 4.6))
    _seg(d, ch, w / 2 + u / 2, h / 2, u)
    return crt(im.filter(ImageFilter.GaussianBlur(0.6)), 40, 0.0)


def hand(w, h):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon(
        [(w / 2, 2), (w - 2, h * 0.82), (w / 2, h - 2), (2, h * 0.82)],
        outline=G,
        fill=(10, 80, 36, 255),
    )
    d.ellipse((w / 2 - 4, h * 0.82 - 4, w / 2 + 4, h * 0.82 + 4), fill=G)
    return im.filter(ImageFilter.GaussianBlur(0.4))


def main(ipsw, out, prev_dir):
    fw = load_ipsw(Path(ipsw))
    proj = make_project(fw)
    db = fw.db
    proj.name = "Phosphor Terminal"
    proj.accent = "#14ff6a"
    for app in fw.catalog["apps"]:
        apply_app_art(proj, app, glyph(app.name))
    for m in (C.MASK_LARGE, C.MASK_SMALL):  # tap-down masks unchanged (shape matches stock)
        pass
    wall = wallpaper()
    _, wid, thumb = fw.catalog["wallpapers"][-1]
    proj.apply_replacement(wid, wall, "wallpaper")
    proj.wallpaper_id = wid
    if thumb:
        proj.apply_replacement(thumb, wall.resize((79, 79), Image.Resampling.LANCZOS), "wallpaper")
    faces = fw.catalog["clock_faces"]
    f1 = faces[0]  # analog face: background(s) + hands
    for r, i in f1.parts:
        im = db.images[i]
        if r == "Background":
            proj.apply_replacement(i, analog_face(), "clock")
        elif r == "Hand":
            proj.apply_replacement(i, hand(im.width, im.height), "clock")
    proj.apply_replacement(
        f1.preview, H.render_clock(db, f1).resize((79, 79), Image.Resampling.LANCZOS), "clock"
    )
    dig = next(f for f in faces if (f.preview & 0xFFF) == 0x3BD)  # digital (nixie) face
    for r, i in dig.parts:
        if r == "Background":
            proj.apply_replacement(i, digital_face(), "clock")
    for k, i in enumerate(H.digit_set(db, dig)):
        im = db.images[i]
        proj.apply_replacement(i, digit_glyph(str(k), im.width, im.height), "clock")
    proj.apply_replacement(
        dig.preview, H.render_clock(db, dig).resize((79, 79), Image.Resampling.LANCZOS), "clock"
    )
    proj.clock_id = f1.background
    proj.save_n6theme(Path(out))
    pd = Path(prev_dir)
    pd.mkdir(parents=True, exist_ok=True)
    for f in pd.glob("*.png"):
        f.unlink()
    apps = H.order_apps(fw.catalog["apps"], True)
    allapps = H.order_apps(fw.catalog["apps"], True)
    up = lambda im: im.resize((480, 480), Image.Resampling.NEAREST)
    up(H.render_home(db, wid, apps, 0, small=True)).save(pd / "home_small_p1.png")
    up(H.render_home(db, wid, apps, 1, small=True)).save(pd / "home_small_p2.png")
    up(H.render_home(db, wid, apps, 1)).save(pd / "home_large_music.png")
    up(H.render_clock(db, f1)).save(pd / "clock_analog.png")
    up(H.render_clock(db, dig)).save(pd / "clock_digital.png")
    up(wall).save(pd / "wallpaper.png")
    sheet = Image.new("RGBA", (6 * 110, 3 * 130), BG + (255,))
    sd = ImageDraw.Draw(sheet)
    for k, a in enumerate(allapps):
        ic = db.images[a.small].to_pil().convert("RGBA")
        x, y = (k % 6) * 110, (k // 6) * 130
        sheet.alpha_composite(ic, (x + 2, y + 2))
        sd.text((x + 8, y + 108), a.name, fill=G)
    sheet.save(pd / "icons_all_apps.png")
    print("saved", out, "previews:", sorted(p.name for p in pd.iterdir()))


if __name__ == "__main__":
    main(*sys.argv[1:4])
