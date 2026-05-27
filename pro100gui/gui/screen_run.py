"""Run screen: live job status tree + scrolling log + cancel button."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

_PHASE_LABELS = {
    "back": "BACK",
    "fwd": "FORWARD",
    "real": "REAL",
    "mm_sweep": "MM-SWEEP",
    "pdf": "PDF",
}


class RunScreen(QWidget):

    cancelRequested = Signal()

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)

        # ----- Header -----
        head = QHBoxLayout()
        self.session_label = QLabel("Session: -")
        head.addWidget(self.session_label)
        head.addStretch()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancelRequested.emit)
        head.addWidget(self.cancel_btn)
        layout.addLayout(head)

        # ----- Splitter: tree / log -----
        split = QSplitter(Qt.Vertical)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Job", "Status", "Duration", "Rows", "Notes"])
        self.tree.setColumnWidth(0, 240)
        self.tree.setColumnWidth(1, 100)
        self.tree.setColumnWidth(2, 80)
        self.tree.setColumnWidth(3, 60)
        split.addWidget(self.tree)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(5000)
        split.addWidget(self.log)
        split.setSizes([300, 200])

        layout.addWidget(split)

        # ----- Footer status -----
        self.summary = QLabel("")
        layout.addWidget(self.summary)

    # ---------- public slots ----------

    def reset(self) -> None:
        self.tree.clear()
        self.log.clear()
        self.summary.setText("")
        self.session_label.setText("Session: -")
        self.cancel_btn.setEnabled(False)

    def on_session_started(self, session_id: str, n_phases: int) -> None:
        self.session_label.setText(f"Session: {session_id} ({n_phases} phases)")
        self.cancel_btn.setEnabled(True)
        self.summary.setText("Running...")

    def on_phase_started(self, job_key: str, tf: str, phase: str) -> None:
        item = self._find_or_make(job_key, tf, phase)
        item.setText(1, "RUNNING")
        item.setForeground(1, QColor("#1e88e5"))
        self.tree.scrollToItem(item)
        self._append_log(f"-> {job_key} [{phase.upper()}] started")

    def on_phase_progress(self, job_key: str, message: str) -> None:
        self._append_log(f"   {job_key}: {message}")

    def on_phase_finished(
        self, job_key: str, ok: bool, duration_s: float,
        output_path, rows, reason,
    ) -> None:
        item = self._find_or_make(job_key)
        if ok:
            item.setText(1, "DONE")
            item.setForeground(1, QColor("#2e7d32"))
        else:
            item.setText(1, "FAILED")
            item.setForeground(1, QColor("#c62828"))
        item.setText(2, f"{duration_s:.1f}s")
        if rows is not None:
            item.setText(3, str(rows))
        if reason:
            item.setText(4, reason)
        status_word = "OK" if ok else "FAIL"
        self._append_log(
            f"<- {job_key} {status_word} {duration_s:.1f}s"
            + (f" rows={rows}" if rows is not None else "")
            + (f"  {reason}" if reason and not ok else "")
        )

    def on_log_line(self, job_key: str, line: str) -> None:
        self._append_log(f"   {job_key}: {line}")

    def on_session_finished(self, session_id: str, ok: bool, summary: str) -> None:
        word = "completed" if ok else "ended with errors"
        self.summary.setText(f"Session {session_id} {word}. {summary}")
        self.cancel_btn.setEnabled(False)

    def on_crashed(self, msg: str) -> None:
        self.summary.setText(f"CRASH: {msg}")
        self.cancel_btn.setEnabled(False)

    # ---------- internal ----------

    def _find_or_make(
        self, job_key: str, tf: str = "", phase: str = "",
    ) -> QTreeWidgetItem:
        for i in range(self.tree.topLevelItemCount()):
            it = self.tree.topLevelItem(i)
            if it.text(0) == job_key:
                return it
        label = job_key
        if tf and phase:
            label = f"{tf}.{_PHASE_LABELS.get(phase, phase)}"
        elif phase:
            label = _PHASE_LABELS.get(phase, phase)
        item = QTreeWidgetItem([label, "PENDING", "", "", ""])
        self.tree.addTopLevelItem(item)
        return item

    def _append_log(self, line: str) -> None:
        self.log.appendPlainText(line)
