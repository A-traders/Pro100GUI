"""Tests for PdfRenderer.

Verify the generated PDF: file exists, expected number of pages,
correct number of AcroForm fields, header text present.
"""

from pathlib import Path

import pytest
from pypdf import PdfReader

from pro100gui.adapters.pdf_renderer import PdfRenderer, PageSpec
from pro100gui.core.filters import Pro100Row


def _row(rating: float, dd: float, setup_no: int) -> Pro100Row:
    return Pro100Row(
        rating=rating,
        annual_gmean_pct=rating * 10,
        max_rel_dd_pct=dd,
        trades=50,
        setup_no=setup_no,
    )


def _page(rows: int, tf: str = "M5") -> PageSpec:
    return PageSpec(
        symbol="XAUUSD",
        tf=tf,
        min_depo=10000,
        fwd_from="2025.09.01",
        fwd_to="2026.05.24",
        rows=[_row(100 - i, 30 + i / 10, -i - 1) for i in range(rows)],
    )


def test_render_creates_pdf(tmp_path: Path):
    out = tmp_path / "out.pdf"
    res = PdfRenderer().render(out, [_page(rows=5)])
    assert out.is_file()
    assert res.pdf_path == out
    assert res.n_pages == 1


def test_render_multiple_pages(tmp_path: Path):
    out = tmp_path / "out.pdf"
    pages = [_page(rows=3, tf="M1"), _page(rows=4, tf="M5"), _page(rows=5, tf="H1")]
    res = PdfRenderer().render(out, pages)
    assert res.n_pages == 3
    reader = PdfReader(str(out))
    assert len(reader.pages) == 3


def test_field_count_matches_rows(tmp_path: Path):
    out = tmp_path / "out.pdf"
    res = PdfRenderer().render(out, [_page(rows=10)])
    # 10 checkbox + 10 textfield = 20 AcroForm fields
    assert res.fields_per_page == (20,)
    reader = PdfReader(str(out))
    fields = reader.get_fields() or {}
    assert len(fields) == 20


def test_field_names_disambiguate_pages(tmp_path: Path):
    out = tmp_path / "out.pdf"
    pages = [_page(rows=3, tf="M1"), _page(rows=3, tf="M5")]
    PdfRenderer().render(out, pages)
    reader = PdfReader(str(out))
    field_names = set(reader.get_fields() or {})
    # 6 chk + 6 note = 12 fields total, all unique
    assert len(field_names) == 12
    # Page index is in the name to keep them disjoint
    assert any("_p01_" in n for n in field_names)
    assert any("_p02_" in n for n in field_names)


def test_header_text_present_in_pdf(tmp_path: Path):
    out = tmp_path / "out.pdf"
    page = PageSpec(
        symbol="XAUUSD", tf="H1", min_depo=10000,
        fwd_from="2025.01.01", fwd_to="2026.05.24",
        rows=[_row(50, 40, -1)],
    )
    PdfRenderer().render(out, [page])
    reader = PdfReader(str(out))
    text = reader.pages[0].extract_text() or ""
    assert "XAUUSD" in text
    assert "H1" in text
    assert "10000" in text
    assert "2025.01.01" in text


def test_empty_rows_produces_no_rows_note(tmp_path: Path):
    out = tmp_path / "out.pdf"
    page = PageSpec(
        symbol="XAUUSD", tf="M5", min_depo=10000,
        fwd_from="2025.01.01", fwd_to="2026.05.24",
        rows=[],
    )
    res = PdfRenderer().render(out, [page])
    assert res.n_rows_per_page == (0,)
    assert res.fields_per_page == (0,)
    text = PdfReader(str(out)).pages[0].extract_text() or ""
    assert "no rows" in text.lower()


def test_capacity_truncates_overflow_rows(tmp_path: Path):
    out = tmp_path / "out.pdf"
    capacity = PdfRenderer.page_capacity()
    page = _page(rows=capacity + 50)
    res = PdfRenderer().render(out, [page])
    # Renderer caps to capacity
    assert res.n_rows_per_page[0] == capacity
    # AcroForm field count = 2 * capacity
    assert res.fields_per_page[0] == 2 * capacity


def test_page_capacity_is_reasonable():
    cap = PdfRenderer.page_capacity()
    # Sanity bounds based on A4 portrait + 15mm margins + 12.5pt rows.
    # v005 empirically fit 57 rows; renderer must stay close.
    assert 50 <= cap <= 65


def test_title_extra_appears_in_header(tmp_path: Path):
    out = tmp_path / "out.pdf"
    page = PageSpec(
        symbol="XAUUSD", tf="M5", min_depo=10000,
        fwd_from="2025.01.01", fwd_to="2026.05.24",
        rows=[_row(50, 40, -1)],
        title_extra="MM-sweep applied",
    )
    PdfRenderer().render(out, [page])
    text = PdfReader(str(out)).pages[0].extract_text() or ""
    assert "MM-sweep applied" in text


def test_pdf_title_metadata(tmp_path: Path):
    out = tmp_path / "out.pdf"
    PdfRenderer().render(out, [_page(rows=2)])
    reader = PdfReader(str(out))
    meta = reader.metadata or {}
    title = meta.get("/Title") or ""
    assert "Pro100" in str(title)
