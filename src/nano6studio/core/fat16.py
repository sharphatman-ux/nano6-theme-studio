# SPDX-License-Identifier: GPL-3.0-only
# Nano 6 Theme Studio - Copyright (C) 2026 sharphatman-ux and contributors. See LICENSE.
"""Minimal pure-Python FAT12/16 reader/writer (no mtools, no external deps).

Supports: reading files by path (8.3 or VFAT long names, case-insensitive),
listing directories, and replacing an existing file's contents in place,
reusing its cluster chain and allocating/freeing clusters as needed.
Every byte not belonging to the target file's data, its FAT entries, or its
directory-entry size/cluster fields is left untouched.
"""

from __future__ import annotations

import struct
from collections.abc import Iterator
from dataclasses import dataclass


@dataclass
class DirEntry:
    name: str  # long name if present, else 8.3
    short: str
    attr: int
    cluster: int
    size: int
    entry_off: int  # absolute byte offset of the 32-byte short entry in the image

    @property
    def is_dir(self) -> bool:
        return bool(self.attr & 0x10)


class FatImage:
    def __init__(self, data: bytes | bytearray):
        self.buf = bytearray(data)
        b = self.buf
        if b[510:512] != b"\x55\xaa" and b[0] not in (0xEB, 0xE9):
            raise ValueError("not a FAT boot sector")
        (
            self.bps,
            self.spc,
            self.reserved,
            self.nfats,
            self.root_entries,
            tot16,
            _media,
            self.spf,
            _spt,
            _heads,
            _hidden,
            tot32,
        ) = struct.unpack_from("<HBHBHHBHHHII", b, 11)
        if self.bps == 0 or self.spc == 0 or self.spf == 0:
            raise ValueError("unsupported FAT (FAT32 or corrupt BPB)")
        self.total_sectors = tot16 or tot32
        self.cluster_size = self.bps * self.spc
        self.fat_off = self.reserved * self.bps
        self.root_off = self.fat_off + self.nfats * self.spf * self.bps
        self.root_size = self.root_entries * 32
        self.data_off = self.root_off + ((self.root_size + self.bps - 1) // self.bps) * self.bps
        data_sectors = self.total_sectors - self.data_off // self.bps
        self.nclusters = data_sectors // self.spc
        self.fat12 = self.nclusters < 4085
        if self.nclusters >= 65525:
            raise ValueError("FAT32 not supported")
        self.eoc = 0xFFF if self.fat12 else 0xFFFF

    # ---- FAT table ----
    def _get(self, n: int, copy: int = 0) -> int:
        base = self.fat_off + copy * self.spf * self.bps
        if self.fat12:
            off = base + n + n // 2
            v = self.buf[off] | (self.buf[off + 1] << 8)
            return (v >> 4) if n & 1 else (v & 0xFFF)
        return struct.unpack_from("<H", self.buf, base + n * 2)[0]

    def _set(self, n: int, val: int) -> None:
        for c in range(self.nfats):
            base = self.fat_off + c * self.spf * self.bps
            if self.fat12:
                off = base + n + n // 2
                v = self.buf[off] | (self.buf[off + 1] << 8)
                v = ((v & 0x000F) | (val << 4)) if n & 1 else ((v & 0xF000) | (val & 0xFFF))
                self.buf[off] = v & 0xFF
                self.buf[off + 1] = (v >> 8) & 0xFF
            else:
                struct.pack_into("<H", self.buf, base + n * 2, val & 0xFFFF)

    def _is_end(self, v: int) -> bool:
        return v >= (0xFF8 if self.fat12 else 0xFFF8)

    def chain(self, start: int) -> list[int]:
        out, seen, c = [], set(), start
        while 2 <= c < self.nclusters + 2 and not self._is_end(c):
            if c in seen:
                raise ValueError("FAT chain loop")
            seen.add(c)
            out.append(c)
            c = self._get(c)
            if c == 0 or (self.fat12 and c == 0xFF7) or (not self.fat12 and c == 0xFFF7):
                raise ValueError("broken FAT chain")
        return out

    def _coff(self, c: int) -> int:
        return self.data_off + (c - 2) * self.cluster_size

    # ---- directories ----
    def _dir_slots(self, cluster: int):
        """Yield absolute offsets of 32-byte slots in a directory."""
        if cluster == 0:
            for i in range(self.root_entries):
                yield self.root_off + i * 32
        else:
            for c in self.chain(cluster):
                base = self._coff(c)
                for i in range(self.cluster_size // 32):
                    yield base + i * 32

    def listdir(self, cluster: int = 0) -> list[DirEntry]:
        res, lfn = [], {}
        for off in self._dir_slots(cluster):
            e = self.buf[off : off + 32]
            if e[0] == 0x00:
                break
            if e[0] == 0xE5:
                lfn = {}
                continue
            attr = e[11]
            if attr == 0x0F:
                seq = e[0] & 0x1F
                part = bytes(e[1:11] + e[14:26] + e[28:32]).decode("utf-16-le", "replace")
                lfn[seq] = part.split("\x00")[0]
                continue
            if attr & 0x08:
                lfn = {}
                continue
            base = e[0:8].decode("latin-1").rstrip()
            ext = e[8:11].decode("latin-1").rstrip()
            if base and base[0] == "\x05":
                base = "\xe5" + base[1:]
            short = base + ("." + ext if ext else "")
            long = "".join(lfn[k] for k in sorted(lfn)) if lfn else ""
            lfn = {}
            clus = struct.unpack_from("<H", e, 26)[0]
            size = struct.unpack_from("<I", e, 28)[0]
            res.append(DirEntry(long or short, short, attr, clus, size, off))
        return res

    def find(self, path: str) -> DirEntry:
        parts = [p for p in path.replace("\\", "/").split("/") if p]
        cluster, ent = 0, None
        for i, p in enumerate(parts):
            pl = p.lower()
            ent = next(
                (d for d in self.listdir(cluster) if d.name.lower() == pl or d.short.lower() == pl),
                None,
            )
            if ent is None:
                raise FileNotFoundError(path)
            if i < len(parts) - 1:
                if not ent.is_dir:
                    raise NotADirectoryError(path)
                cluster = ent.cluster
        if ent is None:
            raise FileNotFoundError(path)
        return ent

    def walk(self, cluster: int = 0, prefix: str = "") -> Iterator:
        for d in self.listdir(cluster):
            if d.short in (".", ".."):
                continue
            p = prefix + d.name
            if d.is_dir:
                yield p + "/", d
                yield from self.walk(d.cluster, p + "/")
            else:
                yield p, d

    # ---- file IO ----
    def read(self, path: str) -> bytes:
        ent = self.find(path)
        if ent.is_dir:
            raise IsADirectoryError(path)
        out = bytearray()
        for c in self.chain(ent.cluster) if ent.cluster else []:
            o = self._coff(c)
            out += self.buf[o : o + self.cluster_size]
        if len(out) < ent.size:
            raise ValueError(f"{path}: chain shorter than file size")
        return bytes(out[: ent.size])

    def free_clusters(self) -> int:
        return sum(1 for n in range(2, self.nclusters + 2) if self._get(n) == 0)

    def write(self, path: str, data: bytes) -> None:
        """Replace an existing file's contents. Reuses clusters in order,
        allocates free clusters if it grows, frees tail clusters if it shrinks."""
        ent = self.find(path)
        if ent.is_dir:
            raise IsADirectoryError(path)
        cs = self.cluster_size
        need = (len(data) + cs - 1) // cs
        old = self.chain(ent.cluster) if ent.cluster else []
        if need > len(old):
            extra, n = [], 2
            while len(extra) < need - len(old) and n < self.nclusters + 2:
                if self._get(n) == 0 and n not in old:
                    extra.append(n)
                n += 1
            if len(extra) < need - len(old):
                raise OSError("FAT image full: not enough free clusters")
            new = old + extra
        else:
            new = old[:need]
        # FAT: only touch entries whose values actually change
        for i, c in enumerate(new):
            nxt = new[i + 1] if i + 1 < len(new) else self.eoc
            if self._get(c) != nxt or any(self._get(c, k) != nxt for k in range(self.nfats)):
                if i + 1 < len(new) or not self._is_end(self._get(c)):
                    self._set(c, nxt)
        for c in old[need:]:
            self._set(c, 0)
        # data: overwrite only the file's bytes, leave slack after EOF as is
        for i, c in enumerate(new):
            chunk = data[i * cs : (i + 1) * cs]
            o = self._coff(c)
            self.buf[o : o + len(chunk)] = chunk
        first = new[0] if new else 0
        struct.pack_into("<H", self.buf, ent.entry_off + 26, first)
        struct.pack_into("<I", self.buf, ent.entry_off + 28, len(data))

    def tobytes(self) -> bytes:
        return bytes(self.buf)
