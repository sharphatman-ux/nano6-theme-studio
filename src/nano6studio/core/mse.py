# SPDX-License-Identifier: GPL-3.0-only
# Nano 6 Theme Studio - Copyright (C) 2026 sharphatman-ux and contributors. See LICENSE.
# MSE layout as documented by ipodhax (mse/, MIT) and ipod_sun by CUB3D (src/mse.rs, GPL-3.0).
# Reimplemented; see THIRD_PARTY_LICENSES.md.
"""Parse and rebuild Firmware.MSE containers (nano 6G layout).

An IPSW is a zip; its Firmware.MSE holds the firmware as a list of sections. A
directory at 0x5000 describes each section (4-char type/name stored as
little-endian char packs, offset and length). The sections we care about are
'rsrc' (a FAT16 resource volume whose boot sector sits 0x1400 into the section,
see rsrc_fs) and the 'disk'/'osos' pair whose
names are swapped when an image is meant to be installed. Everything else is
copied byte for byte."""

from __future__ import annotations

import struct
from dataclasses import dataclass

DIR_OFF = 0x5000
ENTRY_SIZE = 40
RSRC_FAT_REL = 0x1400  # FAT boot relative to rsrc section start


@dataclass
class MseSection:
    name: str
    offset: int
    length: int
    raw_entry: bytes
    u32: tuple[int, ...]


def parse_mse(data: bytes) -> list[MseSection]:
    if not data.startswith(b"{{~~"):
        raise ValueError("Not a Firmware.MSE (missing STOP banner)")
    out: list[MseSection] = []
    for i in range(16):
        o = DIR_OFF + i * ENTRY_SIZE
        e = data[o : o + ENTRY_SIZE]
        if e == b"\0" * ENTRY_SIZE:
            break
        # type (4) + name (4) both little-endian char packs → reverse for ASCII
        e[0:4][::-1].decode("ascii", "replace")
        name = e[4:8][::-1].decode("ascii", "replace")
        u = struct.unpack("<8I", e[8:40])
        # u[1]=file offset, u[2]=length (observed on nano 6G 1.2)
        off, ln = u[1], u[2]
        out.append(MseSection(name=name.strip("\0"), offset=off, length=ln, raw_entry=e, u32=u))
    return out


def find_section(sections: list[MseSection], name: str) -> MseSection:
    for s in sections:
        if s.name == name:
            return s
    raise KeyError(f"MSE section {name!r} not found")


def extract_rsrc_fat(mse: bytes, sections: list[MseSection] | None = None) -> bytes:
    sections = sections or parse_mse(mse)
    rsrc = find_section(sections, "rsrc")
    # Payload starts at section offset; FAT at +0x1400
    start = rsrc.offset + RSRC_FAT_REL
    # Length field is declared body size; FAT volume is that region minus header
    # Empirically: copy through end of declared length from section start
    end = rsrc.offset + rsrc.length
    if end > len(mse):
        end = len(mse)
    fat = mse[start:end]
    if fat[0] != 0xEB or b"FAT" not in fat[:64]:
        raise ValueError("rsrc FAT16 boot sector not found at +0x1400")
    return fat


def patch_rsrc_file(mse: bytes, fat_path: str, new_data: bytes) -> bytes:
    """Replace a file inside the extracted FAT image bytes by rewriting the whole rsrc slice.
    Caller supplies an already-updated FAT image of the SAME length (padded).
    """
    sections = parse_mse(mse)
    rsrc = find_section(sections, "rsrc")
    start = rsrc.offset + RSRC_FAT_REL
    end = rsrc.offset + rsrc.length
    region_len = end - start
    if len(new_data) > region_len:
        raise ValueError(f"Updated rsrc FAT ({len(new_data)}) exceeds region ({region_len})")
    padded = new_data + b"\x00" * (region_len - len(new_data))
    return mse[:start] + padded + mse[end:]
