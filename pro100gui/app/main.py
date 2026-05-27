"""Pro100GUI app entry point: builds the QApplication and main window."""

from __future__ import annotations

import sys


def run() -> int:
    from PySide6.QtWidgets import QApplication

    from pro100gui.gui.main_window import MainWindow

    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
