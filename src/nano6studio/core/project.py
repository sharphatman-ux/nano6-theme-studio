# SPDX-License-Identifier: GPL-3.0-only
# Nano 6 Theme Studio - Copyright (C) 2026 sharphatman-ux and contributors. See LICENSE.
"""Theme project model (.n6theme zip) with per-asset / per-icon edit tracking."""

from __future__ import annotations

import json
import zipfile
from dataclasses import asdict, dataclass, field
from io import BytesIO
from pathlib import Path

from PIL import Image

from .silverimages import SilverImagesDB


@dataclass
class AssetEdit:
    image_id: int
    category: str  # wallpaper | clock | icon | other
    label: str = ""
    manual: bool = False  # user-edited by hand
    notes: str = ""


@dataclass
class ThemeProject:
    name: str = "Untitled"
    ipsw_path: str = ""
    silver_path: str = ""  # path to loaded SilverImagesDB on disk (working copy)
    edits: dict[int, AssetEdit] = field(default_factory=dict)
    replacements: dict[int, str] = field(default_factory=dict)  # id -> relative png in project
    wallpaper_id: int | None = None
    clock_id: int | None = None
    icon_ids: list[int] = field(default_factory=list)
    accent: str = "#5AC8FA"
    gen_style: str = "tint"
    # working images held in memory after load
    _db: SilverImagesDB | None = field(default=None, repr=False, compare=False)
    _preview_cache: dict[int, Image.Image] = field(default_factory=dict, repr=False, compare=False)

    def mark_manual(self, image_id: int, category: str = "icon", label: str = "") -> None:
        e = self.edits.get(image_id) or AssetEdit(image_id=image_id, category=category, label=label)
        e.manual = True
        e.category = category or e.category
        if label:
            e.label = label
        self.edits[image_id] = e

    def is_manual(self, image_id: int) -> bool:
        e = self.edits.get(image_id)
        return bool(e and e.manual)

    def customized_icon_ids(self) -> set[int]:
        return {i for i in self.icon_ids if self.is_manual(i) or i in self.replacements}

    def apply_replacement(
        self, image_id: int, im: Image.Image, category: str, manual: bool = True
    ) -> None:
        if not self._db or image_id not in self._db.images:
            raise KeyError(image_id)
        slot = self._db.images[image_id]
        slot.set_pil(im, keep_format=True)
        self._preview_cache[image_id] = slot.to_pil()
        if manual:
            self.mark_manual(image_id, category=category)
        else:
            e = self.edits.get(image_id) or AssetEdit(image_id=image_id, category=category)
            e.manual = False
            self.edits[image_id] = e
        self.replacements[image_id] = f"assets/{image_id:08x}.png"

    def revert(self, image_id: int) -> None:
        if not self._db:
            return
        # reload original blob from raw if present
        db = self._db
        for i, iid in enumerate(db.order):
            if iid == image_id:
                import struct

                off = 0x1C + i * 12
                _, orig_off, orig_sz = struct.unpack("<3I", db.raw[off : off + 12])
                if orig_sz:
                    blob = db.raw[db.data_base + orig_off : db.data_base + orig_off + orig_sz]
                    import struct as st

                    from .silverimages import SilverImage

                    fmt, unk, stride, bpp = st.unpack("<4H", blob[:8])
                    h, w = st.unpack("<2I", blob[16:24])
                    db.images[image_id] = SilverImage(
                        image_id=image_id,
                        fmt=fmt,
                        bpp=bpp,
                        stride=stride,
                        width=w,
                        height=h,
                        raw_payload=blob[32:],
                        header32=blob[:32],
                    )
                break
        self.replacements.pop(image_id, None)
        self.edits.pop(image_id, None)
        self._preview_cache.pop(image_id, None)

    def save_n6theme(self, path: Path) -> None:
        meta = {
            "name": self.name,
            "ipsw_path": self.ipsw_path,
            "wallpaper_id": self.wallpaper_id,
            "clock_id": self.clock_id,
            "icon_ids": self.icon_ids,
            "accent": self.accent,
            "gen_style": self.gen_style,
            "edits": {str(k): asdict(v) for k, v in self.edits.items()},
            "replacements": {str(k): v for k, v in self.replacements.items()},
            "version": 1,
        }
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr("project.json", json.dumps(meta, indent=2))
            if self._db:
                for iid in self.replacements:
                    im = self._db.images[iid].to_pil()
                    buf = BytesIO()
                    im.save(buf, format="PNG")
                    z.writestr(f"assets/{iid:08x}.png", buf.getvalue())

    @classmethod
    def load_n6theme(cls, path: Path, db: SilverImagesDB | None = None) -> ThemeProject:
        with zipfile.ZipFile(path, "r") as z:
            meta = json.loads(z.read("project.json"))
            proj = cls(
                name=meta.get("name", "Untitled"),
                ipsw_path=meta.get("ipsw_path", ""),
                wallpaper_id=meta.get("wallpaper_id"),
                clock_id=meta.get("clock_id"),
                icon_ids=list(meta.get("icon_ids") or []),
                accent=meta.get("accent", "#5AC8FA"),
                gen_style=meta.get("gen_style", "tint"),
            )
            for k, v in (meta.get("edits") or {}).items():
                proj.edits[int(k)] = AssetEdit(**v)
            proj.replacements = {int(k): v for k, v in (meta.get("replacements") or {}).items()}
            proj._db = db
            if db:
                for iid, rel in proj.replacements.items():
                    try:
                        data = z.read(rel)
                        im = Image.open(BytesIO(data)).convert("RGBA")
                        manual = proj.is_manual(iid)
                        cat = proj.edits.get(iid).category if iid in proj.edits else "other"
                        proj.apply_replacement(iid, im, cat, manual=manual)
                    except KeyError:
                        pass
            return proj


def catalog_assets(db: SilverImagesDB) -> dict[str, list]:
    """Semantic catalog (see core/catalog.py): real home apps by ID, clock faces
    grouped per style, wallpapers; everything else is 'other' (Advanced)."""
    from . import catalog as C

    apps = C.home_apps(db)
    faces = C.clock_faces(db)
    walls = C.wallpapers(db)
    known = {i for a in apps for i in a.ids}
    known |= {i for f in faces for _, i in f.parts}
    known |= {c for _, w, _ in walls for c in C.wallpaper_copies(w)} | {t for _, _, t in walls if t}
    return {
        "apps": apps,
        "clock_faces": faces,
        "wallpapers": walls,
        "wallpaper": [w for _, w, _ in walls],
        "clock": [f.background for f in faces if f.background],
        "home_icons": [i for a in apps for i in a.ids],
        "other": sorted(i for i in db.images if i not in known),
    }
