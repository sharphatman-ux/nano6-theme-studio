# Contributing

Nano 6 Theme Studio is GPL-3.0. Contributions are welcome under the same licence.

## Setup

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install pytest pyfatfs "setuptools<81" ruff
```

Most tests need a stock iPod nano 6G firmware 1.2 IPSW (`iPod_1.2_36B10147.ipsw`, build
36B10147). It is Apple's and must never be committed. Download it from Apple, or use the copy
iTunes cached; the link, checksums and cache path are in the README section
[Getting the firmware (iPod_1.2_36B10147)](README.md#getting-the-firmware-ipod_1236b10147).
Point `NANO6_IPSW` at your own copy; everything else is read from it in memory
(`tests/firmware.py`). Without it those tests are skipped.

## Tests

```
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests                         # no firmware
NANO6_IPSW=/path/to/iPod_1.2_36B10147.ipsw QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests
```

Important invariants the tests protect:

* rebuilding an unedited SilverImagesDB reproduces the stock file byte for byte;
* the encoder matches upstream ipodhax `encode_image`;
* the validator (`core/validate.py`) passes for every edit path.

Do not change the encoder or the validator without a device test.

## Style

```
.venv/bin/ruff format src tests scripts
.venv/bin/ruff check src tests scripts
```

Line length is 100 (see `ruff.toml`). Prefer one statement per line, descriptive
names, type hints on public functions, and comments that explain why rather than what.

## Building the Windows .exe

The build runs under Wine with a Windows Python 3.11 that has the requirements and
PyInstaller installed:

```
wine C:\Python311\python.exe -OO -m PyInstaller --noconfirm --clean --upx-dir C:\windows Nano6ThemeStudio.spec
```

`scripts/build_windows.sh` wraps this. The result is `dist/Nano6ThemeStudio.exe`
(keep it under 25 MB). Check it with the headless self-test:

```
wine dist/Nano6ThemeStudio.exe --selftest iPod_1.2_36B10147.ipsw report.txt [theme.n6theme] [shots_dir]
```

The app never writes to an iPod. It produces an IPSW that the user restores with iTunes.

## What must not be committed

Apple firmware (`.ipsw`, `Firmware.MSE`), anything extracted from it (`SilverImagesDB*`, stock
PNGs, fonts such as HelveticaBold.ttf), screenshots that show stock artwork, and build output.
`.gitignore` covers the usual names.
