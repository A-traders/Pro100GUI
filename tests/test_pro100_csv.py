"""Tests for the pro100.csv codec: UTF-16 LE BOM + ';' + Setup № header."""

from pathlib import Path

import pytest

from pro100gui.core.filters import Pro100Row
from pro100gui.core.pro100_csv import (
    HEADER_BASE,
    HEADER_MM,
    NUMERO,
    read_pro100_csv,
    write_pro100_csv,
)


def test_header_uses_numero_sign():
    assert NUMERO == "№"
    assert HEADER_BASE[4] == f"Setup {NUMERO}"


def test_roundtrip_forward_rows(tmp_path: Path):
    rows = [
        Pro100Row(
            rating=12.34,
            annual_gmean_pct=156.7,
            max_rel_dd_pct=42.5,
            trades=128,
            setup_no=-15,
            fine_tune=0.5,
            min_depo=10000,
        ),
        Pro100Row(
            rating=8.0,
            annual_gmean_pct=80.0,
            max_rel_dd_pct=64.99,
            trades=10,
            setup_no=-3,
        ),
    ]
    p = tmp_path / "pro100.csv"
    write_pro100_csv(p, rows)
    back = read_pro100_csv(p)
    assert len(back) == 2
    assert back[0].rating == 12.34
    assert back[0].setup_no == -15
    assert back[0].min_depo == 10000
    assert back[1].fine_tune is None
    assert back[1].min_depo is None


def test_written_file_starts_with_utf16_le_bom(tmp_path: Path):
    p = tmp_path / "pro100.csv"
    write_pro100_csv(p, [Pro100Row(1.0, 2.0, 3.0, 4, 5)])
    raw = p.read_bytes()
    assert raw[:2] == b"\xff\xfe"


def test_written_file_has_numero_glyph(tmp_path: Path):
    p = tmp_path / "pro100.csv"
    write_pro100_csv(p, [])
    text = p.read_bytes().decode("utf-16")
    assert "Setup №" in text


def test_written_file_has_blank_separator_line(tmp_path: Path):
    p = tmp_path / "pro100.csv"
    write_pro100_csv(p, [Pro100Row(1.0, 2.0, 3.0, 4, 5)])
    text = p.read_bytes().decode("utf-16")
    lines = text.split("\r\n")
    # lines[0] header, lines[1] empty, lines[2] data, lines[3] trailing empty
    assert lines[0].startswith("Rating")
    assert lines[1] == ""
    assert lines[2].startswith("1.0")


def test_read_skips_garbage_rows(tmp_path: Path):
    # Hand-craft a file with a non-numeric first cell -- must be skipped.
    p = tmp_path / "pro100.csv"
    body = (
        ";".join(HEADER_BASE) + "\r\n"
        + "\r\n"
        + "garbage;header;like;line;here;;\r\n"
        + "1.0;2.0;3.0;4;5;;\r\n"
    )
    p.write_bytes(b"\xff\xfe" + body.encode("utf-16-le"))
    rows = read_pro100_csv(p)
    assert len(rows) == 1
    assert rows[0].rating == 1.0


def test_mm_sweep_variant_roundtrip(tmp_path: Path):
    rows = [
        Pro100Row(
            rating=5.0,
            annual_gmean_pct=200.0,
            max_rel_dd_pct=50.0,
            trades=20,
            setup_no=-7,
            inp_mm=2500,
        ),
    ]
    p = tmp_path / "pro100_mm.csv"
    write_pro100_csv(p, rows, with_mm_column=True)
    text = p.read_bytes().decode("utf-16")
    assert text.splitlines()[0] == ";".join(HEADER_MM)
    back = read_pro100_csv(p)
    assert back[0].inp_mm == 2500


def test_read_handles_utf8_fallback(tmp_path: Path):
    # No BOM, plain UTF-8 -- some external tools save like this.
    p = tmp_path / "pro100.csv"
    body = (
        ";".join(HEADER_BASE) + "\n"
        + "\n"
        + "1.5;3.0;10.0;7;-2;;\n"
    )
    p.write_bytes(body.encode("utf-8"))
    rows = read_pro100_csv(p)
    assert len(rows) == 1
    assert rows[0].setup_no == -2
