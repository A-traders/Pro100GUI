"""Session state: the durable snapshot of one full GUI run.

What's stored:
  * the RunConfig that started the run (for re-creating the job list);
  * one JobSpec per phase (TF x phase) with status + artifact refs;
  * timestamps and a session_id (for filename + log namespace).

Persisted as JSON next to the run's output dir so the GUI can resume
after a crash or a forced shutdown of MT5. Persistence is best-effort
and atomic: writes go to a temp file, then os.replace.
"""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path

from pro100gui.core.models import AddFrMode, RunConfig, TF, TFPlan


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


class Phase(str, Enum):
    BACK = "back"
    FWD = "fwd"
    REAL = "real"
    MM_SWEEP = "mm_sweep"
    PDF = "pdf"


@dataclass(slots=True)
class JobSpec:
    """One unit of work in the session graph."""

    job_key: str           # unique within the session, e.g. "M5.back"
    tf: str | None         # canonical TF string or None for cross-TF jobs (PDF)
    phase: Phase
    status: JobStatus = JobStatus.PENDING
    duration_s: float = 0.0
    output_path: str | None = None
    rows: int | None = None
    reason: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class SessionState:
    """All the durable state of one in-progress / finished session."""

    session_id: str
    created_at: datetime
    run_config: RunConfig
    jobs: list[JobSpec] = field(default_factory=list)
    finished_at: datetime | None = None
    ok: bool | None = None  # None until the session ends

    @classmethod
    def new(cls, run_config: RunConfig) -> "SessionState":
        return cls(
            session_id=_make_session_id(),
            created_at=_now(),
            run_config=run_config,
            jobs=list(_default_jobs_for(run_config)),
        )

    def by_key(self, key: str) -> JobSpec:
        for j in self.jobs:
            if j.job_key == key:
                return j
        raise KeyError(f"no job with key: {key!r}")

    def n_pending(self) -> int:
        return sum(1 for j in self.jobs if j.status == JobStatus.PENDING)

    def n_done(self) -> int:
        return sum(1 for j in self.jobs if j.status == JobStatus.DONE)

    def n_failed(self) -> int:
        return sum(1 for j in self.jobs if j.status == JobStatus.FAILED)


def _make_session_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]


def _default_jobs_for(rc: RunConfig) -> Iterable[JobSpec]:
    """Build the canonical job list from RunConfig.

    For v1 we generate BACK + FWD per TF plus an optional REAL.
    MM-sweep is reserved for the future EA-_009 wiring and not emitted.
    A final PDF job is appended.
    """
    for plan in rc.tf_plans:
        yield JobSpec(
            job_key=f"{plan.tf.value}.{Phase.BACK.value}",
            tf=plan.tf.value,
            phase=Phase.BACK,
        )
        yield JobSpec(
            job_key=f"{plan.tf.value}.{Phase.FWD.value}",
            tf=plan.tf.value,
            phase=Phase.FWD,
        )
        if rc.do_real_phase:
            yield JobSpec(
                job_key=f"{plan.tf.value}.{Phase.REAL.value}",
                tf=plan.tf.value,
                phase=Phase.REAL,
            )
    yield JobSpec(job_key="pdf", tf=None, phase=Phase.PDF)


# ---------- JSON serialization ----------

def _enum_to_str(v):
    if isinstance(v, Enum):
        return v.value
    return v


def _serialize(obj):
    if isinstance(obj, datetime):
        return {"__dt__": obj.isoformat()}
    if isinstance(obj, date):
        return {"__d__": obj.isoformat()}
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, tuple):
        return list(obj)
    raise TypeError(f"unsupported type: {type(obj).__name__}")


def _to_dict(state: SessionState) -> dict:
    raw = asdict(state)
    raw["jobs"] = [asdict(j) for j in state.jobs]
    return raw


def save_session(path: Path, state: SessionState) -> None:
    """Atomically write the session JSON snapshot."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _to_dict(state)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=_serialize)
    os.replace(tmp, path)


# ---------- JSON deserialization ----------

def _restore(d):
    if isinstance(d, dict):
        if "__dt__" in d:
            return datetime.fromisoformat(d["__dt__"])
        if "__d__" in d:
            return date.fromisoformat(d["__d__"])
        return {k: _restore(v) for k, v in d.items()}
    if isinstance(d, list):
        return [_restore(x) for x in d]
    return d


def _runconfig_from_dict(d: dict) -> RunConfig:
    tf_plans = tuple(
        TFPlan(
            tf=TF(p["tf"]),
            back_months=int(p["back_months"]),
            forward_months=int(p["forward_months"]),
        )
        for p in d.get("tf_plans", [])
    )
    return RunConfig(
        end_date=d["end_date"] if isinstance(d["end_date"], date) else date.fromisoformat(str(d["end_date"])),
        symbol=d.get("symbol", "XAUUSD"),
        min_depo=int(d.get("min_depo", 10000)),
        snap_to_month_start=bool(d.get("snap_to_month_start", True)),
        do_real_phase=bool(d.get("do_real_phase", False)),
        addfr_mode=AddFrMode(d.get("addfr_mode", "standard")),
        top_n=int(d.get("top_n", 57)),
        dd_max=float(d.get("dd_max", 65.0)),
        passes_after_fail=int(d.get("passes_after_fail", 3)),
        dup_threshold=float(d.get("dup_threshold", 0.10)),
        twr_cap=float(d.get("twr_cap", 100_000.0)),
        tf_plans=tf_plans,
    )


def _job_from_dict(d: dict) -> JobSpec:
    return JobSpec(
        job_key=d["job_key"],
        tf=d.get("tf"),
        phase=Phase(d["phase"]),
        status=JobStatus(d.get("status", "pending")),
        duration_s=float(d.get("duration_s", 0.0)),
        output_path=d.get("output_path"),
        rows=d.get("rows"),
        reason=d.get("reason"),
        started_at=d.get("started_at"),
        finished_at=d.get("finished_at"),
    )


def load_session(path: Path) -> SessionState:
    """Read a previously saved session JSON."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw = _restore(raw)
    return SessionState(
        session_id=raw["session_id"],
        created_at=raw["created_at"],
        run_config=_runconfig_from_dict(raw["run_config"]),
        jobs=[_job_from_dict(j) for j in raw.get("jobs", [])],
        finished_at=raw.get("finished_at"),
        ok=raw.get("ok"),
    )
