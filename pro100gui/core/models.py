"""Configuration models for one Pro100 GUI run.

All data classes here are frozen / immutable -- mutation would defeat
the purpose of "config snapshot" used by the orchestrator's
JSON-persistence layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class AddFrMode(str, Enum):
    """AddFr filter profile selected via radio in GUI."""

    STANDARD = "standard"  # MAX_FR=1000, BEST_MM=3, BEST_FT=10 -- main EA build
    SWEEP = "sweep"        # MAX_FR=100000, BEST_MM=20, BEST_FT=20 -- _opt EA build


class TF(str, Enum):
    """Timeframes supported by the Pro100 pipeline."""

    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    M30 = "M30"
    H1 = "H1"


@dataclass(frozen=True, slots=True)
class TFPlan:
    """Per-timeframe horizon: how many months back/forward to test."""

    tf: TF
    back_months: int
    forward_months: int

    def __post_init__(self) -> None:
        if self.back_months < 1:
            raise ValueError(f"back_months must be >= 1, got {self.back_months}")
        if self.forward_months < self.back_months:
            raise ValueError(
                f"forward_months ({self.forward_months}) must be >= "
                f"back_months ({self.back_months})"
            )


@dataclass(frozen=True, slots=True)
class DateWindow:
    """Closed-closed test window: [begin, end]."""

    begin: date
    end: date

    def __post_init__(self) -> None:
        if self.begin > self.end:
            raise ValueError(f"begin {self.begin} > end {self.end}")


@dataclass(frozen=True, slots=True)
class RunConfig:
    """Single GUI run configuration -- inputs of one full pipeline pass."""

    end_date: date
    symbol: str = "XAUUSD"
    min_depo: int = 10000
    snap_to_month_start: bool = True
    do_real_phase: bool = False
    addfr_mode: AddFrMode = AddFrMode.STANDARD
    top_n: int = 57
    dd_max: float = 65.0
    passes_after_fail: int = 3
    dup_threshold: float = 0.10
    twr_cap: float = 100_000.0
    tf_plans: tuple[TFPlan, ...] = field(default_factory=tuple)
