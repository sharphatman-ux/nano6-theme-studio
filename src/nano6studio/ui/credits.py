# SPDX-License-Identifier: GPL-3.0-only
# Nano 6 Theme Studio - Copyright (C) 2026 sharphatman-ux and contributors. See LICENSE.
"""About / Credits — community iPod tools only; libraries via separate licenses dialog."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

CREDITS_HTML = """
<h2>Nano 6 Theme Studio</h2>
<p>Theme editor for the iPod nano 6th generation.
Apple firmware is <b>not</b> bundled — you supply your own IPSW.
This app does <b>not</b> flash your device.</p>

<h3>Built on</h3>
<ul>
<li><b>ipod_theme</b> by nfzerox, with TGRgitx, CUB3D and unknown321 (GPL-3.0).
  The themed-IPSW export is a Python port of its nano 6G repack.
  <a href="https://github.com/nfzerox/ipod_theme">github.com/nfzerox/ipod_theme</a></li>
<li><b>ipod_sun</b> by CUB3D (GPL-3.0), the base of ipod_theme.
  <a href="https://github.com/CUB3D/ipod_sun">github.com/CUB3D/ipod_sun</a></li>
<li><b>ipodhax</b> by 760ceb3b9c0ba4872cadf3ce35a7a494 (MIT): SilverImagesDB, MSE and IMG1 formats;
  the image encoder matches it bit for bit.
  <a href="https://github.com/760ceb3b9c0ba4872cadf3ce35a7a494/ipodhax">github.com/…/ipodhax</a></li>
<li><b>silverutil</b> by Spotlight (MIT): SilverImagesDB research.
  <a href="https://github.com/spotlightishere/silverutil">github.com/spotlightishere/silverutil</a></li>
</ul>

<h3>Research and community</h3>
<ul>
<li><b>ipod_theme_testing_changes</b> (formerly ipod_theme_max_features) by TGRgitx (GPL-3.0)
  <a href="https://github.com/TGRgitx/ipod_theme_testing_changes">github.com/TGRgitx/ipod_theme_testing_changes</a></li>
<li><b>wInd3x</b> by Serge 'q3k' Bazanski / freemyipod (GPL-2.0-or-later)
  <a href="https://github.com/freemyipod/wInd3x">github.com/freemyipod/wInd3x</a></li>
<li><b>S5Late</b> by m-gsch (GPL-2.0)
  <a href="https://github.com/m-gsch/S5Late">github.com/m-gsch/S5Late</a></li>
<li><b>S5Late-8723</b> by NyanSatan
  <a href="https://github.com/NyanSatan/S5Late-8723">github.com/NyanSatan/S5Late-8723</a></li>
<li><b>freemyipod</b> community <a href="https://freemyipod.org/">freemyipod.org</a></li>
<li><b>Asset Replacer</b> by Zeehondie
  <a href="https://assetreplacer.zeehondie.net/">assetreplacer.zeehondie.net</a></li>
<li><b>NanoVault</b> by g0lder <a href="https://github.com/g0lder/NanoVault">github.com/g0lder/NanoVault</a></li>
</ul>
<p>Nano 6 Theme Studio is licensed under the <b>GNU GPL v3</b> because it ports GPL-3.0 code.
Source: the nano6-theme-studio source zip / GitHub repository.</p>
<p style="color:#888">Apple, iPod, iPod nano and iTunes are trademarks of Apple Inc. All other trademarks belong to
their respective owners. This project is independent and not affiliated with or endorsed by Apple
or any other trademark owner. The sample themes are original art with no logos.</p>
"""

OSS_HTML = """
<h2>Open-source licenses</h2>
<p>This app is built with third-party libraries. Their licenses require attribution;
they are listed here rather than on the community Credits screen.</p>
<ul>
<li><b>Python</b> (PSF License) <a href="https://docs.python.org/3/license.html">docs.python.org</a></li>
<li><b>PySide6 / Qt 6</b> (LGPL-3.0) <a href="https://doc.qt.io/qtforpython/licenses.html">doc.qt.io</a></li>
<li><b>Pillow</b> (MIT-CMU) <a href="https://python-pillow.org/">python-pillow.org</a></li>
<li><b>PyInstaller</b> bootloader (GPL-2.0+ with exception)
  <a href="https://pyinstaller.org/en/stable/license.html">pyinstaller.org</a></li>
<li><b>UPX</b> (GPL-2.0+ with exception) <a href="https://upx.github.io/">upx.github.io</a></li>
</ul>
<p>Full text notes also ship in <code>THIRD_PARTY_LICENSES.md</code> and <code>third_party/</code>.</p>
"""


class CreditsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About / Credits")
        self.resize(640, 520)
        lay = QVBoxLayout(self)
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        self.browser.setHtml(CREDITS_HTML)
        lay.addWidget(self.browser)
        row = QHBoxLayout()
        oss = QPushButton("Open-source licenses…")
        oss.clicked.connect(self._oss)
        row.addWidget(oss)
        row.addStretch(1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        row.addWidget(buttons)
        lay.addLayout(row)

    def _oss(self) -> None:
        d = QDialog(self)
        d.setWindowTitle("Open-source licenses")
        d.resize(560, 420)
        v = QVBoxLayout(d)
        b = QTextBrowser()
        b.setOpenExternalLinks(True)
        b.setHtml(OSS_HTML)
        v.addWidget(b)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        bb.accepted.connect(d.accept)
        v.addWidget(bb)
        d.exec()
