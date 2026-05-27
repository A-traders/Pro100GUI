"""Qt worker that runs the Orchestrator off the main thread.

Two responsibilities:
  1. Run Orchestrator.run() in a separate thread so the GUI stays
     responsive while MT5 grinds through phases.
  2. Translate orchestrator EventBus events into Qt signals, which
     are automatically marshalled across thread boundaries so widget
     slots can update the UI safely.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal, Slot

from pro100gui.core.models import RunConfig
from pro100gui.orchestrator.events import (
    Event,
    EventBus,
    LogLine,
    PhaseFinished,
    PhaseProgress,
    PhaseStarted,
    SessionFinished,
    SessionStarted,
)
from pro100gui.orchestrator.orchestrator import Orchestrator
from pro100gui.orchestrator.session import SessionState


class OrchestratorWorker(QObject):
    """Wraps an Orchestrator instance for use with QThread.

    Usage:
        worker = OrchestratorWorker(orchestrator)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(lambda: worker.start_run(config))
        worker.session_finished.connect(thread.quit)
        thread.start()
    """

    sessionStarted = Signal(str, int)       # session_id, n_phases
    phaseStarted = Signal(str, str, str)     # job_key, tf, phase
    phaseFinished = Signal(str, bool, float, object, object, object)
    """job_key, ok, duration_s, output_path (str|None), rows (int|None), reason (str|None)"""
    phaseProgress = Signal(str, str)         # job_key, message
    logLine = Signal(str, str)               # job_key, line
    sessionFinished = Signal(str, bool, str)  # session_id, ok, summary
    crashed = Signal(str)                    # str(exception) when orchestrator itself raises

    def __init__(self, orchestrator: Orchestrator, bus: EventBus) -> None:
        super().__init__()
        self._orch = orchestrator
        self._bus = bus
        self._bus.subscribe(self._on_event)

    # ---------- Qt slots ----------

    @Slot(object)
    def start_run(self, run_config: RunConfig) -> None:
        try:
            self._orch.run(run_config)
        except Exception as e:
            self.crashed.emit(f"{type(e).__name__}: {e}")

    @Slot(object)
    def resume_run(self, state: SessionState) -> None:
        try:
            self._orch.resume(state)
        except Exception as e:
            self.crashed.emit(f"{type(e).__name__}: {e}")

    @Slot()
    def cancel(self) -> None:
        self._orch.cancel()

    # ---------- bus -> Qt translation ----------

    def _on_event(self, event: Event) -> None:
        if isinstance(event, SessionStarted):
            self.sessionStarted.emit(event.session_id, event.n_phases)
        elif isinstance(event, PhaseStarted):
            self.phaseStarted.emit(event.job_key, event.tf, event.phase)
        elif isinstance(event, PhaseProgress):
            self.phaseProgress.emit(event.job_key, event.message)
        elif isinstance(event, PhaseFinished):
            self.phaseFinished.emit(
                event.job_key, event.ok, event.duration_s,
                event.output_path, event.rows, event.reason,
            )
        elif isinstance(event, LogLine):
            self.logLine.emit(event.job_key, event.line)
        elif isinstance(event, SessionFinished):
            self.sessionFinished.emit(event.session_id, event.ok, event.summary)


def start_worker_thread(worker: OrchestratorWorker) -> QThread:
    """Create a QThread, move the worker onto it, and start it.

    Caller is responsible for keeping references to both objects so
    Python's garbage collector doesn't drop them mid-run.
    """
    thread = QThread()
    worker.moveToThread(thread)
    thread.start()
    return thread
