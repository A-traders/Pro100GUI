"""Tests for TerminalRunner (subprocess mocked, no real MT5 launch)."""

from pathlib import Path

import pytest

from pro100gui.adapters.paths import MT5Paths
from pro100gui.adapters.terminal_runner import (
    RunResult,
    TerminalAlreadyRunning,
    TerminalRunner,
)


def _make_terminal_exe(tmp_path: Path) -> Path:
    p = tmp_path / "mt5" / "terminal64.exe"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"")
    return p


def _runner(
    tmp_path: Path,
    watchdog=None,
    launcher=None,
    clock=None,
) -> TerminalRunner:
    paths = MT5Paths(install_dir=tmp_path / "mt5", project_dir=tmp_path / "home")
    return TerminalRunner(
        paths,
        watchdog=watchdog or (lambda _: False),
        launcher=launcher or (lambda exe, cwd, ini, t: (0, False)),
        clock=clock or (lambda: 0.0),
    )


def test_is_running_returns_watchdog_value(tmp_path: Path):
    _make_terminal_exe(tmp_path)
    r = _runner(tmp_path, watchdog=lambda _: True)
    assert r.is_running() is True


def test_assert_not_running_raises_when_running(tmp_path: Path):
    _make_terminal_exe(tmp_path)
    r = _runner(tmp_path, watchdog=lambda _: True)
    with pytest.raises(TerminalAlreadyRunning):
        r.assert_not_running()


def test_assert_not_running_silent_when_clear(tmp_path: Path):
    _make_terminal_exe(tmp_path)
    _runner(tmp_path).assert_not_running()


def test_run_returns_runresult_on_success(tmp_path: Path):
    _make_terminal_exe(tmp_path)
    ini = tmp_path / "x.ini"
    ini.write_bytes(b"")
    clock_values = iter([100.0, 101.5])
    r = _runner(
        tmp_path,
        launcher=lambda exe, cwd, p, t: (0, False),
        clock=lambda: next(clock_values),
    )
    res = r.run(ini, timeout_s=60)
    assert isinstance(res, RunResult)
    assert res.exit_code == 0
    assert res.duration_s == 1.5
    assert res.timed_out is False
    assert res.ok is True


def test_run_reports_timeout(tmp_path: Path):
    _make_terminal_exe(tmp_path)
    ini = tmp_path / "x.ini"
    ini.write_bytes(b"")
    r = _runner(tmp_path, launcher=lambda exe, cwd, p, t: (-1, True))
    res = r.run(ini, timeout_s=1)
    assert res.timed_out is True
    assert res.ok is False


def test_run_reports_nonzero_exit(tmp_path: Path):
    _make_terminal_exe(tmp_path)
    ini = tmp_path / "x.ini"
    ini.write_bytes(b"")
    r = _runner(tmp_path, launcher=lambda exe, cwd, p, t: (3, False))
    res = r.run(ini, timeout_s=60)
    assert res.exit_code == 3
    assert res.ok is False


def test_run_missing_terminal_raises(tmp_path: Path):
    # terminal64.exe NOT created
    r = _runner(tmp_path)
    ini = tmp_path / "x.ini"
    ini.write_bytes(b"")
    with pytest.raises(FileNotFoundError):
        r.run(ini, timeout_s=60)


def test_run_missing_ini_raises(tmp_path: Path):
    _make_terminal_exe(tmp_path)
    r = _runner(tmp_path)
    with pytest.raises(FileNotFoundError):
        r.run(tmp_path / "no_such.ini", timeout_s=60)


def test_run_refuses_when_already_running(tmp_path: Path):
    _make_terminal_exe(tmp_path)
    ini = tmp_path / "x.ini"
    ini.write_bytes(b"")
    r = _runner(tmp_path, watchdog=lambda _: True)
    with pytest.raises(TerminalAlreadyRunning):
        r.run(ini, timeout_s=60)


def test_launcher_receives_correct_args(tmp_path: Path):
    _make_terminal_exe(tmp_path)
    ini = tmp_path / "x.ini"
    ini.write_bytes(b"")
    captured: dict = {}

    def launcher(exe, cwd, ini_path, timeout_s):
        captured["exe"] = exe
        captured["cwd"] = cwd
        captured["ini"] = ini_path
        captured["timeout"] = timeout_s
        return 0, False

    r = _runner(tmp_path, launcher=launcher)
    r.run(ini, timeout_s=123)
    assert captured["exe"].name == "terminal64.exe"
    assert captured["cwd"].name == "mt5"
    assert captured["ini"] == ini
    assert captured["timeout"] == 123
