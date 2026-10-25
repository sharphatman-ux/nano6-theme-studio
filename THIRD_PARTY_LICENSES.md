# Third-party licences

Nano 6 Theme Studio is licensed GPL-3.0-only (see `LICENSE`). This file lists everything
it includes, ports or links against, with the licence and where the full text lives.

## Ported or vendored code

| Component | Licence | Full text | Used as |
|---|---|---|---|
| ipod_theme (nfzerox and contributors), commit 3ff647a | GPL-3.0 | `third_party/ipod_theme-LICENSE.txt` (upstream LICENSE verbatim, including its MIT notices for bundled ipodhax and silverutil) | ported to Python in `core/firmware_pack.py` |
| ipod_sun (CUB3D), commit b7891b3 | GPL-3.0 | `third_party/ipod_sun-LICENSE.txt` | upstream of the code above |
| ipodhax (760ceb3b9c0ba4872cadf3ce35a7a494), commit 3c680ff | MIT | `third_party/ipodhax-LICENSE.txt`, `tests/upstream/ipodhax/LICENSE` | format reference; vendored unmodified for tests only |
| silverutil (Spotlight) | MIT | `third_party/silverutil-LICENSE.txt` | format reference |

What was ported and what was left out: `third_party/ipod_theme-ipod_sun-NOTICE.txt`.
wInd3x (GPL-2.0-or-later) is referenced for research only: `third_party/wInd3x-LICENSE-NOTE.txt`.

## Libraries in the Windows build

| Component | Licence | More info |
|---|---|---|
| Python 3.11 | PSF License | https://docs.python.org/3/license.html |
| PySide6 / Shiboken6 / Qt 6 | LGPL-3.0 (also GPL / commercial) | https://doc.qt.io/qtforpython/licenses.html |
| Pillow | MIT-CMU (HPND) | https://github.com/python-pillow/Pillow/blob/main/LICENSE |
| PyInstaller (bootloader) | GPL-2.0-or-later with bootloader exception | https://pyinstaller.org/en/stable/license.html |
| UPX | GPL-2.0-or-later with UPX exception | https://github.com/upx/upx/blob/devel/LICENSE |

Qt is used unmodified under the LGPL. The complete source of this app and the build spec are
published, so anyone can rebuild the .exe against a different Qt/PySide6.

## Development and test tools (not shipped)

| Component | Licence | More info |
|---|---|---|
| pytest | MIT | https://github.com/pytest-dev/pytest |
| pyfatfs (upstream comparison test) | MIT | https://github.com/nathanhi/pyfatfs |
| PyFilesystem2 (`fs`, pyfatfs dependency) | MIT | https://github.com/PyFilesystem/pyfilesystem2 |
| ruff | MIT | https://github.com/astral-sh/ruff |
