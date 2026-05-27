"""Visual QC support: rasterize PDF pages to PNG via pypdfium2.

Used to satisfy the CLAUDE.md 'Подготовка PDF-презентаций' rule --
render the pages that were changed and visually inspect them for
overlap / overflow / truncation. The adapter is read-only over the
PDF -- it does not modify the document.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RenderedPage:
    page_index: int  # 0-based
    png_path: Path
    width_px: int
    height_px: int


def render_pages_to_png(
    pdf_path: Path,
    out_dir: Path,
    page_indices: Sequence[int] | None = None,
    scale: float = 2.0,
) -> list[RenderedPage]:
    """Rasterize selected pages of a PDF to PNG files.

    Args:
      pdf_path: source PDF.
      out_dir: directory to drop PNGs into (created if missing).
      page_indices: 0-based indices to render; None means all pages.
      scale: pypdfium2 scale factor (2.0 -> ~144 DPI on A4).

    Returns one RenderedPage per page actually rendered.
    """
    import pypdfium2 as pdfium

    out_dir.mkdir(parents=True, exist_ok=True)
    rendered: list[RenderedPage] = []
    pdf = pdfium.PdfDocument(str(pdf_path))
    try:
        total = len(pdf)
        targets = (
            list(range(total)) if page_indices is None else list(page_indices)
        )
        for idx in targets:
            if idx < 0 or idx >= total:
                continue
            page = pdf[idx]
            try:
                image = page.render(scale=scale).to_pil()
                png_path = out_dir / f"page_{idx + 1:03d}.png"
                image.save(png_path, format="PNG")
                rendered.append(
                    RenderedPage(
                        page_index=idx,
                        png_path=png_path,
                        width_px=image.width,
                        height_px=image.height,
                    )
                )
            finally:
                page.close()
    finally:
        pdf.close()
    return rendered


class PdfQC:
    """Thin object wrapper for testing convenience and future extension."""

    def __init__(self, scale: float = 2.0) -> None:
        self.scale = scale

    def render(
        self,
        pdf_path: Path,
        out_dir: Path,
        page_indices: Sequence[int] | None = None,
    ) -> list[RenderedPage]:
        return render_pages_to_png(
            pdf_path=pdf_path, out_dir=out_dir,
            page_indices=page_indices, scale=self.scale,
        )

    def cleanup(self, rendered: Sequence[RenderedPage]) -> None:
        """Delete the PNG files produced by a prior render() call."""
        for r in rendered:
            try:
                r.png_path.unlink(missing_ok=True)
            except OSError:
                pass
