"""Tests for TWR math."""

import math

import pytest

from pro100gui.core.twr import format_twr, months_to_x, twr_year


def test_twr_year_basic():
    assert twr_year(0) == 1.0
    assert twr_year(100) == 2.0
    assert twr_year(-50) == 0.5


def test_months_to_x_examples():
    # Doubling at 100% annual TWR -> exactly 12 months.
    assert months_to_x(2.0, 2.0) == 12
    # x11 at TWR_year=11 -> exactly 12 months.
    assert months_to_x(11.0, 11.0) == 12


def test_months_to_x_target_unreachable_at_flat_twr():
    assert months_to_x(10.0, 1.0) is None
    assert months_to_x(10.0, 0.5) is None


def test_months_to_x_zero_growth_target():
    assert months_to_x(1.0, 1.5) == 0
    assert months_to_x(0.5, 1.5) == 0


def test_months_to_x_rounds_up():
    # log(11)/log(twr) = 11.999 -> ceil = 12
    twr = math.exp(math.log(11.0) / 11.999 * 12)  # constructed
    assert months_to_x(11.0, twr) == 12


def test_months_to_x_target_invalid():
    with pytest.raises(ValueError):
        months_to_x(0.0, 1.5)


def test_format_twr_normal():
    assert format_twr(1.23) == "1.23"
    assert format_twr(99999.99) == "99999.99"


def test_format_twr_caps_huge():
    out = format_twr(150_000.0)
    assert ">" in out
    # default cap 100'000 -> "100'000"
    assert "100'000" in out
