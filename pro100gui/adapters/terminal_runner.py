"""Launch and supervise terminal64.exe for one tester run.

Single public entry point: `TerminalRunner.run(ini_path, timeout_s)`.
Before launching, asserts that no instance of OUR target terminal is
already running -- racing instances of MT5 produce inconsistent
results and can corrupt the global tester cache.

The watchdog uses PowerShell's Get-Process for accuracy (matches by
the full path of the running terminal64.exe). For unit tests, the
subprocess implementations are pluggable through the `launcher` and
`watchdog` constructor arguments.
"""

from __future__ import annotations

import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .paths import MT5Paths

_PS_NO_WIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)


@dataclass(frozen=True, slots=True)
class RunResult:
    """Outcome of one terminal64.exe invocation."""

    exit_code: int
    duration_s: float
    timed_out: bool

    @property
    def ok(self) -> bool:
        return not self.timed_out and self.exit_code == 0


class Watchdog(Protocol):
    """Determines whether the target terminal64.exe is currently running."""

    def __call__(self, terminal_exe: Path) -> bool: ...


class Launcher(Protocol):
    """Launches terminal64.exe with the given .ini and waits for it."""

    def __call__(
        self, terminal_exe: Path, cwd: Path, ini_path: Path, timeout_s: int
    ) -> tuple[int, bool]: ...


def _powershell_watchdog(terminal_exe: Path) -> bool:
    """Get-Process terminal64 | check Path == ours."""
    target = str(terminal_exe).lower()
    ps_cmd = (
        "Get-Process terminal64 -ErrorAction SilentlyContinue | "
        "Select-Object -ExpandProperty Path"
    )
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=20,
            creationflags=_PS_NO_WIN,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
    paths = [ln.strip().lower() for ln in proc.stdout.splitlines() if ln.strip()]
    return any(p == target for p in paths)


def _direct_launcher(
    terminal_exe: Path, cwd: Path, ini_path: Path, timeout_s: int
) -> tuple[int, bool]:
    """Spawn terminal64.exe directly. Window is minimized via STARTUPINFO."""
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 2  # SW_SHOWMINIMIZED
    try:
        proc = subprocess.run(
            [str(terminal_exe), "/portable", f"/config:{ini_path}"],
            cwd=str(cwd), timeout=timeout_s,
            startupinfo=startupinfo,
            creationflags=_PS_NO_WIN,
        )
        return proc.returncode, False
    except subprocess.TimeoutExpired:
        return -1, True


class TerminalAlreadyRunning(RuntimeError):
    """Raised when the target terminal64.exe is detected before launch."""


class TerminalRunner:
    """Launches the configured MT5 terminal with a given .ini and waits."""

    def __init__(
        self,
        paths: MT5Paths,
        *,
        watchdog: Watchdog | None = None,
        launcher: Launcher | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.paths = paths
        self._watchdog = watchdog or _powershell_watchdog
        self._launcher = launcher or _direct_launcher
        self._clock = clock

    def is_running(self) -> bool:
        """True if our target terminal64.exe is currently running."""
        return self._watchdog(self.paths.terminal_exe)

    def assert_not_running(self) -> None:
        """Raise TerminalAlreadyRunning if a stale instance is up."""
        if self.is_running():
            raise TerminalAlreadyRunning(
                f"{self.paths.terminal_exe} is already running; "
                f"close it before launching a new tester run."
            )

    def run(self, ini_path: Path, timeout_s: int) -> RunResult:
        """Launch terminal64.exe /portable /config:<ini_path> and wait.

        Pre-flight: terminal64.exe must exist, must not be running.
        """
        if not self.paths.terminal_exe.is_file():
            raise FileNotFoundError(
                f"terminal64.exe not found: {self.paths.terminal_exe}"
            )
        if not ini_path.is_file():
            raise FileNotFoundError(f"ini not found: {ini_path}")
        self.assert_not_running()

        started = self._clock()
        exit_code, timed_out = self._launcher(
            self.paths.terminal_exe, self.paths.install_dir, ini_path, timeout_s
        )
        return RunResult(
            exit_code=exit_code,
            duration_s=round(self._clock() - started, 2),
            timed_out=timed_out,
        )
