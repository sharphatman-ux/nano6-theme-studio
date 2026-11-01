# Music and clock label color

Checked against a local copy of stock `iPod_1.2_36B10147.ipsw` (SHA-256
`84b27d59f376eaf51270f2ee7ee67016e67fc992882d518f9b294ee21122297d`). That file is not
in this repository. There is no editable asset for the draw color of UI strings such as
"Music". This app does not add a label-color control: a picker that only recolored the
studio preview would not match the device.

## Strings, not tinted bitmaps

"Music", "Clock", and the battery line are null-terminated strings in the `Str ` section
of `Resources/UI/SilverDB.*.LE.bin` (for example `Music` and `%d per cent battery power`
in `en_GB`). Editing a string would change the words. It would not change the paint color.

The home-screen preview draws those names with `Resources/Fonts/HelveticaBold.ttf` from
the firmware you opened, in white with a dark shadow (`home_render._label`). That white
is the studio's mock. It is not read from a color field.

## Fonts have no color channel

Every file under `Resources/Fonts/` is an outline font (`glyf` or `CFF `). None of them
has a `COLR`, `CPAL`, `SVG `, `CBDT`, `CBLC`, `sbix`, `EBDT`, or `EBLC` table:

| File | Kind |
| --- | --- |
| Helvetica.ttf, HelveticaBold.ttf | TrueType outlines |
| AppleGothicRegular, ArialHB, GeezaPro, HKGPW3UI, Thonburi | TrueType outlines |
| CinecavXMono.otf, HiraKakuProN-W3/W6.otf | CFF outlines |
| STHeiti-Medium.ttc | TrueType collection, outlines |
| ipod_glyphs.ttf | TrueType outlines, 19 non-empty glyphs, name "ipod glyphs" |

`ipod_glyphs.ttf` is a small symbol font, not a bitmap strike and not a color font.
Outline contours do not store a fill color. The 2011 OS has nothing in these files to
recolor, and it does not advertise a color-font table that a newer COLR font could hook.

## No color section in the plaintext databases

Each of the 29 `SilverDB.*.LE.bin` files has the same three section types: `LDTm`,
`Str `, and `VLyt`. There is no `COLR` section (silverutil's name for UI colors) and no
`FONT` section. `COLR`, `CPAL`, and `sbix` do not occur in the `rsrc` FAT at all.
The two `FONT` byte hits in `Firmware.MSE` are the FAT directory name `FONTS` and the
place name "Milfontes" inside other data, not a font-color table.

`VLyt` (60 records in `en_GB`, 3,987 little-endian words, 246 distinct values) is small
integers: counts, flags, and signed offsets such as -2…-10. None of those words is a
saturated RGB value (`0x00FFFFFF`, `0xFF000000`, and the other on/off channel
combinations are absent). It does not carry a label color next to a layout.

SilverImagesDB is image pixels only. Its 58 grey (`0x0004` / `0x0008`) images are large
masks (120×120, 120×240) and a handful of tiny marks, not a label alphabet. Clock digit
glyphs are ordinary bitmaps (often one flat color, white or otherwise). Replacing or
recoloring **that bitmap** changes the pixels the OS already blits, which the image
editor can do today. That is not the color of the string "Music".

## Where the color lives

`osos` and the other non-`rsrc` MSE sections are ciphertext (see
[CLOCK_FACES.md](CLOCK_FACES.md)). The code that picks white, black, or a theme tint
when it rasterizes a string is in that image. It is not in a plist: `rsrc` has no plist
files, and the XML/text there does not name a label color.

So label color cannot be themed from the files this app packs. Digit and icon pixels
still can, because they are images.
