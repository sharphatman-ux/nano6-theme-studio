# SPDX-License-Identifier: GPL-3.0-only
# Nano 6 Theme Studio - Copyright (C) 2026 sharphatman-ux and contributors. See LICENSE.
"""One scratch directory per session, always cleaned up.

Firmware is now read entirely in memory, so nothing normally needs disk space.
Anything that does must go through session_dir(): it is a single
TemporaryDirectory (prefix "n6ts_") that is removed when a new firmware is
opened, when the window closes and at interpreter exit. Directories left
behind by a crashed session are removed at startup once they are a day old."""

from __future__ import annotations

import atexit
import shutil
import tempfile
import time
from pathlib import Path

PREFIX = "n6ts_"
STALE_AFTER_SECONDS = 24 * 60 * 60

_current: tempfile.TemporaryDirectory | None = None


def session_dir() -> Path:
    """Return the session scratch directory, creating it on first use."""
    global _current
    if _current is None:
        _current = tempfile.TemporaryDirectory(prefix=PREFIX)
    return Path(_current.name)


def cleanup() -> None:
    """Delete the session directory (safe to call more than once)."""
    global _current
    if _current is not None:
        _current.cleanup()
        _current = None


def remove_stale(max_age: float = STALE_AFTER_SECONDS, root: Path | None = None) -> int:
    """Remove n6ts_* directories older than max_age seconds; return how many."""
    root = Path(root or tempfile.gettempdir())
    cutoff = time.time() - max_age
    current = Path(_current.name) if _current is not None else None
    removed = 0
    for path in root.glob(PREFIX + "*"):
        try:
            if path == current or not path.is_dir() or path.stat().st_mtime > cutoff:
                continue
        except OSError:
            continue
        shutil.rmtree(path, ignore_errors=True)
        removed += 1
    return removed


atexit.register(cleanup)
