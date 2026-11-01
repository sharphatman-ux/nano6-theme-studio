# SPDX-License-Identifier: GPL-3.0-only
# Nano 6 Theme Studio - Copyright (C) 2026 sharphatman-ux and contributors. See LICENSE.
"""Shared fixtures: every test's temp files go under pytest's tmp_path."""

import os
import sys
import tempfile

import pytest

# Offscreen Qt. Software GL avoids a Mesa abort on GitHub runners when the
# offscreen plugin initialises EGL without a GPU.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_OPENGL", "software")
os.environ.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_sessionfinish(session, exitstatus):
    """Leave before PySide's static destructors run.

    On CPython 3.11 (what GitHub Actions uses) those destructors segfault
    after a successful offscreen run, so pytest's 0 becomes 139. Yield first
    so the result summary is printed, then os._exit with that status.
    """
    result = yield
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(int(getattr(session, "exitstatus", exitstatus)))
    return result


@pytest.fixture(autouse=True)
def isolated_tempdir(tmp_path, monkeypatch):
    """Point tempfile at tmp_path so a leaking scratch dir is caught, not left in /tmp."""
    from nano6studio.core import session

    scratch = tmp_path / "tempdir"
    scratch.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    yield scratch
    session.cleanup()
