"""Tests for Orchestrator end-to-end on a real filesystem with a
mocked terminal launcher. No actual MT5 is invoked."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pytest

from pro100gui.adapters.ea_registry import TESTER_BUILD, EARegistry
from pro100gui.adapters.files_staging import FilesStaging
from pro100gui.adapters.paths import MT5Paths
from pro100gui.adapters.pdf_renderer import PdfRenderer
from pro100gui.adapters.terminal_runner import TerminalRunner
from pro100gui.core.filters import Pro100Row
from pro100gui.core.models import RunConfig, TF, TFPlan
from pro100gui.core.pro100_csv import write_pro100_csv
from pro100gui.core.tf import tf_str
from pro100gui.orchestrator.events import (
    EventBus,
    EventRecorder,
    PhaseFinished,
    PhaseStarted,
    SessionFinished,
    SessionStarted,
)
from pro100gui.orchestrator.orchestrator import Orchestrator
from pro100gui.orchestrator.session import (
    JobStatus,
    Phase,
    SessionState,
    load_session,
)


# ---------- helpers ----------

def _read_utf16(p: Path) -> str:
    raw = p.read_bytes()
    if raw.startswith(b"\xff\xfe"):
        return raw[2:].decode("utf-16-le")
    if raw.startswith(b"\xfe\xff"):
        return raw[2:].decode("utf-16-be")
    return raw.decode("utf-8", errors="replace")


def _dname_from_run_artifacts(paths: MT5Paths, ini_path: Path) -> str:
    ini_text = _read_utf16(ini_path)
    symbol = re.search(r"Symbol=([^\r\n]+)", ini_text).group(1).strip()
    set_rel = re.search(r"ExpertParameters=([^\r\n]+)", ini_text).group(1).strip()
    set_path = paths.mql5_dir / "Profiles" / "Tester" / set_rel
    set_text = _read_utf16(set_path)
    enum_val = int(re.search(r"inp_tf1=(-?\d+)", set_text).group(1))
    return f"{symbol}_S2_M1{tf_str(enum_val)}"


def _make_rows(n: int) -> list[Pro100Row]:
    return [
        Pro100Row(
            rating=100.0 - i,
            annual_gmean_pct=150.0 + i * 5,
            max_rel_dd_pct=30.0 + i * 0.5,
            trades=80 - i,
            setup_no=-(i + 1),
        )
        for i in range(n)
    ]


@dataclass
class Harness:
    tmp_path: Path
    paths: MT5Paths
    bus: EventBus
    recorder: EventRecorder
    orch: Orchestrator
    staging: FilesStaging
    ea_path: Path
    results_dir: Path
    session_path: Path
    launcher_calls: list[tuple]


def _build_harness(
    tmp_path: Path,
    csv_rows: int = 5,
    fail_after: int | None = None,
) -> Harness:
    install = tmp_path / "mt5"
    install.mkdir(parents=True, exist_ok=True)
    (install / "terminal64.exe").write_bytes(b"")
    paths = MT5Paths(install_dir=install, project_dir=tmp_path / "home")

    ea_src = tmp_path / "ea_source"
    ea_src.mkdir(parents=True, exist_ok=True)
    ea_path = ea_src / "XaurusPro100MK2_tst_008.ex5"
    ea_path.write_bytes(b"fake-compiled-bytes")

    registry = EARegistry()
    registry.register(TESTER_BUILD, ea_path)

    staging = FilesStaging(paths)
    bus = EventBus()
    recorder = EventRecorder()
    bus.subscribe(recorder)

    results_dir = tmp_path / "results"
    session_path = tmp_path / "session.json"
    launcher_calls: list[tuple] = []

    def launcher(exe, cwd, ini, timeout_s):
        launcher_calls.append((exe, cwd, ini, timeout_s))
        if fail_after is not None and len(launcher_calls) > fail_after:
            return 3, False
        dname = _dname_from_run_artifacts(paths, ini)
        local_csv = paths.pro100_local(dname)
        write_pro100_csv(local_csv, _make_rows(csv_rows))
        return 0, False

    runner = TerminalRunner(
        paths, watchdog=lambda _: False, launcher=launcher,
        clock=lambda: 100.0,
    )
    orch = Orchestrator(
        paths=paths,
        ea_registry=registry,
        files_staging=staging,
        terminal_runner=runner,
        pdf_renderer=PdfRenderer(),
        bus=bus,
        results_dir=results_dir,
        session_path=session_path,
    )
    return Harness(
        tmp_path=tmp_path, paths=paths, bus=bus, recorder=recorder,
        orch=orch, staging=staging, ea_path=ea_path,
        results_dir=results_dir, session_path=session_path,
        launcher_calls=launcher_calls,
    )


def _basic_config(real: bool = False) -> RunConfig:
    return RunConfig(
        end_date=date(2026, 5, 24),
        symbol="XAUUSD",
        min_depo=10000,
        do_real_phase=real,
        tf_plans=(TFPlan(tf=TF.M5, back_months=4, forward_months=8),),
    )


# ---------- tests ----------


def test_happy_path_single_tf(tmp_path: Path):
    h = _build_harness(tmp_path, csv_rows=10)
    state = h.orch.run(_basic_config())
    assert state.ok is True
    assert state.n_failed() == 0
    # Jobs: M5.back, M5.fwd, pdf -- 3
    assert len(state.jobs) == 3
    assert all(j.status == JobStatus.DONE for j in state.jobs)


def test_back_and_fwd_csvs_written_to_results(tmp_path: Path):
    h = _build_harness(tmp_path, csv_rows=8)
    state = h.orch.run(_basic_config())
    back = state.by_key("M5.back")
    fwd = state.by_key("M5.fwd")
    assert back.output_path is not None
    assert fwd.output_path is not None
    assert Path(back.output_path).is_file()
    assert Path(fwd.output_path).is_file()
    assert back.rows == 8
    assert fwd.rows == 8


def test_pdf_produced(tmp_path: Path):
    h = _build_harness(tmp_path, csv_rows=5)
    state = h.orch.run(_basic_config())
    pdf_job = state.by_key("pdf")
    assert pdf_job.status == JobStatus.DONE
    assert pdf_job.output_path is not None
    assert Path(pdf_job.output_path).is_file()
    assert Path(pdf_job.output_path).suffix == ".pdf"


def test_real_phase_included_when_flag_on(tmp_path: Path):
    h = _build_harness(tmp_path, csv_rows=3)
    state = h.orch.run(_basic_config(real=True))
    # back + fwd + real + pdf = 4
    assert len(state.jobs) == 4
    assert state.by_key("M5.real").status == JobStatus.DONE


def test_terminal_failure_aborts_subsequent_phases(tmp_path: Path):
    # First phase succeeds (BACK), second (FWD) fails, PDF skipped.
    h = _build_harness(tmp_path, csv_rows=5, fail_after=1)
    state = h.orch.run(_basic_config())
    assert state.by_key("M5.back").status == JobStatus.DONE
    assert state.by_key("M5.fwd").status == JobStatus.FAILED
    assert state.by_key("pdf").status == JobStatus.SKIPPED
    assert state.ok is False


def test_events_published_in_order(tmp_path: Path):
    h = _build_harness(tmp_path, csv_rows=3)
    h.orch.run(_basic_config())
    types = [type(e).__name__ for e in h.recorder.events]
    assert types[0] == "SessionStarted"
    assert types[-1] == "SessionFinished"
    # For each phase we expect a Started and a Finished
    starts = h.recorder.of_type(PhaseStarted)
    finishes = h.recorder.of_type(PhaseFinished)
    assert len(starts) == 3  # back, fwd, pdf
    assert len(finishes) == 3
    # job_keys match expected order
    assert [s.job_key for s in starts] == ["M5.back", "M5.fwd", "pdf"]


def test_session_persisted_after_each_phase(tmp_path: Path):
    h = _build_harness(tmp_path, csv_rows=3)
    state = h.orch.run(_basic_config())
    assert h.session_path.is_file()
    restored = load_session(h.session_path)
    assert restored.session_id == state.session_id
    assert restored.n_done() == 3


def test_cancel_between_phases(tmp_path: Path):
    h = _build_harness(tmp_path, csv_rows=3)

    # Stop after BACK by cancelling from a subscriber
    def on_phase_finished(e):
        if isinstance(e, PhaseFinished) and e.job_key == "M5.back":
            h.orch.cancel()

    h.bus.subscribe(on_phase_finished)
    state = h.orch.run(_basic_config())
    assert state.by_key("M5.back").status == JobStatus.DONE
    assert state.by_key("M5.fwd").status == JobStatus.SKIPPED
    assert state.by_key("pdf").status == JobStatus.SKIPPED


def test_resume_runs_only_pending(tmp_path: Path):
    h = _build_harness(tmp_path, csv_rows=3)
    state = h.orch.run(_basic_config())  # full run
    # All done.
    initial_calls = len(h.launcher_calls)
    # Resume -- nothing pending, no new launcher calls.
    h.orch.resume(state)
    assert len(h.launcher_calls) == initial_calls


def test_resume_after_failure_with_fix(tmp_path: Path):
    # First run: FWD fails. Resume after marking failed job back to pending.
    h = _build_harness(tmp_path, csv_rows=3, fail_after=1)
    state = h.orch.run(_basic_config())
    assert state.n_failed() == 1
    # User fixes -- reset failed job to pending; PDF too.
    state.by_key("M5.fwd").status = JobStatus.PENDING
    state.by_key("M5.fwd").reason = None
    state.by_key("pdf").status = JobStatus.PENDING
    state.by_key("pdf").reason = None
    # Rebuild harness without injected failure
    h2 = _build_harness(tmp_path, csv_rows=3, fail_after=None)
    # Re-register EA at the same path (was already registered)
    final = h2.orch.resume(state)
    assert final.by_key("M5.fwd").status == JobStatus.DONE
    assert final.by_key("pdf").status == JobStatus.DONE
    assert final.ok is True


def test_addfr_cfg_present_at_launch_with_standard_profile(tmp_path: Path):
    """Every tester phase must write pro100_addfr.cfg next to pro100.csv
    with the STANDARD profile (extended profile would only be used by
    MM-sweep, not yet generated by SessionState)."""
    install = tmp_path / "mt5"
    install.mkdir(parents=True, exist_ok=True)
    (install / "terminal64.exe").write_bytes(b"")
    paths = MT5Paths(install_dir=install, project_dir=tmp_path / "home")

    ea_src = tmp_path / "ea_source"
    ea_src.mkdir(parents=True, exist_ok=True)
    ea_path = ea_src / "XaurusPro100MK2_tst_009.ex5"
    ea_path.write_bytes(b"fake")

    registry = EARegistry()
    registry.register(TESTER_BUILD, ea_path)
    staging = FilesStaging(paths)
    bus = EventBus()

    cfg_seen: list[bytes] = []

    def launcher(exe, cwd, ini, timeout_s):
        dname = _dname_from_run_artifacts(paths, ini)
        cfg_path = paths.addfr_cfg_local(dname)
        if cfg_path.is_file():
            cfg_seen.append(cfg_path.read_bytes())
        write_pro100_csv(paths.pro100_local(dname), _make_rows(3))
        return 0, False

    runner = TerminalRunner(
        paths, watchdog=lambda _: False, launcher=launcher,
        clock=lambda: 0.0,
    )
    orch = Orchestrator(
        paths=paths, ea_registry=registry, files_staging=staging,
        terminal_runner=runner, pdf_renderer=PdfRenderer(),
        bus=bus, results_dir=tmp_path / "results",
        session_path=tmp_path / "session.json",
    )

    orch.run(_basic_config())

    # 2 tester phases (back + fwd) + 1 PDF phase that doesn't launch terminal
    assert len(cfg_seen) == 2
    for raw in cfg_seen:
        text = raw.decode("ascii")
        assert "profile: standard" in text
        assert "MAX_FR=1000" in text


def test_two_tf_pages_in_pdf(tmp_path: Path):
    h = _build_harness(tmp_path, csv_rows=3)
    rc = RunConfig(
        end_date=date(2026, 5, 24),
        symbol="XAUUSD",
        min_depo=10000,
        tf_plans=(
            TFPlan(tf=TF.M1, back_months=3, forward_months=6),
            TFPlan(tf=TF.H1, back_months=8, forward_months=16),
        ),
    )
    state = h.orch.run(rc)
    assert state.ok is True
    pdf_path = Path(state.by_key("pdf").output_path)
    from pypdf import PdfReader
    reader = PdfReader(str(pdf_path))
    assert len(reader.pages) == 2  # one page per TF
