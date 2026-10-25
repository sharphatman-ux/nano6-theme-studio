# SPDX-License-Identifier: GPL-3.0-only
# Nano 6 Theme Studio - Copyright (C) 2026 sharphatman-ux and contributors. See LICENSE.
"""Command-line entry point: starts the GUI, or runs the self-test with --selftest."""

import sys


def main() -> None:
    from nano6studio.core import session

    # clear scratch folders left by a crashed earlier run
    session.remove_stale()
    if len(sys.argv) > 3 and sys.argv[1] == "--selftest":
        # --selftest <fw.ipsw> <report.txt> [theme.n6theme|-] [shots_dir]
        from pathlib import Path

        from nano6studio.shots import run

        a = sys.argv[2:]
        theme = Path(a[2]) if len(a) > 2 and a[2] != "-" else None
        shots = Path(a[3]) if len(a) > 3 else None
        sys.exit(run(Path(a[0]), Path(a[1]), theme, shots))
    from PySide6.QtWidgets import QApplication

    from nano6studio.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Nano 6 Theme Studio")
    app.setStyle("Fusion")
    app.aboutToQuit.connect(session.cleanup)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
