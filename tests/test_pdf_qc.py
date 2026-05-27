"""Tests for PdfQC (rasterize PDF -> PNG)."""

from pathlib import Path

import pytest

from pro100gui.adapters.pdf_qc import PdfQC, render_pages_to_png
from pro100gui.adapters.pdf_renderer import PdfRenderer, PageSpec
from pro100gui.core.filters import Pro100Row


def _make_pdf(tmp_path: Path, n_pages: int = 2) -> Path:
    pages = [
        PageSpec(
            symbol="XAUUSD", tf=f"M{1 + i}", min_depo=10000,
            fwd_from="2025.01.01", fwd_to="2026.05.24",
            rows=[Pro100Row(rating=10.0, annual_gmean_pct=50.0,
                            max_rel_dd_pct=30.0, trades=10, setup_no=-1)],
        )
        for i in range(n_pages)
    ]
    out = tmp_path / "src.pdf"
    PdfRenderer().render(out, pages)
    return out


def test_render_pages_to_png_all_pages(tmp_path: Path):
    pdf = _make_pdf(tmp_path, n_pages=2)
    out_dir = tmp_path / "png"
    rendered = render_pages_to_png(pdf, out_dir)
    assert len(rendered) == 2
    for r in rendered:
        assert r.png_path.is_file()
        assert r.png_path.stat().st_size > 0
        assert r.width_px > 0 and r.height_px > 0


def test_render_pages_to_png_selected_indices(tmp_path: Path):
    pdf = _make_pdf(tmp_path, n_pages=3)
    out_dir = tmp_path / "png"
    rendered = render_pages_to_png(pdf, out_dir, page_indices=[0, 2])
    assert len(rendered) == 2
    assert {r.page_index for r in rendered} == {0, 2}


def test_render_pages_to_png_out_of_range_ignored(tmp_path: Path):
    pdf = _make_pdf(tmp_path, n_pages=1)
    out_dir = tmp_path / "png"
    rendered = render_pages_to_png(pdf, out_dir, page_indices=[0, 5])
    assert len(rendered) == 1
    assert rendered[0].page_index == 0


def test_scale_affects_image_size(tmp_path: Path):
    pdf = _make_pdf(tmp_path, n_pages=1)
    small = render_pages_to_png(pdf, tmp_path / "s", scale=1.0)
    big = render_pages_to_png(pdf, tmp_path / "b", scale=2.0)
    assert big[0].width_px > small[0].width_px
    assert big[0].height_px > small[0].height_px


def test_pdfqc_class_render(tmp_path: Path):
    pdf = _make_pdf(tmp_path)
    qc = PdfQC(scale=1.5)
    rendered = qc.render(pdf, tmp_path / "png")
    assert all(r.png_path.is_file() for r in rendered)


def test_pdfqc_cleanup_removes_files(tmp_path: Path):
    pdf = _make_pdf(tmp_path)
    qc = PdfQC()
    rendered = qc.render(pdf, tmp_path / "png")
    qc.cleanup(rendered)
    for r in rendered:
        assert not r.png_path.exists()


def test_pdfqc_cleanup_on_missing_is_silent(tmp_path: Path):
    pdf = _make_pdf(tmp_path)
    qc = PdfQC()
    rendered = qc.render(pdf, tmp_path / "png")
    qc.cleanup(rendered)
    qc.cleanup(rendered)  # second call -- files already gone
