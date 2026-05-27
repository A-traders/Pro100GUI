"""Codec for pro100.csv files produced/consumed by the EA.

Format (journal 2.2):
  - encoding: UTF-16 LE with BOM (FF FE)
  - separator: ';'
  - line 1: header 'Rating;Annual gmean %;Max rel DD %;Trades;Setup №;Fine tune;Min depo'
  - line 2: empty
  - line 3+: data rows

The 'Setup №' header uses U+2116 (NUMERO SIGN) -- preserved on write.
Forward CSVs from opt_pro100 follow this exact schema. mm-sweep CSVs
add an inp_mm column appended at the end (column name 'inp_mm').
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from .filters import Pro100Row

NUMERO = "№"
HEADER_BASE = (
    "Rating",
    "Annual gmean %",
    "Max rel DD %",
    "Trades",
    f"Setup {NUMERO}",
    "Fine tune",
    "Min depo",
)
HEADER_MM = HEADER_BASE + ("inp_mm",)

_BOM_LE = b"\xff\xfe"
_BOM_BE = b"\xfe\xff"


def _decode(raw: bytes) -> str:
    if raw.startswith(_BOM_LE) or raw.startswith(_BOM_BE):
        text = raw.decode("utf-16")
    else:
        text = raw.decode("utf-8")
    if text.startswith("﻿"):
        text = text[1:]
    return text


def _parse_float(s: str) -> float:
    s = s.strip()
    if not s:
        return 0.0
    return float(s.replace(",", "."))


def _parse_int(s: str) -> int:
    s = s.strip()
    return int(float(s)) if s else 0


def read_pro100_csv(path: Path) -> list[Pro100Row]:
    """Read a pro100 CSV (forward or mm-sweep variant) into Pro100Row list.

    Tolerates extra trailing columns (inp_mm). Skips empty lines and
    rows where the first cell is not a number.
    """
    text = _decode(path.read_bytes())
    rows: list[Pro100Row] = []
    saw_header = False
    has_mm_col = False
    for line in text.splitlines():
        if not line.strip():
            continue
        cells = [c.strip() for c in line.split(";")]
        if not saw_header:
            if cells and cells[0] == "Rating":
                saw_header = True
                has_mm_col = len(cells) > len(HEADER_BASE) and cells[-1] == "inp_mm"
            continue
        if len(cells) < len(HEADER_BASE):
            continue
        try:
            rating = _parse_float(cells[0])
        except ValueError:
            continue
        rows.append(
            Pro100Row(
                rating=rating,
                annual_gmean_pct=_parse_float(cells[1]),
                max_rel_dd_pct=_parse_float(cells[2]),
                trades=_parse_int(cells[3]),
                setup_no=_parse_int(cells[4]),
                fine_tune=_parse_float(cells[5]) if cells[5] else None,
                min_depo=_parse_int(cells[6]) if cells[6] else None,
                inp_mm=_parse_int(cells[7]) if has_mm_col and len(cells) > 7 and cells[7] else None,
            )
        )
    return rows


def write_pro100_csv(
    path: Path,
    rows: Iterable[Pro100Row],
    with_mm_column: bool = False,
    line_ending: str = "\r\n",
) -> None:
    """Write Pro100Rows in the EA's canonical format (UTF-16 LE BOM + ';')."""

    header = HEADER_MM if with_mm_column else HEADER_BASE
    out_lines = [";".join(header), ""]
    for r in rows:
        cells = [
            f"{r.rating}",
            f"{r.annual_gmean_pct}",
            f"{r.max_rel_dd_pct}",
            f"{r.trades}",
            f"{r.setup_no}",
            "" if r.fine_tune is None else f"{r.fine_tune}",
            "" if r.min_depo is None else f"{r.min_depo}",
        ]
        if with_mm_column:
            cells.append("" if r.inp_mm is None else f"{r.inp_mm}")
        out_lines.append(";".join(cells))
    body = line_ending.join(out_lines) + line_ending
    path.write_bytes(_BOM_LE + body.encode("utf-16-le"))
