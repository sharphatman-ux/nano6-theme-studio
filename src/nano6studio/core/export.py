# SPDX-License-Identifier: GPL-3.0-only
# Nano 6 Theme Studio - Copyright (C) 2026 sharphatman-ux and contributors. See LICENSE.
"""Export SilverImagesDB / asset pack / install instructions (themed IPSW: core/firmware_pack.py)."""

from __future__ import annotations

import json
import zipfile
from io import BytesIO
from pathlib import Path

from .project import ThemeProject
from .silverimages import SilverImagesDB

INSTALL_GUIDE = """# Nano 6 Theme Studio - how to install a theme

Back up your music first. If it ever gets stuck, see "If it gets stuck" at the bottom.

This app never touches your iPod. You install the file yourself with iTunes.
It works only on the iPod nano 6th generation, firmware 1.2 (36B10147).

You need:
- A Windows PC with iTunes. Do not use the "Apple Devices" app.
  A Mac with macOS 10.14 Mojave or older also works.
- The Apple cable that came with the iPod.
- The stock firmware file iPod_1.2_36B10147.ipsw (link at the bottom). Keep it.

## Step 1. Make the themed file
1. In this app, click Export, then "Export themed firmware (.ipsw)".
2. Save the file. It is called iPod_1.2_36B10147_themed.ipsw.

## Step 2. Back up your music first
1. Plug in the iPod. Open File Explorer.
2. Turn on View > Show > Hidden items.
3. Open the iPod drive. Copy everything on it, including the hidden
   iPod_Control folder, into a new folder on your PC.

## Step 3. Install the theme
1. Plug the iPod into a USB port on the BACK of the PC.
   No hub. No keyboard port. No front port.
2. Open iTunes.
3. Click the small iPod icon near the top-left of the iTunes window.
4. You are now on the Summary page.
5. HOLD the Shift key. While still holding it, click "Check for Update".
   Do NOT click Restore.
6. A file window opens. Choose iPod_1.2_36B10147_themed.ipsw and click Open.
7. If iTunes asks, click Update.
8. Wait. Do not unplug the iPod until it has restarted and shows the Home screen.

## Step 4. If it shows "OK to disconnect" in black and white
This is normal for themed firmware after a restart or a flat battery.
1. Hold Volume Down + Sleep/Wake until you see the Apple logo.
2. Let go of Sleep/Wake right away. Keep holding Volume Down.
3. Now also hold Volume Up (hold both volume buttons) until the Home screen shows.
Themed firmware may also forget ratings, playlist edits or settings after a restart.

## If it gets stuck or keeps restarting
1. Charge it on the PC for 10-15 minutes first.
2. Plug it into a BACK USB port with the Apple cable. Open iTunes.
3. Hold Volume Down + Sleep/Wake together.
4. Keep holding through the Apple logo, until the screen goes black.
5. Keep holding 1-2 seconds more, then let go.
6. iTunes says it found an iPod in recovery mode. The iPod screen stays black.
   If iTunes shows an error, you held too long. Try again and let go sooner.
7. HOLD Shift and click "Restore iPod".
8. Choose the stock iPod_1.2_36B10147.ipsw and click Open. Then click Restore.
9. This wipes the iPod. After it finishes, copy your backup from Step 2 back.
If iTunes does not see it at all: reinstall iTunes (this reinstalls the Apple
Mobile Device USB driver), try another cable, another port, or another PC.

Stock IPSW (Apple):
https://secure-appldnld.apple.com/iPod/SBML/osx/bundles/041-1920.20111004.CpeEw/iPod_1.2_36B10147.ipsw

## Credits
- ipod_theme (nfzerox and contributors), GPL-3.0: https://github.com/nfzerox/ipod_theme
- ipod_sun (CUB3D), GPL-3.0: https://github.com/CUB3D/ipod_sun
- ipodhax (MIT) and silverutil by Spotlight (MIT)
"""


def export_silver_db(db: SilverImagesDB, path: Path) -> Path:
    path.write_bytes(db.rebuild())
    return path


def export_asset_pack(proj: ThemeProject, path: Path) -> Path:
    db = proj._db
    if not db:
        raise RuntimeError("No DB")
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("README_FLASH.txt", INSTALL_GUIDE)
        manifest = {"icons_manual": sorted(proj.customized_icon_ids()), "replacements": {}}
        for iid, _rel in proj.replacements.items():
            im = db.images[iid]
            buf = BytesIO()
            im.to_pil().save(buf, format="PNG")
            name = f"{iid:08x}_{im.fmt_name}.png"
            z.writestr(f"body/{name}", buf.getvalue())
            manifest["replacements"][str(iid)] = {
                "file": name,
                "w": im.width,
                "h": im.height,
                "fmt": im.fmt_name,
                "manual": proj.is_manual(iid),
                "category": (proj.edits.get(iid).category if iid in proj.edits else "other"),
            }
        z.writestr("manifest.json", json.dumps(manifest, indent=2))
        z.writestr("SilverImagesDB.LE.bin", db.rebuild())
    return path


def write_install_guide(path: Path) -> Path:
    path.write_text(INSTALL_GUIDE, encoding="utf-8")
    return path
