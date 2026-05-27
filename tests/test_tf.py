"""Tests for the TF table."""

import pytest

from pro100gui.core.tf import tf_enum, tf_minutes, tf_str


@pytest.mark.parametrize(
    "tf, enum_val",
    [
        ("M1", 1),
        ("M5", 5),
        ("M15", 15),
        ("M30", 30),
        ("H1", 16385),
        ("H4", 16388),
        ("D1", 16408),
    ],
)
def test_tf_enum_from_string(tf, enum_val):
    assert tf_enum(tf) == enum_val


def test_tf_enum_from_minutes():
    assert tf_enum(60) == 16385  # H1
    assert tf_enum(5) == 5


def test_tf_enum_from_enum_value():
    assert tf_enum(16385) == 16385


def test_tf_enum_case_insensitive():
    assert tf_enum("h1") == 16385


def test_tf_enum_numeric_string():
    assert tf_enum("60") == 16385


def test_tf_enum_unknown_raises():
    with pytest.raises(ValueError):
        tf_enum("X1")
    with pytest.raises(ValueError):
        tf_enum(9999)


def test_tf_enum_rejects_bool():
    with pytest.raises(TypeError):
        tf_enum(True)


def test_tf_str_roundtrip():
    assert tf_str(16385) == "H1"
    assert tf_str("h1") == "H1"
    assert tf_str(60) == "H1"


def test_tf_minutes_lookup():
    assert tf_minutes("H1") == 60
    assert tf_minutes("M30") == 30
