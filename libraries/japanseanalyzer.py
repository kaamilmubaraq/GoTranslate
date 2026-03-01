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

import csv
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
_ENTRY_CACHE: Dict[str, Tuple[List[str], int]] = {}  # lemma:max_senses → (meanings, freq_score)


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


# =========================
# JLPT word list (Jonathan Waller / elzup)
# libraries/data/jlpt/all.csv  columns: expression,reading,meaning,tags
# tags contains e.g. "JLPT_1 JLPT" → N1
# =========================

_JLPT_EXPR: Dict[str, str] = {}   # expression (kanji/kana) → "N1"…"N5"
_JLPT_READ: Dict[str, str] = {}   # reading (hiragana) → level, fallback only
_JLPT_LOADED: bool = False
_JLPT_TAG_RE = re.compile(r"JLPT_(\d)")
_LEVEL_RANK: Dict[str, int] = {"N5": 5, "N4": 4, "N3": 3, "N2": 2, "N1": 1}


def _load_jlpt_index() -> None:
    global _JLPT_LOADED
    _JLPT_LOADED = True
    csv_path = os.path.join(_module_dir(), "data", "jlpt", "all.csv")
    if not os.path.exists(csv_path):
        return
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            m = _JLPT_TAG_RE.search(row.get("tags", ""))
            if not m:
                continue
            level = f"N{m.group(1)}"
            expr = (row.get("expression") or "").strip()
            reading = (row.get("reading") or "").strip()
            if expr:
                # keep easiest (highest rank) level when expression appears multiple times
                if _LEVEL_RANK.get(level, 0) > _LEVEL_RANK.get(_JLPT_EXPR.get(expr, ""), 0):
                    _JLPT_EXPR[expr] = level
            if reading:
                if _LEVEL_RANK.get(level, 0) > _LEVEL_RANK.get(_JLPT_READ.get(reading, ""), 0):
                    _JLPT_READ[reading] = level


def _get_jlpt_level(word: str, reading: str = "") -> Optional[str]:
    """
    Look up JLPT level from the bundled Jonathan Waller word list.
    Returns None for words not in the list (no badge shown in UI).
    """
    if not _JLPT_LOADED:
        _load_jlpt_index()
    return _JLPT_EXPR.get(word) or (_JLPT_READ.get(reading) if reading else None)


def _entry_freq_score(entry) -> int:
    """
    Convert JMdict priority tags into a difficulty score.
    Higher score = rarer/harder word = displayed first.

    Tag mapping:
      nfXX  → score = XX  (nf01=1 most common, nf48=48 rarest tagged)
      ichi1/news1/spec1/gai1 → 5  (common word, no nf rank)
      ichi2/news2/spec2/gai2 → 25 (slightly less common)
      (no tags)              → 999 (rare/unknown → hardest)
    """
    pri_tags: List[str] = []
    for kf in (entry.kanji_forms or []):
        pri_tags.extend(getattr(kf, "pri", None) or [])
    for rf in (entry.kana_forms or []):
        pri_tags.extend(getattr(rf, "pri", None) or [])

    if not pri_tags:
        return 999

    nf_scores = []
    for tag in pri_tags:
        if tag.startswith("nf"):
            try:
                nf_scores.append(int(tag[2:]))
            except ValueError:
                pass

    if nf_scores:
        return min(nf_scores)  # best (lowest) nf rank wins

    # Has common markers but no nfXX ranking
    tier1 = {"ichi1", "news1", "spec1", "gai1"}
    if any(t in tier1 for t in pri_tags):
        return 5
    return 25  # ichi2/news2/etc.


def lookup_entry_data(jmd: Jamdict, query: str, max_senses: int = 2) -> Tuple[List[str], int]:
    """
    Lookup English meanings + difficulty score for a lemma in one DB call.
    Cached in _ENTRY_CACHE so repeated lookups hit memory, not the DB.

    Returns (meanings, freq_score) where higher freq_score = harder/rarer word.
    """
    cache_key = f"{query}\x00{max_senses}"
    if cache_key in _ENTRY_CACHE:
        return _ENTRY_CACHE[cache_key]

    meanings: List[str] = []
    freq_score: int = 999
    try:
        lookup = jmd.lookup(query)
        if lookup.entries:
            entry = lookup.entries[0]
            for sense in entry.senses[:max_senses]:
                glosses = [gloss_to_text(g) for g in sense.gloss]
                definition = "; ".join(glosses).strip()
                if definition:
                    meanings.append(definition)
            freq_score = _entry_freq_score(entry)
    except Exception:
        pass

    _ENTRY_CACHE[cache_key] = (meanings, freq_score)
    return meanings, freq_score


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

            meanings, freq_score = lookup_entry_data(jmd, lemma, max_senses=max_senses)

            results.append({
                "word": lemma,
                "reading": reading,
                "pos": pos1,
                "english": meanings,
                "jlpt": _get_jlpt_level(lemma, reading),
                "_freq_score": freq_score,
            })

    except Exception as e:
        print(f"Error analyzing text: {e}")

    # Sort hardest (rarest) words first — higher freq_score = harder
    results.sort(key=lambda x: x["_freq_score"], reverse=True)
    for r in results:
        del r["_freq_score"]

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
