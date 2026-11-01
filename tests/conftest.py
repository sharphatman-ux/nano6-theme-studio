# SPDX-License-Identifier: GPL-3.0-only
# Nano 6 Theme Studio - Copyright (C) 2026 sharphatman-ux and contributors. See LICENSE.
"""Shared fixtures: every test's temp files go under pytest's tmp_path."""

import os
import sys
import tempfile

import pytest

# Offscreen Qt. Software GL avoids a Mesa abort on GitHub runners when the
# offscreen plugin initialises EGL without a GPU (exit 134, no Python traceback).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_OPENGL", "software")
os.environ.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")


def _install_qt_fatal_log() -> None:
    """Flush Qt's fatal text before abort(), which otherwise drops the C buffer."""
    try:
        from PySide6.QtCore import QtMsgType, qInstallMessageHandler
    except ImportError:
        return

    def _handler(mode, _context, message):
        if mode == QtMsgType.QtFatalMsg:
            sys.stderr.write(f"Qt fatal: {message}\n")
            sys.stderr.flush()

    qInstallMessageHandler(_handler)


_install_qt_fatal_log()


@pytest.fixture(autouse=True)
def isolated_tempdir(tmp_path, monkeypatch):
    """Point tempfile at tmp_path so a leaking scratch dir is caught, not left in /tmp."""
    from nano6studio.core import session

    scratch = tmp_path / "tempdir"
    scratch.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    yield scratch
    session.cleanup()
