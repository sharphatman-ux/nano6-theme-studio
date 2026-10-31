# Clock faces: hand pivots and digit positions

Checked against a local copy of stock `iPod_1.2_36B10147.ipsw` (SHA-256
`84b27d59f376eaf51270f2ee7ee67016e67fc992882d518f9b294ee21122297d`). That file is not
in this repository. Nothing below is written back into the IPSW by Hand alignment.

## Hand pivots — not stored in the firmware

SilverImagesDB on this build has 1,509 images (ids `0x0DAD0158`–`0x0DAD0760`). Every
32-byte image header has the usual `1` in the unknown field at offset 2, and the eight
bytes at offset 8 are zero. There is no per-image origin or pivot.

The IPSW is the bootloader, `manifest.plist`, and `Firmware.MSE`. The only plaintext UI
databases are on the `rsrc` FAT volume. `SilverDB.*.LE.bin` has three section types:
`LDTm`, `Str `, and `VLyt` (60 records in `en_GB`, ids `0x0DAD146F`–`0x0DAD15D3`).
Shared `VLyt` records are byte-identical in `de_DE` (`de_DE` has one extra record).
`VLyt` does not contain clock bitmap ids, and it does not contain the "Clock Face"
string id `0x0DAD0C78`. Ids embedded in those records (for example `0x0DAD1F42`) are
above both the image range and the `en_GB` string range (`0x81`–`0x0DAD114B`), so they
point at resources that are not in `rsrc`. No non-media file on `rsrc` contains a
clock-hand image id. `CLKH` (a section silverutil has seen in a nano 7G internal
database) does not occur anywhere in this IPSW. `paMB` occurs once, in SilverImagesDB.

`osos`, `disk`, `appl`, `diag`, `lbat`, `bdsw`, `bdhw`, and `chrg` are ciphertext
(entropy about 7.96 bits/byte from offset `0x1400`, with the plaintext tag `87232.0`
at `0x1000`). A per-face pivot table, if the OS has one, is in that encrypted image.
It cannot be read or edited from the files this app packs.

So the iPod's hand placement is not an asset field:

* Hands turn about the **middle of the 240×240 screen** (120, 120). Nothing in the
  assets selects another point. That is what earlier device-verified clock edits were
  built around, and it is what this preview uses unless you move Centre X/Y.
* Which **pixel of the hand bitmap** lands on that centre is not stored either. Stock
  hands do not share one fraction: the widest opaque row sits anywhere from about 45%
  to 86% of the way down the bitmap (simple hands cluster nearer 80%, character hands
  do not). The studio's previous preview used the horizontal centre and 82% down. That
  remains the default. It is a preview convention, not a value read out of the firmware.

### What you can edit

On the Clock Faces tab, **Hand alignment** sets:

* Centre X/Y — where the preview pins the hands. Leave this at 120, 120 to match a
  centre-pivoted hand on the device.
* Pivot X/Y — the bitmap pixel that sits on that centre, per hand. The detail view and
  the hand editor draw a cross on it. Draw the pin of a custom hand on the default
  pixel (centre, 82% down) when you want the device to agree with the preview.

The numbers are saved in the `.n6theme` project. They are not written into SilverImagesDB
or the IPSW. Changing them does not move the hands in the OS. If a stock face's preview
does not match a photo of the device, nudge the pivot until the preview matches; that
only calibrates the studio. The running clock still composites the bitmaps itself.

Hour and minute hands are shown at 10:09 (the shorter of the first two bitmaps is the
hour hand). Any further hand bitmaps are drawn pointing up, so a second hand's pivot
can be checked. Digit glyphs are not drawn on top: their positions are not known.

When a background, overlay, or hand bitmap is edited, the 79×79 Settings thumbnail is
regenerated with this same placement. That thumbnail is a bitmap the picker shows. The
running clock does not read it to decide where a hand turns.

## Digit, date, and other static glyphs — position is not editable

The same search found no coordinate table for digit, date, "Music", or battery art.
Those bitmaps live in SilverImagesDB (the Clock Faces list calls them **Glyph**). Where
the OS paints them is in the encrypted image, not next to the bitmap.

You can replace a glyph's picture. The new picture is scaled into the original width and
height, which is the safe edit: the slot, the id, and the OS position stay as they are.
The preview does not invent a position for the glyph, and Hand alignment does not move it.
The 79×79 thumbnail is not rebuilt for a glyph-only edit, because the thumbnail does not
composite those glyphs (the OS draws them on the live clock).

The word "Music" and the battery readout are UI strings in `SilverDB.en_GB.LE.bin`
(`Music`, `%d per cent battery power`), not a coordinate table. This app does not edit
those strings, and editing them would not move the label. Any other status art in
SilverImagesDB can be replaced as a bitmap under Advanced; its position is not stored
beside the image.
