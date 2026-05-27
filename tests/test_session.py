"""Tests for SessionState data model + JSON persistence."""

from datetime import date
from pathlib import Path

import pytest

from pro100gui.core.models import AddFrMode, RunConfig, TF, TFPlan
from pro100gui.orchestrator.session import (
    JobStatus,
    Phase,
    SessionState,
    load_session,
    save_session,
)


def _rc(
    real: bool = False,
    plans=(TFPlan(tf=TF.M5, back_months=4, forward_months=8),),
) -> RunConfig:
    return RunConfig(
        end_date=date(2026, 5, 24),
        symbol="XAUUSD",
        min_depo=10000,
        do_real_phase=real,
        tf_plans=plans,
    )


def test_new_session_has_jobs_per_tf_plus_pdf():
    state = SessionState.new(_rc(plans=(
        TFPlan(tf=TF.M1, back_months=3, forward_months=6),
        TFPlan(tf=TF.M5, back_months=4, forward_months=8),
    )))
    # 2 phases per TF (back, fwd) * 2 TF + 1 PDF = 5
    assert len(state.jobs) == 5
    phases = [(j.tf, j.phase) for j in state.jobs]
    assert ("M1", Phase.BACK) in phases
    assert ("M1", Phase.FWD) in phases
    assert ("M5", Phase.BACK) in phases
    assert ("M5", Phase.FWD) in phases
    assert (None, Phase.PDF) in phases


def test_new_session_adds_real_when_enabled():
    state = SessionState.new(_rc(real=True))
    # 1 TF * 3 phases (back, fwd, real) + 1 PDF = 4
    assert len(state.jobs) == 4
    assert any(j.phase == Phase.REAL for j in state.jobs)


def test_jobs_start_pending():
    state = SessionState.new(_rc())
    assert all(j.status == JobStatus.PENDING for j in state.jobs)


def test_session_id_is_unique():
    a = SessionState.new(_rc())
    b = SessionState.new(_rc())
    assert a.session_id != b.session_id


def test_by_key_returns_job():
    state = SessionState.new(_rc())
    j = state.by_key("M5.back")
    assert j.phase == Phase.BACK
    assert j.tf == "M5"


def test_by_key_missing_raises():
    state = SessionState.new(_rc())
    with pytest.raises(KeyError):
        state.by_key("nope")


def test_counters_reflect_status_changes():
    state = SessionState.new(_rc())
    initial_pending = state.n_pending()
    state.jobs[0].status = JobStatus.DONE
    state.jobs[1].status = JobStatus.FAILED
    assert state.n_done() == 1
    assert state.n_failed() == 1
    assert state.n_pending() == initial_pending - 2


def test_save_and_load_roundtrip(tmp_path: Path):
    rc = _rc(plans=(
        TFPlan(tf=TF.M1, back_months=3, forward_months=6),
        TFPlan(tf=TF.H1, back_months=8, forward_months=16),
    ))
    state = SessionState.new(rc)
    # Mark some progress
    state.jobs[0].status = JobStatus.DONE
    state.jobs[0].duration_s = 12.5
    state.jobs[0].output_path = "C:/x.csv"
    state.jobs[0].rows = 999
    state.jobs[1].status = JobStatus.FAILED
    state.jobs[1].reason = "intentional"

    p = tmp_path / "session.json"
    save_session(p, state)
    restored = load_session(p)

    assert restored.session_id == state.session_id
    assert restored.run_config.end_date == date(2026, 5, 24)
    assert restored.run_config.symbol == "XAUUSD"
    assert len(restored.run_config.tf_plans) == 2
    assert restored.run_config.tf_plans[0].tf == TF.M1
    assert restored.jobs[0].status == JobStatus.DONE
    assert restored.jobs[0].duration_s == 12.5
    assert restored.jobs[0].output_path == "C:/x.csv"
    assert restored.jobs[0].rows == 999
    assert restored.jobs[1].status == JobStatus.FAILED
    assert restored.jobs[1].reason == "intentional"


def test_save_is_atomic(tmp_path: Path):
    state = SessionState.new(_rc())
    p = tmp_path / "session.json"
    save_session(p, state)
    assert p.is_file()
    # tmp file is cleaned up
    assert not p.with_suffix(p.suffix + ".tmp").exists()


def test_run_config_defaults_round_trip(tmp_path: Path):
    state = SessionState.new(RunConfig(
        end_date=date(2026, 5, 24),
        addfr_mode=AddFrMode.SWEEP,
        tf_plans=(TFPlan(tf=TF.M30, back_months=6, forward_months=12),),
    ))
    p = tmp_path / "s.json"
    save_session(p, state)
    restored = load_session(p)
    assert restored.run_config.addfr_mode == AddFrMode.SWEEP
