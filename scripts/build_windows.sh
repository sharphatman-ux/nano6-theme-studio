#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-only
set -euo pipefail
# Build Nano6ThemeStudio.exe under Wine (Windows Python 3.11 + PyInstaller 6.3 + UPX).
# Uses the checked-in slim Nano6ThemeStudio.spec. No mtools / NumPy needed.
WINE=${WINE:-wine}
PY='C:\Python311\python.exe'
cd "$(dirname "$0")/.."
$WINE "$PY" -m pip install "PySide6==6.6.3.1" Pillow pyinstaller==6.3.0
$WINE "$PY" -OO -m PyInstaller --noconfirm --clean --upx-dir 'C:\windows' Nano6ThemeStudio.spec
ls -la dist/Nano6ThemeStudio.exe
