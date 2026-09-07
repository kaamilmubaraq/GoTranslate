import fitz
from document import process_document


class FakeEngine:
    def __init__(self):
        self.calls = 0
    def read_image(self, image):
        self.calls += 1
        assert max(image.shape[:2]) <= 1100
        return 'scanned text'


def test_mixed_pdf_preserves_pages_and_uses_ocr_only_where_needed(monkeypatch):
    with fitz.open() as doc:
        doc.new_page().insert_text((50, 50), 'Digital document text')
        doc.new_page()
        data = doc.tobytes()
    monkeypatch.setattr('document.translate_document', lambda text, lang: {'translated_text': text, 'translation_status': 'complete'})
    engine = FakeEngine()
    result = process_document(data, '.pdf', engine)
    assert engine.calls == 1
    assert result['source_text'] == 'Digital document text\n\nscanned text'
    assert result['pages_processed'] == 2
    assert result['ocr_pages'] == 1


def test_pdf_reports_truncation(monkeypatch):
    monkeypatch.setattr('document.MAX_PDF_PAGES', 1)
    with fitz.open() as doc:
        for _ in range(2):
            doc.new_page().insert_text((50, 50), 'Some text')
        data = doc.tobytes()
    monkeypatch.setattr('document.translate_document', lambda *args: {})
    result = process_document(data, '.pdf', FakeEngine())
    assert result['pages_processed'] == 1
    assert result['total_pages'] == 2
    assert 'first 1 of 2' in result['warnings'][0]


def test_malformed_pdf_is_actionable():
    import pytest
    with pytest.raises(ValueError, match='could not be opened'):
        process_document(b'bad pdf', '.pdf', FakeEngine())
