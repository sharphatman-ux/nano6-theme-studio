# SPDX-License-Identifier: GPL-3.0-only
# Nano 6 Theme Studio - Copyright (C) 2026 sharphatman-ux and contributors. See LICENSE.
"""Install guide wizard — warnings only; never flashes."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWizard,
    QWizardPage,
)

from nano6studio.core.export import INSTALL_GUIDE
from nano6studio.ui.credits import CreditsDialog


class WarnPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Before you install")
        lay = QVBoxLayout(self)
        lab = QLabel(
            "<b>This app never flashes your iPod.</b> You install the exported .ipsw yourself "
            "with iTunes: click the iPod icon, <b>hold Shift</b> and click <b>Check for Update</b> (not Restore).<br><br>"
            "Flashing a modified IPSW can soft-brick your device. "
            "ipod_sun warns that bad packs <b>can and have</b> permanently bricked units.<br><br>"
            "Keep the stock IPSW and back up your iPod before you install."
        )
        lab.setWordWrap(True)
        lay.addWidget(lab)
        self.ack = QCheckBox(
            "I understand the risk, I backed up my music, and I know the recovery steps."
        )
        lay.addWidget(self.ack)
        self.ack.toggled.connect(lambda _: self.completeChanged.emit())

    def isComplete(self) -> bool:
        return self.ack.isChecked()


class StepsPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Back up, install with iTunes Shift+Update, recover")
        lay = QVBoxLayout(self)
        tb = QTextBrowser()
        tb.setPlainText(INSTALL_GUIDE)
        lay.addWidget(tb)


class CreditsPage(QWizardPage):
    def __init__(self, parent_wizard=None):
        super().__init__()
        self.setTitle("Credits")
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Community tools make this possible. Open the full credits list:"))
        btn = QPushButton("Open About / Credits…")
        btn.clicked.connect(lambda: CreditsDialog(self).exec())
        lay.addWidget(btn)
        lay.addWidget(
            QLabel(
                "Also see CREDITS.md, THIRD_PARTY_LICENSES.md, and third_party/ in the source zip."
            )
        )


class InstallWizard(QWizard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Install guide")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.addPage(WarnPage())
        self.addPage(StepsPage())
        self.addPage(CreditsPage())
        self.resize(700, 500)
