"""Tests for the .set file builder."""

from pathlib import Path

import pytest

from pro100gui.adapters.set_file import (
    FixedParam,
    RangeParam,
    back_opt_range_params,
    back_params,
    fwd_params,
    mm_sweep_params,
    real_params,
    render_set,
    write_set_file,
)


def test_fixed_param_render():
    assert FixedParam("inp_tf1", 16385).render() == "inp_tf1=16385"
    assert FixedParam("inp_mm", 10000.0).render() == "inp_mm=10000"
    assert FixedParam("inp_set", -1).render() == "inp_set=-1"


def test_range_param_render():
    p = RangeParam("inp_set", default=0, start=-1, step=-1, stop=-57)
    assert p.render() == "inp_set=0||-1||-1||-57||Y"


def test_range_param_mm():
    p = RangeParam("inp_mm", default=10000, start=1000, step=500, stop=8000)
    assert p.render() == "inp_mm=10000||1000||500||8000||Y"


def test_range_zero_step_rejected():
    with pytest.raises(ValueError):
        RangeParam("x", default=0, start=1, step=0, stop=5)


def test_range_direction_mismatch_rejected():
    with pytest.raises(ValueError):
        RangeParam("x", default=0, start=1, step=1, stop=-5)
    with pytest.raises(ValueError):
        RangeParam("x", default=0, start=-1, step=-1, stop=5)


def test_back_preset_matches_journal():
    params = back_params(tf_enum_value=16385, min_depo=10000)
    rendered = render_set(params)
    expected = "inp_tf1=16385\r\ninp_set=-1\r\ninp_mm=10000\r\n"
    assert rendered == expected


def test_fwd_preset_matches_journal():
    params = fwd_params(tf_enum_value=5, min_depo=10000)
    rendered = render_set(params)
    expected = "inp_tf1=5\r\ninp_set=-1000\r\ninp_mm=10000\r\n"
    assert rendered == expected


def test_real_preset_matches_journal():
    params = real_params(tf_enum_value=5, min_depo=10000, n=15)
    rendered = render_set(params)
    expected = "inp_tf1=5\r\ninp_set=-15\r\ninp_mm=10000\r\n"
    assert rendered == expected


def test_real_n_bounds():
    with pytest.raises(ValueError):
        real_params(tf_enum_value=5, min_depo=10000, n=0)
    with pytest.raises(ValueError):
        real_params(tf_enum_value=5, min_depo=10000, n=1001)


def test_mm_sweep_preset_matches_journal():
    params = mm_sweep_params(tf_enum_value=16385, n_sets=25)
    rendered = render_set(params)
    expected = (
        "inp_tf1=16385\r\n"
        "inp_set=0||-1||-1||-25||Y\r\n"
        "inp_mm=10000||1000||500||8000||Y\r\n"
    )
    assert rendered == expected


def test_mm_sweep_custom_mm_axis():
    params = mm_sweep_params(
        tf_enum_value=5, n_sets=10, mm_start=2000, mm_step=1000, mm_stop=10000
    )
    rendered = render_set(params)
    assert "inp_mm=10000||2000||1000||10000||Y" in rendered


def test_mm_sweep_zero_sets_rejected():
    with pytest.raises(ValueError):
        mm_sweep_params(tf_enum_value=5, n_sets=0)


def test_back_opt_range_preset():
    params = back_opt_range_params(
        tf_enum_value=16385, min_depo=10000, opt_start=1, opt_stop=100
    )
    rendered = render_set(params)
    expected = (
        "inp_tf1=16385\r\n"
        "inp_set=0||1||1||100||Y\r\n"
        "inp_mm=10000\r\n"
    )
    assert rendered == expected


def test_back_opt_range_bad_bounds():
    with pytest.raises(ValueError):
        back_opt_range_params(tf_enum_value=5, min_depo=10000, opt_start=5, opt_stop=5)


def test_write_set_file_format(tmp_path: Path):
    params = back_params(tf_enum_value=16385, min_depo=10000)
    p = tmp_path / "test.set"
    write_set_file(p, params)
    raw = p.read_bytes()
    assert raw.startswith(b"\xff\xfe")
    text = raw[2:].decode("utf-16-le")
    assert text == "inp_tf1=16385\r\ninp_set=-1\r\ninp_mm=10000\r\n"
