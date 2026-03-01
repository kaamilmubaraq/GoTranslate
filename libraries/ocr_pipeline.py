"""
ocr_pipeline.py — Public API shim (backward-compatible).

All logic lives in the sub-modules:
  ocr/paddle.py    → PaddleEngine
  ocr/yomitoku.py  → YomitokuEngine
  pdf_utils.py     → PDF text extraction and page rendering
  pipeline.py      → run_pipeline (dependency-injected core)

This file exposes the same API the backend has always used:
  process_bytes(data, suffix, engine, ...)
  process_file(path, engine, ...)
  warmup()
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, Optional, Union

# Ensure this libraries/ directory is importable as a root for sibling modules.
_THIS_DIR = str(Path(__file__).parent)
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from ocr.paddle import PaddleEngine
from ocr.yomitoku import YomitokuEngine
from pdf_utils import extract_text_layer, pdf_bytes_to_images, pdf_path_to_images
from pipeline import run_pipeline, images_from_bytes, images_from_file
from cleaning import normalize_ocr_ja
from japanseanalyzer import analyze_text

# ── One singleton per engine, shared across all requests ────────────────────
_paddle = PaddleEngine()
_yomitoku = YomitokuEngine()


def _get_engine(name: str):
    return _yomitoku if name == "yomitoku" else _paddle


# ── Public API ───────────────────────────────────────────────────────────────

def warmup() -> None:
    """Pre-load PaddleOCR at server startup to avoid the cold-start penalty."""
    _paddle.warmup()


def process_bytes(
    data: bytes,
    suffix: str,
    engine: str = "paddleocr",
    pdf_dpi: int = 120,
    max_vocab_words: Optional[int] = None,
    db_path: Optional[str] = None,
) -> Dict:
    """
    Run the full OCR + Japanese analysis pipeline on raw file bytes.
    No temp file is written — all processing happens in memory.

    Parameters
    ----------
    data       : raw bytes of the file
    suffix     : file extension including dot, e.g. ".jpg" or ".pdf"
    engine     : "paddleocr" (normal/fast) or "yomitoku" (advanced/accurate)
    pdf_dpi    : render resolution for PDF pages (120 is fast; 150 is sharper)
    """
    suffix = suffix.lower()
    engine = engine.lower()

    if suffix == ".pdf":
        # Fast path: use the embedded text layer if the PDF has one.
        text_layer = extract_text_layer(data)
        if text_layer is not None:
            cleaned = normalize_ocr_ja(text_layer)
            vocabulary = analyze_text(cleaned, max_words=max_vocab_words, db_path=db_path)
            return {"vocabulary": vocabulary}
        # Slow path: scanned PDF — render pages and run OCR.
        image_source = pdf_bytes_to_images(data, dpi=pdf_dpi)
    else:
        image_source = images_from_bytes(data, suffix)

    return run_pipeline(
        image_source,
        _get_engine(engine),
        max_vocab_words=max_vocab_words,
        db_path=db_path,
    )


def process_file(
    file_path: Union[str, Path],
    engine: str = "paddleocr",
    pdf_dpi: int = 120,
    max_vocab_words: Optional[int] = None,
    db_path: Optional[str] = None,
) -> Dict:
    """
    Run the full OCR + Japanese analysis pipeline on an image or PDF file path.

    Returns
    -------
    dict with key:
        vocabulary : list of dicts  (word, reading, pos, english)
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    suffix = file_path.suffix.lower()
    engine = engine.lower()

    if suffix == ".pdf":
        pdf_data = file_path.read_bytes()
        text_layer = extract_text_layer(pdf_data)
        if text_layer is not None:
            cleaned = normalize_ocr_ja(text_layer)
            vocabulary = analyze_text(cleaned, max_words=max_vocab_words, db_path=db_path)
            return {"vocabulary": vocabulary}
        image_source = pdf_path_to_images(file_path, dpi=pdf_dpi)
    else:
        image_source = images_from_file(file_path, pdf_dpi=pdf_dpi)

    return run_pipeline(
        image_source,
        _get_engine(engine),
        max_vocab_words=max_vocab_words,
        db_path=db_path,
    )
