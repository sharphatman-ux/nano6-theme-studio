# Wallpapers on iPod nano 6G 1.2 (36B10147)

Bug (2026-10-24): sharphatman-ux edited "row 1, col 3" in the Wallpapers tab and chose row 1, col 3 in
Settings > General > Wallpaper; the iPod kept the stock image.

Cause: the tab listed all 32 240x240 images 0x30C-0x343 in ID order, but Settings shows only
24 wallpapers, in the order of their 79x79 thumbnails (0x322-0x330 textured, then the plain/photo
pairs 0x331/0x332 ... 0x342/0x343). The tab's row 1 col 3 was 0x30E (blossoms = Settings #2);
Settings row 1 col 3 is thumbnail 0x324 = 0x30F (denim), which was never edited. The old
look-based thumbnail matching also paired only 8 of 22 textured images, some wrongly.

Mapping (catalog.SETTINGS_WALLPAPERS): found with a multi-scale crop search of each thumbnail
against every 240x240 image (thumbnails are zoomed crops) plus a visual check; plain-colour
thumbnails are exact downscales. Near-twins (two equally good matches) are all written:
0x322 -> 0x30D + 0x30C, 0x329 -> 0x315 + 0x314 + 0x316, 0x333 -> 0x334 + 0x335.
Not offered by Settings (Advanced only): 0x30B, 0x317, 0x318, 0x31B, 0x31E, 0x344 and the other
non-clock 240x240 screens.

Device status: home icons and clock faces verified on device on 2026-10-24; wallpapers (Settings-order mapping) verified on device on 2026-10-24
the next device test with this mapping.
