"""Tests for the .ini config builder."""

from pathlib import Path

from pro100gui.adapters.ini_file import (
    IniConfig,
    OptimizationMode,
    TesterModel,
    render_ini,
    write_ini_file,
)


def _basic_cfg(**overrides) -> IniConfig:
    defaults = dict(
        expert=r"_TesterAgent\some_ea\some_ea.ex5",
        expert_parameters=r"_TesterAgent\abc.set",
        symbol="XAUUSD",
        from_date="2025.09.01",
        to_date="2026.05.24",
        report=r"MQL5\Files\_TesterAgent\report123",
    )
    defaults.update(overrides)
    return IniConfig(**defaults)


def test_basic_render_contains_section_header():
    out = render_ini(_basic_cfg())
    assert out.startswith("[Tester]\r\n")


def test_basic_render_includes_all_required_keys():
    out = render_ini(_basic_cfg())
    for key in [
        "Expert=", "ExpertParameters=", "Symbol=", "Period=",
        "Login=", "Model=", "Optimization=", "OptimizationCriterion=",
        "FromDate=", "ToDate=", "Report=", "Deposit=", "Currency=",
        "Leverage=", "UseLocal=", "UseRemote=", "UseCloud=", "Visual=",
        "ShutdownTerminal=", "ReplaceReport=", "ForwardMode=",
        "ProfitInPips=", "ExecutionMode=",
    ]:
        assert key in out, f"missing key in ini: {key}"


def test_default_period_is_m1():
    out = render_ini(_basic_cfg())
    assert "Period=M1\r\n" in out


def test_default_optimization_is_slow_complete():
    out = render_ini(_basic_cfg())
    assert "Optimization=1\r\n" in out


def test_default_model_is_open_prices_only():
    out = render_ini(_basic_cfg())
    assert "Model=2\r\n" in out


def test_pro100_real_phase_model_4():
    out = render_ini(_basic_cfg(model=TesterModel.REAL_TICKS))
    assert "Model=4\r\n" in out


def test_mm_sweep_model_1():
    out = render_ini(_basic_cfg(model=TesterModel.ONE_MINUTE_OHLC))
    assert "Model=1\r\n" in out


def test_optimization_disabled_for_single_test():
    out = render_ini(_basic_cfg(optimization=OptimizationMode.DISABLED))
    assert "Optimization=0\r\n" in out


def test_dates_passed_through():
    out = render_ini(_basic_cfg(from_date="2025.01.15", to_date="2025.12.31"))
    assert "FromDate=2025.01.15\r\n" in out
    assert "ToDate=2025.12.31\r\n" in out


def test_empty_expert_parameters_keeps_empty_value():
    out = render_ini(_basic_cfg(expert_parameters=""))
    assert "ExpertParameters=\r\n" in out


def test_write_ini_file_has_utf16_bom(tmp_path: Path):
    p = tmp_path / "t.ini"
    write_ini_file(p, _basic_cfg())
    raw = p.read_bytes()
    assert raw[:2] == b"\xff\xfe"


def test_write_ini_file_decodes_clean(tmp_path: Path):
    p = tmp_path / "t.ini"
    cfg = _basic_cfg(symbol="EURUSD", deposit=5000, leverage=500)
    write_ini_file(p, cfg)
    text = p.read_bytes().decode("utf-16")
    assert "Symbol=EURUSD" in text
    assert "Deposit=5000" in text
    assert "Leverage=500" in text


def test_render_matches_canonical_template_shape(tmp_path: Path):
    """Verify our generated body matches the structural shape of
    optimize_complete.ini.template (key order, Login= empty, etc.)."""
    out = render_ini(_basic_cfg())
    lines = out.splitlines()
    # Order assertions for the most stable section of the template
    assert lines[0] == "[Tester]"
    assert lines[1].startswith("Expert=")
    assert lines[2].startswith("ExpertParameters=")
    assert lines[3].startswith("Symbol=")
    assert lines[4].startswith("Period=")
    assert lines[5] == "Login="
    assert lines[6].startswith("Model=")
