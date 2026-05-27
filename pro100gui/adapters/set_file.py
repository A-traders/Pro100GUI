"""MT5 Strategy Tester .set file builder.

File format:
  - Encoding: UTF-16 LE with BOM (FF FE).
  - Line ending: CRLF.
  - Each line: 'key=value' for a fixed input, or
    'key=default||start||step||stop||Y' for an optimization range
    (Y means 'optimize this parameter').

Pro100 always writes exactly three parameters:
  - inp_tf1 (signal timeframe, MT5 enum value)
  - inp_set (which setup to use; negative -- algorithmic mode)
  - inp_mm  (money management starting deposit)

Preset helpers (`back_params`, `fwd_params`, `real_params`,
`mm_sweep_params`, `back_opt_range_params`) match the phases defined
in the journal and in opt_pro100_002 / mm_sweep_001.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path


def _fmt(v: int | float | str) -> str:
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


@dataclass(frozen=True, slots=True)
class FixedParam:
    """Single non-optimized parameter: 'name=value'."""

    name: str
    value: int | float | str

    def render(self) -> str:
        return f"{self.name}={_fmt(self.value)}"


@dataclass(frozen=True, slots=True)
class RangeParam:
    """Optimization range: 'name=default||start||step||stop||Y'.

    The tester treats `default` as the value used when optimization is
    OFF; during optimization the range is `[start..stop]` step `step`.
    Sign of `step` must match direction (start..stop).
    """

    name: str
    default: int | float
    start: int | float
    step: int | float
    stop: int | float

    def __post_init__(self) -> None:
        if self.step == 0:
            raise ValueError(f"step must be non-zero for {self.name}")
        if self.step > 0 and self.stop < self.start:
            raise ValueError(
                f"step>0 but stop<start for {self.name}: "
                f"start={self.start}, stop={self.stop}"
            )
        if self.step < 0 and self.stop > self.start:
            raise ValueError(
                f"step<0 but stop>start for {self.name}: "
                f"start={self.start}, stop={self.stop}"
            )

    def render(self) -> str:
        return (
            f"{self.name}="
            f"{_fmt(self.default)}||{_fmt(self.start)}||"
            f"{_fmt(self.step)}||{_fmt(self.stop)}||Y"
        )


SetParam = FixedParam | RangeParam


# ---------- presets (named by phase from the journal) ----------

def back_params(tf_enum_value: int, min_depo: float) -> list[SetParam]:
    """BACK phase: full slow-complete with inp_set=-1 (algorithmic)."""
    return [
        FixedParam("inp_tf1", tf_enum_value),
        FixedParam("inp_set", -1),
        FixedParam("inp_mm", min_depo),
    ]


def fwd_params(tf_enum_value: int, min_depo: float) -> list[SetParam]:
    """FORWARD phase: re-test top-1000 of BACK via inp_set=-1000."""
    return [
        FixedParam("inp_tf1", tf_enum_value),
        FixedParam("inp_set", -1000),
        FixedParam("inp_mm", min_depo),
    ]


def real_params(tf_enum_value: int, min_depo: float, n: int) -> list[SetParam]:
    """REAL phase: re-test top-N survivors via inp_set=-N, real ticks."""
    if n < 1 or n > 1000:
        raise ValueError(f"real N must be 1..1000, got {n}")
    return [
        FixedParam("inp_tf1", tf_enum_value),
        FixedParam("inp_set", -n),
        FixedParam("inp_mm", min_depo),
    ]


def mm_sweep_params(
    tf_enum_value: int,
    n_sets: int,
    mm_start: int = 1000,
    mm_step: int = 500,
    mm_stop: int = 8000,
) -> list[SetParam]:
    """MM-sweep: double-axis optimization over inp_set and inp_mm.

    inp_set ranges over -1..-n_sets (negative step) -- EA picks the
    n-th setup from pro100.csv input.
    inp_mm ranges over [mm_start..mm_stop] step mm_step.
    """
    if n_sets < 1:
        raise ValueError(f"n_sets must be >= 1, got {n_sets}")
    return [
        FixedParam("inp_tf1", tf_enum_value),
        RangeParam("inp_set", default=0, start=-1, step=-1, stop=-n_sets),
        RangeParam("inp_mm", default=10000, start=mm_start, step=mm_step, stop=mm_stop),
    ]


def back_opt_range_params(
    tf_enum_value: int, min_depo: float, opt_start: int, opt_stop: int
) -> list[SetParam]:
    """BACK with explicit inp_set optimization range (opt:XXX-YYY mode).

    Used by opt_pro100 when a custom range is supplied; EA must be
    version _006 or newer.
    """
    if opt_start >= opt_stop:
        raise ValueError(f"opt_start must be < opt_stop, got {opt_start}..{opt_stop}")
    return [
        FixedParam("inp_tf1", tf_enum_value),
        RangeParam("inp_set", default=0, start=opt_start, step=1, stop=opt_stop),
        FixedParam("inp_mm", min_depo),
    ]


# ---------- rendering / writing ----------

def render_set(params: Iterable[SetParam], line_ending: str = "\r\n") -> str:
    """Render parameters to .set file body (text form, no BOM)."""
    return line_ending.join(p.render() for p in params) + line_ending


def write_set_file(
    path: Path, params: Sequence[SetParam], line_ending: str = "\r\n"
) -> None:
    """Write .set file in MT5-canonical format: UTF-16 LE BOM + CRLF."""
    body = render_set(params, line_ending=line_ending)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\xff\xfe" + body.encode("utf-16-le"))
