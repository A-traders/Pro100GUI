"""Test back/forward period computation against the journal 1.2 matrix."""

from datetime import date

import pytest

from pro100gui.core.models import TF, TFPlan
from pro100gui.core.periods import _sub_months, compute_periods


END = date(2026, 5, 24)


@pytest.mark.parametrize(
    "tf, back, fwd, back_from, fwd_from",
    [
        (TF.M1, 3, 6, date(2026, 2, 1), date(2025, 11, 1)),
        (TF.M5, 4, 8, date(2026, 1, 1), date(2025, 9, 1)),
        (TF.M15, 5, 10, date(2025, 12, 1), date(2025, 7, 1)),
        (TF.M30, 6, 12, date(2025, 11, 1), date(2025, 5, 1)),
        (TF.H1, 8, 16, date(2025, 9, 1), date(2025, 1, 1)),
    ],
)
def test_journal_matrix_with_snap(tf, back, fwd, back_from, fwd_from):
    plan = TFPlan(tf=tf, back_months=back, forward_months=fwd)
    bw, fw = compute_periods(END, plan, snap=True)
    assert bw.begin == back_from
    assert bw.end == END
    assert fw.begin == fwd_from
    assert fw.end == END


def test_no_snap_preserves_day():
    plan = TFPlan(tf=TF.M1, back_months=3, forward_months=6)
    bw, fw = compute_periods(END, plan, snap=False)
    assert bw.begin == date(2026, 2, 24)
    assert fw.begin == date(2025, 11, 24)


def test_sub_months_clamps_day():
    # 31 March - 1 month -> Feb has no 31, clamp to 28 (2026 non-leap).
    assert _sub_months(date(2026, 3, 31), 1) == date(2026, 2, 28)


def test_sub_months_year_rollover():
    assert _sub_months(date(2026, 2, 15), 14) == date(2024, 12, 15)


def test_negative_months_rejected():
    with pytest.raises(ValueError):
        _sub_months(END, -1)


def test_invalid_plan_back_zero():
    with pytest.raises(ValueError):
        TFPlan(tf=TF.M1, back_months=0, forward_months=1)


def test_invalid_plan_forward_less_than_back():
    with pytest.raises(ValueError):
        TFPlan(tf=TF.M1, back_months=6, forward_months=3)
