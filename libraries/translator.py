"""Bounded Google web translation with explicit partial failures.

Uses the existing unofficial Google translation service with HTTP timeouts.
Document text is never cached across requests.
"""
from concurrent.futures import ThreadPoolExecutor
import re

LANG_CODES = {"en": "en", "zh-CN": "zh-CN", "lo": "lo", "th": "th", "mn": "mn", "ko": "ko"}
CHUNK_SIZE = 3500


def _translate_one(text, source, target):
    import requests
    from bs4 import BeautifulSoup
    with requests.get(
        "https://translate.google.com/m",
        params={"sl": source, "tl": target, "q": text}, timeout=(5, 20),
    ) as response:
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        element = soup.find("div", {"class": "result-container"}) or soup.find("div", {"class": "t0"})
        if element is None or not element.get_text(strip=True):
            raise ValueError("Translation service returned no text")
        return element.get_text(strip=True)


def split_text(text, limit=CHUNK_SIZE):
    """Prefer paragraph/sentence boundaries, with a hard provider-safe cap."""
    if limit < 1:
        raise ValueError("Chunk limit must be positive")
    chunks = []
    for paragraph in re.split(r"\n\s*\n", text.strip()):
        remaining = paragraph.strip()
        while len(remaining) > limit:
            boundaries = [m.end() for m in re.finditer(r"[。！？.!?\n]\s*", remaining[:limit])]
            cut = boundaries[-1] if boundaries else limit
            chunks.append(remaining[:cut])
            remaining = remaining[cut:]
        if remaining:
            chunks.append(remaining)
    return chunks


def _translate_many(texts, source, target):
    unique = list(dict.fromkeys(texts))
    def work(text):
        try:
            return text, _translate_one(text, source, target)
        except Exception:
            return text, None
    with ThreadPoolExecutor(max_workers=4) as pool:
        return dict(pool.map(work, unique))


def translate_document(text, target_lang):
    if target_lang not in LANG_CODES:
        raise ValueError("Unsupported translation language")
    chunks = split_text(text)
    if not chunks:
        return {"translated_text": "", "translation_status": "empty", "translation_failures": 0}
    lookup = _translate_many(chunks, "ja", target_lang)
    failures = sum(lookup[chunk] is None for chunk in chunks)
    translated = [lookup[chunk] if lookup[chunk] is not None else "[Translation unavailable for this passage]\n" + chunk for chunk in chunks]
    return {
        "translated_text": "\n\n".join(translated),
        "translation_status": "complete" if not failures else "failed" if failures == len(chunks) else "partial",
        "translation_failures": failures,
    }


def translate_vocabulary(vocabulary, target_lang):
    if target_lang not in LANG_CODES:
        raise ValueError("Unsupported translation language")
    if target_lang == "en":
        return 0
    meanings = [meaning for entry in vocabulary for meaning in entry.get("english", [])]
    lookup = _translate_many(meanings, "en", target_lang)
    for entry in vocabulary:
        entry["english"] = [lookup.get(m) or m for m in entry.get("english", [])]
    return sum(value is None for value in lookup.values())
