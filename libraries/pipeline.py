"""
Core OCR pipeline with dependency injection.

Design principle: every parameter that can vary is injectable, so any stage
can be replaced with a mock in tests — no ML model loading required.

    engine   — anything with  read_image(img: ndarray) -> str
    cleaner  — any callable   (str) -> str
    analyzer — any callable   (str, **kwargs) -> list[dict]

Usage:
    from pipeline import run_pipeline, resize_if_large, images_from_bytes
    from ocr.paddle import PaddleEngine

    result = run_pipeline(images_from_bytes(data, ".jpg"), PaddleEngine())
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Callable, Dict, Iterator, List, Optional

import cv2
import numpy as np

# Ensure sibling library modules (cleaning, japanseanalyzer) are importable
# when pipeline.py is used from outside the libraries/ directory.
_LIB_DIR = str(Path(__file__).parent)
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from cleaning import normalize_ocr_ja
from japanseanalyzer import analyze_text

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_OCR_SIDE = 1100  # longest image side passed to the OCR engine (pixels)

SUPPORTED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}


# ---------------------------------------------------------------------------
# Image helpers
# ---------------------------------------------------------------------------

def resize_if_large(img: np.ndarray, max_side: int = MAX_OCR_SIDE) -> np.ndarray:
    """
    Downscale image so its longest side is at most max_side pixels.
    Uses INTER_AREA (best quality for shrinking). No-op if already small enough.
    """
    if max_side < 1 or img.ndim < 2 or not all(img.shape[:2]):
        raise ValueError("Image dimensions and max_side must be positive")
    h, w = img.shape[:2]
    if max(h, w) <= max_side:
        return img
    scale = max_side / max(h, w)
    return cv2.resize(
        img, (max(1, int(w * scale)), max(1, int(h * scale))), interpolation=cv2.INTER_AREA
    )


# ---------------------------------------------------------------------------
# Image source factories
# ---------------------------------------------------------------------------

def images_from_bytes(
    data: bytes,
    suffix: str,
    pdf_dpi: int = 120,
) -> Iterator[np.ndarray]:
    """
    Decode raw file bytes into an iterator of BGR ndarrays.
    Handles both images and scanned PDFs.
    Note: digital PDFs with an embedded text layer are handled upstream
    in ocr_pipeline.py (they skip OCR entirely).
    """
    from pdf_utils import pdf_bytes_to_images

    suffix = suffix.lower()
    if suffix == ".pdf":
        yield from pdf_bytes_to_images(data, dpi=pdf_dpi)
    elif suffix in SUPPORTED_IMAGE_EXTS:
        if not data:
            raise ValueError("The uploaded image is empty")
        arr = np.frombuffer(data, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Could not decode image data")
        yield img
    else:
        raise ValueError(
            f"Unsupported file type '{suffix}'. "
            "Supported: .pdf, .jpg, .jpeg, .png, .bmp, .tiff, .webp"
        )


def images_from_file(
    path: Path,
    pdf_dpi: int = 120,
) -> Iterator[np.ndarray]:
    """
    Load a file from disk into an iterator of BGR ndarrays.
    Handles both images and scanned PDFs.
    """
    from pdf_utils import pdf_path_to_images

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        yield from pdf_path_to_images(path, dpi=pdf_dpi)
    elif suffix in SUPPORTED_IMAGE_EXTS:
        img = cv2.imread(str(path))
        if img is None:
            raise ValueError(f"Could not read image: {path}")
        yield img
    else:
        raise ValueError(
            f"Unsupported file type '{suffix}'. "
            "Supported: .pdf, .jpg, .jpeg, .png, .bmp, .tiff, .webp"
        )


# ---------------------------------------------------------------------------
# Core pipeline (dependency-injected)
# ---------------------------------------------------------------------------

def run_pipeline(
    images: Iterator[np.ndarray],
    engine,
    cleaner: Callable[[str], str] = normalize_ocr_ja,
    analyzer: Callable = analyze_text,
    max_vocab_words: Optional[int] = None,
    db_path: Optional[str] = None,
    target_lang: str = "en",
) -> Dict:
    """
    Run the full pipeline: OCR → clean → analyze vocab → translate.

    Parameters
    ----------
    images         : iterator of BGR ndarrays (one per page / image)
    engine         : object with  read_image(img: ndarray) -> str
    cleaner        : text normalizer — default normalize_ocr_ja
    analyzer       : vocab extractor — default analyze_text
    max_vocab_words: optional cap on words passed to analyzer
    db_path        : optional path to a local jamdict.db
    target_lang    : BCP-47 code for definition language ("en" = no translation)

    Returns
    -------
    {"vocabulary": list[dict]}  where each dict has word/reading/pos/english
    """
    raw_parts: List[str] = []
    for img in images:
        img = resize_if_large(img)
        raw_parts.append(engine.read_image(img))

    raw_text = "\n".join(raw_parts)
    cleaned = cleaner(raw_text)
    vocabulary = analyzer(cleaned, max_words=max_vocab_words, db_path=db_path)

    if target_lang != "en":
        from translator import translate_vocabulary
        translate_vocabulary(vocabulary, target_lang)

    return {"vocabulary": vocabulary, "source_text": raw_text}
