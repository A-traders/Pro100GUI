"""Back/forward test period computation.

Logic comes from journal sections 1.1-1.2. With snap=True the start
of each phase is moved to the 1st of its month so the very first
calendar month is fully captured.
"""

from __future__ import annotations

import calendar
from datetime import date

from .models import DateWindow, TFPlan


def _sub_months(d: date, months: int) -> date:
    """Subtract `months` calendar months. Day clamped to month length."""
    if months < 0:
        raise ValueError(f"months must be >= 0, got {months}")
    y, m = d.year, d.month - months
    while m <= 0:
        m += 12
        y -= 1
    last_day = calendar.monthrange(y, m)[1]
    return date(y, m, min(d.day, last_day))


def compute_periods(
    end: date, plan: TFPlan, snap: bool = True
) -> tuple[DateWindow, DateWindow]:
    """Return (back_window, forward_window) for given end date and plan.

    With snap=True (the journal-recommended default) both windows start
    on day 1 of their first month.
    """
    back_from = _sub_months(end, plan.back_months)
    fwd_from = _sub_months(end, plan.forward_months)
    if snap:
        back_from = back_from.replace(day=1)
        fwd_from = fwd_from.replace(day=1)
    return DateWindow(back_from, end), DateWindow(fwd_from, end)
