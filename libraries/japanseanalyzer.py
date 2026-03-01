"""
Japanese vocab analyzer (OCR-friendly)
- Tokenize Japanese text with fugashi (MeCab)
- Filter to "study vocab" (content words)
- Get readings (hiragana) via jaconv
- Get English glosses via Jamdict (JMdict)

Requirements:
  pip install fugashi[unidic-lite] jaconv jamdict
  # If you use a local jamdict.db, place it next to this file (optional).

Usage:
  from jp_vocab import analyze_text
  rows = analyze_text("日本語の文章...", max_words=None)
"""

from __future__ import annotations

import os
import re
import unicodedata
from typing import Dict, List, Optional, Set, Tuple

import fugashi
import jaconv
from jamdict import Jamdict


# =========================
# Config
# =========================

TARGET_POS: Set[str] = {
    "名詞",   # Noun
    "動詞",   # Verb
    "形容詞", # i-Adjective
    "形状詞", # na-Adjective
    "副詞",   # Adverb
}

IGNORE_SUB_POS: Set[str] = {
    "数詞",       # Numbers
    "代名詞",     # Pronouns
    "非自立可能", # Dependent nouns
    "接尾辞",     # Suffixes
}

# Keep tokens only if they contain some Japanese script (kanji/kana)
_JP_CHAR_RE = re.compile(r"[一-龯々〆ヵヶぁ-んァ-ヶー]")

# Matches tokens made entirely of katakana (loanwords — excluded from output)
_PURE_KATAKANA_RE = re.compile(r"^[\u30A1-\u30FC\u30FD\u30FE]+$")
# OCR sometimes leaves standalone combining dakuten/handakuten
_COMBINING_MARKS = {"\u3099", "\u309A"}  # ゙ ゚
_WS_RE = re.compile(r"\s+")             # compiled once at import time


# =========================
# Global caches (lazy init)
# =========================

_TAGGER: Optional[fugashi.Tagger] = None
_JMD: Optional[Jamdict] = None
_MEANINGS_CACHE: Dict[str, List[str]] = {}   # lemma:max_senses → meanings


# =========================
# Path helpers
# =========================

def _module_dir() -> str:
    """
    Directory where this file lives.
    Works even when __file__ is missing (interactive).
    """
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        return os.getcwd()


def resolve_jamdict_db_path(db_filename: str = "jamdict.db") -> str:
    """
    Default behavior:
    - Look for jamdict.db next to this module
    - Return the path if found, else empty string
    """
    path = os.path.join(_module_dir(), db_filename)
    return path if os.path.exists(path) else ""


# =========================
# OCR/text cleanup
# =========================

def normalize_ocr_text(text: str) -> str:
    """
    OCR-friendly normalization:
    - NFKC: width/compatibility normalization (half/full-width fixes)
    - NFC: compose kana + diacritics to single chars
    - remove control/format chars
    - remove leftover combining marks (゙ ゚)
    - collapse whitespace
    """
    if not text:
        return ""

    # NFKC already subsumes NFC — one pass is enough
    text = unicodedata.normalize("NFKC", text)

    # Single pass: drop control/format chars and stray combining marks
    text = "".join(
        ch for ch in text
        if unicodedata.category(ch)[0] != "C" and ch not in _COMBINING_MARKS
    )

    # Normalize whitespace
    text = _WS_RE.sub(" ", text).strip()
    return text


def is_japanese_token(s: str) -> bool:
    """True if token contains kanji/kana characters."""
    return bool(_JP_CHAR_RE.search(s or ""))


# =========================
# Resource initialization
# =========================

def get_tagger() -> fugashi.Tagger:
    """
    Lazily create and cache fugashi Tagger.
    """
    global _TAGGER
    if _TAGGER is None:
        _TAGGER = fugashi.Tagger()
    return _TAGGER


def get_jamdict(db_path: Optional[str] = None, db_filename: str = "jamdict.db") -> Jamdict:
    """
    Lazily create and cache Jamdict.
    Prefers local jamdict.db if present, unless db_path is explicitly provided.

    If no local DB is found, it falls back to Jamdict() default behavior.
    """
    global _JMD
    if _JMD is not None:
        return _JMD

    # Resolve db path
    chosen_path = (db_path or "").strip()
    if not chosen_path:
        chosen_path = resolve_jamdict_db_path(db_filename=db_filename)

    if chosen_path and os.path.exists(chosen_path):
        _JMD = Jamdict(db_file=chosen_path)
    else:
        if chosen_path:
            print(f"⚠️ Warning: jamdict.db not found at: {chosen_path} (falling back to default)")
        _JMD = Jamdict()

    return _JMD


def init_analyzer(db_path: Optional[str] = None) -> None:
    """
    Optional explicit initializer if you want to fail fast.
    """
    _ = get_tagger()
    _ = get_jamdict(db_path=db_path)


# =========================
# Token-level helpers
# =========================

def extract_pos(word: fugashi.fugashi.Node) -> Tuple[str, str]:
    """
    Returns (pos1, pos2). If missing, returns empty strings.
    """
    pos1 = getattr(word.feature, "pos1", "") or ""
    pos2 = getattr(word.feature, "pos2", "") or ""
    return pos1, pos2


def should_keep_token(surface: str, pos1: str, pos2: str) -> bool:
    """
    Filtering logic for learner vocab:
    - Keep only content POS (TARGET_POS)
    - Drop subcategories like 数詞, 代名詞, etc.
    - Drop non-Japanese-script tokens (math/latin noise)
    - Drop pure katakana tokens (loanwords like テレビ, コーヒー)
    """
    if pos1 not in TARGET_POS:
        return False
    if pos2 in IGNORE_SUB_POS:
        return False
    if not is_japanese_token(surface):
        return False
    if _PURE_KATAKANA_RE.match(surface):
        return False
    return True


def extract_lemma(word: fugashi.fugashi.Node) -> str:
    """
    Get lemma (dictionary form). Fallback to surface if missing.
    """
    lemma = getattr(word.feature, "lemma", "") or ""
    if not lemma or lemma == "*":
        lemma = word.surface
    return lemma


def extract_reading_hiragana(word: fugashi.fugashi.Node) -> str:
    """
    Get reading in hiragana.
    fugashi/unidic typically provides kana in katakana; convert to hiragana.
    """
    raw = getattr(word.feature, "kana", "") or ""
    if raw and raw != "*":
        try:
            return jaconv.kata2hira(raw)
        except Exception:
            return word.surface
    return word.surface


def gloss_to_text(gloss_obj) -> str:
    """
    Jamdict gloss entries may be objects with `.text`.
    Fall back to str().
    """
    txt = getattr(gloss_obj, "text", None)
    return txt if isinstance(txt, str) and txt else str(gloss_obj)


def lookup_english_meanings(jmd: Jamdict, query: str, max_senses: int = 2) -> List[str]:
    """
    Lookup English meanings for a lemma.
    Results are cached in _MEANINGS_CACHE so repeated lookups hit memory, not the DB.
    Returns up to max_senses strings (each may be multiple glosses joined by '; ').
    """
    cache_key = f"{query}\x00{max_senses}"
    if cache_key in _MEANINGS_CACHE:
        return _MEANINGS_CACHE[cache_key]

    meanings: List[str] = []
    try:
        lookup = jmd.lookup(query)
        if lookup.entries:
            entry = lookup.entries[0]
            for sense in entry.senses[:max_senses]:
                glosses = [gloss_to_text(g) for g in sense.gloss]
                definition = "; ".join(glosses).strip()
                if definition:
                    meanings.append(definition)
    except Exception:
        pass  # safe fallback: cache and return empty

    _MEANINGS_CACHE[cache_key] = meanings
    return meanings


# =========================
# Public API
# =========================

def analyze_text(
    text: str,
    max_words: Optional[int] = None,
    db_path: Optional[str] = None,
    max_senses: int = 2,
    dedupe_by: str = "lemma",
    normalize_text: bool = True,
) -> List[Dict]:
    """
    Analyze Japanese text -> unique vocab list with reading + English glosses.

    Parameters
    ----------
    text : str
        Input Japanese text (OCR output OK).
    max_words : Optional[int]
        Limit number of tokens processed (after tokenization, before filtering).
    db_path : Optional[str]
        Optional path to jamdict.db.
    max_senses : int
        Number of senses to keep from dictionary lookup.
    dedupe_by : str
        "lemma" (recommended) or "surface"
    normalize_text : bool
        Apply OCR normalization (NFKC+NFC) and cleanup before tokenization.

    Returns
    -------
    List[Dict] where each dict has:
        word, reading, pos, english
    """
    if not text or not text.strip():
        return []

    if normalize_text:
        text = normalize_ocr_text(text)

    tagger = get_tagger()
    jmd = get_jamdict(db_path=db_path)

    results: List[Dict] = []
    seen: Set[str] = set()

    try:
        for i, w in enumerate(tagger(text)):
            if max_words is not None and i >= max_words:
                break

            pos1, pos2 = extract_pos(w)
            surface = w.surface

            if not should_keep_token(surface=surface, pos1=pos1, pos2=pos2):
                continue

            lemma = extract_lemma(w)
            key = lemma if dedupe_by == "lemma" else surface
            if key in seen:
                continue
            seen.add(key)

            reading = extract_reading_hiragana(w)

            meanings = lookup_english_meanings(jmd, lemma, max_senses=max_senses)

            results.append({
                "word": lemma,
                "reading": reading,
                "pos": pos1,
                "english": meanings,
            })

    except Exception as e:
        print(f"Error analyzing text: {e}")
        return results  # partial results are still useful

    return results


def analyze_text_to_jsonable(
    text: str,
    **kwargs,
) -> List[Dict]:
    """
    Alias for analyze_text for clarity: returns JSON-serializable list of dicts.
    """
    return analyze_text(text, **kwargs)


# =========================
# Optional: quick test
# =========================

if __name__ == "__main__":
    sample = "次の定積分を求めなさい。直交行列Pによる相似変換。"
    init_analyzer()  # optional
    out = analyze_text(sample)
    for row in out:
        print(row)
