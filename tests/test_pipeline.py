"""
Tests for libraries/pipeline.py

Uses a MockEngine — zero ML model loading.  All tests run in milliseconds.
Run with: pytest tests/test_pipeline.py
"""
import numpy as np
import pytest

from pipeline import run_pipeline, resize_if_large, images_from_bytes, MAX_OCR_SIDE


# ---------------------------------------------------------------------------
# Mock engine — stands in for PaddleEngine / YomitokuEngine
# ---------------------------------------------------------------------------

class MockEngine:
    """Deterministic fake OCR engine for testing the pipeline logic."""

    def __init__(self, text: str = "日本語のテスト文章"):
        self.text = text
        self.call_count = 0

    def read_image(self, img: np.ndarray) -> str:
        self.call_count += 1
        return self.text

    def warmup(self) -> None:
        pass


# ---------------------------------------------------------------------------
# resize_if_large
# ---------------------------------------------------------------------------

def test_resize_downscales_large_image():
    img = np.zeros((2000, 1500, 3), dtype=np.uint8)
    result = resize_if_large(img, max_side=1100)
    assert max(result.shape[:2]) <= 1100


def test_resize_noop_on_small_image():
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    result = resize_if_large(img, max_side=1100)
    assert result.shape == (100, 100, 3)


def test_resize_preserves_aspect_ratio():
    img = np.zeros((2000, 1000, 3), dtype=np.uint8)  # 2:1 ratio
    result = resize_if_large(img, max_side=1000)
    h, w = result.shape[:2]
    assert abs(h / w - 2.0) < 0.01, "Aspect ratio not preserved"


def test_resize_custom_max_side():
    img = np.zeros((500, 500, 3), dtype=np.uint8)
    result = resize_if_large(img, max_side=200)
    assert max(result.shape[:2]) <= 200


# ---------------------------------------------------------------------------
# run_pipeline — with mock engine
# ---------------------------------------------------------------------------

def test_run_pipeline_returns_vocabulary_key():
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    result = run_pipeline(iter([img]), MockEngine())
    assert "vocabulary" in result
    assert isinstance(result["vocabulary"], list)


def test_run_pipeline_calls_engine_once_per_image():
    engine = MockEngine()
    images = [np.zeros((50, 50, 3), dtype=np.uint8) for _ in range(3)]
    run_pipeline(iter(images), engine)
    assert engine.call_count == 3


def test_run_pipeline_with_real_japanese_text():
    """End-to-end: mock engine returns real Japanese → analyzer extracts vocab."""
    engine = MockEngine("勉強して日本語を学ぶ")
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    result = run_pipeline(iter([img]), engine)
    assert len(result["vocabulary"]) > 0
    for entry in result["vocabulary"]:
        assert "word" in entry
        assert "reading" in entry
        assert "pos" in entry
        assert "english" in entry


def test_run_pipeline_empty_ocr_output():
    """If OCR returns nothing, vocabulary should be empty — not an error."""
    engine = MockEngine("")
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    result = run_pipeline(iter([img]), engine)
    assert result["vocabulary"] == []


def test_run_pipeline_injectable_cleaner():
    """Custom cleaner is called instead of the default normalize_ocr_ja."""
    calls = []

    def spy_cleaner(text: str) -> str:
        calls.append(text)
        return text

    engine = MockEngine("日本語")
    img = np.zeros((50, 50, 3), dtype=np.uint8)
    run_pipeline(iter([img]), engine, cleaner=spy_cleaner)
    assert len(calls) == 1


def test_run_pipeline_injectable_analyzer():
    """Custom analyzer is called with cleaned text."""
    received = []

    def spy_analyzer(text, **kwargs):
        received.append(text)
        return []

    engine = MockEngine("日本語")
    img = np.zeros((50, 50, 3), dtype=np.uint8)
    run_pipeline(iter([img]), engine, analyzer=spy_analyzer)
    assert len(received) == 1


def test_run_pipeline_resizes_large_image():
    """Engine should never receive an image larger than MAX_OCR_SIDE."""
    received_shapes = []

    class ShapeCapture:
        def read_image(self, img):
            received_shapes.append(img.shape)
            return ""
        def warmup(self): pass

    big_img = np.zeros((3000, 2000, 3), dtype=np.uint8)
    run_pipeline(iter([big_img]), ShapeCapture())
    assert received_shapes, "Engine was never called"
    h, w = received_shapes[0][:2]
    assert max(h, w) <= MAX_OCR_SIDE


# ---------------------------------------------------------------------------
# images_from_bytes
# ---------------------------------------------------------------------------

def test_images_from_bytes_decodes_png():
    import cv2, io
    img = np.zeros((50, 50, 3), dtype=np.uint8)
    _, buf = cv2.imencode(".png", img)
    images = list(images_from_bytes(buf.tobytes(), ".png"))
    assert len(images) == 1
    assert isinstance(images[0], np.ndarray)


def test_images_from_bytes_invalid_suffix_raises():
    with pytest.raises(ValueError, match="Unsupported file type"):
        list(images_from_bytes(b"data", ".xyz"))


def test_images_from_bytes_invalid_image_data_raises():
    with pytest.raises((ValueError, Exception)):
        list(images_from_bytes(b"not an image", ".jpg"))

def test_resize_extremely_narrow_image():
    img = np.zeros((5000, 1, 3), dtype=np.uint8)
    result = resize_if_large(img)
    assert result.shape == (1100, 1, 3)
