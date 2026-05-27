"""Pro100GUI main window: 4 tabs + worker wiring."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Slot
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
)
from pro100gui.core.models import RunConfig
from pro100gui.orchestrator.events import EventBus
from pro100gui.orchestrator.orchestrator import Orchestrator

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

    # ---------- slots ----------

    @Slot(object)
    def _on_settings_changed(self, settings: AppSettings) -> None:
        self.settings = settings
        self.results_screen.set_results_dir(settings.effective_results_dir())

    @Slot(object)
    def _on_start(self, run_config: RunConfig) -> None:
        if self._thread is not None:
            QMessageBox.warning(self, "Already running",
                                "A session is already in progress.")
            return
        if not self.settings.ea_path:
            QMessageBox.warning(
                self, "EA not set",
                "Set the EA .ex5 path on the Settings tab before starting a run.",
            )
            self.tabs.setCurrentWidget(self.settings_screen)
            return
        ea_path = Path(self.settings.ea_path)
        if not ea_path.is_file():
            QMessageBox.warning(
                self, "EA not found",
                f"The configured EA file does not exist:\n{ea_path}",
            )
            self.tabs.setCurrentWidget(self.settings_screen)
            return

        # Build adapter stack
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
            return

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

        thread.started.connect(lambda: worker.start_run(run_config))

        self._thread = thread
        self._worker = worker
        self.run_screen.reset()
        self.tabs.setCurrentWidget(self.run_screen)
        thread.start()

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

    @Slot(str)
    def _on_crashed(self, msg: str) -> None:
        self.run_screen.on_crashed(msg)
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(2000)
        self._thread = None
        self._worker = None

    # ---------- shutdown ----------

    def closeEvent(self, event) -> None:
        if self._worker is not None:
            self._worker.cancel()
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(2000)
        super().closeEvent(event)
