"""Run configuration screen.

User builds a RunConfig by editing form fields and a TFPlan table.
Emits `start_requested(RunConfig)` when the Start button is pressed.
"""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pro100gui.core.models import RunConfig, TF, TFPlan

_DEFAULT_PLANS: tuple[tuple[str, int, int], ...] = (
    ("M1", 3, 6),
    ("M5", 4, 8),
    ("M15", 5, 10),
    ("M30", 6, 12),
    ("H1", 8, 16),
)


class ConfigScreen(QWidget):

    startRequested = Signal(object)  # carries RunConfig

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)

        # ----- Basic params -----
        basic = QGroupBox("Параметры прогона")
        form = QFormLayout()

        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("yyyy.MM.dd")
        today = date.today()
        self.end_date.setDate(QDate(today.year, today.month, today.day))
        form.addRow("End date:", self.end_date)

        self.symbol = QLineEdit("XAUUSD")
        form.addRow("Symbol:", self.symbol)

        self.min_depo = QSpinBox()
        self.min_depo.setRange(100, 10_000_000)
        self.min_depo.setSingleStep(1000)
        self.min_depo.setValue(10000)
        form.addRow("Min depo:", self.min_depo)

        self.snap_to_month = QCheckBox("Snap dates to 1st of month")
        self.snap_to_month.setChecked(True)
        form.addRow(self.snap_to_month)

        self.do_real = QCheckBox("Run REAL phase (top-N real ticks)")
        form.addRow(self.do_real)

        basic.setLayout(form)
        layout.addWidget(basic)

        # ----- TF plans -----
        plans_box = QGroupBox("Timeframe plans")
        plans_v = QVBoxLayout()
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["TF", "Back months", "Forward months"])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.Stretch)
        for tf, b, f in _DEFAULT_PLANS:
            self._append_row(tf, b, f)
        plans_v.addWidget(self.table)

        btns = QHBoxLayout()
        self.add_btn = QPushButton("Add TF")
        self.add_btn.clicked.connect(self._on_add_row)
        self.remove_btn = QPushButton("Remove selected")
        self.remove_btn.clicked.connect(self._on_remove_row)
        btns.addWidget(self.add_btn)
        btns.addWidget(self.remove_btn)
        btns.addStretch()
        plans_v.addLayout(btns)
        plans_box.setLayout(plans_v)
        layout.addWidget(plans_box)

        # ----- Footer -----
        footer = QHBoxLayout()
        self.status = QLabel("")
        footer.addWidget(self.status)
        footer.addStretch()
        self.start_btn = QPushButton("Start")
        self.start_btn.clicked.connect(self._on_start)
        footer.addWidget(self.start_btn)
        layout.addLayout(footer)

    # ---------- helpers ----------

    def _append_row(self, tf: str, back: int, forward: int) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        combo = QComboBox()
        for v in (m.value for m in TF):
            combo.addItem(v)
        idx = combo.findText(tf)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        self.table.setCellWidget(row, 0, combo)
        b_spin = QSpinBox()
        b_spin.setRange(1, 60)
        b_spin.setValue(back)
        self.table.setCellWidget(row, 1, b_spin)
        f_spin = QSpinBox()
        f_spin.setRange(1, 120)
        f_spin.setValue(forward)
        self.table.setCellWidget(row, 2, f_spin)

    def _on_add_row(self) -> None:
        self._append_row("M5", 4, 8)

    def _on_remove_row(self) -> None:
        sel = self.table.selectionModel().selectedRows()
        for idx in sorted((i.row() for i in sel), reverse=True):
            self.table.removeRow(idx)

    def _collect_plans(self) -> list[TFPlan]:
        plans: list[TFPlan] = []
        for row in range(self.table.rowCount()):
            tf_combo: QComboBox = self.table.cellWidget(row, 0)
            b_spin: QSpinBox = self.table.cellWidget(row, 1)
            f_spin: QSpinBox = self.table.cellWidget(row, 2)
            plans.append(TFPlan(
                tf=TF(tf_combo.currentText()),
                back_months=b_spin.value(),
                forward_months=f_spin.value(),
            ))
        return plans

    def _on_start(self) -> None:
        try:
            plans = self._collect_plans()
            if not plans:
                self.status.setText("Add at least one TF plan.")
                return
            qd = self.end_date.date()
            cfg = RunConfig(
                end_date=date(qd.year(), qd.month(), qd.day()),
                symbol=self.symbol.text().strip() or "XAUUSD",
                min_depo=self.min_depo.value(),
                snap_to_month_start=self.snap_to_month.isChecked(),
                do_real_phase=self.do_real.isChecked(),
                tf_plans=tuple(plans),
            )
        except ValueError as e:
            self.status.setText(f"Invalid config: {e}")
            return
        self.status.setText("")
        self.startRequested.emit(cfg)
