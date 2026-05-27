"""Tests for FilesStaging adapter (pure filesystem ops on tmp_path)."""

from pathlib import Path

import pytest

from pro100gui.adapters.files_staging import FilesStaging
from pro100gui.adapters.ini_file import IniConfig
from pro100gui.adapters.paths import MT5Paths
from pro100gui.adapters.set_file import back_params


@pytest.fixture()
def staging(tmp_path: Path) -> FilesStaging:
    paths = MT5Paths(install_dir=tmp_path / "mt5", project_dir=tmp_path / "home")
    return FilesStaging(paths)


def _make_ex5(tmp_path: Path, name: str = "fake.ex5") -> Path:
    src = tmp_path / "cache" / name
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_bytes(b"FAKE_EX5_BYTES")
    return src


def test_stage_ea_copies_to_namespace_dir(tmp_path: Path, staging: FilesStaging):
    src = _make_ex5(tmp_path)
    dst = staging.stage_ea("my_ea", src)
    assert dst.is_file()
    assert dst.read_bytes() == b"FAKE_EX5_BYTES"
    assert dst.parent == staging.paths.ea_staging_dir("my_ea")


def test_stage_ea_missing_source_raises(staging: FilesStaging, tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        staging.stage_ea("ea", tmp_path / "no_such.ex5")


def test_stage_ea_is_idempotent(tmp_path: Path, staging: FilesStaging):
    src = _make_ex5(tmp_path)
    staging.stage_ea("ea", src)
    src.write_bytes(b"NEW_BYTES")
    dst = staging.stage_ea("ea", src)
    assert dst.read_bytes() == b"NEW_BYTES"


def test_unstage_ea_removes_dir(tmp_path: Path, staging: FilesStaging):
    src = _make_ex5(tmp_path)
    staging.stage_ea("ea", src)
    assert staging.paths.ea_staging_dir("ea").is_dir()
    staging.unstage_ea("ea")
    assert not staging.paths.ea_staging_dir("ea").exists()


def test_unstage_ea_missing_is_noop(staging: FilesStaging):
    staging.unstage_ea("never_existed")  # must not raise


def test_write_set_creates_file(staging: FilesStaging):
    p = staging.write_set("run1", back_params(tf_enum_value=16385, min_depo=10000))
    assert p.is_file()
    raw = p.read_bytes()
    assert raw.startswith(b"\xff\xfe")
    assert "inp_set=-1" in raw.decode("utf-16")


def test_write_ini_creates_file(staging: FilesStaging):
    cfg = IniConfig(
        expert=r"_Pro100GUI\ea\ea.ex5",
        expert_parameters=r"_Pro100GUI\run1.set",
        symbol="XAUUSD",
        from_date="2025.01.01",
        to_date="2026.05.24",
        report=r"_Pro100GUI\run1",
    )
    p = staging.write_ini("run1", cfg)
    assert p.is_file()
    text = p.read_bytes().decode("utf-16")
    assert "Symbol=XAUUSD" in text


def test_cleanup_profile_removes_files(staging: FilesStaging):
    staging.write_set("r", back_params(16385, 10000))
    cfg = IniConfig(
        expert="x", expert_parameters="y", symbol="XAUUSD",
        from_date="2025.01.01", to_date="2026.05.24", report="r",
    )
    staging.write_ini("r", cfg)
    assert staging.paths.set_file("r").is_file()
    assert staging.paths.ini_file("r").is_file()
    staging.cleanup_profile("r")
    assert not staging.paths.set_file("r").exists()
    assert not staging.paths.ini_file("r").exists()


def test_cleanup_profile_missing_is_noop(staging: FilesStaging):
    staging.cleanup_profile("never")  # must not raise


def test_write_pro100_input_writes_bytes(staging: FilesStaging):
    payload = b"\xff\xfeFAKE_CSV_BYTES"
    dst = staging.write_pro100_input("XAUUSD_S2_M1H1", payload)
    assert dst.read_bytes() == payload
    assert dst == staging.paths.pro100_local("XAUUSD_S2_M1H1")


def test_write_pro100_input_clears_common_copy(staging: FilesStaging):
    common = staging.paths.pro100_common("XAUUSD_S2_M1H1")
    common.parent.mkdir(parents=True, exist_ok=True)
    common.write_bytes(b"stale")
    assert common.is_file()
    staging.write_pro100_input("XAUUSD_S2_M1H1", b"new")
    assert not common.exists()


def test_cleanup_pro100_removes_both_copies(staging: FilesStaging):
    dname = "XAUUSD_S2_M1H1"
    staging.write_pro100_input(dname, b"data")
    common = staging.paths.pro100_common(dname)
    common.parent.mkdir(parents=True, exist_ok=True)
    common.write_bytes(b"common_data")
    removed = staging.cleanup_pro100(dname)
    assert len(removed) == 2
    assert not staging.paths.pro100_local(dname).exists()
    assert not common.exists()


def test_cleanup_pro100_with_nothing_to_remove(staging: FilesStaging):
    assert staging.cleanup_pro100("XAUUSD_S2_M1H1") == []


def test_collect_pro100_output_copies_file(tmp_path: Path, staging: FilesStaging):
    dname = "XAUUSD_S2_M1H1"
    staging.write_pro100_input(dname, b"\xff\xfeRESULT_DATA")
    dest = tmp_path / "out" / "result.csv"
    res = staging.collect_pro100_output(dname, dest)
    assert res == dest
    assert dest.is_file()
    assert dest.read_bytes() == b"\xff\xfeRESULT_DATA"


def test_collect_pro100_output_missing_returns_none(tmp_path: Path, staging: FilesStaging):
    dest = tmp_path / "out" / "result.csv"
    assert staging.collect_pro100_output("never_existed", dest) is None
    assert not dest.exists()
