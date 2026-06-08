"""Tests for the FirstRunWizard + needs_first_run decision."""

from __future__ import annotations

from pathlib import Path

import pytest

from pro100gui.app.settings_store import AppSettings
from pro100gui.gui.first_run_wizard import FirstRunWizard, needs_first_run


def _make_install(tmp_path: Path) -> Path:
    install = tmp_path / "mt5"
    install.mkdir()
    (install / "terminal64.exe").write_bytes(b"")
    return install


def _make_ea(tmp_path: Path, name: str = "XaurusPro100MK2_tst_009.ex5") -> Path:
    ea = tmp_path / name
    ea.write_bytes(b"fake")
    return ea


def test_needs_first_run_empty():
    s = AppSettings(mt5_install_dir="", ea_path="")
    assert needs_first_run(s) is True


def test_needs_first_run_partial_mt5_missing(tmp_path):
    ea = _make_ea(tmp_path)
    s = AppSettings(mt5_install_dir="", ea_path=str(ea))
    assert needs_first_run(s) is True


def test_needs_first_run_partial_ea_missing(tmp_path):
    install = _make_install(tmp_path)
    s = AppSettings(mt5_install_dir=str(install), ea_path="")
    assert needs_first_run(s) is True


def test_needs_first_run_invalid_paths(tmp_path):
    # MT5 dir without terminal64.exe -> invalid
    bad = tmp_path / "fakemt5"
    bad.mkdir()
    ea = _make_ea(tmp_path)
    s = AppSettings(mt5_install_dir=str(bad), ea_path=str(ea))
    assert needs_first_run(s) is True


def test_needs_first_run_false_when_both_valid(tmp_path):
    install = _make_install(tmp_path)
    ea = _make_ea(tmp_path)
    s = AppSettings(mt5_install_dir=str(install), ea_path=str(ea))
    assert needs_first_run(s) is False


def test_wizard_accept_with_valid_paths(qtbot, tmp_path):
    install = _make_install(tmp_path)
    ea = _make_ea(tmp_path)
    s = AppSettings(mt5_install_dir="", ea_path="")
    dlg = FirstRunWizard(s)
    qtbot.addWidget(dlg)
    dlg.mt5_dir.setText(str(install))
    dlg.ea_path.setText(str(ea))
    dlg._on_accept()
    assert dlg.result() == FirstRunWizard.Accepted
    collected = dlg.collected()
    assert collected.mt5_install_dir == str(install)
    assert collected.ea_path == str(ea)


def test_wizard_rejects_empty_mt5(qtbot):
    s = AppSettings()
    dlg = FirstRunWizard(s)
    qtbot.addWidget(dlg)
    dlg.mt5_dir.setText("")
    dlg._on_accept()
    assert dlg.result() != FirstRunWizard.Accepted
    assert "MetaTrader" in dlg.error_label.text()


def test_wizard_rejects_mt5_without_terminal_exe(qtbot, tmp_path):
    bad = tmp_path / "fakemt5"
    bad.mkdir()
    ea = _make_ea(tmp_path)
    s = AppSettings()
    dlg = FirstRunWizard(s)
    qtbot.addWidget(dlg)
    dlg.mt5_dir.setText(str(bad))
    dlg.ea_path.setText(str(ea))
    dlg._on_accept()
    assert dlg.result() != FirstRunWizard.Accepted
    assert "terminal64.exe" in dlg.error_label.text()


def test_wizard_rejects_missing_ea_file(qtbot, tmp_path):
    install = _make_install(tmp_path)
    s = AppSettings()
    dlg = FirstRunWizard(s)
    qtbot.addWidget(dlg)
    dlg.mt5_dir.setText(str(install))
    dlg.ea_path.setText(str(tmp_path / "ghost.ex5"))
    dlg._on_accept()
    assert dlg.result() != FirstRunWizard.Accepted
    assert "не найден" in dlg.error_label.text().lower() or "ne nayden" in ""


def test_wizard_rejects_non_ex5_extension(qtbot, tmp_path):
    install = _make_install(tmp_path)
    not_ea = tmp_path / "wrong.txt"
    not_ea.write_bytes(b"x")
    s = AppSettings()
    dlg = FirstRunWizard(s)
    qtbot.addWidget(dlg)
    dlg.mt5_dir.setText(str(install))
    dlg.ea_path.setText(str(not_ea))
    dlg._on_accept()
    assert dlg.result() != FirstRunWizard.Accepted
    assert ".ex5" in dlg.error_label.text()


def test_wizard_preserves_other_settings(qtbot, tmp_path):
    install = _make_install(tmp_path)
    ea = _make_ea(tmp_path)
    s = AppSettings(
        mt5_install_dir="",
        ea_path="",
        telegram_post_url="https://custom/url",
        results_dir=str(tmp_path / "myresults"),
        last_session_path=str(tmp_path / "session.json"),
    )
    dlg = FirstRunWizard(s)
    qtbot.addWidget(dlg)
    dlg.mt5_dir.setText(str(install))
    dlg.ea_path.setText(str(ea))
    dlg._on_accept()
    collected = dlg.collected()
    # Two new fields filled, the rest preserved.
    assert collected.telegram_post_url == "https://custom/url"
    assert collected.results_dir == str(tmp_path / "myresults")
    assert collected.last_session_path == str(tmp_path / "session.json")
