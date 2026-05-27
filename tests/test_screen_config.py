"""Tests for ConfigScreen: form -> RunConfig + startRequested signal."""

from __future__ import annotations

from datetime import date

import pytest

from pro100gui.core.models import RunConfig, TF
from pro100gui.gui.screen_config import ConfigScreen


@pytest.fixture
def screen(qtbot):
    s = ConfigScreen()
    qtbot.addWidget(s)
    return s


def test_defaults_populate_five_tf_rows(screen):
    assert screen.table.rowCount() == 5
    tfs = [
        screen.table.cellWidget(r, 0).currentText()
        for r in range(screen.table.rowCount())
    ]
    assert tfs == ["M1", "M5", "M15", "M30", "H1"]


def test_default_symbol_and_min_depo(screen):
    assert screen.symbol.text() == "XAUUSD"
    assert screen.min_depo.value() == 10000
    assert screen.snap_to_month.isChecked() is True
    assert screen.do_real.isChecked() is False


def test_start_emits_run_config_with_form_values(qtbot, screen):
    screen.symbol.setText("EURUSD")
    screen.min_depo.setValue(50000)
    screen.do_real.setChecked(True)

    with qtbot.waitSignal(screen.startRequested, timeout=1000) as blocker:
        screen.start_btn.click()

    cfg = blocker.args[0]
    assert isinstance(cfg, RunConfig)
    assert cfg.symbol == "EURUSD"
    assert cfg.min_depo == 50000
    assert cfg.do_real_phase is True
    assert len(cfg.tf_plans) == 5
    assert cfg.tf_plans[0].tf == TF.M1
    assert cfg.tf_plans[0].back_months == 3
    assert cfg.tf_plans[0].forward_months == 6


def test_add_row_appends_default_m5_plan(qtbot, screen):
    before = screen.table.rowCount()
    screen.add_btn.click()
    assert screen.table.rowCount() == before + 1
    last = screen.table.cellWidget(before, 0)
    assert last.currentText() == "M5"


def test_remove_selected_row(qtbot, screen):
    before = screen.table.rowCount()
    screen.table.selectRow(0)
    screen.remove_btn.click()
    assert screen.table.rowCount() == before - 1


def test_empty_plans_blocks_start(qtbot, screen):
    while screen.table.rowCount() > 0:
        screen.table.selectRow(0)
        screen.remove_btn.click()
    # No signal should fire when plans are empty.
    with qtbot.assertNotEmitted(screen.startRequested, wait=100):
        screen.start_btn.click()
    assert "TF plan" in screen.status.text()


def test_end_date_is_recent(screen):
    qd = screen.end_date.date()
    today = date.today()
    assert qd.year() == today.year
    assert qd.month() == today.month
    assert qd.day() == today.day
