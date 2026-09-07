"""
PDF utilities — text layer extraction and page-to-image rendering.

All functions are pure / stateless and can be tested independently.
No OCR model is required; only pymupdf (fitz) and opencv.
"""
from __future__ import annotations

from pathlib import Path
from typing import Generator, Optional

import cv2
import numpy as np

# Hard cap on pages to process — prevents multi-minute waits on long PDFs.
MAX_PDF_PAGES = 20


def extract_text_layer(data: bytes) -> Optional[str]:
    """
    Fast path: pull text directly from a PDF's embedded text layer.

    Returns the combined text if the PDF contains real text on all processed
    of pages, or None if the PDF appears to be a scanned image document
    (meaning OCR will be needed).

    A page is considered "text" if it yields at least 20 characters.
    If any page falls below that threshold, returns None to avoid losing pages.
    """
    import fitz

    doc = fitz.open(stream=data, filetype="pdf")
    try:
        parts: list[str] = []
        ocr_needed = 0
        total = min(doc.page_count, MAX_PDF_PAGES)
        for page in doc:
            if len(parts) + ocr_needed >= total:
                break
            text = page.get_text().strip()
            if len(text) >= 20:
                parts.append(text)
            else:
                ocr_needed += 1
        if ocr_needed:
            return None
        return "\n".join(parts) if parts else None
    finally:
        doc.close()


def pdf_bytes_to_images(data: bytes, dpi: int = 120) -> Generator[np.ndarray, None, None]:
    """Yield cv2 BGR arrays from PDF bytes — no temp file needed."""
    import fitz

    doc = fitz.open(stream=data, filetype="pdf")
    yield from _fitz_doc_to_images(doc, dpi)


def pdf_path_to_images(path: Path, dpi: int = 120) -> Generator[np.ndarray, None, None]:
    """Yield cv2 BGR arrays from a PDF file path, one page at a time."""
    import fitz

    doc = fitz.open(str(path))
    yield from _fitz_doc_to_images(doc, dpi)


def _fitz_doc_to_images(doc, dpi: int) -> Generator[np.ndarray, None, None]:
    """Core renderer: converts each fitz page to a cv2 BGR ndarray."""
    import fitz

    mat = fitz.Matrix(dpi / 72, dpi / 72)
    try:
        for i, page in enumerate(doc):
            if i >= MAX_PDF_PAGES:
                break
            pix = page.get_pixmap(matrix=mat, alpha=False, colorspace=fitz.csRGB)
            arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, 3
            )
            yield cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    finally:
        doc.close()
