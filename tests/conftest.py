# SPDX-License-Identifier: GPL-3.0-only
# Nano 6 Theme Studio - Copyright (C) 2026 sharphatman-ux and contributors. See LICENSE.
"""Shared fixtures: every test's temp files go under pytest's tmp_path."""

import tempfile

import pytest


@pytest.fixture(autouse=True)
def isolated_tempdir(tmp_path, monkeypatch):
    """Point tempfile at tmp_path so a leaking scratch dir is caught, not left in /tmp."""
    from nano6studio.core import session

    scratch = tmp_path / "tempdir"
    scratch.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    yield scratch
    session.cleanup()
