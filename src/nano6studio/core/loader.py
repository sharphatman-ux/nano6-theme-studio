# SPDX-License-Identifier: GPL-3.0-only
# Nano 6 Theme Studio - Copyright (C) 2026 sharphatman-ux and contributors. See LICENSE.
"""Load a firmware: IPSW (zip) -> Firmware.MSE -> rsrc FAT16 -> SilverImagesDB.

Returns a LoadedFirmware with the parsed image database, the semantic catalog
(icons, clock faces, wallpapers) and the stock bytes. Everything is read from
the zip into memory; nothing is extracted to disk (a full extraction used to
leave ~356 MB in the temp folder per open)."""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path

from . import session
from .mse import extract_rsrc_fat, find_section, parse_mse
from .project import ThemeProject, catalog_assets
from .rsrc_fs import SILVER_IMAGES
from .silverimages import SilverImagesDB


@dataclass
class LoadedFirmware:
    ipsw_path: Path
    mse_bytes: bytes
    fat_bytes: bytes
    stock_silver: bytes
    db: SilverImagesDB
    catalog: dict
    silver_rel: str = SILVER_IMAGES


def load_ipsw(ipsw_path: Path) -> LoadedFirmware:
    ipsw_path = Path(ipsw_path)
    # a new firmware replaces the old session; drop any scratch files it made
    session.cleanup()
    with zipfile.ZipFile(ipsw_path, "r") as z:
        names = z.namelist()
        mse_name = next(
            (n for n in names if n.endswith("Firmware.MSE") or n == "Firmware.MSE"), None
        )
        if not mse_name:
            # sometimes nested
            mse_name = next((n for n in names if n.lower().endswith(".mse")), None)
        if not mse_name:
            raise FileNotFoundError("Firmware.MSE not found in IPSW")
        mse = z.read(mse_name)
    sections = parse_mse(mse)
    find_section(sections, "rsrc")
    fat = extract_rsrc_fat(mse, sections)
    from . import home_render
    from .fat16 import FatImage

    img = FatImage(fat)
    silver = img.read(SILVER_IMAGES)
    try:  # label font comes from the user's own firmware (never bundled)
        home_render.set_font(img.read("Resources/Fonts/HelveticaBold.ttf"))
    except (FileNotFoundError, ValueError):
        pass
    db = SilverImagesDB.parse(silver)
    cat = catalog_assets(db)
    return LoadedFirmware(
        ipsw_path=ipsw_path,
        mse_bytes=mse,
        fat_bytes=fat,
        stock_silver=silver,
        db=db,
        catalog=cat,
    )


def make_project(fw: LoadedFirmware) -> ThemeProject:
    cat = fw.catalog
    proj = ThemeProject(
        name=fw.ipsw_path.stem,
        ipsw_path=str(fw.ipsw_path),
        wallpaper_id=cat["wallpaper"][-1] if cat["wallpaper"] else None,
        clock_id=cat["clock"][0] if cat["clock"] else None,
        icon_ids=list(cat["home_icons"]),
    )
    proj._db = fw.db
    return proj
