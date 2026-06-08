"""Tests for MainWindow._load_resume_candidate (pure logic)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from pro100gui.app.settings_store import AppSettings
from pro100gui.core.models import RunConfig, TF, TFPlan
from pro100gui.gui import main_window as mw_mod
from pro100gui.gui.main_window import MainWindow
from pro100gui.orchestrator.session import (
    JobStatus,
    SessionState,
    save_session,
)


def _make_settings(tmp_path: Path, session_path: str = "") -> AppSettings:
    return AppSettings(
        mt5_install_dir=str(tmp_path / "mt5"),
        project_dir=str(tmp_path / "proj"),
        ea_path="",
        telegram_post_url="https://t.me/xauruspro/16",
        results_dir=str(tmp_path / "results"),
        last_session_path=session_path,
    )


def _make_session(tmp_path: Path, finalize: bool = False) -> Path:
    cfg = RunConfig(
        end_date=date(2026, 5, 1),
        symbol="XAUUSD",
        min_depo=10000,
        tf_plans=(TFPlan(tf=TF.M1, back_months=3, forward_months=6),),
    )
    state = SessionState.new(cfg)
    if finalize:
        for j in state.jobs:
            j.status = JobStatus.DONE
    path = tmp_path / "session.json"
    save_session(path, state)
    return path


@pytest.fixture
def patch_settings(monkeypatch):
    """Install a fake AppSettings AND silence the resume dialog.

    `_offer_resume_if_any` is QTimer.singleShot-scheduled in __init__;
    if it ran in a test it would pop a modal QMessageBox and block
    indefinitely (no human to click). We're testing the pure-logic
    `_load_resume_candidate` anyway.
    """

    def install(settings: AppSettings) -> None:
        monkeypatch.setattr(mw_mod, "load_settings", lambda: settings)
        # Silence the QTimer-scheduled startup chain so MainWindow
        # construction does not show modal dialogs that would hang
        # the test. We exercise _load_resume_candidate directly.
        monkeypatch.setattr(
            mw_mod.MainWindow, "_first_run_check_then_resume",
            lambda self: None,
        )
        monkeypatch.setattr(
            mw_mod.MainWindow, "_offer_resume_if_any", lambda self: None,
        )

    return install


def test_no_path_returns_none(qtbot, tmp_path, patch_settings):
    patch_settings(_make_settings(tmp_path, session_path=""))
    w = MainWindow()
    qtbot.addWidget(w)
    assert w._load_resume_candidate() is None


def test_missing_file_returns_none(qtbot, tmp_path, patch_settings):
    patch_settings(_make_settings(tmp_path, session_path=str(tmp_path / "ghost.json")))
    w = MainWindow()
    qtbot.addWidget(w)
    assert w._load_resume_candidate() is None


def test_corrupted_file_returns_none(qtbot, tmp_path, patch_settings):
    bad = tmp_path / "broken.json"
    bad.write_text("{ this is not json", encoding="utf-8")
    patch_settings(_make_settings(tmp_path, session_path=str(bad)))
    w = MainWindow()
    qtbot.addWidget(w)
    assert w._load_resume_candidate() is None


def test_completed_session_returns_none(qtbot, tmp_path, patch_settings):
    path = _make_session(tmp_path, finalize=True)
    patch_settings(_make_settings(tmp_path, session_path=str(path)))
    w = MainWindow()
    qtbot.addWidget(w)
    assert w._load_resume_candidate() is None


def test_unfinished_session_returns_state(qtbot, tmp_path, patch_settings):
    path = _make_session(tmp_path, finalize=False)
    patch_settings(_make_settings(tmp_path, session_path=str(path)))
    w = MainWindow()
    qtbot.addWidget(w)
    state = w._load_resume_candidate()
    assert state is not None
    assert state.run_config.symbol == "XAUUSD"
    assert any(j.status == JobStatus.PENDING for j in state.jobs)


def test_running_jobs_counted_as_unfinished(qtbot, tmp_path, patch_settings):
    cfg = RunConfig(
        end_date=date(2026, 5, 1),
        tf_plans=(TFPlan(tf=TF.M1, back_months=3, forward_months=6),),
    )
    state = SessionState.new(cfg)
    state.jobs[0].status = JobStatus.RUNNING  # crashed mid-phase
    for j in state.jobs[1:]:
        j.status = JobStatus.DONE
    path = tmp_path / "session.json"
    save_session(path, state)

    patch_settings(_make_settings(tmp_path, session_path=str(path)))
    w = MainWindow()
    qtbot.addWidget(w)
    assert w._load_resume_candidate() is not None
