"""
Shared fixtures and configuration for the GoTranslate test suite.

Fast tests (no marks):  pytest -m "not slow"       # runs in seconds
All tests:              pytest                      # loads ML models too
Single engine test:     pytest tests/test_ocr_paddle.py -m slow -s
"""
import sys
from pathlib import Path

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Path setup — makes all libraries/ modules importable.
# (pyproject.toml also sets pythonpath = ["libraries"] for pytest, but
#  adding it here ensures imports work when conftest is loaded directly.)
# ---------------------------------------------------------------------------
_LIBS = Path(__file__).parent.parent / "libraries"
if str(_LIBS) not in sys.path:
    sys.path.insert(0, str(_LIBS))


# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------

def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "slow: tests that load ML models — skip with: pytest -m 'not slow'",
    )


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def paddle_engine():
    """PaddleEngine singleton — loaded once for the whole test session."""
    from ocr.paddle import PaddleEngine
    engine = PaddleEngine()
    engine.warmup()
    return engine


@pytest.fixture(scope="session")
def yomitoku_engine():
    """YomitokuEngine singleton — loaded once for the whole test session."""
    from ocr.yomitoku import YomitokuEngine
    engine = YomitokuEngine()
    engine.warmup()
    return engine


@pytest.fixture
def blank_image():
    """A 100×300 black BGR image — useful for smoke-testing OCR engines."""
    return np.zeros((100, 300, 3), dtype=np.uint8)


@pytest.fixture
def test_image_path():
    """Path to the bundled testimage.png in libraries/."""
    path = _LIBS / "testimage.png"
    if not path.exists():
        pytest.skip("testimage.png not found in libraries/")
    return path
