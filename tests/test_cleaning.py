"""
Unit tests for libraries/cleaning.py

All tests are pure — no model loading, no I/O.
Run with: pytest tests/test_cleaning.py
"""
from cleaning import normalize_ocr_ja


def test_empty_string():
    assert normalize_ocr_ja("") == ""


def test_none_like_empty():
    # Function accepts empty string — just verify it doesn't crash
    assert normalize_ocr_ja("   ") == ""


def test_nfkc_full_width_to_ascii():
    # Full-width ASCII → normal ASCII via NFKC
    assert normalize_ocr_ja("Ａ１") == "A1"


def test_nfkc_half_width_katakana():
    # Half-width katakana → full-width katakana
    assert normalize_ocr_ja("ｱｲｳ") == "アイウ"


def test_latin_gloss_stripped_no_separator():
    # "色color" → "色"
    assert normalize_ocr_ja("色color") == "色"


def test_latin_gloss_stripped_with_dash():
    # "スポットライト-spotlight" → "スポットライト"
    result = normalize_ocr_ja("スポットライト-spotlight")
    assert result == "スポットライト"


def test_latin_gloss_stripped_after_kanji():
    # "漢字kanji" → "漢字"
    assert normalize_ocr_ja("漢字kanji") == "漢字"


def test_standalone_latin_not_stripped():
    # Plain Latin with no Japanese lookbehind is kept as-is
    result = normalize_ocr_ja("hello world")
    assert "hello" in result
    assert "world" in result


def test_whitespace_collapsed():
    assert normalize_ocr_ja("日本  語") == "日本 語"


def test_leading_trailing_whitespace_stripped():
    assert normalize_ocr_ja("  日本語  ") == "日本語"


def test_control_chars_removed():
    # Null byte and other control chars should be dropped
    assert "\x00" not in normalize_ocr_ja("日本\x00語")


def test_regular_japanese_unchanged():
    text = "次の定積分を求めなさい"
    result = normalize_ocr_ja(text)
    assert "定積分" in result
    assert "求め" in result
