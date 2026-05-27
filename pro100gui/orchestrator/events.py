"""In-process event bus and event types for the orchestrator.

Adapters and the orchestrator publish events; subscribers (the GUI,
loggers, tests) receive them synchronously in the publishing thread.
This keeps Pro100GUI decoupled from any specific UI toolkit -- the
GUI layer wraps subscribers in Qt signals as needed.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


# ---------- event types ----------

@dataclass(frozen=True, slots=True)
class Event:
    """Base of all orchestrator events. Carries a timestamp."""

    ts: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc),
        compare=False,
    )


@dataclass(frozen=True, slots=True)
class SessionStarted(Event):
    """A new run started. session_id is unique per invocation."""

    session_id: str = ""
    n_phases: int = 0


@dataclass(frozen=True, slots=True)
class SessionFinished(Event):
    session_id: str = ""
    ok: bool = False
    summary: str = ""


@dataclass(frozen=True, slots=True)
class PhaseStarted(Event):
    """One BACK/FWD/REAL/MM-SWEEP/PDF phase began."""

    job_key: str = ""  # e.g., "M5.back"
    tf: str = ""
    phase: str = ""  # 'back' | 'fwd' | 'real' | 'mm_sweep' | 'pdf'


@dataclass(frozen=True, slots=True)
class PhaseProgress(Event):
    """Free-form progress text emitted by adapters during a phase."""

    job_key: str = ""
    message: str = ""


@dataclass(frozen=True, slots=True)
class PhaseFinished(Event):
    job_key: str = ""
    ok: bool = False
    duration_s: float = 0.0
    output_path: str | None = None  # for PDF/CSV outputs
    rows: int | None = None  # CSV row count, if applicable
    reason: str | None = None  # human-readable, esp. on failure


@dataclass(frozen=True, slots=True)
class LogLine(Event):
    """Auxiliary log line (terminal stdout fragment, etc.)."""

    job_key: str = ""
    line: str = ""


# ---------- event bus ----------

Subscriber = Callable[[Event], None]


class EventBus:
    """Synchronous in-process event bus.

    Subscribers are called in registration order. A subscriber that
    raises is unsubscribed and the exception is silently dropped so
    one broken consumer cannot disrupt the run.
    """

    def __init__(self) -> None:
        self._subs: list[Subscriber] = []
        self._lock = threading.RLock()

    def subscribe(self, fn: Subscriber) -> None:
        with self._lock:
            if fn not in self._subs:
                self._subs.append(fn)

    def unsubscribe(self, fn: Subscriber) -> None:
        with self._lock:
            try:
                self._subs.remove(fn)
            except ValueError:
                pass

    def publish(self, event: Event) -> None:
        with self._lock:
            subs = list(self._subs)
        broken: list[Subscriber] = []
        for fn in subs:
            try:
                fn(event)
            except Exception:
                broken.append(fn)
        if broken:
            with self._lock:
                for fn in broken:
                    try:
                        self._subs.remove(fn)
                    except ValueError:
                        pass

    def subscriber_count(self) -> int:
        with self._lock:
            return len(self._subs)


class EventRecorder:
    """Helper subscriber that records all events into a list.

    Useful for tests and for the GUI's history pane. Not thread-safe
    for concurrent reads; treat the .events list as snapshot data.
    """

    def __init__(self) -> None:
        self.events: list[Event] = []

    def __call__(self, event: Event) -> None:
        self.events.append(event)

    def of_type(self, cls: type) -> list[Any]:
        return [e for e in self.events if isinstance(e, cls)]
