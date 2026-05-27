"""TWR (Terminal Wealth Relative) math.

Used for the 'TWR' and 'Mo to xN' columns in the merged PDF table
(journal sections 4 and 6/_010, with the x11 correction).
"""

from __future__ import annotations

import math


def twr_year(annual_gmean_pct: float) -> float:
    """Annual TWR from annual geometric-mean percentage profit.

    annual_gmean_pct = 100 -> TWR = 2.0 (deposit doubled).
    annual_gmean_pct = 0   -> TWR = 1.0 (no growth).
    annual_gmean_pct = -50 -> TWR = 0.5 (deposit halved).
    """
    return 1.0 + annual_gmean_pct / 100.0


def months_to_x(target_x: float, twr_y: float) -> int | None:
    """Months required to multiply deposit by `target_x` at annual TWR `twr_y`.

    Solves TWR_year ^ (months / 12) = target_x, then rounds up.

    Returns None when target is unreachable: twr_y <= 1.0 and target > 1.

    Notes from journal:
      - 1000% net profit => x11 multiplier (TWR), not x10.
      - For target <= 1 returns 0 (already there or shrinking allowed).
    """
    if target_x <= 0:
        raise ValueError("target_x must be > 0")
    if target_x <= 1.0:
        return 0
    if twr_y <= 1.0:
        return None
    months = 12.0 * math.log(target_x) / math.log(twr_y)
    return max(1, math.ceil(months))


def format_twr(twr_y: float, cap: float = 100_000.0) -> str:
    """Format annual TWR for the PDF table, capping huge values.

    Journal _013: values above 100'000 are rendered as '>100'000', no
    scientific notation. Default cap matches the v013 behavior.
    """
    if twr_y > cap:
        return f">{int(cap):,}".replace(",", "'")
    return f"{twr_y:.2f}"
