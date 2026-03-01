import re
import unicodedata

_COMBINING = {"\u3099", "\u309A"}  # ゙ ゚
_WS_RE = re.compile(r"\s+")        # compiled once at import time

# Strip a Latin gloss that is glued directly to a Japanese character.
# Matches an optional dash then an ASCII word after any hiragana/katakana/kanji.
# e.g. "スポットライト-spotlight" → "スポットライト"
#      "色color"                 → "色"
# Does NOT match standalone Latin words (no Japanese lookbehind).
_JP_LATIN_SUFFIX_RE = re.compile(
    r"(?<=[\u3040-\u30FF\u4E00-\u9FFF々〆])[-\u2010\u2014]?[a-zA-Z][a-zA-Z0-9\-]*"
)

def normalize_ocr_ja(text: str) -> str:
    if not text:
        return ""

    # NFKC already subsumes NFC — one pass is enough
    text = unicodedata.normalize("NFKC", text)

    # Single pass: drop control/format chars and stray combining marks
    text = "".join(
        ch for ch in text
        if unicodedata.category(ch)[0] != "C" and ch not in _COMBINING
    )

    # Strip Latin glosses glued to Japanese characters
    text = _JP_LATIN_SUFFIX_RE.sub("", text)

    # collapse whitespace
    text = _WS_RE.sub(" ", text).strip()
    return text

