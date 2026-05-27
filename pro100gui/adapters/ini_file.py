"""MT5 Strategy Tester .ini config builder.

Consumed by `terminal64.exe /portable /config:<path>` to drive a
single optimization or test pass. The schema mirrors the original
template in TesterAgent\\templates\\optimize_complete.ini.template
but is generated entirely in Python -- no external template file.

Encoding: UTF-16 LE BOM + CRLF (same as .set).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path


class TesterModel(IntEnum):
    """MT5 Strategy Tester `Model` field values."""

    __test__ = False  # silence pytest's 'Test*' class collection warning

    EVERY_TICK = 0
    ONE_MINUTE_OHLC = 1  # 'Open prices only' for M1 historical -- fast
    OPEN_PRICES_ONLY = 2  # default for Pro100 BACK/FWD phases
    MATH_CALCULATIONS = 3  # custom
    REAL_TICKS = 4  # for Pro100 REAL phase


class OptimizationMode(IntEnum):
    """MT5 Strategy Tester `Optimization` field values."""

    DISABLED = 0
    SLOW_COMPLETE = 1
    FAST_GENETIC = 2
    ALL_SYMBOLS_MW = 3


@dataclass(frozen=True, slots=True)
class IniConfig:
    """Concrete .ini config for one tester invocation."""

    expert: str
    """Relative path under MQL5\\Experts\\ (no leading backslash).
    Example: '_TesterAgent\\\\<ea_id>\\\\<ea_id>.ex5'."""

    expert_parameters: str
    """Relative path under MQL5\\Profiles\\Tester\\ (no leading
    backslash), or '' for no .set file."""

    symbol: str
    from_date: str  # 'YYYY.MM.DD'
    to_date: str    # 'YYYY.MM.DD'
    report: str
    """Relative path under MQL5\\Files\\ for the .xml report."""

    period: str = "M1"
    """Tester base period. Pro100 always runs on M1; the signal TF
    is set via the EA's inp_tf1 input."""

    model: TesterModel = TesterModel.OPEN_PRICES_ONLY
    optimization: OptimizationMode = OptimizationMode.SLOW_COMPLETE
    optimization_criterion: int = 6  # 6 = Custom max (OnTester result)

    deposit: int = 10000
    currency: str = "USD"
    leverage: int = 1000

    forward_mode: int = 0
    visual: int = 0
    shutdown_terminal: int = 1
    replace_report: int = 1
    execution_mode: int = 0
    use_local: int = 1
    use_remote: int = 0
    use_cloud: int = 0
    profit_in_pips: int = 0


def render_ini(cfg: IniConfig, line_ending: str = "\r\n") -> str:
    """Render IniConfig to the [Tester] section text body (no BOM)."""
    lines: list[str] = [
        "[Tester]",
        f"Expert={cfg.expert}",
        f"ExpertParameters={cfg.expert_parameters}",
        f"Symbol={cfg.symbol}",
        f"Period={cfg.period}",
        "Login=",
        f"Model={int(cfg.model)}",
        f"ExecutionMode={cfg.execution_mode}",
        f"Optimization={int(cfg.optimization)}",
        f"OptimizationCriterion={cfg.optimization_criterion}",
        f"FromDate={cfg.from_date}",
        f"ToDate={cfg.to_date}",
        f"ForwardMode={cfg.forward_mode}",
        f"Report={cfg.report}",
        f"ReplaceReport={cfg.replace_report}",
        f"ShutdownTerminal={cfg.shutdown_terminal}",
        f"Deposit={cfg.deposit}",
        f"Currency={cfg.currency}",
        f"ProfitInPips={cfg.profit_in_pips}",
        f"Leverage={cfg.leverage}",
        f"UseLocal={cfg.use_local}",
        f"UseRemote={cfg.use_remote}",
        f"UseCloud={cfg.use_cloud}",
        f"Visual={cfg.visual}",
    ]
    return line_ending.join(lines) + line_ending


def write_ini_file(
    path: Path, cfg: IniConfig, line_ending: str = "\r\n"
) -> None:
    """Write .ini file in MT5-canonical format: UTF-16 LE BOM + CRLF."""
    body = render_ini(cfg, line_ending=line_ending)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\xff\xfe" + body.encode("utf-16-le"))
