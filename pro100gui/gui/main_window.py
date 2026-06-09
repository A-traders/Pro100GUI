"""Pro100GUI main window: 4 tabs + worker wiring."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, QTimer, Slot
from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QWidget,
)

from pro100gui.adapters.ea_registry import TESTER_BUILD, EARegistry
from pro100gui.adapters.ea_version_checker import EAVersionChecker
from pro100gui.adapters.files_staging import FilesStaging
from pro100gui.adapters.paths import MT5Paths
from pro100gui.adapters.pdf_renderer import PdfRenderer
from pro100gui.adapters.terminal_runner import TerminalRunner
from pro100gui.app.settings_store import (
    AppSettings,
    default_settings_path,
    load_settings,
    save_settings,
)
from pro100gui.core.models import RunConfig
from pro100gui.orchestrator.events import EventBus
from pro100gui.orchestrator.orchestrator import Orchestrator
from pro100gui.orchestrator.session import (
    JobStatus,
    SessionState,
    load_session,
)

from .first_run_wizard import FirstRunWizard, needs_first_run
from .screen_config import ConfigScreen
from .screen_results import ResultsScreen
from .screen_run import RunScreen
from .screen_settings import SettingsScreen
from .worker import OrchestratorWorker


class MainWindow(QMainWindow):

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Pro100GUI")
        self.resize(1100, 740)

        self.settings: AppSettings = load_settings()
        self.bus = EventBus()
        self._thread: QThread | None = None
        self._worker: OrchestratorWorker | None = None

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.config_screen = ConfigScreen()
        self.run_screen = RunScreen()
        self.results_screen = ResultsScreen()
        self.settings_screen = SettingsScreen(self.settings)

        self.tabs.addTab(self.config_screen, "Конфигурация")
        self.tabs.addTab(self.run_screen, "Прогон")
        self.tabs.addTab(self.results_screen, "Результаты")
        self.tabs.addTab(self.settings_screen, "Настройки")

        self.results_screen.set_results_dir(self.settings.effective_results_dir())

        # ----- wiring -----
        self.config_screen.startRequested.connect(self._on_start)
        self.run_screen.cancelRequested.connect(self._on_cancel)
        self.settings_screen.settingsChanged.connect(self._on_settings_changed)

        # On first launch: ask paths, then maybe offer resume.
        QTimer.singleShot(0, self._first_run_check_then_resume)

    # ---------- slots ----------

    @Slot(object)
    def _on_settings_changed(self, settings: AppSettings) -> None:
        self.settings = settings
        self.results_screen.set_results_dir(settings.effective_results_dir())

    @Slot(object)
    def _on_start(self, run_config: RunConfig) -> None:
        if not self._guard_idle():
            return
        built = self._build_orchestrator()
        if built is None:
            return
        orch, session_path = built

        worker, thread = self._wire_worker(orch)
        thread.started.connect(lambda: worker.start_run(run_config))

        self._launch(worker, thread)
        self._remember_session_path(session_path)

    @Slot(object)
    def _on_resume(self, state: SessionState) -> None:
        if not self._guard_idle():
            return
        built = self._build_orchestrator()
        if built is None:
            return
        orch, session_path = built

        worker, thread = self._wire_worker(orch)
        thread.started.connect(lambda: worker.resume_run(state))

        self._launch(worker, thread)
        self._remember_session_path(session_path)

    # ---------- helpers ----------

    def _guard_idle(self) -> bool:
        """Return False (and warn) if a session is already running."""
        if self._thread is not None:
            QMessageBox.warning(self, "Already running",
                                "A session is already in progress.")
            return False
        return True

    def _build_orchestrator(self) -> tuple[Orchestrator, Path] | None:
        """Validate settings and build the adapter stack.

        Returns (orchestrator, session_path) or None if validation
        failed (the user has been informed and switched to Settings).
        """
        if not self.settings.ea_path:
            QMessageBox.warning(
                self, "EA not set",
                "Set the EA .ex5 path on the Settings tab before starting a run.",
            )
            self.tabs.setCurrentWidget(self.settings_screen)
            return None
        ea_path = Path(self.settings.ea_path)
        if not ea_path.is_file():
            QMessageBox.warning(
                self, "EA not found",
                f"The configured EA file does not exist:\n{ea_path}",
            )
            self.tabs.setCurrentWidget(self.settings_screen)
            return None

        paths = MT5Paths(
            install_dir=Path(self.settings.mt5_install_dir),
            project_dir=Path(self.settings.project_dir),
        )
        if not paths.terminal_exe.is_file():
            QMessageBox.warning(
                self, "terminal64.exe not found",
                f"Cannot find terminal64.exe at:\n{paths.terminal_exe}",
            )
            self.tabs.setCurrentWidget(self.settings_screen)
            return None

        registry = EARegistry(version_checker=EAVersionChecker(
            post_url=self.settings.telegram_post_url,
        ))
        registry.register(TESTER_BUILD, ea_path)
        staging = FilesStaging(paths)
        runner = TerminalRunner(paths)

        results_dir = self.settings.effective_results_dir()
        session_path = results_dir / "session.json"

        orch = Orchestrator(
            paths=paths,
            ea_registry=registry,
            files_staging=staging,
            terminal_runner=runner,
            pdf_renderer=PdfRenderer(),
            bus=self.bus,
            results_dir=results_dir,
            session_path=session_path,
        )
        return orch, session_path

    def _wire_worker(self, orch: Orchestrator) -> tuple[OrchestratorWorker, QThread]:
        worker = OrchestratorWorker(orch, self.bus)
        thread = QThread()
        worker.moveToThread(thread)

        worker.sessionStarted.connect(self.run_screen.on_session_started)
        worker.phaseStarted.connect(self.run_screen.on_phase_started)
        worker.phaseProgress.connect(self.run_screen.on_phase_progress)
        worker.phaseFinished.connect(self.run_screen.on_phase_finished)
        worker.logLine.connect(self.run_screen.on_log_line)
        worker.sessionFinished.connect(self._on_session_finished)
        worker.crashed.connect(self._on_crashed)
        return worker, thread

    def _launch(self, worker: OrchestratorWorker, thread: QThread) -> None:
        self._thread = thread
        self._worker = worker
        self.run_screen.reset()
        self.tabs.setCurrentWidget(self.run_screen)
        thread.start()

    def _remember_session_path(self, session_path: Path) -> None:
        try:
            self.settings.last_session_path = str(session_path)
            save_settings(self.settings)
        except OSError:
            # non-fatal: resume offer at next launch just won't appear
            pass

    @Slot()
    def _on_cancel(self) -> None:
        if self._worker is not None:
            self._worker.cancel()

    @Slot(str, bool, str)
    def _on_session_finished(self, session_id: str, ok: bool, summary: str) -> None:
        self.run_screen.on_session_finished(session_id, ok, summary)
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(2000)
        self._thread = None
        self._worker = None
        self.results_screen.refresh()
        if ok:
            self.results_screen.open_results_folder()

    @Slot(str)
    def _on_crashed(self, msg: str) -> None:
        self.run_screen.on_crashed(msg)
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(2000)
        self._thread = None
        self._worker = None

    # ---------- first run + resume ----------

    def _first_run_check_then_resume(self) -> None:
        """Chain the first-run wizard then the resume dialog.

        If the wizard runs and user cancels, close the app -- no
        point continuing without MT5/EA paths. If it runs and user
        accepts, persist settings, sync screens, then proceed to
        the resume dialog.
        """
        if needs_first_run(self.settings):
            dlg = FirstRunWizard(self.settings, parent=self)
            if dlg.exec() != FirstRunWizard.Accepted:
                # User chose Cancel -> exit the app entirely.
                self.close()
                return
            self.settings = dlg.collected()
            try:
                save_settings(self.settings)
            except OSError:
                pass
            self.settings_screen.reload_from_settings(self.settings)
            self.results_screen.set_results_dir(
                self.settings.effective_results_dir()
            )

        self._offer_resume_if_any()

    def _load_resume_candidate(self) -> SessionState | None:
        """Return SessionState iff a Resume dialog should be offered.

        Pure-logic split from `_offer_resume_if_any` so tests can
        assert the decision without invoking QMessageBox.
        """
        raw = self.settings.last_session_path
        if not raw:
            return None
        sess_path = Path(raw)
        if not sess_path.is_file():
            return None
        try:
            state = load_session(sess_path)
        except (OSError, ValueError, KeyError, TypeError):
            return None
        unfinished = sum(
            1 for j in state.jobs
            if j.status in (JobStatus.PENDING, JobStatus.RUNNING)
        )
        if unfinished == 0:
            return None
        return state

    def _offer_resume_if_any(self) -> None:
        """If a previous session has unfinished jobs, ask the user."""
        state = self._load_resume_candidate()
        if state is None:
            return

        total = len(state.jobs)
        done = state.n_done()
        failed = state.n_failed()
        unfinished = total - done - failed - sum(
            1 for j in state.jobs if j.status.value == "skipped"
        )
        created = state.created_at.strftime("%Y-%m-%d %H:%M")

        box = QMessageBox(self)
        box.setWindowTitle("Незавершённая сессия")
        box.setIcon(QMessageBox.Question)
        box.setText(
            f"Найдена незавершённая сессия от {created}.\n"
            f"Прогресс: {done}/{total} job(ов) готово, "
            f"{unfinished} ожидает, {failed} с ошибкой.\n\n"
            f"Продолжить с того же места или начать новую?"
        )
        resume_btn = box.addButton("Продолжить", QMessageBox.AcceptRole)
        new_btn = box.addButton("Новая сессия", QMessageBox.DestructiveRole)
        box.addButton("Отмена", QMessageBox.RejectRole)
        box.setDefaultButton(resume_btn)
        box.exec()

        clicked = box.clickedButton()
        if clicked is resume_btn:
            self._on_resume(state)
        elif clicked is new_btn:
            self.tabs.setCurrentWidget(self.config_screen)
        # else: cancel -- user can resume later via the dialog at next launch.

    # ---------- shutdown ----------

    def closeEvent(self, event) -> None:
        if self._worker is not None:
            self._worker.cancel()
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(2000)
        super().closeEvent(event)
