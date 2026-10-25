# SPDX-License-Identifier: GPL-3.0-only
# Nano 6 Theme Studio - themed IPSW builder for iPod nano 6G (fw 1.2, 36B10147).
#
# Copyright (C) 2026 sharphatman-ux and contributors.
#
# Ported from ipod_theme by nfzerox and contributors and ipod_sun by CUB3D, licence GPL-3.0.
# This module is a Python port of the nano 6G IPSW repack path of ipod_theme
# (https://github.com/nfzerox/ipod_theme, GPL-3.0, commit 3ff647a), which itself
# is based on ipod_sun by CUB3D (https://github.com/CUB3D/ipod_sun, GPL-3.0):
#   src/mse.rs   (MSE unpack/write)      -> parse_mse_full / write_mse
#   src/img1.rs  (rsrc Img1 parse/write) -> Img1
#   src/main.rs  (rsrc patch, "disk swap", IPSW zip)  -> build_themed_ipsw
#   helpers/fat_patch.py (SilverImagesDB replacement) -> core/fat16.py
# Modified: ported from Rust/pyfatfs to pure Python; reads the user's own stock
# IPSW instead of downloading it; takes SilverImagesDB bytes from the editor.
# See THIRD_PARTY_LICENSES.md and third_party/ for the upstream notices.
"""Build a ready-to-install themed IPSW. This never talks to the device."""

from __future__ import annotations

import struct
import zipfile
from dataclasses import dataclass
from pathlib import Path

from .fat16 import FatImage
from .rsrc_fs import SILVER_IMAGES
from .validate import validate

NANO6_BUILD = "36B10147"


@dataclass
class Sec:
    tag: bytes
    name: bytes  # stored reversed, e.g. b"crsr" for rsrc
    f: list[int]  # _idk, dev_offset, length, address, entry_offset, _idk2, version, load_addr
    head: bytes
    body: bytes

    @property
    def dev_offset(self) -> int:
        return self.f[1]


def parse_mse_full(data: bytes) -> tuple:
    """ipod_sun mse::unpack (Device::Nano6): body = length + 0x800 bytes after a 0x1000 head."""
    header = data[:0x5000]
    secs = []
    for i in range(16):
        e = data[0x5000 + i * 40 : 0x5000 + (i + 1) * 40]
        if e[:4] == b"\0\0\0\0":
            continue
        f = list(struct.unpack("<8I", e[8:40]))
        off, length = f[1], f[2]
        secs.append(
            Sec(
                e[:4],
                e[4:8],
                f,
                data[off : off + 0x1000],
                data[off + 0x1000 : off + 0x1000 + length + 0x800],
            )
        )
    return header, secs


def write_mse(header: bytes, secs: list[Sec]) -> bytes:
    """ipod_sun Mse::write."""
    out = bytearray(header)
    for s in secs:
        out += s.tag + s.name + struct.pack("<8I", *s.f)
    for _ in range(16 - len(secs)):
        out += b"\0" * 36 + b"\xff" * 4
    for s in sorted(secs, key=lambda s: s.dev_offset):
        if len(out) < s.dev_offset:
            out += b"\0" * (s.dev_offset - len(out))
        out += s.head + s.body
    if len(out) % 0x1000:
        out += b"\0" * (0x1000 - len(out) % 0x1000)
    return bytes(out)


class Img1:
    """ipod_sun img1::img1_parse / Img1::write for Nano6 (0x400 header area, no cert)."""

    def __init__(self, data: bytes):
        if data[:4] not in (b"8723", b"8720", b"8900") and data[:3] != b"872":
            pass  # upstream does not validate the magic either
        body_len = struct.unpack_from("<I", data, 12)[0]
        self.head = data[:0x54]
        self.padding = data[0x54:0x400]
        self.body = data[0x400 : 0x400 + body_len]

    def write(self) -> bytes:
        return self.head + self.padding + self.body


def build_themed_ipsw(stock_ipsw: Path, silver_db: bytes, out_ipsw: Path) -> dict:
    stock_ipsw, out_ipsw = Path(stock_ipsw), Path(out_ipsw)
    with zipfile.ZipFile(stock_ipsw) as z:
        names = z.namelist()
        files = {n: z.read(n) for n in names if not n.endswith("/")}
    mse_name = next((n for n in files if n.endswith("Firmware.MSE")), None)
    if not mse_name:
        raise ValueError("Firmware.MSE not found in IPSW")
    man = files.get("manifest.plist", b"")
    if NANO6_BUILD.encode() not in man:
        raise ValueError(f"Only the iPod nano 6G 1.2 ({NANO6_BUILD}) stock IPSW is supported")
    header, secs = parse_mse_full(files[mse_name])
    rsrc = next((s for s in secs if s.name == b"crsr"), None)
    if rsrc is None:
        raise ValueError("Failed to find rsrc section in MSE")
    img = Img1(rsrc.body)
    fat = FatImage(img.body)
    validate(silver_db, fat.read(SILVER_IMAGES))  # blocks the build on any problem
    fat.write(SILVER_IMAGES, silver_db)
    new_body = fat.tobytes()
    if len(new_body) != len(img.body):
        raise AssertionError("FAT image size changed")
    img.body = new_body
    rsrc.body = img.write()
    mse = bytearray(write_mse(header, secs))
    # "Disk swap" (ipod_sun, Nano6 only): swap osos <-> disk so the patched
    # firmware boots as the main OS.
    mse[0x5004:0x5008] = b"soso"
    mse[0x5144:0x5148] = b"ksid"
    files[mse_name] = bytes(mse)
    # read back what we are about to ship
    _, chk = parse_mse_full(files[mse_name])
    back = FatImage(Img1(next(s for s in chk if s.name == b"crsr").body).body).read(SILVER_IMAGES)
    if back != silver_db:
        raise AssertionError("rsrc read-back differs from the validated SilverImagesDB")
    out_ipsw.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_ipsw, "w", compression=zipfile.ZIP_STORED) as z:
        for n in names:
            if n in files:
                zi = zipfile.ZipInfo(n, date_time=(2011, 9, 16, 22, 35, 0))
                zi.external_attr = 0o100755 << 16
                zi.compress_type = zipfile.ZIP_STORED
                z.writestr(zi, files[n])
    return {"mse_size": len(mse), "rsrc_free_clusters": fat.free_clusters()}


def verify_themed_ipsw(ipsw: Path, expected_silver: bytes) -> dict:
    """Re-parse a built IPSW and check the rsrc carries the expected SilverImagesDB."""
    with zipfile.ZipFile(ipsw) as z:
        mse = z.read(next(n for n in z.namelist() if n.endswith("Firmware.MSE")))
    header, secs = parse_mse_full(mse)
    rsrc = next(s for s in secs if s.name == b"crsr")
    fat = FatImage(Img1(rsrc.body).body)
    got = fat.read(SILVER_IMAGES)
    return {
        "sections": [s.name[::-1].decode() for s in secs],
        "disk_swap": (mse[0x5004:0x5008], mse[0x5144:0x5148]),
        "silver_matches": got == expected_silver,
    }
