# SPDX-License-Identifier: GPL-3.0-only
# Nano 6 Theme Studio - Copyright (C) 2026 sharphatman-ux and contributors. See LICENSE.
"""Dark Qt style sheet used by the main window and dialogs."""

DARK_QSS = """
QWidget { background-color: #1a1b1e; color: #e8e8ed; font-size: 13px; }
QMainWindow, QDialog { background-color: #1a1b1e; }
QMenuBar { background: #121316; }
QMenuBar::item:selected { background: #2a2d34; }
QMenu { background: #1e2026; border: 1px solid #333; }
QMenu::item:selected { background: #3a7afe; }
QToolBar { background: #121316; border: none; spacing: 6px; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit {
  background: #121316; border: 1px solid #3a3d45; border-radius: 6px; padding: 6px;
}
QPushButton {
  background: #2a2d34; border: 1px solid #3a3d45; border-radius: 8px; padding: 8px 14px;
}
QPushButton:hover { background: #343842; }
QPushButton#primary { background: #3a7afe; border: none; font-weight: 600; }
QPushButton#primary:hover { background: #5a90ff; }
QPushButton#danger { background: #5a2430; }
QListWidget, QTreeWidget {
  background: #121316; border: 1px solid #2a2d34; border-radius: 8px;
}
QListWidget::item:selected { background: #3a7afe; }
QSlider::groove:horizontal { height: 6px; background: #2a2d34; border-radius: 3px; }
QSlider::handle:horizontal { width: 14px; margin: -5px 0; background: #3a7afe; border-radius: 7px; }
QProgressBar { border: 1px solid #2a2d34; border-radius: 6px; text-align: center; background: #121316; }
QProgressBar::chunk { background: #3a7afe; border-radius: 5px; }
QGroupBox { border: 1px solid #2a2d34; border-radius: 8px; margin-top: 10px; padding-top: 12px; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color: #9aa0a6; }
QLabel#hint { color: #9aa0a6; }
QStatusBar { background: #121316; }
"""
