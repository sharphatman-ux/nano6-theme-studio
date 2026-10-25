# SPDX-License-Identifier: GPL-3.0-only
# Nano 6 Theme Studio - Copyright (C) 2026 sharphatman-ux and contributors. See LICENSE.
"""Access to the stock firmware for tests.

Apple firmware cannot be redistributed, so it is never part of the repository.
Point the NANO6_IPSW environment variable at your own iPod nano 6G 1.2 IPSW
(iPod_1.2_36B10147.ipsw). Tests that need it are skipped when it is not set.
Everything else (MSE, SilverImagesDB) is read from that IPSW in memory."""

from __future__ import annotations

import os
import zipfile
from functools import cache
from pathlib import Path

import pytest

ENV_VAR = "NANO6_IPSW"
SKIP_REASON = f"stock firmware not available: set {ENV_VAR} to iPod_1.2_36B10147.ipsw"


def ipsw_path() -> Path | None:
    value = os.environ.get(ENV_VAR)
    if value and Path(value).is_file():
        return Path(value)
    return None


HAVE_FIRMWARE = ipsw_path() is not None
needs_firmware = pytest.mark.skipif(not HAVE_FIRMWARE, reason=SKIP_REASON)


def require_ipsw() -> Path:
    """Return the IPSW path, or skip the calling test when it is missing."""
    path = ipsw_path()
    if path is None:
        pytest.skip(SKIP_REASON)
    return path


@cache
def _stock_mse(path: Path) -> bytes:
    return zipfile.ZipFile(path).read("Firmware.MSE")


def stock_mse() -> bytes:
    return _stock_mse(require_ipsw())


@cache
def _stock_silver(path: Path) -> bytes:
    from nano6studio.core.fat16 import FatImage
    from nano6studio.core.mse import extract_rsrc_fat
    from nano6studio.core.rsrc_fs import SILVER_IMAGES

    return FatImage(extract_rsrc_fat(_stock_mse(path))).read(SILVER_IMAGES)


def stock_silver() -> bytes:
    return _stock_silver(require_ipsw())
