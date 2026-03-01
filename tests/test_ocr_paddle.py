"""
Tests for libraries/ocr/paddle.py  (PaddleOCR 2.x engine)

Marked @pytest.mark.slow because they load the PaddleOCR model.

Run just these:
    pytest tests/test_ocr_paddle.py -m slow -s

The -s flag lets you see the extracted text printed to stdout.
"""
import numpy as np
import pytest

from ocr.paddle import PaddleEngine


@pytest.mark.slow
def test_read_blank_image_returns_string(paddle_engine):
    """A completely black image should return an empty string, not crash."""
    img = np.zeros((100, 300, 3), dtype=np.uint8)
    result = paddle_engine.read_image(img)
    assert isinstance(result, str)


@pytest.mark.slow
def test_read_real_image_returns_text(paddle_engine, test_image_path):
    """testimage.png should produce non-empty Japanese text."""
    import cv2
    img = cv2.imread(str(test_image_path))
    assert img is not None, "Could not load testimage.png"
    result = paddle_engine.read_image(img)
    print(f"\n[PaddleOCR result]\n{result!r}\n")
    assert isinstance(result, str)
    assert len(result) > 0, "Expected non-empty OCR output on testimage.png"


@pytest.mark.slow
def test_warmup_is_idempotent(paddle_engine):
    """Calling warmup() on an already-loaded engine must not crash."""
    paddle_engine.warmup()  # model already loaded by fixture — should be a no-op


@pytest.mark.slow
def test_multiple_calls_consistent(paddle_engine, test_image_path):
    """Two calls on the same image should return the same result."""
    import cv2
    img = cv2.imread(str(test_image_path))
    r1 = paddle_engine.read_image(img)
    r2 = paddle_engine.read_image(img)
    assert r1 == r2


@pytest.mark.slow
def test_fresh_instance_loads_on_demand():
    """A new PaddleEngine should not load until read_image is called."""
    engine = PaddleEngine()
    assert engine._ocr is None, "Model should not be loaded before first use"
    img = np.zeros((50, 50, 3), dtype=np.uint8)
    engine.read_image(img)
    assert engine._ocr is not None, "Model should be loaded after first use"
