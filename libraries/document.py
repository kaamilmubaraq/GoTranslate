"""Document extraction with per-page PDF fallback and explicit result metadata."""
import unicodedata

import cv2
import numpy as np

from japanseanalyzer import analyze_text
from pipeline import images_from_bytes, resize_if_large, MAX_OCR_SIDE
from pdf_utils import MAX_PDF_PAGES
from translator import translate_document


def process_document(data, suffix, engine, target_lang="en", mode="document"):
    parts, warnings = [], []
    total_pages = 1
    ocr_pages = 0
    if suffix == ".pdf":
        import fitz
        try:
            doc = fitz.open(stream=data, filetype="pdf")
        except Exception as exc:
            raise ValueError("This PDF could not be opened. Try exporting it again.") from exc
        with doc:
            if doc.needs_pass:
                raise ValueError("This PDF is password protected. Upload an unlocked copy.")
            total_pages = doc.page_count
            if total_pages > MAX_PDF_PAGES:
                warnings.append(f"Only the first {MAX_PDF_PAGES} of {total_pages} pages were processed.")
            for index in range(min(total_pages, MAX_PDF_PAGES)):
                page = doc[index]
                text = page.get_text(sort=True).strip()
                # A text header can coexist with a scanned body. Never drop that body.
                if not text or page.get_images():
                    scale = min(120 / 72, MAX_OCR_SIDE / max(page.rect.width, page.rect.height))
                    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False, colorspace=fitz.csRGB)
                    rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
                    text = engine.read_image(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)) or text
                    ocr_pages += 1
                parts.append(text)
    else:
        parts = [engine.read_image(resize_if_large(img)) for img in images_from_bytes(data, suffix)]
        ocr_pages = len(parts)

    source = "\n\n".join(parts).strip()
    source = "".join(ch for ch in source if ch in "\n\t" or unicodedata.category(ch)[0] != "C")
    result = {
        "source_text": source, "translated_text": "", "vocabulary": [],
        "target_lang": target_lang, "translation_status": "not_requested",
        "warnings": warnings, "pages_processed": len(parts),
        "total_pages": total_pages, "ocr_pages": ocr_pages,
    }
    if not source:
        warnings.append("No readable text was found. Try a clearer scan or the detailed OCR option.")
        return result
    if mode == "document":
        result.update(translate_document(source, target_lang))
    else:
        result["vocabulary"] = analyze_text(source)
        if target_lang != "en":
            from translator import translate_vocabulary
            if translate_vocabulary(result["vocabulary"], target_lang):
                warnings.append("Some definitions could not be translated and remain in English.")
    return result
