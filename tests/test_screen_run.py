"""Tests for RunScreen: tree updates + log + cancel signal."""

from __future__ import annotations

import pytest

from pro100gui.gui.screen_run import RunScreen


@pytest.fixture
def screen(qtbot):
    s = RunScreen()
    qtbot.addWidget(s)
    return s


def test_session_started_enables_cancel(screen):
    assert screen.cancel_btn.isEnabled() is False
    screen.on_session_started("sid-1", 5)
    assert screen.cancel_btn.isEnabled() is True
    assert "sid-1" in screen.session_label.text()
    assert "5 phases" in screen.session_label.text()


def test_phase_started_inserts_running_row(screen):
    screen.on_phase_started("M1.back", "M1", "back")
    assert screen.tree.topLevelItemCount() == 1
    item = screen.tree.topLevelItem(0)
    assert item.text(1) == "RUNNING"
    assert item.text(0) == "M1.BACK"
    assert "M1.back" in screen.log.toPlainText()


def test_phase_finished_marks_done(screen):
    screen.on_phase_started("M1.back", "M1", "back")
    screen.on_phase_finished(
        "M1.back", True, 12.5, "/tmp/out.csv", 57, None,
    )
    item = screen.tree.topLevelItem(0)
    assert item.text(1) == "DONE"
    assert item.text(2) == "12.5s"
    assert item.text(3) == "57"


def test_phase_finished_failure_records_reason(screen):
    screen.on_phase_started("M5.fwd", "M5", "fwd")
    screen.on_phase_finished(
        "M5.fwd", False, 4.0, None, None, "terminal exit=1",
    )
    item = screen.tree.topLevelItem(0)
    assert item.text(1) == "FAILED"
    assert "terminal exit=1" in item.text(4)


def test_log_line_appended(screen):
    screen.on_log_line("M1.back", "launching terminal")
    assert "launching terminal" in screen.log.toPlainText()


def test_session_finished_disables_cancel_and_summary(screen):
    screen.on_session_started("sid-2", 3)
    screen.on_session_finished("sid-2", True, "done=3 failed=0 skipped=0")
    assert screen.cancel_btn.isEnabled() is False
    assert "completed" in screen.summary.text()
    assert "done=3" in screen.summary.text()


def test_crashed_shows_error(screen):
    screen.on_crashed("RuntimeError: oops")
    assert "CRASH" in screen.summary.text()
    assert "oops" in screen.summary.text()


def test_reset_clears_state(screen):
    screen.on_session_started("sid-3", 2)
    screen.on_phase_started("M1.back", "M1", "back")
    screen.on_log_line("M1.back", "hello")
    screen.reset()
    assert screen.tree.topLevelItemCount() == 0
    assert screen.log.toPlainText() == ""
    assert screen.cancel_btn.isEnabled() is False
    assert screen.session_label.text() == "Session: -"


def test_cancel_button_emits_signal(qtbot, screen):
    screen.on_session_started("sid-4", 1)  # enables the button
    with qtbot.waitSignal(screen.cancelRequested, timeout=1000):
        screen.cancel_btn.click()
