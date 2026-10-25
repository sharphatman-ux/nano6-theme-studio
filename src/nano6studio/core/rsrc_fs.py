# SPDX-License-Identifier: GPL-3.0-only
# Nano 6 Theme Studio - Copyright (C) 2026 sharphatman-ux and contributors. See LICENSE.
"""Extract and patch files inside the nano 6G rsrc FAT16 image (pure Python).

The 'rsrc' MSE section is a small FAT16 volume. The UI artwork lives at
Resources/UI/SilverImagesDB.LE.bin inside it. Patching rewrites only that file's
data and directory entry (via fat16), so the rest of the volume is unchanged."""

from __future__ import annotations

from pathlib import Path

from .fat16 import FatImage

SILVER_IMAGES = "Resources/UI/SilverImagesDB.LE.bin"


def read_file(fat_path: Path, rel: str) -> bytes:
    return FatImage(Path(fat_path).read_bytes()).read(rel)


def write_file(fat_path: Path, rel: str, data: bytes) -> None:
    img = FatImage(Path(fat_path).read_bytes())
    img.write(rel, data)
    Path(fat_path).write_bytes(img.tobytes())


def extract_tree(fat_path: Path, dest: Path, only_prefix: str | None = None) -> None:
    img = FatImage(Path(fat_path).read_bytes())
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    for p, ent in img.walk():
        if only_prefix and not p.lower().startswith(only_prefix.lower()):
            continue
        target = dest / p
        if ent.is_dir:
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(img.read(p))
