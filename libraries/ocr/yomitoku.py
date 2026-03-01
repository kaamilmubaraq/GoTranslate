"""
yomitoku engine wrapper (DBNet detector + PARSeq recognizer).

Lazy-loads the model on first use. Safe to import with zero cost.
The Windows UTF-8 builtins.open patch is applied only when the model is
actually loaded (inside _load), not at import time.

Quick test (runs yomitoku on the bundled testimage.png):
    python libraries/ocr/yomitoku.py
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np

# Config YAMLs live in libraries/ (one level up from this ocr/ package)
_LIB_DIR = str(Path(__file__).parent.parent)
_CFG_DETECTOR = str(Path(_LIB_DIR) / "cfg_detector.yaml")
_CFG_RECOGNIZER = str(Path(_LIB_DIR) / "cfg_recognizer.yaml")


def _apply_utf8_open_patch() -> None:
    """
    Patch builtins.open to default to UTF-8 on Windows.
    yomitoku reads Japanese charset files that require UTF-8;
    Windows defaults to cp1252 which causes UnicodeDecodeError.
    Idempotent — safe to call multiple times.
    """
    import builtins

    if getattr(builtins.open, "_utf8_patched", False):
        return

    _original = builtins.open

    def _utf8_open(file, mode="r", *args, **kwargs):
        if "r" in mode and "b" not in mode and "encoding" not in kwargs:
            kwargs["encoding"] = "utf-8"
        return _original(file, mode, *args, **kwargs)

    _utf8_open._utf8_patched = True
    builtins.open = _utf8_open


class YomitokuEngine:
    """yomitoku OCR engine — Japanese-specialised, lazy-loaded on first use."""

    def __init__(self) -> None:
        self._ocr = None

    def _load(self) -> None:
        if self._ocr is not None:
            return
        _apply_utf8_open_patch()
        from yomitoku import OCR
        self._ocr = OCR(
            configs={
                "text_detector":   {"path_cfg": _CFG_DETECTOR},
                "text_recognizer": {"path_cfg": _CFG_RECOGNIZER},
            },
            visualize=False,
            device="cpu",
        )

    def warmup(self) -> None:
        """Pre-load the model (call at server startup to avoid cold-start delay)."""
        print("[YomitokuEngine] Loading yomitoku model…")
        self._load()
        print("[YomitokuEngine] Ready.")

    def read_image(self, img: np.ndarray) -> str:
        """
        Run OCR on a BGR ndarray.  Returns extracted text as a single string.
        Image must already be resized to a reasonable resolution before calling.
        """
        self._load()
        results, _ = self._ocr(img)
        return "".join(word.content for word in results.words)


# ---------------------------------------------------------------------------
# Quick manual test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import cv2

    img_path = Path(__file__).parent.parent / "testimage.png"
    if not img_path.exists():
        print(f"testimage.png not found at {img_path}")
    else:
        img = cv2.imread(str(img_path))
        engine = YomitokuEngine()
        print("Running yomitoku on testimage.png …")
        text = engine.read_image(img)
        print("Result:", repr(text))
