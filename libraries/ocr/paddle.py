"""
PaddleOCR 2.x engine wrapper.

Lazy-loads the model on first use. Safe to import with zero cost.

Quick test (runs PaddleOCR on the bundled testimage.png):
    python libraries/ocr/paddle.py
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np

# PADDLE_OCR_DIR env var points to the pre-baked model directory in Docker
# (/app/models/paddleocr). Falls back to the standard ~/.cache/paddleocr for
# local development where models are auto-downloaded by PaddleOCR itself.
_MODEL_DIR = os.environ.get("PADDLE_OCR_DIR") or os.path.join(
    os.environ.get("HOME", "/root"), ".cache", "paddleocr"
)


class PaddleEngine:
    """PaddleOCR 2.x — Japanese OCR engine, lazy-loaded on first use."""

    def __init__(self) -> None:
        self._ocr = None

    def _load(self) -> None:
        if self._ocr is not None:
            return
        from paddleocr import PaddleOCR
        self._ocr = PaddleOCR(
            use_angle_cls=True,
            lang="japan",
            use_gpu=False,
            show_log=False,
            det_model_dir=os.path.join(_MODEL_DIR, "det"),
            rec_model_dir=os.path.join(_MODEL_DIR, "rec"),
            cls_model_dir=os.path.join(_MODEL_DIR, "cls"),
        )

    def warmup(self) -> None:
        """Pre-load the model (call at server startup to avoid cold-start delay)."""
        print("[PaddleEngine] Loading PaddleOCR model…")
        self._load()
        print("[PaddleEngine] Ready.")

    def read_image(self, img: np.ndarray) -> str:
        """
        Run OCR on a BGR ndarray.  Returns extracted text as a single string.
        Image must already be resized to a reasonable resolution before calling.
        """
        self._load()
        result = self._ocr.ocr(img, cls=True)
        if not result or result[0] is None:
            return ""
        return "\n".join(line[1][0] for line in result[0] if line and line[1])


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
        engine = PaddleEngine()
        print("Running PaddleOCR on testimage.png …")
        text = engine.read_image(img)
        print("Result:", repr(text))
