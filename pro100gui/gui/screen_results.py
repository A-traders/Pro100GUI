"""Results screen: list of PDF artifacts from past sessions.

Lightweight v1 -- just enumerates PDFs in the results dir, allows
opening with the system default app. No embedded preview yet.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ResultsScreen(QWidget):

    def __init__(self) -> None:
        super().__init__()
        self._results_dir: Path | None = None

        layout = QVBoxLayout(self)

        head = QHBoxLayout()
        self.dir_label = QLabel("Results dir: -")
        head.addWidget(self.dir_label)
        head.addStretch()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh)
        head.addWidget(self.refresh_btn)
        layout.addLayout(head)

        self.list = QListWidget()
        layout.addWidget(self.list)

        actions = QHBoxLayout()
        self.open_btn = QPushButton("Open selected")
        self.open_btn.clicked.connect(self._open_selected)
        actions.addWidget(self.open_btn)
        self.open_dir_btn = QPushButton("Open results folder")
        self.open_dir_btn.clicked.connect(self._open_dir)
        actions.addWidget(self.open_dir_btn)
        actions.addStretch()
        layout.addLayout(actions)

    # ---------- public ----------

    def set_results_dir(self, path: Path) -> None:
        self._results_dir = path
        self.dir_label.setText(f"Results dir: {path}")
        self.refresh()

    def refresh(self) -> None:
        self.list.clear()
        if self._results_dir is None or not self._results_dir.is_dir():
            return
        for p in sorted(self._results_dir.glob("*.pdf")):
            item = QListWidgetItem(p.name)
            item.setData(Qt.UserRole, str(p))
            self.list.addItem(item)

    # ---------- internal ----------

    def _open_selected(self) -> None:
        items = self.list.selectedItems()
        if not items:
            return
        self._launch(items[0].data(Qt.UserRole))

    def _open_dir(self) -> None:
        if self._results_dir:
            self._launch(str(self._results_dir))

    def _launch(self, target: str) -> None:
        try:
            if sys.platform.startswith("win"):
                os.startfile(target)
            elif sys.platform == "darwin":
                subprocess.run(["open", target], check=False)
            else:
                subprocess.run(["xdg-open", target], check=False)
        except OSError:
            pass
