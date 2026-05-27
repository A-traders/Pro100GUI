"""PDF report renderer for Pro100 forward results.

Each page renders one (symbol, TF, forward-period) view as an A4
portrait sheet: a one-line header followed by a 7-column table:

  Rating | Annual gmean % | Max rel DD % | Trades | Setup No | Check | Note

Check and Note are interactive AcroForm fields (a checkbox and a
short textfield) so the user can mark / annotate results inside the
PDF -- Edge / Adobe Reader / Foxit persist the values on save
(Chrome notably does NOT, see journal 3).

Layout ported from build_pro100_pdf_005.py. The 9-column merged
table (v010-v013) is deferred until MM-sweep is wired in via the
forthcoming EA _009.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as pdfcanvas

from pro100gui.core.filters import Pro100Row

# ---------- layout constants ----------

COL_WIDTHS: tuple[float, ...] = (
    60.0,   # Rating
    88.0,   # Annual gmean %
    78.0,   # Max rel DD %
    48.0,   # Trades
    60.0,   # Setup No
    26.0,   # Check
    150.0,  # Note
)
COL_HEADERS: tuple[str, ...] = (
    "Rating", "Annual gmean %", "Max rel DD %",
    "Trades", "Setup No", "Check", "Note",
)
N_DATA_COLS = 5
ROW_H = 12.5
HEADER_ROW_H = 14.5
PAGE_MARGIN = 15 * mm
FONT_BODY = "Helvetica"
FONT_BODY_BOLD = "Helvetica-Bold"
FONT_BODY_SIZE = 8.5
FONT_HEADER_SIZE = 9.0
FONT_TITLE_SIZE = 11.0

TABLE_HEADER_BG = colors.HexColor("#244055")
ROW_ALT_BG = colors.HexColor("#f3f6f9")
GRID_COLOR = colors.HexColor("#9a9a9a")
FIELD_BORDER = colors.HexColor("#7a8aa0")
FIELD_BG = colors.HexColor("#fbfdff")


# ---------- public dataclasses ----------

@dataclass(frozen=True, slots=True)
class PageSpec:
    """One page in the output PDF."""

    symbol: str
    tf: str
    min_depo: int
    fwd_from: str  # YYYY.MM.DD as shown in the header
    fwd_to: str
    rows: Sequence[Pro100Row]
    title_extra: str = ""
    """Optional trailing segment in the header (e.g. for marking phase)."""


@dataclass(frozen=True, slots=True)
class RenderResult:
    pdf_path: Path
    n_pages: int
    n_rows_per_page: tuple[int, ...]
    fields_per_page: tuple[int, ...] = field(default=())


# ---------- formatting helpers ----------

def _fmt_float(v: float) -> str:
    """All float cells use 2-decimal format consistently."""
    return f"{v:.2f}"


def _fmt_int(v: int) -> str:
    return str(int(v))


def _row_cells(row: Pro100Row) -> list[str]:
    """Format one Pro100Row into the 5 displayed string cells."""
    return [
        _fmt_float(row.rating),
        _fmt_float(row.annual_gmean_pct),
        _fmt_float(row.max_rel_dd_pct),
        _fmt_int(row.trades),
        _fmt_int(row.setup_no),
    ]


def _safe_id(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", str(s)).strip("_") or "x"


# ---------- canvas drawing primitives ----------

def _draw_page_header(c: pdfcanvas.Canvas, page: PageSpec, page_size: tuple[float, float]) -> None:
    x = PAGE_MARGIN
    y = page_size[1] - PAGE_MARGIN - FONT_TITLE_SIZE
    c.setFillColor(colors.black)
    segments: list[tuple[str, str]] = [
        (FONT_BODY_BOLD, page.symbol),
        (FONT_BODY, " | Signal TF: "),
        (FONT_BODY_BOLD, page.tf),
        (FONT_BODY, f" | Min depo {int(page.min_depo)}"),
        (FONT_BODY, " | Forward: "),
        (FONT_BODY_BOLD, f"{page.fwd_from} -- {page.fwd_to}"),
    ]
    if page.title_extra:
        segments.append((FONT_BODY, f" | {page.title_extra}"))
    cx = x
    for font, text in segments:
        c.setFont(font, FONT_TITLE_SIZE)
        c.drawString(cx, y, text)
        cx += c.stringWidth(text, font, FONT_TITLE_SIZE)


def _draw_table_header(c: pdfcanvas.Canvas, x0: float, y_top: float) -> float:
    y_bot = y_top - HEADER_ROW_H
    c.setFillColor(TABLE_HEADER_BG)
    total_w = sum(COL_WIDTHS)
    c.rect(x0, y_bot, total_w, HEADER_ROW_H, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont(FONT_BODY_BOLD, FONT_HEADER_SIZE)
    cx = x0
    for w, label in zip(COL_WIDTHS, COL_HEADERS):
        tw = c.stringWidth(label, FONT_BODY_BOLD, FONT_HEADER_SIZE)
        c.drawString(cx + (w - tw) / 2, y_bot + 4, label)
        cx += w
    return y_bot


def _draw_grid(c: pdfcanvas.Canvas, x0: float, y_top: float, y_bot: float) -> None:
    c.setStrokeColor(GRID_COLOR)
    c.setLineWidth(0.25)
    total_w = sum(COL_WIDTHS)
    c.line(x0, y_bot, x0 + total_w, y_bot)
    c.line(x0, y_top, x0 + total_w, y_top)
    cx = x0
    for w in COL_WIDTHS:
        c.line(cx, y_top, cx, y_bot)
        cx += w
    c.line(cx, y_top, cx, y_bot)


def _draw_row(
    c: pdfcanvas.Canvas,
    row_idx: int,
    y_top: float,
    x0: float,
    cells: list[str],
    page_idx: int,
    tf: str,
) -> float:
    y_bot = y_top - ROW_H
    if row_idx % 2 == 1:
        c.setFillColor(ROW_ALT_BG)
        c.rect(x0, y_bot, sum(COL_WIDTHS), ROW_H, stroke=0, fill=1)
    c.setStrokeColor(GRID_COLOR)
    c.setLineWidth(0.25)
    c.line(x0, y_bot, x0 + sum(COL_WIDTHS), y_bot)

    c.setFillColor(colors.black)
    c.setFont(FONT_BODY, FONT_BODY_SIZE)
    cx = x0
    for i in range(N_DATA_COLS):
        w = COL_WIDTHS[i]
        text = cells[i]
        tw = c.stringWidth(text, FONT_BODY, FONT_BODY_SIZE)
        c.drawString(cx + (w - tw) / 2, y_bot + 3.2, text)
        cx += w

    chk_w = COL_WIDTHS[5]
    chk_size = 9
    chk_x = cx + (chk_w - chk_size) / 2
    chk_y = y_bot + (ROW_H - chk_size) / 2
    c.acroForm.checkbox(
        name=f"chk_p{page_idx:02d}_{_safe_id(tf)}_r{row_idx:03d}",
        x=chk_x, y=chk_y, size=chk_size,
        buttonStyle="check",
        borderColor=FIELD_BORDER,
        fillColor=colors.white,
        textColor=colors.black,
        forceBorder=True,
    )
    cx += chk_w

    note_w = COL_WIDTHS[6]
    pad = 1.5
    c.acroForm.textfield(
        name=f"note_p{page_idx:02d}_{_safe_id(tf)}_r{row_idx:03d}",
        x=cx + pad, y=y_bot + pad,
        width=note_w - 2 * pad, height=ROW_H - 2 * pad,
        borderColor=FIELD_BORDER, fillColor=FIELD_BG,
        textColor=colors.black,
        fontName=FONT_BODY, fontSize=8,
        forceBorder=True, maxlen=120,
    )
    return y_bot


def _capacity(page_size: tuple[float, float], y_table_top: float) -> int:
    """Maximum number of data rows that fit on one page."""
    y_avail = y_table_top - PAGE_MARGIN
    return max(0, int((y_avail - HEADER_ROW_H) / ROW_H))


def _build_page(
    c: pdfcanvas.Canvas, page: PageSpec, page_size: tuple[float, float], page_idx: int
) -> int:
    """Render one page; return the number of data rows actually drawn."""
    _draw_page_header(c, page, page_size)

    x0 = PAGE_MARGIN
    y_title = page_size[1] - PAGE_MARGIN - FONT_TITLE_SIZE
    y_table_top = y_title - 10

    if not page.rows:
        c.setFont(FONT_BODY, 10)
        c.setFillColor(colors.gray)
        c.drawString(PAGE_MARGIN, y_table_top - 12, "(no rows)")
        return 0

    capacity = _capacity(page_size, y_table_top)
    n = min(len(page.rows), capacity)

    y_after_header = _draw_table_header(c, x0, y_table_top)
    y = y_after_header
    for i in range(n):
        cells = _row_cells(page.rows[i])
        y = _draw_row(c, i, y, x0, cells, page_idx, page.tf)
    _draw_grid(c, x0, y_table_top, y)
    return n


# ---------- public entry point ----------

class PdfRenderer:
    """Renders a Pro100 forward report PDF from a sequence of PageSpecs."""

    def __init__(self, page_size: tuple[float, float] = A4) -> None:
        self.page_size = page_size

    def render(self, out_pdf: Path, pages: Sequence[PageSpec]) -> RenderResult:
        out_pdf.parent.mkdir(parents=True, exist_ok=True)
        c = pdfcanvas.Canvas(str(out_pdf), pagesize=self.page_size)
        c.setTitle("Pro100 forward results")

        rows_per_page: list[int] = []
        for i, page in enumerate(pages):
            if i > 0:
                c.showPage()
            rows_drawn = _build_page(c, page, self.page_size, page_idx=i + 1)
            rows_per_page.append(rows_drawn)

        c.save()

        return RenderResult(
            pdf_path=out_pdf,
            n_pages=len(pages),
            n_rows_per_page=tuple(rows_per_page),
            fields_per_page=tuple(2 * n for n in rows_per_page),
        )

    @staticmethod
    def page_capacity(page_size: tuple[float, float] = A4) -> int:
        """How many data rows fit on one A4 portrait page (excluding the
        title header but including the table header)."""
        y_title = page_size[1] - PAGE_MARGIN - FONT_TITLE_SIZE
        y_table_top = y_title - 10
        return _capacity(page_size, y_table_top)
