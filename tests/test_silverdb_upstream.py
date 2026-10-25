# SPDX-License-Identifier: GPL-3.0-only
"""SilverImagesDB encoder vs stock bytes and upstream ipodhax (reference implementation)."""

import io
import random
import struct
import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent / "upstream"))
from firmware import stock_silver  # noqa: E402
from ipodhax.silverdb.pack import encode_image  # noqa: E402
from ipodhax.silverdb.unpack import unpack_silverdb  # noqa: E402

from nano6studio.core.silverimages import SilverImagesDB, default_stride
from nano6studio.core.validate import ValidationError, check, validate


@pytest.fixture(scope="module")
def raw():
    return stock_silver()


def test_unchanged_rebuild_is_stock_bytes(raw):
    db = SilverImagesDB.parse(raw)
    assert db.rebuild(force=True) == raw
    for im in db.images.values():
        im.modified = True  # every blob through the writer
    assert db.rebuild() == raw
    assert check(raw, raw) == []  # stock passes the validator


def _sample(db, fmt, k=3):
    ids = sorted(
        i
        for i, im in db.images.items()
        if im.fmt == fmt and im.stride == default_stride(fmt, im.width)
    )
    random.Random(fmt).shuffle(ids)
    return ids[:k]


def _art(w, h, colours=None):
    im = Image.new("RGBA", (w, h))
    px = im.load()
    for y in range(h):
        for x in range(w):
            c = ((x * 37 + y * 11) % 256, (x * 5) % 256, (y * 9) % 256, 255 if (x + y) % 5 else 128)
            if colours:
                c = colours[(x + y) % len(colours)]
            px[x, y] = c
    return im


@pytest.mark.parametrize("fmt", [0x1888, 0x0565, 0x0064, 0x0065, 0x0008])
def test_blob_matches_upstream_encoder_and_roundtrips(raw, fmt, tmp_path):
    db = SilverImagesDB.parse(raw)
    for iid in _sample(db, fmt):
        im = db.images[iid]
        cols = (
            [(i * 9 % 256, 255 - i, i * 3 % 256, 255) for i in range(40)] if fmt == 0x0064 else None
        )
        art = _art(im.width, im.height, cols)
        if fmt in (0x0008,):
            art = art.convert("L").convert("RGBA")
        im.set_pil(art)
        mine = im.header32 + im.raw_payload
        png = tmp_path / f"{iid}_{fmt:04x}.png"
        art.save(png)
        s = io.BytesIO()
        encode_image(iid, fmt, png, s)
        assert mine == s.getvalue(), f"{iid} {fmt:04x} differs from upstream encode_image"
    new = db.rebuild()
    validate(new, raw)
    out = tmp_path / "out"
    out.mkdir()
    unpack_silverdb(io.BytesIO(new), out)  # upstream decoder: every id must come out
    got = {int(p.stem.split("_")[0]) for p in out.glob("*.png")}
    assert set(db.images) <= got
    for iid in _sample(db, fmt):
        ref = Image.open(out / f"{iid}_{fmt:04x}.png").convert("RGBA")
        mine = db.images[iid].to_pil().convert("RGBA")
        assert ref.size == mine.size
        if fmt != 0x0565:
            assert list(ref.getdata()) == list(mine.getdata())


def test_validator_blocks_bad_files(raw):
    db = SilverImagesDB.parse(raw)
    iid = _sample(db, 0x1888, 1)[0]
    im = db.images[iid]
    im.set_pil(_art(im.width, im.height))
    good = db.rebuild()
    assert check(good, raw) == []
    n, base = struct.unpack_from("<I", good, 16)[0], None

    def entry(data):
        i = db.order.index(iid)
        return 0x1C + i * 12

    o = entry(good)
    _, off, sz = struct.unpack_from("<3I", good, o)
    base = 0x1C + n * 12
    bad = bytearray(good)
    struct.pack_into("<I", bad, base + off + 28, 0)
    assert any("length field" in p for p in check(bytes(bad), raw))
    bad = bytearray(good)
    struct.pack_into("<H", bad, base + off + 4, im.width)  # wrong row length
    assert check(bytes(bad), raw)
    bad = bytearray(good)
    struct.pack_into("<I", bad, o + 4, off + 1)  # misaligned
    assert any("aligned" in p for p in check(bytes(bad), raw))
    four = next(i for i, x in db.images.items() if x.fmt == 0x0004)
    db.images[four].set_pil(_art(db.images[four].width, db.images[four].height))
    with pytest.raises(ValidationError):
        validate(db.rebuild(), raw)
