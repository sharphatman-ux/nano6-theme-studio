# SPDX-License-Identifier: GPL-3.0-only
# Nano 6 Theme Studio - Copyright (C) 2026 sharphatman-ux and contributors. See LICENSE.
# Checks mirror the structural checks in ipodhax silverdb/unpack.py (MIT) by
# 760ceb3b9c0ba4872cadf3ce35a7a494. Reimplemented; see THIRD_PARTY_LICENSES.md.
"""Pre-export validator for SilverImagesDB.LE.bin. Any problem blocks the IPSW build.

Rules come from the stock 36B10147 file (all 1509 images satisfy them) and from what
upstream's ipodhax unpacker checks: ids/sizes match, length field = payload length,
4-byte aligned images, payload size = palette + row_length * height, sane row
lengths, palette limits and indices in range."""

from __future__ import annotations

import struct

from .silverimages import FLAGS, PALETTE_MAX, default_stride

# Formats whose stock row layout we do not fully understand: edits are refused.
UNSAFE_TO_EDIT = {0x0004}


class ValidationError(Exception):
    def __init__(self, problems: list[str]):
        super().__init__("SilverImagesDB failed validation:\n" + "\n".join(problems[:20]))
        self.problems = problems


def _entries(data: bytes):
    n = struct.unpack_from("<I", data, 16)[0]
    return n, 0x1C + n * 12, [struct.unpack_from("<3I", data, 0x1C + i * 12) for i in range(n)]


def check(data: bytes, stock: bytes | None = None) -> list[str]:
    p: list[str] = []
    if len(data) < 0x1C or data[:4] != b"\x03\0\0\0" or data[12:16] != b"paMB":
        return ["bad file header"]
    n, base, ents = _entries(data)
    if struct.unpack_from("<I", data, 4)[0] != base:
        p.append("header word 1 is not the end of the directory")
    if struct.unpack_from("<2I", data, 20) != (1, 28):
        p.append("unexpected header constants")
    stock_ents = {}
    if stock is not None:
        sn, sbase, se = _entries(stock)
        if [e[0] for e in se] != [e[0] for e in ents]:
            p.append("image id list differs from stock")
        stock_ents = {iid: stock[sbase + off : sbase + off + sz] for iid, off, sz in se}
    ids = [e[0] for e in ents]
    if ids != sorted(ids) or len(set(ids)) != len(ids):
        p.append("directory not sorted by unique id")
    end = 0
    for iid, off, sz in ents:
        if off % 2:  # stock is 4-aligned (we write that); upstream's 2-aligned files boot too
            p.append(f"{iid}: offset {off} not 2-byte aligned")
        if sz == 0:
            continue
        if off < end:
            p.append(f"{iid}: overlaps previous image")
        end = off + sz
        if base + end > len(data):
            p.append(f"{iid}: runs past end of file")
            continue
        b = data[base + off : base + end]
        if sz < 32:
            p.append(f"{iid}: shorter than a header")
            continue
        fmt, one, row, flags = struct.unpack_from("<4H", b, 0)
        z1, z2, h, w, hid, ln = struct.unpack_from("<6I", b, 8)
        if hid != iid:
            p.append(f"{iid}: header id {hid} differs")
        if ln + 32 != sz:
            p.append(f"{iid}: length field {ln} != size {sz} - 32")
        if one != 1 or z1 or z2:
            p.append(f"{iid}: reserved header fields wrong")
        if fmt not in FLAGS:
            p.append(f"{iid}: unknown format {fmt:04x}")
            continue
        if flags != FLAGS[fmt]:
            p.append(f"{iid}: flags {flags:#x} wrong for {fmt:04x}")
        if not (0 < w <= 1024 and 0 < h <= 1024):
            p.append(f"{iid}: odd size {w}x{h}")
        if row < default_stride(fmt, w):
            p.append(f"{iid}: row length {row} too short for width {w}")
        body = b[32:]
        pal = 0
        if fmt in PALETTE_MAX:
            if len(body) < 4:
                p.append(f"{iid}: missing palette")
                continue
            pc = struct.unpack_from("<I", body)[0]
            pal = 4 + 4 * pc
            if not 0 < pc <= PALETTE_MAX[fmt]:
                p.append(f"{iid}: palette size {pc} out of range")
            k = 1 if fmt == 0x0064 else 2
            idx = body[pal:]
            if len(idx) == row * h:
                hi = (
                    max(idx)
                    if k == 1
                    else max(
                        (struct.unpack_from("<H", idx, j)[0] for j in range(0, len(idx), 2)),
                        default=0,
                    )
                )
                if hi >= pc:
                    p.append(f"{iid}: palette index {hi} >= {pc}")
        if len(body) != pal + row * h:
            p.append(f"{iid}: payload {len(body)} != {pal} + {row}x{h}")
        if stock is not None and iid in stock_ents and stock_ents[iid] != b:
            sh = stock_ents[iid]
            if fmt in UNSAFE_TO_EDIT:
                p.append(
                    f"{iid}: editing format {fmt:04x} images is not supported (layout unverified)"
                )
            if sh[:4] != b[:4] or sh[6:28] != b[6:28]:
                p.append(f"{iid}: header (format/size/row length) differs from stock")
    return p


def validate(data: bytes, stock: bytes | None = None) -> None:
    probs = check(data, stock)
    if probs:
        raise ValidationError(probs)
