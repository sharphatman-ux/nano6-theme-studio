# SPDX-License-Identifier: GPL-3.0-only
# Nano 6 Theme Studio - Copyright (C) 2026 sharphatman-ux and contributors. See LICENSE.
"""Core unit tests — MSE, SilverImages round-trip, cropper, project."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest
from PIL import Image

from nano6studio.core.cropper import CropParams
from nano6studio.core.cropper import framed_crop as crop
from nano6studio.core.export import export_asset_pack
from nano6studio.core.loader import load_ipsw
from nano6studio.core.mse import extract_rsrc_fat, find_section, parse_mse
from nano6studio.core.project import ThemeProject, catalog_assets
from nano6studio.core.silverimages import SilverImagesDB


@pytest.fixture(scope="module")
def mse_bytes():
    return stock_mse()


@pytest.fixture(scope="module")
def silver_bytes():
    return stock_silver()


def test_parse_mse(mse_bytes):
    secs = parse_mse(mse_bytes)
    names = [s.name for s in secs]
    assert "rsrc" in names and "osos" in names
    rsrc = find_section(secs, "rsrc")
    assert rsrc.offset == 0x2E7000


def test_extract_rsrc_fat(mse_bytes):
    fat = extract_rsrc_fat(mse_bytes)
    assert fat[0] == 0xEB
    assert b"FAT" in fat[:64]


def test_silver_roundtrip_unmodified(silver_bytes):
    db = SilverImagesDB.parse(silver_bytes)
    out = db.rebuild()
    assert out == silver_bytes, "Unmodified rebuild must be byte-identical"


def test_silver_decode_sample(silver_bytes):
    db = SilverImagesDB.parse(silver_bytes)
    assert len(db.images) > 1000
    # pick a 240x240
    sample = next(im for im in db.images.values() if im.width == 240 and im.height == 240)
    pil = sample.to_pil()
    assert pil.size == (240, 240)


def test_modified_then_decode(silver_bytes):
    db = SilverImagesDB.parse(silver_bytes)
    sample = next(im for im in db.images.values() if im.fmt == 0x1888 and im.width >= 50)
    red = Image.new("RGBA", (sample.width, sample.height), (255, 0, 0, 255))
    sample.set_pil(red)
    rebuilt = db.rebuild()
    db2 = SilverImagesDB.parse(rebuilt)
    pil = db2.images[sample.image_id].to_pil()
    px = pil.getpixel((sample.width // 2, sample.height // 2))
    assert px[0] > 200 and px[1] < 40  # reddish


def test_cropper_no_stretch():
    src = Image.new("RGB", (800, 400), (10, 20, 30))
    p = CropParams(240, 240, mode="fill", zoom=1.0)
    out = crop(src, p)
    assert out.size == (240, 240)
    p2 = CropParams(240, 240, mode="fit", zoom=1.0, bg_color=(1, 2, 3, 255))
    out2 = crop(src, p2)
    assert out2.size == (240, 240)
    # fit should letterbox — corners near bg
    c = out2.getpixel((0, 0))
    assert c[0] == 1 and c[1] == 2


def test_theme_generator_is_gone():
    import importlib.util

    from nano6studio.core.project import ThemeProject
    from nano6studio.ui import main_window as M

    assert importlib.util.find_spec("nano6studio.core.theme_gen") is None
    assert not hasattr(ThemeProject, "run_generator")
    assert not hasattr(M, "GeneratorDialog") and not hasattr(M.MainWindow, "run_generator")


def test_project_save_load(silver_bytes, tmp_path):
    db = SilverImagesDB.parse(silver_bytes)
    cat = catalog_assets(db)
    proj = ThemeProject(
        name="demo",
        icon_ids=cat["home_icons"][:2],
        wallpaper_id=cat["wallpaper"][0],
        clock_id=cat["wallpaper"][0],
    )
    proj._db = db
    iid = proj.icon_ids[0]
    proj.apply_replacement(
        iid, Image.new("RGBA", db.images[iid].size, (12, 34, 56, 255)), "icon", manual=True
    )
    path = tmp_path / "t.n6theme"
    proj.save_n6theme(path)
    db2 = SilverImagesDB.parse(silver_bytes)
    loaded = ThemeProject.load_n6theme(path, db=db2)
    assert loaded.is_manual(iid)
    assert iid in loaded.customized_icon_ids()


def test_export_pack(silver_bytes, tmp_path):
    db = SilverImagesDB.parse(silver_bytes)
    cat = catalog_assets(db)
    proj = ThemeProject(name="e", icon_ids=cat["home_icons"][:1], wallpaper_id=cat["wallpaper"][0])
    proj._db = db
    iid = proj.icon_ids[0]
    proj.apply_replacement(iid, Image.new("RGBA", db.images[iid].size, (9, 9, 9, 255)), "icon")
    zpath = tmp_path / "pack.zip"
    export_asset_pack(proj, zpath)
    with zipfile.ZipFile(zpath) as z:
        assert "README_FLASH.txt" in z.namelist()
        assert "SilverImagesDB.LE.bin" in z.namelist()
        assert "manifest.json" in z.namelist()


def test_load_ipsw_if_present():
    fw = load_ipsw(require_ipsw())
    assert len(fw.db.images) > 1000
    # an unmodified database rebuilds to the stock bytes
    assert fw.db.rebuild() == fw.stock_silver
    assert SilverImagesDB.parse(fw.stock_silver).rebuild() == fw.stock_silver


def test_remove_stale_session_dirs(tmp_path):
    import os
    import time

    from nano6studio.core import session

    old = tmp_path / "n6ts_old"
    new = tmp_path / "n6ts_new"
    other = tmp_path / "keep_me"
    for path in (old, new, other):
        path.mkdir()
    two_days_ago = time.time() - 2 * 24 * 60 * 60
    os.utime(old, (two_days_ago, two_days_ago))
    os.utime(other, (two_days_ago, two_days_ago))
    assert session.remove_stale(root=tmp_path) == 1
    assert not old.exists() and new.exists() and other.exists()


# ---- pure-Python FAT16 (no mtools) ----
from nano6studio.core.fat16 import FatImage
from nano6studio.core.rsrc_fs import SILVER_IMAGES, read_file, write_file


@pytest.fixture(scope="module")
def fat_bytes(mse_bytes):
    return extract_rsrc_fat(mse_bytes)


def test_fat16_extract_matches_reference(fat_bytes, silver_bytes):
    img = FatImage(fat_bytes)
    assert not img.fat12
    assert img.read(SILVER_IMAGES) == silver_bytes


def test_fat16_unmodified_reinsert_byte_identical(fat_bytes):
    img = FatImage(fat_bytes)
    img.write(SILVER_IMAGES, img.read(SILVER_IMAGES))
    assert img.tobytes() == fat_bytes


def test_fat16_silver_rebuild_reinsert_byte_identical(fat_bytes):
    img = FatImage(fat_bytes)
    db = SilverImagesDB.parse(img.read(SILVER_IMAGES))
    img.write(SILVER_IMAGES, db.rebuild())
    assert img.tobytes() == fat_bytes


def test_fat16_grow_and_shrink(fat_bytes, tmp_path):
    img = FatImage(fat_bytes)
    orig = img.read(SILVER_IMAGES)
    others = {p: img.read(p) for p, e in img.walk() if not e.is_dir and p != SILVER_IMAGES}
    free0 = img.free_clusters()
    grown = orig + bytes(range(256)) * 200  # +50 KiB -> new clusters
    img.write(SILVER_IMAGES, grown)
    img2 = FatImage(img.tobytes())
    assert img2.read(SILVER_IMAGES) == grown
    assert img2.free_clusters() < free0
    img2.write(SILVER_IMAGES, orig[:1000])  # shrink -> frees clusters
    img3 = FatImage(img2.tobytes())
    assert img3.read(SILVER_IMAGES) == orig[:1000]
    assert img3.free_clusters() > free0
    for p, d in others.items():  # nothing else disturbed
        assert img3.read(p) == d
    # file-path API round trip
    fp = tmp_path / "rsrc.fat"
    fp.write_bytes(fat_bytes)
    write_file(fp, SILVER_IMAGES, read_file(fp, SILVER_IMAGES))
    assert fp.read_bytes() == fat_bytes


def test_no_mtools_dependency():
    import nano6studio.core.rsrc_fs as r

    src = Path(r.__file__).read_text()
    assert "subprocess" not in src and "mcopy" not in src


# ---- semantic catalog / layout ----
from firmware import require_ipsw, stock_mse, stock_silver  # noqa: E402

from nano6studio.core import catalog as C
from nano6studio.core import home_render as H


@pytest.fixture(scope="module")
def db(silver_bytes):
    return SilverImagesDB.parse(silver_bytes)


def test_home_apps_mapped_by_id(db):
    apps = {a.name: a for a in C.home_apps(db, include_hidden=True)}
    assert len(apps) == 18 and len(C.home_apps(db)) == 18 and not C.LEFTOVERS
    assert apps["Music"].large == 0x0DAD02C6 and apps["Clock"].large == 0x0DAD02D0
    assert apps["Fitness"].small == 0x0DAD02E1 and apps["Radio"].list_icon == 0x0DAD06C8
    for a in apps.values():
        sizes = {(db.images[i].width, db.images[i].height) for i in a.ids}
        assert (154, 164) in sizes and (105, 105) in sizes
    all_ids = [i for a in apps.values() for i in a.ids]
    assert len(all_ids) == len(set(all_ids))  # no bitmap shared by two apps


def test_clock_faces_grouped(db):
    faces = C.clock_faces(db)
    assert len(faces) >= 30
    for f in faces:
        assert f.preview and db.images[f.preview].width == 79
        assert f.background and db.images[f.background].width == 240
    f1 = faces[0]
    assert f1.background == 0x0DAD034E and len(f1.hands()) == 2


def test_wallpapers_and_advanced_split(db):
    cat = catalog_assets(db)
    assert len(cat["wallpapers"]) == 24  # Settings offers 24 (8 rows of 3)
    assert all(db.images[w].width == 240 for _, w, _ in cat["wallpapers"])
    B = C.BASE
    thumbs = [t - B for _, _, t in cat["wallpapers"]]
    assert thumbs[:15] == list(range(0x322, 0x331))  # Settings order = thumbnail id order
    assert cat["wallpapers"][2][1] == B + 0x30F and thumbs[2] == 0x324  # row 1, col 3: denim
    assert C.wallpaper_copies(B + 0x30D) == [B + 0x30D, B + 0x30C]
    assert C.wallpaper_copies(B + 0x315) == [B + 0x315, B + 0x314, B + 0x316]
    assert C.wallpaper_copies(B + 0x334) == [B + 0x334, B + 0x335]
    # unmatched 240x240 images are only in Advanced
    for x in (0x317, 0x318, 0x31B, 0x31E, 0x30B, 0x344, 0x51F):
        assert B + x in cat["other"]
    # plain colours: thumbnail is an exact downscale of its wallpaper
    from PIL import ImageChops, ImageStat

    for _, w, t in cat["wallpapers"][15:]:
        a = db.images[w].to_pil().convert("RGB").resize((79, 79))
        b = db.images[t].to_pil().convert("RGB")
        assert sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) < 12
    assert len(cat["other"]) > 900 and not set(cat["other"]) & set(cat["home_icons"])


def test_home_render_layout(db):
    apps = H.order_apps(C.home_apps(db))  # stock default set
    assert [a.name for a in apps][:3] == ["Now Playing", "Music", "Radio"]
    names = [a.name for a in apps]
    assert names == [
        "Now Playing",
        "Music",
        "Radio",
        "Fitness",
        "Clock",
        "Photos",
        "Podcasts",
        "Settings",
    ]
    assert H.page_count(apps, small=False) == 8 and H.page_count(apps, small=True) == 2

    big = H.render_home(db, None, apps, 1)
    assert big.size == (240, 240)
    # Music's large bitmap lands at LARGE_POS
    ic = db.images[apps[1].large].to_pil().convert("RGBA")
    x, y = C.LARGE_POS
    px = big.getpixel((x + 77, y + 74))[:3]
    ref = ic.getpixel((77, 74))[:3]
    assert sum(abs(a - b) for a, b in zip(px, ref)) < 30


def test_app_art_writes_all_variants(db, silver_bytes):
    from nano6studio.core.icons import apply_app_art

    proj = ThemeProject()
    proj._db = SilverImagesDB.parse(silver_bytes)
    app = next(a for a in C.home_apps(proj._db) if a.name == "Photos")
    apply_app_art(proj, app, Image.new("RGBA", (256, 256), (255, 0, 0, 255)))
    for i in app.ids:
        im = proj._db.images[i].to_pil().convert("RGBA")
        cx, cy = im.width // 2, im.height // 2 - 4
        r, g, b, a = im.getpixel((cx, cy))
        assert r > 200 and g < 60 and a > 200
        assert proj.is_manual(i)


def test_placement_math():
    from nano6studio.core.cropper import Placement, initial_placement, render_placement, zoom_about

    p = initial_placement(480, 240, 240, 240, "fill")
    assert p.scale == 1.0 and p.ox == -120 and p.oy == 0
    q = zoom_about(p, 2.0, 120, 120)
    # the source pixel under the frame centre stays under it
    assert abs((120 - p.ox) / p.scale - (120 - q.ox) / q.scale) < 1e-9
    src = Image.new("RGBA", (480, 240), (0, 0, 255, 255))
    src.paste((255, 0, 0, 255), (0, 0, 240, 240))
    out = render_placement(src, 240, 240, Placement(1.0, 0, 0))
    assert out.getpixel((10, 10))[:3] == (255, 0, 0)
    out = render_placement(src, 240, 240, Placement(1.0, -240, 0))
    assert out.getpixel((10, 10))[:3] == (0, 0, 255)


# ---- themed IPSW (port of ipod_theme/ipod_sun nano6 repack) ----


def test_themed_ipsw_build_and_verify(tmp_path, silver_bytes):
    from nano6studio.core.firmware_pack import build_themed_ipsw, verify_themed_ipsw

    db = SilverImagesDB.parse(silver_bytes)
    first = next(iter(db.images.values()))
    first.set_pil(
        Image.new("RGBA", (first.width, first.height), (255, 0, 0, 255)), keep_format=True
    )
    edited = db.rebuild()
    assert edited != silver_bytes
    out = tmp_path / "themed.ipsw"
    build_themed_ipsw(require_ipsw(), edited, out)
    v = verify_themed_ipsw(out, edited)
    assert v["silver_matches"] and v["disk_swap"] == (b"soso", b"ksid")
    assert v["sections"] == ["osos", "diag", "appl", "lbat", "bdsw", "bdhw", "chrg", "rsrc", "disk"]
    with zipfile.ZipFile(out) as a, zipfile.ZipFile(require_ipsw()) as b:
        assert sorted(a.namelist()) == sorted(b.namelist())
        for n in ("manifest.plist", "N20.bootloader.release.rb3"):
            assert a.read(n) == b.read(n)
        assert len(a.read("Firmware.MSE")) == len(b.read("Firmware.MSE"))


def _upstream_pipeline(stock_ipsw, silver: bytes, tmp) -> bytes:
    """ipod_theme nano6 path: helpers/fat_patch.py (pyfatfs delete + recreate) and the
    src/mse.rs + src/img1.rs repack + disk swap (1:1 port, see docs/UPSTREAM_COMPARE.md)."""
    pyfat = pytest.importorskip("pyfatfs.PyFatFS")
    from nano6studio.core.firmware_pack import Img1, parse_mse_full, write_mse

    mse = zipfile.ZipFile(stock_ipsw).read("Firmware.MSE")
    h, secs = parse_mse_full(mse)
    r = next(s for s in secs if s.name == b"crsr")
    img = Img1(r.body)
    rs = tmp / "rsrc.bin"
    rs.write_bytes(img.body)
    fat = pyfat.PyFatFS(str(rs), read_only=False)
    p = "/Resources/UI/SilverImagesDB.LE.bin"
    fat.remove(p)
    with fat.openbin(p, mode="wb") as b:
        b.write(silver)
    fat.close()
    img.body = rs.read_bytes()
    r.body = img.write()
    out = bytearray(write_mse(h, secs))
    out[0x5004:0x5008] = b"soso"
    out[0x5144:0x5148] = b"ksid"
    return bytes(out)


def test_themed_ipsw_matches_upstream(tmp_path, silver_bytes):
    from nano6studio.core.firmware_pack import build_themed_ipsw

    db = SilverImagesDB.parse(silver_bytes)
    for iid in list(db.images)[::50]:
        im = db.images[iid]
        if im.fmt != 0x0004:
            im.set_pil(Image.new("RGBA", im.size, (200, 40, 40, 255)))
    silver = db.rebuild()
    out = tmp_path / "ours.ipsw"
    build_themed_ipsw(require_ipsw(), silver, out)
    ma = zipfile.ZipFile(out).read("Firmware.MSE")
    mb = _upstream_pipeline(require_ipsw(), silver, tmp_path)
    assert len(ma) == len(mb)
    diff = [i for i in range(len(ma)) if ma[i] != mb[i]] if ma != mb else []
    # only the SilverImagesDB directory entry differs: pyfatfs re-creates it
    # (new 8.3 alias, LFN checksum, timestamps). Data, FAT and every other byte match.
    assert len(diff) <= 16 and diff[-1] - diff[0] < 96
