"""
Tests for libraries/ocr/yomitoku.py  (DBNet + PARSeq engine)

Marked @pytest.mark.slow because they load the yomitoku model (~30 s on first run).

Run just these:
    pytest tests/test_ocr_yomitoku.py -m slow -s

The -s flag lets you see the extracted text printed to stdout.
"""
import numpy as np
import pytest

from ocr.yomitoku import YomitokuEngine


@pytest.mark.slow
def test_read_blank_image_returns_string(yomitoku_engine):
    """A completely black image should return an empty string, not crash."""
    img = np.zeros((100, 300, 3), dtype=np.uint8)
    result = yomitoku_engine.read_image(img)
    assert isinstance(result, str)


@pytest.mark.slow
def test_read_real_image_returns_text(yomitoku_engine, test_image_path):
    """testimage.png should produce non-empty Japanese text."""
    import cv2
    img = cv2.imread(str(test_image_path))
    assert img is not None, "Could not load testimage.png"
    result = yomitoku_engine.read_image(img)
    print(f"\n[yomitoku result]\n{result!r}\n")
    assert isinstance(result, str)
    assert len(result) > 0, "Expected non-empty OCR output on testimage.png"


@pytest.mark.slow
def test_warmup_is_idempotent(yomitoku_engine):
    """Calling warmup() on an already-loaded engine must not crash."""
    yomitoku_engine.warmup()


@pytest.mark.slow
def test_fresh_instance_loads_on_demand():
    """A new YomitokuEngine should not load until read_image is called."""
    engine = YomitokuEngine()
    assert engine._ocr is None, "Model should not be loaded before first use"
    img = np.zeros((50, 50, 3), dtype=np.uint8)
    engine.read_image(img)
    assert engine._ocr is not None, "Model should be loaded after first use"
