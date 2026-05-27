"""Top-level pipeline orchestrator.

Given a RunConfig and the assembled adapter set, runs all phases
serially (one MT5 instance) and writes results to disk. Publishes
events through the EventBus so the GUI / loggers can follow along.
After every phase the session JSON is rewritten so the run can
resume after a crash or forced shutdown.
"""

from __future__ import annotations

import threading
import time
import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

from pro100gui.adapters.ea_registry import TESTER_BUILD, EARegistry
from pro100gui.adapters.files_staging import FilesStaging
from pro100gui.adapters.ini_file import IniConfig, OptimizationMode, TesterModel
from pro100gui.adapters.paths import MT5Paths
from pro100gui.adapters.pdf_renderer import PageSpec, PdfRenderer
from pro100gui.adapters.set_file import back_params, fwd_params, real_params
from pro100gui.adapters.terminal_runner import (
    TerminalAlreadyRunning,
    TerminalRunner,
)
from pro100gui.core.filters import filter_top_n_dd
from pro100gui.core.models import RunConfig, TFPlan
from pro100gui.core.periods import compute_periods
from pro100gui.core.pro100_csv import read_pro100_csv
from pro100gui.core.tf import tf_enum

from .events import (
    EventBus,
    LogLine,
    PhaseFinished,
    PhaseStarted,
    SessionFinished,
    SessionStarted,
)
from .session import JobSpec, JobStatus, Phase, SessionState, save_session

DEFAULT_TIMEOUTS_S: dict[Phase, int] = {
    Phase.BACK: 12 * 3600,
    Phase.FWD: 4 * 3600,
    Phase.REAL: 2 * 3600,
}
"""Per-phase wall-clock timeout caps. Real phase durations are
typically much shorter; these only kick in for runaway tests."""

REAL_N_DEFAULT = 5
"""Number of top survivors to retest with real ticks if REAL is on.
Not yet exposed in RunConfig; can be raised in code per run."""

DNAME_SYS = 2
DNAME_TF0 = "M1"
"""Constants matching the EA's directory layout (see EA_INP_SYS and
EA_INP_TF0_STR in opt_pro100_002.py)."""


# ---------- helpers ----------

def _fmt_date(d: date) -> str:
    return d.strftime("%Y.%m.%d")


def _end_compact(d: date) -> str:
    return d.strftime("%Y%m%d")


def _phase_inp_set(phase: Phase, real_n: int = REAL_N_DEFAULT) -> int:
    if phase == Phase.BACK:
        return -1
    if phase == Phase.FWD:
        return -1000
    if phase == Phase.REAL:
        return -real_n
    raise ValueError(f"unsupported tester phase: {phase}")


def _phase_model(phase: Phase) -> TesterModel:
    if phase == Phase.REAL:
        return TesterModel.REAL_TICKS
    return TesterModel.OPEN_PRICES_ONLY


def _phase_window(plan: TFPlan, phase: Phase, run_config: RunConfig):
    back_w, fwd_w = compute_periods(
        run_config.end_date, plan, snap=run_config.snap_to_month_start,
    )
    if phase == Phase.BACK:
        return back_w
    return fwd_w


def _dname(symbol: str, tf_str: str) -> str:
    return f"{symbol}_S{DNAME_SYS}_{DNAME_TF0}{tf_str}"


def _phase_csv_name(run_config: RunConfig, plan: TFPlan, phase: Phase) -> str:
    return (
        f"pro100_{run_config.symbol}_{_end_compact(run_config.end_date)}_"
        f"{plan.back_months}_{plan.forward_months}_{plan.tf.value}_"
        f"{int(run_config.min_depo)}_{phase.value}.csv"
    )


# ---------- orchestrator ----------

class Orchestrator:
    """Coordinator that runs one Pro100GUI session end-to-end.

    Construct with already-wired adapters and call `run(config)` or
    `resume(state)`. Events flow through the injected bus.
    """

    def __init__(
        self,
        paths: MT5Paths,
        ea_registry: EARegistry,
        files_staging: FilesStaging,
        terminal_runner: TerminalRunner,
        pdf_renderer: PdfRenderer,
        bus: EventBus,
        *,
        results_dir: Path,
        session_path: Path | None = None,
        clock=time.time,
    ) -> None:
        self.paths = paths
        self.ea_registry = ea_registry
        self.staging = files_staging
        self.runner = terminal_runner
        self.pdf = pdf_renderer
        self.bus = bus
        self.results_dir = results_dir
        self.session_path = session_path
        self._clock = clock
        self._cancel = threading.Event()

    # ---------- public API ----------

    def run(self, run_config: RunConfig) -> SessionState:
        state = SessionState.new(run_config)
        self._reset_cancel()
        return self._execute(state)

    def resume(self, state: SessionState) -> SessionState:
        self._reset_cancel()
        return self._execute(state)

    def cancel(self) -> None:
        """Request cancellation between phases (current phase finishes)."""
        self._cancel.set()

    # ---------- main loop ----------

    def _execute(self, state: SessionState) -> SessionState:
        self.bus.publish(SessionStarted(
            session_id=state.session_id,
            n_phases=len(state.jobs),
        ))
        self.results_dir.mkdir(parents=True, exist_ok=True)
        ok_overall = True
        for job in state.jobs:
            if self._cancel.is_set():
                if job.status == JobStatus.PENDING:
                    job.status = JobStatus.SKIPPED
                    job.reason = "cancelled"
                continue
            if job.status == JobStatus.DONE:
                continue
            if job.status == JobStatus.FAILED:
                ok_overall = False
                continue
            try:
                if job.phase == Phase.PDF:
                    self._run_pdf_job(state, job)
                else:
                    self._run_tester_job(state, job)
            except Exception as e:
                job.status = JobStatus.FAILED
                job.reason = f"{type(e).__name__}: {e}"
                job.finished_at = self._now()
                self.bus.publish(PhaseFinished(
                    job_key=job.job_key, ok=False,
                    duration_s=job.duration_s, reason=job.reason,
                ))
                ok_overall = False
            self._persist(state)
            if job.status == JobStatus.FAILED:
                # First failure aborts the rest, like the reference
                # scripts (no point computing PDF over partial data).
                for j in state.jobs:
                    if j.status == JobStatus.PENDING:
                        j.status = JobStatus.SKIPPED
                        j.reason = "preceding phase failed"
                self._persist(state)
                break

        state.finished_at = self._now()
        state.ok = ok_overall and state.n_failed() == 0
        self._persist(state)
        self.bus.publish(SessionFinished(
            session_id=state.session_id, ok=state.ok or False,
            summary=f"done={state.n_done()} failed={state.n_failed()} "
                    f"skipped={sum(1 for j in state.jobs if j.status == JobStatus.SKIPPED)}",
        ))
        return state

    # ---------- tester phases (BACK / FWD / REAL) ----------

    def _run_tester_job(self, state: SessionState, job: JobSpec) -> None:
        rc = state.run_config
        plan = self._plan_for(rc, job.tf)
        if plan is None:
            raise ValueError(f"no TFPlan for tf {job.tf!r}")

        self._set_running(job, phase=job.phase, tf=plan.tf.value)

        window = _phase_window(plan, job.phase, rc)
        tf_enum_val = tf_enum(plan.tf.value)
        symbol = rc.symbol
        dname = _dname(symbol, plan.tf.value)

        # Per-phase .set
        if job.phase == Phase.BACK:
            params = back_params(tf_enum_val, rc.min_depo)
        elif job.phase == Phase.FWD:
            params = fwd_params(tf_enum_val, rc.min_depo)
        elif job.phase == Phase.REAL:
            params = real_params(tf_enum_val, rc.min_depo, n=REAL_N_DEFAULT)
        else:
            raise ValueError(f"not a tester phase: {job.phase}")

        # EA staging
        build = self.ea_registry.get(TESTER_BUILD)
        self.staging.stage_ea(build.ea_id, build.path)

        # Profile (.set / .ini)
        run_id = f"{state.session_id}_{job.job_key.replace('.', '_')}"
        self.staging.write_set(run_id, params)
        ini_cfg = IniConfig(
            expert=self.paths.expert_rel(build.ea_id, build.ex5_basename),
            expert_parameters=self.paths.set_rel(run_id),
            symbol=symbol,
            from_date=_fmt_date(window.begin),
            to_date=_fmt_date(window.end),
            report=self.paths.report_rel(run_id),
            model=_phase_model(job.phase),
            optimization=OptimizationMode.SLOW_COMPLETE,
            deposit=rc.min_depo,
        )
        ini_path = self.staging.write_ini(run_id, ini_cfg)

        # BACK is the first phase per TF -- ensure pro100.csv is clean.
        if job.phase == Phase.BACK:
            self.staging.cleanup_pro100(dname)

        # Launch MT5
        timeout_s = DEFAULT_TIMEOUTS_S.get(job.phase, 4 * 3600)
        self.bus.publish(LogLine(
            job_key=job.job_key,
            line=f"launching terminal: {window.begin}..{window.end}, "
                 f"model={_phase_model(job.phase).name}, timeout={timeout_s}s",
        ))
        try:
            res = self.runner.run(ini_path, timeout_s=timeout_s)
        except TerminalAlreadyRunning as e:
            raise RuntimeError(str(e)) from e
        finally:
            # Tear down staging artifacts whether the run succeeded or not.
            self.staging.cleanup_profile(run_id)

        if not res.ok:
            self.staging.unstage_ea(build.ea_id)
            raise RuntimeError(
                f"terminal exit={res.exit_code} timed_out={res.timed_out} "
                f"after {res.duration_s}s"
            )

        # Collect output
        out_csv = self.results_dir / _phase_csv_name(rc, plan, job.phase)
        collected = self.staging.collect_pro100_output(dname, out_csv)
        self.staging.unstage_ea(build.ea_id)
        if collected is None:
            raise RuntimeError(
                f"pro100.csv not produced for dname {dname!r} -- "
                f"phase finished with 0 useful frames"
            )

        rows = read_pro100_csv(collected)
        self._set_done(job, duration_s=res.duration_s,
                       output_path=str(collected), rows=len(rows))

    # ---------- PDF phase ----------

    def _run_pdf_job(self, state: SessionState, job: JobSpec) -> None:
        rc = state.run_config
        self._set_running(job, phase=Phase.PDF, tf=None)

        pages: list[PageSpec] = []
        for plan in rc.tf_plans:
            fwd_key = f"{plan.tf.value}.{Phase.FWD.value}"
            try:
                fwd_job = state.by_key(fwd_key)
            except KeyError:
                continue
            if fwd_job.status != JobStatus.DONE or not fwd_job.output_path:
                continue
            rows = read_pro100_csv(Path(fwd_job.output_path))
            kept = filter_top_n_dd(
                rows, top_n=rc.top_n, dd_max=rc.dd_max,
            )
            back_w, fwd_w = compute_periods(
                rc.end_date, plan, snap=rc.snap_to_month_start,
            )
            pages.append(PageSpec(
                symbol=rc.symbol,
                tf=plan.tf.value,
                min_depo=int(rc.min_depo),
                fwd_from=_fmt_date(fwd_w.begin),
                fwd_to=_fmt_date(fwd_w.end),
                rows=kept,
            ))

        if not pages:
            raise RuntimeError("no forward CSVs available -- nothing to render")

        out_pdf = self.results_dir / f"Pro100_{state.session_id}.pdf"
        started = self._clock()
        result = self.pdf.render(out_pdf, pages)
        duration = round(self._clock() - started, 2)
        total_rows = sum(result.n_rows_per_page)
        self._set_done(job, duration_s=duration,
                       output_path=str(result.pdf_path), rows=total_rows)

    # ---------- helpers ----------

    def _plan_for(self, rc: RunConfig, tf: str | None) -> TFPlan | None:
        if tf is None:
            return None
        for plan in rc.tf_plans:
            if plan.tf.value == tf:
                return plan
        return None

    def _reset_cancel(self) -> None:
        self._cancel.clear()

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _set_running(self, job: JobSpec, phase: Phase, tf: str | None) -> None:
        job.status = JobStatus.RUNNING
        job.started_at = self._now()
        self.bus.publish(PhaseStarted(
            job_key=job.job_key, tf=tf or "", phase=phase.value,
        ))

    def _set_done(
        self, job: JobSpec, *, duration_s: float,
        output_path: str | None = None, rows: int | None = None,
    ) -> None:
        job.status = JobStatus.DONE
        job.finished_at = self._now()
        job.duration_s = duration_s
        job.output_path = output_path
        job.rows = rows
        self.bus.publish(PhaseFinished(
            job_key=job.job_key, ok=True,
            duration_s=duration_s,
            output_path=output_path, rows=rows,
        ))

    def _persist(self, state: SessionState) -> None:
        if self.session_path is None:
            return
        try:
            save_session(self.session_path, state)
        except OSError:
            # persistence failure is non-fatal -- run continues in memory.
            pass
