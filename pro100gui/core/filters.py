"""Row filters and the 'third pass after last fail' algorithm.

These are the building blocks for selecting which forward-csv rows
go to the PDF and which mm value to report in the 'Min depo' column.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Pro100Row:
    """One result row from pro100.csv (forward or mm-sweep variant).

    `inp_mm` is set only for mm-sweep rows; for forward rows it stays
    None and the deposit used by the EA equals `min_depo`.
    """

    rating: float
    annual_gmean_pct: float
    max_rel_dd_pct: float
    trades: int
    setup_no: int
    fine_tune: float | None = None
    min_depo: int | None = None
    inp_mm: int | None = None


MM_STEPS: tuple[int, ...] = tuple(range(1000, 8001, 500))


def filter_top_n_dd(
    rows: Sequence[Pro100Row], top_n: int, dd_max: float
) -> list[Pro100Row]:
    """Take first `top_n` rows (already rating-desc from CSV), keep DD <= dd_max."""
    if top_n < 0:
        raise ValueError("top_n must be >= 0")
    return [r for r in rows[:top_n] if r.max_rel_dd_pct <= dd_max]


def third_pass_after_fail(
    passed_mms: Iterable[int],
    steps: Sequence[int] = MM_STEPS,
    passes: int = 3,
) -> int | None:
    """Find the N-th passing mm value after the last fail in `steps`.

    Algorithm from journal 5.4:
      1. If the maximum step is not in passed_mms -> None
         (top of range failed -> set is unstable).
      2. If nothing failed -> sort passed steps ascending.
      3. Otherwise sort passed steps strictly greater than last_fail.
      4. Return steps[passes - 1] (0-indexed), or None if too few.
    """
    if passes < 1:
        raise ValueError("passes must be >= 1")
    if not steps:
        return None
    passed = set(passed_mms) & set(steps)
    max_step = max(steps)
    if max_step not in passed:
        return None
    fails = [m for m in steps if m not in passed]
    if not fails:
        after = sorted(passed)
    else:
        last_fail = max(fails)
        after = sorted(m for m in passed if m > last_fail)
    return after[passes - 1] if len(after) >= passes else None
