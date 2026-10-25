# SPDX-License-Identifier: GPL-3.0-only
# Nano 6 Theme Studio - Copyright (C) 2026 sharphatman-ux and contributors. See LICENSE.
# Ported in part from ipodhax by 760ceb3b9c0ba4872cadf3ce35a7a494, licence MIT
# (https://github.com/760ceb3b9c0ba4872cadf3ce35a7a494/ipodhax, silverdb/pack.py and utils.py:
# the RGB565 conversion, palette order and per-format flags/row lengths).
# Copyright (c) 2023 760ceb3b9c0ba4872cadf3ce35a7a494; MIT text in third_party/ipodhax-LICENSE.txt.
# Format research also from silverutil by Spotlight (MIT).
"""SilverImagesDB.LE.bin decode/encode for iPod nano 6G (Pillow only, no NumPy).

File layout (little endian): a 0x1C-byte header ('paMB' magic at offset 12, image
count), a table of (id, offset, length) records, then the images. Image ids start
at 0x0DAD0000. Each image is a 32-byte header

    format, 1, row_length, flags, 0, 0, height, width, id, payload_length

followed by its payload, 4-byte aligned. Formats: 0x1888 (ARGB 8888), 0x0565
(RGB 565), 0x0064/0x0065 (8-bit palette, with/without alpha), 0x0008 and 0x0004
(grey / 4-bit). The encoder is byte-identical to upstream ipodhax encode_image;
an unedited rebuild reproduces the stock file exactly (tests check this)."""

from __future__ import annotations

import struct
from dataclasses import dataclass, field

from PIL import Image

HEADER_MAGIC = b"paMB"
DIR_START = 0x1C


@dataclass
class SilverImage:
    image_id: int
    fmt: int
    bpp: int
    stride: int
    width: int
    height: int
    raw_payload: bytes
    header32: bytes
    modified: bool = False
    _pil: Image.Image | None = field(default=None, repr=False, compare=False)

    @property
    def fmt_name(self) -> str:
        return f"{self.fmt:04x}"

    @property
    def size(self):
        return (self.width, self.height)

    def to_pil(self) -> Image.Image:
        if self._pil is not None:
            return self._pil
        b = self.header32 + self.raw_payload
        fmt, _, stride, bpp = struct.unpack("<4H", b[:8])
        h, w = struct.unpack("<2I", b[16:24])
        body = b[32:]
        if fmt in (0x64, 0x65):
            pc = struct.unpack("<I", body[:4])[0]
            pal = body[4 : 4 + 4 * pc]
            pix = body[4 + 4 * pc :]
            elem = 1 if fmt == 0x64 else 2
            # build palette as RGB tuples from BGRA
            colors = []
            for i in range(pc):
                bb, gg, rr, aa = pal[i * 4 : i * 4 + 4]
                colors.append((rr, gg, bb, aa))
            if pc == 0:
                im = Image.frombytes("L", (w, h), pix[: stride * h], "raw", "L", stride)
            else:
                im = Image.new("RGBA", (w, h))
                px = im.load()
                for y in range(h):
                    row = pix[y * stride : y * stride + w * elem]
                    for x in range(w):
                        if fmt == 0x64:
                            idx = row[x] if x < len(row) else 0
                        else:
                            if x * 2 + 1 < len(row):
                                idx = row[x * 2] | (row[x * 2 + 1] << 8)
                            else:
                                idx = 0
                        if idx >= pc:
                            idx = pc - 1
                        px[x, y] = colors[idx]
        elif bpp == 16 or fmt == 0x565:
            im = Image.new("RGB", (w, h))
            px = im.load()
            for y in range(h):
                row = body[y * stride : y * stride + w * 2]
                for x in range(w):
                    if x * 2 + 1 >= len(row):
                        break
                    v = row[x * 2] | (row[x * 2 + 1] << 8)
                    r = ((v >> 11) & 0x1F) << 3
                    g = ((v >> 5) & 0x3F) << 2
                    bl = (v & 0x1F) << 3
                    px[x, y] = (r, g, bl)
        elif bpp == 32 or fmt == 0x1888:
            # BGRA
            im = Image.frombytes("RGBA", (w, h), body[: stride * h], "raw", "BGRA", stride)
        elif bpp == 8 or fmt == 0x8:
            im = Image.frombytes("L", (w, h), body, "raw", "L", stride)
        elif bpp == 4 or fmt == 0x4:
            need = (w * h + 1) // 2
            raw = body[:need]
            out = bytearray(w * h)
            for i, byte in enumerate(raw):
                if 2 * i < len(out):
                    out[2 * i] = ((byte >> 4) & 0xF) * 17
                if 2 * i + 1 < len(out):
                    out[2 * i + 1] = (byte & 0xF) * 17
            im = Image.frombytes("L", (w, h), bytes(out))
        else:
            im = Image.new("RGBA", (w, h), (255, 0, 255, 255))
        self._pil = im
        return im

    def set_pil(self, im: Image.Image, keep_format: bool = True) -> None:
        payload = encode_pixels(im, self.fmt, self.bpp, self.width, self.height, self.stride)
        self.raw_payload = payload
        self.header32 = build_header(
            self.fmt,
            self.bpp,
            self.width,
            self.height,
            self.image_id,
            stride=self.stride,
            payload_len=len(payload),
        )
        self._pil = None
        self.modified = True


# Format -> (flags field, default row length) exactly as ipodhax/silverdb/pack.py writes them.
FLAGS = {0x1888: 0x20, 0x0004: 0x04, 0x0008: 0x08, 0x0565: 0x10, 0x0064: 0x08, 0x0065: 0x10}
PALETTE_MAX = {0x0064: 0xFF, 0x0065: 0xFFFF}


def default_stride(fmt: int, w: int) -> int:
    return {
        0x1888: w * 4,
        0x0004: (w + 1) // 2,
        0x0008: w,
        0x0565: w * 2,
        0x0064: w,
        0x0065: w * 2,
    }[fmt]


def build_header(
    fmt: int,
    bpp: int,
    w: int,
    h: int,
    image_id: int = 0,
    stride: int | None = None,
    payload_len: int = 0,
) -> bytes:
    """32-byte image header, field-for-field as upstream: fmt, 1, row_length, flags, 0, 0,
    height, width, id, payload length (bytes after the header)."""
    if fmt not in FLAGS:
        raise ValueError(f"cannot encode unknown format {fmt:04x}")
    row = stride if stride else default_stride(fmt, w)
    head = struct.pack("<4H", fmt, 1, row, FLAGS[fmt]) + b"\0" * 8
    head += struct.pack("<4I", h, w, image_id & 0xFFFFFFFF, payload_len)
    return head


def _to565(p):  # ipodhax utils.pixel_to565, bit-exact
    return (
        ((int(0b11111 * (int(p[0]) / 255)) << 6) + int(0b111111 * (int(p[1]) / 255))) << 5
    ) + int(0b11111 * (int(p[2]) / 255))


def _limit_colours(im: Image.Image, n: int) -> Image.Image:
    if len(set(im.getdata())) <= n:
        return im
    q = im.convert("RGBA").quantize(colors=min(n, 256), method=Image.Quantize.FASTOCTREE)
    return q.convert("RGBA")


def encode_pixels(
    im: Image.Image, fmt: int, bpp: int, w: int, h: int, stride: int | None = None
) -> bytes:
    """Pixel payload. For the stock row length it is byte-identical to ipodhax encode_image;
    rows longer than the pixels (stock padding) are zero-filled."""
    im = im.convert("RGBA")
    if im.size != (w, h):
        im = im.resize((w, h), Image.Resampling.LANCZOS)
    row = stride if stride else default_stride(fmt, w)

    def rows(per_row: list[bytes]) -> bytes:
        out = bytearray()
        for r in per_row:
            if len(r) > row:
                raise ValueError(f"row of {len(r)} bytes exceeds row length {row}")
            out += r + b"\0" * (row - len(r))
        return bytes(out)

    if fmt == 0x1888:
        d = im.tobytes("raw", "BGRA")
        n = w * 4
        return rows([d[y * n : (y + 1) * n] for y in range(h)])
    if fmt == 0x0565:
        px = list(im.convert("RGB").getdata())
        return rows(
            [
                b"".join(struct.pack("<H", _to565(p)) for p in px[y * w : (y + 1) * w])
                for y in range(h)
            ]
        )
    if fmt == 0x0008:
        d = bytes(im.convert("L").getdata())
        return rows([d[y * w : (y + 1) * w] for y in range(h)])
    if fmt == 0x0004:
        g = list(im.convert("L").getdata())
        out = []
        for y in range(h):
            r = g[y * w : (y + 1) * w] + ([0] if w % 2 else [])
            out.append(bytes(((r[i] // 17) << 4) + (r[i + 1] // 17) for i in range(0, len(r), 2)))
        return rows(out)
    if fmt in PALETTE_MAX:
        im = _limit_colours(im, PALETTE_MAX[fmt])
        pixels = im.getdata()
        unique = list(set(pixels))  # same palette order as ipodhax
        if len(unique) > PALETTE_MAX[fmt]:
            raise ValueError("too many colours")
        index = {c: k for k, c in enumerate(unique)}
        k = 1 if fmt == 0x0064 else 2
        pal = struct.pack("<I", len(unique)) + b"".join(
            bytes([c[2], c[1], c[0], c[3]]) for c in unique
        )
        px = list(pixels)
        return pal + rows(
            [
                b"".join(index[p].to_bytes(k, "little") for p in px[y * w : (y + 1) * w])
                for y in range(h)
            ]
        )
    raise ValueError(f"cannot encode unknown format {fmt:04x}")


@dataclass
class SilverImagesDB:
    raw: bytes
    version: int
    entry_count: int
    data_base: int
    images: dict[int, SilverImage]
    order: list[int]
    dir_bytes: bytes

    @classmethod
    def parse(cls, data: bytes) -> SilverImagesDB:
        if len(data) < 0x48AC:
            raise ValueError("SilverImagesDB too small")
        ver, _, nchunks = struct.unpack("<3I", data[:12])
        tag, sz, x, y = struct.unpack("<4s3I", data[12:28])
        if tag != HEADER_MAGIC:
            raise ValueError(f"Expected paMB, got {tag!r}")
        n = sz
        data_base = 0x1C + n * 12
        images: dict[int, SilverImage] = {}
        order: list[int] = []
        for i in range(n):
            iid, off, szb = struct.unpack(
                "<3I", data[DIR_START + i * 12 : DIR_START + (i + 1) * 12]
            )
            order.append(iid)
            if szb == 0:
                continue
            blob = data[data_base + off : data_base + off + szb]
            if len(blob) < 32:
                continue
            fmt, unk, stride, bpp = struct.unpack("<4H", blob[:8])
            h, w = struct.unpack("<2I", blob[16:24])
            images[iid] = SilverImage(
                image_id=iid,
                fmt=fmt,
                bpp=bpp,
                stride=stride,
                width=w,
                height=h,
                raw_payload=blob[32:],
                header32=blob[:32],
            )
        return cls(
            raw=data,
            version=ver,
            entry_count=n,
            data_base=data_base,
            images=images,
            order=order,
            dir_bytes=data[DIR_START:data_base],
        )

    def rebuild(self, force: bool = False) -> bytes:
        """Stock layout: directory in id order, every image 4-byte aligned (zero padding
        between images, not counted in the size), empty entries point at the aligned
        position. With no edits (and force) this reproduces the stock file byte-for-byte."""
        if not force and not any(im.modified for im in self.images.values()):
            return self.raw
        out_dir = bytearray()
        out_data = bytearray()
        for i, iid in enumerate(self.order):
            o = DIR_START + i * 12
            _, orig_off, orig_sz = struct.unpack("<3I", self.raw[o : o + 12])
            img = self.images.get(iid)
            if img is None or not img.modified:
                blob = (
                    b""
                    if orig_sz == 0
                    else self.raw[self.data_base + orig_off : self.data_base + orig_off + orig_sz]
                )
            else:
                blob = img.header32 + img.raw_payload
            out_data += b"\0" * (-len(out_data) % 4)
            out_dir += struct.pack("<3I", iid, len(out_data), len(blob))
            out_data += blob
        return bytes(self.raw[:DIR_START] + out_dir + out_data)

    def _stock_end(self):
        return len(self.raw) - self.data_base

    def classify(self, iid: int) -> str:
        im = self.images.get(iid)
        if not im:
            return "other"
        w, h = im.width, im.height
        if (w, h) == (240, 240):
            return "wallpaper"
        if (w, h) in ((79, 79), (105, 105), (50, 50), (55, 55), (60, 60), (120, 120)):
            return "icon"
        return "other"
