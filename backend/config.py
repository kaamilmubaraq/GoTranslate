"""
GoTranslate — backend configuration
Edit this file to change runtime behaviour.
An environment variable with the same name always overrides the value here.
"""

import os

# ── OCR engine ────────────────────────────────────────────────────────────────
# Which OCR model to use for image/scanned-PDF processing.
#
#   "paddleocr"  — default. Faster, ~10× lighter Docker image, good accuracy
#                  on standard horizontal printed text.
#
#   "yomitoku"   — slower, heavier (needs PyTorch ~1 GB). Better on complex
#                  layouts, vertical Japanese text, and handwriting.
#
# To override at runtime without editing this file:
#   docker run -e OCR_ENGINE=yomitoku ...
# ─────────────────────────────────────────────────────────────────────────────
OCR_ENGINE: str = os.environ.get("OCR_ENGINE", "paddleocr")
