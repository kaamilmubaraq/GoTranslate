"""
Tests for libraries/pdf_utils.py

Uses pymupdf to create minimal PDFs in memory — no model loading, runs fast.
Run with: pytest tests/test_pdf_utils.py
"""
import io

import numpy as np
import pytest


def _make_text_pdf(text: str) -> bytes:
    """Create a minimal single-page PDF with real embedded text."""
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 100), text, fontsize=12)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _make_blank_pdf(n_pages: int = 1) -> bytes:
    """Create a PDF with blank (image-like, no text) pages."""
    import fitz
    doc = fitz.open()
    for _ in range(n_pages):
        doc.new_page()
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# extract_text_layer
# ---------------------------------------------------------------------------

def test_extract_text_layer_digital_pdf():
    from pdf_utils import extract_text_layer
    # A PDF with real text should return that text
    data = _make_text_pdf("次の定積分を求めなさい。直交行列の問題。")
    result = extract_text_layer(data)
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


def test_extract_text_layer_scanned_pdf():
    from pdf_utils import extract_text_layer
    # A PDF with blank pages (no text layer) should return None
    data = _make_blank_pdf(n_pages=2)
    result = extract_text_layer(data)
    assert result is None


def test_extract_text_layer_returns_none_for_mostly_blank():
    from pdf_utils import extract_text_layer
    # If most pages have no text, returns None even if some pages have text
    import fitz, io
    doc = fitz.open()
    # 1 page with text, 3 blank pages → more than half blank → None
    page = doc.new_page()
    page.insert_text((50, 100), "日本語のテスト文章です。これはサンプルです。", fontsize=12)
    for _ in range(3):
        doc.new_page()
    buf = io.BytesIO()
    doc.save(buf)
    data = buf.getvalue()
    result = extract_text_layer(data)
    assert result is None


# ---------------------------------------------------------------------------
# pdf_bytes_to_images
# ---------------------------------------------------------------------------

def test_pdf_bytes_to_images_yields_ndarrays():
    from pdf_utils import pdf_bytes_to_images
    data = _make_blank_pdf(n_pages=2)
    images = list(pdf_bytes_to_images(data, dpi=72))
    assert len(images) == 2
    for img in images:
        assert isinstance(img, np.ndarray)
        assert img.ndim == 3
        assert img.shape[2] == 3  # BGR channels


def test_pdf_bytes_to_images_respects_dpi():
    from pdf_utils import pdf_bytes_to_images
    data = _make_blank_pdf()
    low = list(pdf_bytes_to_images(data, dpi=72))[0]
    high = list(pdf_bytes_to_images(data, dpi=144))[0]
    # Higher DPI → larger image
    assert high.shape[0] > low.shape[0]
    assert high.shape[1] > low.shape[1]


# ---------------------------------------------------------------------------
# MAX_PDF_PAGES cap
# ---------------------------------------------------------------------------

def test_page_count_capped_at_max():
    from pdf_utils import pdf_bytes_to_images, MAX_PDF_PAGES
    # Create a PDF with more pages than the cap
    n = MAX_PDF_PAGES + 5
    data = _make_blank_pdf(n_pages=n)
    images = list(pdf_bytes_to_images(data, dpi=36))
    assert len(images) == MAX_PDF_PAGES
