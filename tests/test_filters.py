"""Tests for filter_top_n_dd and third_pass_after_fail."""

import pytest

from pro100gui.core.filters import (
    MM_STEPS,
    Pro100Row,
    filter_top_n_dd,
    third_pass_after_fail,
)


def _row(rating: float, dd: float, setup_no: int = 1) -> Pro100Row:
    return Pro100Row(
        rating=rating,
        annual_gmean_pct=0.0,
        max_rel_dd_pct=dd,
        trades=0,
        setup_no=setup_no,
    )


def test_mm_steps_matches_journal():
    # 1000..8000 step 500 -- 15 values
    assert MM_STEPS == tuple(range(1000, 8001, 500))
    assert len(MM_STEPS) == 15


def test_filter_top_n_dd_basic():
    rows = [_row(100 - i, dd=30 + i) for i in range(10)]
    out = filter_top_n_dd(rows, top_n=5, dd_max=33)
    # top_n=5 cuts to first 5; DD<=33 keeps rows with i in {0, 1, 2, 3}
    assert len(out) == 4
    assert all(r.max_rel_dd_pct <= 33 for r in out)


def test_filter_top_n_zero():
    rows = [_row(100, dd=10)]
    assert filter_top_n_dd(rows, top_n=0, dd_max=100) == []


def test_filter_top_n_negative_raises():
    with pytest.raises(ValueError):
        filter_top_n_dd([], top_n=-1, dd_max=50)


def test_third_pass_8000_failed_returns_none():
    passed = {1000, 1500, 2000, 2500, 3000}  # 8000 missing
    assert third_pass_after_fail(passed) is None


def test_third_pass_no_fails():
    passed = set(MM_STEPS)
    # No fails -> sorted passed; 3rd is MM_STEPS[2] = 2000
    assert third_pass_after_fail(passed) == 2000


def test_third_pass_with_single_fail():
    # 1500 fails; passed = others
    passed = set(MM_STEPS) - {1500}
    # last_fail = 1500; after = sorted(2000..8000); 3rd = 3000
    assert third_pass_after_fail(passed) == 3000


def test_third_pass_with_late_fail():
    # 6500 fails; passed > 6500 = {7000, 7500, 8000}; 3rd = 8000
    passed = set(MM_STEPS) - {6500}
    assert third_pass_after_fail(passed) == 8000


def test_third_pass_too_few_after_last_fail():
    # 7500 fails; only {8000} after -> not enough for 3rd
    passed = set(MM_STEPS) - {7500}
    assert third_pass_after_fail(passed) is None


def test_third_pass_custom_passes_count():
    # Same data as test_third_pass_no_fails but asking for 1st
    passed = set(MM_STEPS)
    assert third_pass_after_fail(passed, passes=1) == 1000


def test_third_pass_passes_zero_raises():
    with pytest.raises(ValueError):
        third_pass_after_fail({1000}, passes=0)


def test_third_pass_extra_mms_outside_steps_ignored():
    # mm=999 passed but not in MM_STEPS -- should be ignored.
    passed = set(MM_STEPS) | {999}
    assert third_pass_after_fail(passed) == 2000
