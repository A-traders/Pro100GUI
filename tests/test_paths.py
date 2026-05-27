"""Tests for MT5Paths derivation logic."""

from pathlib import Path

from pro100gui.adapters.paths import STAGING_NAMESPACE, MT5Paths, default_paths


def _paths(tmp_path: Path) -> MT5Paths:
    return MT5Paths(install_dir=tmp_path / "mt5", project_dir=tmp_path / "home")


def test_default_paths_factory_returns_mt5paths():
    p = default_paths()
    assert isinstance(p, MT5Paths)
    assert p.terminal_exe.name == "terminal64.exe"


def test_terminal_exe_path(tmp_path: Path):
    p = _paths(tmp_path)
    assert p.terminal_exe == tmp_path / "mt5" / "terminal64.exe"


def test_mql5_dir(tmp_path: Path):
    p = _paths(tmp_path)
    assert p.mql5_dir == tmp_path / "mt5" / "MQL5"


def test_experts_staging_uses_namespace(tmp_path: Path):
    p = _paths(tmp_path)
    assert STAGING_NAMESPACE in str(p.experts_staging_root)
    assert p.experts_staging_root == tmp_path / "mt5" / "MQL5" / "Experts" / STAGING_NAMESPACE


def test_profile_root_uses_namespace(tmp_path: Path):
    p = _paths(tmp_path)
    assert p.profile_root == (
        tmp_path / "mt5" / "MQL5" / "Profiles" / "Tester" / STAGING_NAMESPACE
    )


def test_per_run_derivations(tmp_path: Path):
    p = _paths(tmp_path)
    assert p.set_file("abc").name == "abc.set"
    assert p.ini_file("abc").name == "abc.ini"
    assert p.set_file("abc").parent == p.profile_root


def test_pro100_local_and_common(tmp_path: Path):
    p = _paths(tmp_path)
    assert p.pro100_local("XAUUSD_S2_M1H1") == (
        tmp_path / "mt5" / "MQL5" / "Files" / "XAUUSD_S2_M1H1" / "pro100.csv"
    )
    assert p.pro100_common("XAUUSD_S2_M1H1").name == "pro100.csv"
    assert "Common" in str(p.pro100_common("XAUUSD_S2_M1H1"))


def test_expert_rel_format(tmp_path: Path):
    p = _paths(tmp_path)
    rel = p.expert_rel("XaurusPro100MK2_008", "XaurusPro100MK2_008.ex5")
    # backslashes, no leading sep, includes namespace
    assert rel == f"{STAGING_NAMESPACE}\\XaurusPro100MK2_008\\XaurusPro100MK2_008.ex5"


def test_set_rel_format(tmp_path: Path):
    p = _paths(tmp_path)
    assert p.set_rel("run_xyz") == f"{STAGING_NAMESPACE}\\run_xyz.set"


def test_report_rel_format(tmp_path: Path):
    p = _paths(tmp_path)
    assert p.report_rel("run_xyz") == f"{STAGING_NAMESPACE}\\run_xyz"
