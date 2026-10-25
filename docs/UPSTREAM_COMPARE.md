# Comparing against upstream ipod_theme (nano 6G)

1. `git clone https://github.com/nfzerox/ipod_theme` (tested at commit 3ff647a).
2. The full crate needs a `thumbv6m-none-eabi` toolchain for the 7G shellcode (`build.rs`).
   The nano 6 path doesn't use it, so build a harness from the unmodified `src/mse.rs`,
   `src/img1.rs`, `parse/` and the nano6 branch of `src/main.rs` (download replaced by a local
   `Firmware-36B10147.MSE`).
3. Run it with `helpers/fat_patch.py` (pyfatfs + fontTools) and the same `SilverImagesDB.LE.bin2`.

Result on 36B10147 with the Phosphor Terminal sample theme: `manifest.plist` and the bootloader are identical.
`Firmware.MSE` is the same size (176,721,920 bytes), and all 562 files in rsrc have identical
contents. 16 bytes differ, all in the SilverImagesDB directory entry: pyfatfs deletes and
re-creates the file, which gives a new 8.3 alias (`SILVERIM.BIN` vs the stock `SILVER~1.BIN`),
the matching LFN checksum, and the current time as the timestamp. Nano 6 Theme Studio keeps the
stock entry, so its output is reproducible.

## SilverImagesDB encoder (fixed after a real-device boot loop)
Earlier builds wrote 0 in each edited image's length field, dropped the 2/4-byte padding
between images (odd offsets), and used wrong row lengths for 4-bit images. Now:
- unchanged rebuild == stock bytes; every edited blob is byte-identical to ipodhax
  `encode_image` when the stock row length equals upstream's; layout keeps stock 4-byte alignment
  (upstream pads to 2), so whole files differ from upstream's re-encoded file but are both valid.
- `core/validate.py` blocks the IPSW build on any structural problem; 0x0004 edits are refused.
- `tests/test_silverdb_upstream.py` checks all of this against a verbatim copy of ipodhax.

## Device verification
- 2026-10-24: verified on a real iPod nano 6G (fw 1.2, 36B10147) by sharphatman-ux:
  (a) stock DB rebuilt with no edits and (b) the Music home icon recolored both install via
  iTunes Shift+Update and work. The **home icon path is device-verified**.
- 2026-10-24: a clock face edit was also verified on device. Wallpapers (Settings-order mapping) were also verified on device on 2026-10-24. **Home icons, clock faces and wallpapers are all device-verified.**
  All edits go through the same encoder and validator (formats 0x0565/0x0064/0x0065/0x1888).
