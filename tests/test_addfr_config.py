"""Tests for AddFr config profiles + serializer."""

from __future__ import annotations

from pro100gui.adapters.addfr_config import (
    CONFIG_FILENAME,
    EXTENDED,
    STANDARD,
    AddFrProfile,
    serialize_addfr_config,
)


def test_filename_constant():
    assert CONFIG_FILENAME == "pro100_addfr.cfg"


def test_standard_matches_legacy_tst_008_defaults():
    assert STANDARD.max_fr == 1000
    assert STANDARD.best_mm == 3
    assert STANDARD.best_ft == 10
    assert STANDARD.min_diff == 0.01


def test_extended_matches_legacy_opt_008_defaults():
    assert EXTENDED.max_fr == 100000
    assert EXTENDED.best_mm == 20
    assert EXTENDED.best_ft == 20
    assert EXTENDED.min_diff == 0.000001


def test_serialize_returns_ascii_bytes():
    raw = serialize_addfr_config(STANDARD)
    assert isinstance(raw, bytes)
    raw.decode("ascii")  # round-trips
    assert b"\r\n" in raw  # CRLF for Notepad-friendliness


def test_serialize_includes_all_four_keys():
    raw = serialize_addfr_config(EXTENDED)
    text = raw.decode("ascii")
    assert "MAX_FR=100000" in text
    assert "BEST_MM=20" in text
    assert "BEST_FT=20" in text
    # min_diff should not be in scientific notation
    assert "MIN_DIFF=0.000001" in text
    assert "1e-" not in text.lower()


def test_serialize_header_names_the_profile():
    raw = serialize_addfr_config(STANDARD)
    assert raw.startswith(b"# Pro100GUI addfr config -- profile: standard")


def test_custom_profile_can_be_built():
    p = AddFrProfile(name="custom", max_fr=42, best_mm=5,
                    best_ft=7, min_diff=0.1)
    raw = serialize_addfr_config(p)
    text = raw.decode("ascii")
    assert "profile: custom" in text
    assert "MAX_FR=42" in text
    assert "MIN_DIFF=0.1" in text
