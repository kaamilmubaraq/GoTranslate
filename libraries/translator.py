"""
translator.py — Translate English definitions via deep-translator (Google Translate backend).

Uses ThreadPoolExecutor to fire all translation requests in parallel so the total
time is roughly the latency of ONE request (~2-3s) regardless of vocabulary size.
Falls back to the original English strings on any error.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import List

LANG_CODES = {
    "en":    None,
    "zh-CN": "zh-CN",
    "lo":    "lo",
    "th":    "th",
    "mn":    "mn",
    "ko":    "ko",
}


def translate_vocabulary(vocabulary: list, target_lang: str) -> None:
    """
    Translate all definition strings across every vocabulary entry in-place.

    Fires one parallel HTTP request per unique definition string (up to 10 at once),
    so the total wall-clock time is roughly the latency of a single request (~2-3s)
    regardless of how many words were found.
    """
    code = LANG_CODES.get(target_lang)
    if code is None or not vocabulary:
        return

    # Collect unique definition strings across all entries
    all_meanings: List[str] = []
    for entry in vocabulary:
        all_meanings.extend(entry.get("english", []))

    unique_meanings = list(dict.fromkeys(all_meanings))  # deduplicate, preserve order
    if not unique_meanings:
        return

    def _translate_one(text: str):
        try:
            from deep_translator import GoogleTranslator
            result = GoogleTranslator(source="en", target=code).translate(text)
            return text, result if result else text
        except Exception:
            return text, text

    try:
        with ThreadPoolExecutor(max_workers=10) as executor:
            lookup = dict(executor.map(_translate_one, unique_meanings))

        for entry in vocabulary:
            entry["english"] = [lookup.get(m, m) for m in entry.get("english", [])]
    except Exception:
        pass  # Keep original English on any failure
