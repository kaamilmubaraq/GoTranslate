"""
Unit tests for libraries/japanseanalyzer.py

Uses MeCab (fugashi) and Jamdict — loads in ~1 s, no ML model needed.
Run with: pytest tests/test_analyzer.py
"""
from japanseanalyzer import (
    analyze_text,
    should_keep_token,
    is_japanese_token,
    extract_reading_hiragana,
    lookup_english_meanings,
    get_tagger,
    get_jamdict,
)


# ---------------------------------------------------------------------------
# analyze_text — integration of all steps
# ---------------------------------------------------------------------------

def test_analyze_returns_list():
    result = analyze_text("日本語を勉強する")
    assert isinstance(result, list)


def test_analyze_empty_returns_empty():
    assert analyze_text("") == []
    assert analyze_text("   ") == []


def test_analyze_result_has_required_keys():
    result = analyze_text("勉強する")
    assert len(result) > 0
    for entry in result:
        assert "word" in entry
        assert "reading" in entry
        assert "pos" in entry
        assert "english" in entry


def test_analyze_english_is_list():
    result = analyze_text("勉強する")
    for entry in result:
        assert isinstance(entry["english"], list)


def test_analyze_deduplication():
    # Same word repeated — should appear only once
    result = analyze_text("勉強 勉強 勉強")
    words = [r["word"] for r in result]
    assert len(words) == len(set(words)), "Duplicate words found in output"


def test_analyze_filters_pure_katakana():
    # Pure katakana loanwords should not appear
    result = analyze_text("テレビを見る")
    words = [r["word"] for r in result]
    assert "テレビ" not in words


def test_analyze_filters_pronouns():
    # 私 (pronoun) should be excluded
    result = analyze_text("私は学生です")
    words = [r["word"] for r in result]
    assert "私" not in words
    assert "わたし" not in words


def test_analyze_max_words_limits_processing():
    long_text = "日本語の勉強をする。歴史を学ぶ。経済を理解する。"
    result_full = analyze_text(long_text)
    result_capped = analyze_text(long_text, max_words=1)
    assert len(result_capped) <= len(result_full)


def test_analyze_content_words_included():
    # 勉強 (study, noun) and 学ぶ (learn, verb) are canonical content words
    result = analyze_text("勉強して学ぶ")
    words = [r["word"] for r in result]
    assert any("勉強" in w for w in words) or any("学" in w for w in words)


# ---------------------------------------------------------------------------
# should_keep_token — filtering logic
# ---------------------------------------------------------------------------

def test_keep_noun():
    assert should_keep_token("日本", "名詞", "") is True


def test_keep_verb():
    assert should_keep_token("食べる", "動詞", "") is True


def test_keep_adjective():
    assert should_keep_token("美しい", "形容詞", "") is True


def test_reject_pronoun():
    assert should_keep_token("私", "名詞", "代名詞") is False


def test_reject_number():
    assert should_keep_token("一", "名詞", "数詞") is False


def test_reject_particle():
    assert should_keep_token("は", "助詞", "") is False


def test_reject_pure_katakana():
    assert should_keep_token("テレビ", "名詞", "") is False
    assert should_keep_token("コーヒー", "名詞", "") is False


def test_reject_latin_noise():
    assert should_keep_token("ABC", "名詞", "") is False


# ---------------------------------------------------------------------------
# is_japanese_token
# ---------------------------------------------------------------------------

def test_is_japanese_kanji():
    assert is_japanese_token("日本") is True


def test_is_japanese_hiragana():
    assert is_japanese_token("ひらがな") is True


def test_is_japanese_mixed():
    assert is_japanese_token("食べる") is True


def test_not_japanese_latin():
    assert is_japanese_token("hello") is False


def test_not_japanese_empty():
    assert is_japanese_token("") is False


# ---------------------------------------------------------------------------
# lookup_english_meanings — dictionary lookup with caching
# ---------------------------------------------------------------------------

def test_lookup_returns_list():
    jmd = get_jamdict()
    result = lookup_english_meanings(jmd, "日本語")
    assert isinstance(result, list)


def test_lookup_unknown_word_returns_empty():
    jmd = get_jamdict()
    result = lookup_english_meanings(jmd, "xyznotaword")
    assert result == []


def test_lookup_cached(monkeypatch):
    """Second lookup with same key must hit cache (no DB call)."""
    jmd = get_jamdict()
    # Warm the cache
    lookup_english_meanings(jmd, "勉強")

    called = []
    original_lookup = jmd.lookup

    def fake_lookup(q):
        called.append(q)
        return original_lookup(q)

    monkeypatch.setattr(jmd, "lookup", fake_lookup)
    lookup_english_meanings(jmd, "勉強")  # should hit cache
    assert called == [], "Cache miss — DB was called on second lookup"


def test_reading_matches_dictionary_form():
    from types import SimpleNamespace
    word = SimpleNamespace(surface='食べた', feature=SimpleNamespace(kana='タベタ', kanaBase='タベル'))
    assert extract_reading_hiragana(word) == 'たべる'


def test_lookup_cache_isolated_by_dictionary():
    from types import SimpleNamespace
    from japanseanalyzer import lookup_entry_data
    class Dictionary:
        def __init__(self, text):
            self.text = text
        def lookup(self, query):
            return SimpleNamespace(entries=[SimpleNamespace(senses=[SimpleNamespace(gloss=[self.text])], kanji_forms=[], kana_forms=[])])
    assert lookup_entry_data(Dictionary('first'), 'same')[0] == ['first']
    assert lookup_entry_data(Dictionary('second'), 'same')[0] == ['second']


def test_transient_dictionary_failure_can_recover():
    from types import SimpleNamespace
    from japanseanalyzer import lookup_entry_data
    class Dictionary:
        calls = 0
        def lookup(self, query):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError('temporary')
            return SimpleNamespace(entries=[])
    dictionary = Dictionary()
    lookup_entry_data(dictionary, 'word')
    lookup_entry_data(dictionary, 'word')
    assert dictionary.calls == 2
