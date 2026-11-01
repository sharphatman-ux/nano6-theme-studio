# SPDX-License-Identifier: GPL-3.0-only
# Nano 6 Theme Studio - Copyright (C) 2026 sharphatman-ux and contributors. See LICENSE.
"""fw 1.2 has no asset that sets the draw color of UI strings. See docs/LABEL_COLOR.md."""

from __future__ import annotations

import struct

COLOR_TABLES = {
    b"COLR",
    b"CPAL",
    b"SVG ",
    b"CBDT",
    b"CBLC",
    b"sbix",
    b"EBDT",
    b"EBLC",
    b"bdat",
    b"bloc",
}


def _sfnt_tags(data: bytes, start: int = 0) -> list[bytes]:
    ntab = struct.unpack_from(">H", data, start + 4)[0]
    return [data[start + 12 + i * 16 : start + 16 + i * 16] for i in range(ntab)]


def test_fonts_and_silverdb_have_no_label_color():
    import zipfile

    from firmware import require_ipsw

    from nano6studio.core.fat16 import FatImage
    from nano6studio.core.mse import extract_rsrc_fat

    mse = zipfile.ZipFile(require_ipsw()).read("Firmware.MSE")
    fat = FatImage(extract_rsrc_fat(mse))
    assert fat.tobytes().count(b"COLR") == 0
    assert fat.tobytes().count(b"CPAL") == 0

    fonts = [p for p, ent in fat.walk() if not ent.is_dir and "/Fonts/" in p]
    assert fonts
    for path in fonts:
        blob = fat.read(path)
        if blob[:4] == b"ttcf":
            count = struct.unpack_from(">I", blob, 8)[0]
            offsets = [struct.unpack_from(">I", blob, 12 + i * 4)[0] for i in range(count)]
            tag_sets = [_sfnt_tags(blob, off) for off in offsets]
        else:
            tag_sets = [_sfnt_tags(blob)]
        for tags in tag_sets:
            assert not (set(tags) & COLOR_TABLES), path

    sections = set()
    for path, ent in fat.walk():
        if ent.is_dir or not path.startswith("Resources/UI/SilverDB."):
            continue
        blob = fat.read(path)
        ver, _hdr, nsec = struct.unpack_from("<3I", blob, 0)
        assert ver == 3
        for i in range(nsec):
            magic, _count, _seq, _off = struct.unpack_from("<4sIII", blob, 12 + i * 16)
            sections.add(magic[::-1])
    assert sections == {b"LDTm", b"Str ", b"VLyt"}
