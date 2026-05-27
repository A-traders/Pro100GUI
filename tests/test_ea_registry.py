"""Tests for EARegistry."""

from pathlib import Path

import pytest

from pro100gui.adapters.ea_registry import (
    OPT_BUILD,
    TESTER_BUILD,
    EABuild,
    EARegistry,
)
from pro100gui.adapters.ea_version_checker import EAVersionChecker

FIXTURE_HTML = (
    Path(__file__).parent / "fixtures" / "tg_xauruspro_16.html"
).read_text(encoding="utf-8")


def _make_ea(tmp_path: Path, name: str = "XaurusPro100MK2_tst_008.ex5") -> Path:
    p = tmp_path / name
    p.write_bytes(b"compiled")
    return p


def test_eabuild_derives_id_and_basename(tmp_path: Path):
    p = _make_ea(tmp_path)
    b = EABuild(path=p)
    assert b.ea_id == "XaurusPro100MK2_tst_008"
    assert b.ex5_basename == "XaurusPro100MK2_tst_008.ex5"


def test_register_and_get(tmp_path: Path):
    r = EARegistry()
    p = _make_ea(tmp_path)
    b = r.register(TESTER_BUILD, p)
    assert r.has(TESTER_BUILD)
    assert r.get(TESTER_BUILD) is b
    assert b.path == p


def test_register_missing_file_raises(tmp_path: Path):
    r = EARegistry()
    with pytest.raises(FileNotFoundError):
        r.register(TESTER_BUILD, tmp_path / "absent.ex5")


def test_register_replaces_existing(tmp_path: Path):
    r = EARegistry()
    p1 = _make_ea(tmp_path, "a.ex5")
    p2 = _make_ea(tmp_path, "b.ex5")
    r.register(TESTER_BUILD, p1)
    r.register(TESTER_BUILD, p2)
    assert r.get(TESTER_BUILD).path == p2


def test_unregister_removes(tmp_path: Path):
    r = EARegistry()
    r.register(TESTER_BUILD, _make_ea(tmp_path))
    r.unregister(TESTER_BUILD)
    assert not r.has(TESTER_BUILD)


def test_unregister_absent_is_noop():
    EARegistry().unregister(TESTER_BUILD)  # must not raise


def test_get_missing_raises_keyerror():
    r = EARegistry()
    with pytest.raises(KeyError):
        r.get(TESTER_BUILD)


def test_keys_returns_all_registered(tmp_path: Path):
    r = EARegistry()
    r.register(TESTER_BUILD, _make_ea(tmp_path, "a.ex5"))
    r.register(OPT_BUILD, _make_ea(tmp_path, "b.ex5"))
    assert set(r.keys()) == {TESTER_BUILD, OPT_BUILD}


def test_verify_without_checker_returns_none(tmp_path: Path):
    r = EARegistry()
    r.register(TESTER_BUILD, _make_ea(tmp_path))
    assert r.verify(TESTER_BUILD) is None


def test_verify_with_matching_canonical(tmp_path: Path):
    # Local file name matches the fixture's canonical filename.
    p = _make_ea(tmp_path, "XaurusPro100MK2_tst_008.ex5")
    checker = EAVersionChecker(
        post_url="https://t.me/xauruspro/16",
        http_get=lambda _: FIXTURE_HTML,
    )
    r = EARegistry(version_checker=checker)
    r.register(TESTER_BUILD, p)
    res = r.verify(TESTER_BUILD)
    assert res is not None
    assert res.match is True


def test_verify_with_mismatched_canonical(tmp_path: Path):
    p = _make_ea(tmp_path, "XaurusPro100MK2_tst_007.ex5")
    checker = EAVersionChecker(
        post_url="https://t.me/xauruspro/16",
        http_get=lambda _: FIXTURE_HTML,
    )
    r = EARegistry(version_checker=checker)
    r.register(TESTER_BUILD, p)
    res = r.verify(TESTER_BUILD)
    assert res is not None
    assert res.match is False


def test_verify_missing_key_raises(tmp_path: Path):
    checker = EAVersionChecker(
        post_url="https://t.me/xauruspro/16",
        http_get=lambda _: FIXTURE_HTML,
    )
    r = EARegistry(version_checker=checker)
    with pytest.raises(KeyError):
        r.verify(TESTER_BUILD)
