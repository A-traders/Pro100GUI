"""Tests for SettingsScreen: form population + Save -> JSON + signal."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pro100gui.app.settings_store import AppSettings
from pro100gui.gui import screen_settings as ss_mod
from pro100gui.gui.screen_settings import SettingsScreen


@pytest.fixture
def settings(tmp_path):
    return AppSettings(
        mt5_install_dir=str(tmp_path / "mt5"),
        project_dir=str(tmp_path / "proj"),
        ea_path=str(tmp_path / "ea.ex5"),
        telegram_post_url="https://t.me/xauruspro/16",
        results_dir=str(tmp_path / "results"),
        last_session_path="",
    )


@pytest.fixture
def screen(qtbot, settings):
    s = SettingsScreen(settings)
    qtbot.addWidget(s)
    return s


def test_fields_populate_from_settings(screen, settings):
    assert screen.mt5_install.text() == settings.mt5_install_dir
    assert screen.project_dir.text() == settings.project_dir
    assert screen.ea_path.text() == settings.ea_path
    assert screen.telegram_url.text() == settings.telegram_post_url
    assert screen.results_dir.text() == settings.results_dir


def test_save_writes_json_and_emits(qtbot, monkeypatch, tmp_path, screen, settings):
    settings_path = tmp_path / "settings.json"

    def fake_save(s, path=None):
        settings_path.write_text(
            json.dumps({
                "mt5_install_dir": s.mt5_install_dir,
                "project_dir": s.project_dir,
                "ea_path": s.ea_path,
                "telegram_post_url": s.telegram_post_url,
                "results_dir": s.results_dir,
                "last_session_path": s.last_session_path,
            }),
            encoding="utf-8",
        )
        return settings_path

    monkeypatch.setattr(ss_mod, "save_settings", fake_save)

    screen.symbol_changed = False
    new_ea = str(tmp_path / "new_ea.ex5")
    screen.ea_path.setText(new_ea)

    with qtbot.waitSignal(screen.settingsChanged, timeout=1000) as blocker:
        screen.save_btn.click()

    emitted: AppSettings = blocker.args[0]
    assert emitted.ea_path == new_ea
    assert settings_path.is_file()
    raw = json.loads(settings_path.read_text(encoding="utf-8"))
    assert raw["ea_path"] == new_ea


def test_verify_needs_ea_path(screen):
    screen.ea_path.setText("")
    screen._on_verify()
    assert "Сначала укажите" in screen.verify_result.text()
