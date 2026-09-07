import pytest
from translator import split_text, translate_document, translate_vocabulary


def test_chunks_are_bounded_and_preserve_sentence_text():
    source = '日本語です。' * 1500
    chunks = split_text(source)
    assert ''.join(chunks) == source
    assert all(len(chunk) <= 3500 for chunk in chunks)


def test_document_deduplicates_and_preserves_order(monkeypatch):
    calls = []
    def translate(text, source, target):
        calls.append((text, source, target))
        return 'translated:' + text
    monkeypatch.setattr('translator._translate_one', translate)
    result = translate_document('one\n\ntwo\n\none', 'en')
    assert len(calls) == 2
    assert result['translated_text'] == 'translated:one\n\ntranslated:two\n\ntranslated:one'
    assert result['translation_status'] == 'complete'


def test_document_partial_failure_is_visible(monkeypatch):
    def translate(text, *args):
        if text == 'bad':
            raise TimeoutError()
        return 'translated'
    monkeypatch.setattr('translator._translate_one', translate)
    result = translate_document('good\n\nbad', 'en')
    assert result['translation_status'] == 'partial'
    assert result['translation_failures'] == 1
    assert '[Translation unavailable for this passage]\nbad' in result['translated_text']


def test_vocabulary_keeps_english_on_failure(monkeypatch):
    monkeypatch.setattr('translator._translate_one', lambda *args: (_ for _ in ()).throw(TimeoutError()))
    vocab = [{'english': ['hello']}]
    assert translate_vocabulary(vocab, 'ko') == 1
    assert vocab[0]['english'] == ['hello']


def test_rejects_unsupported_language():
    with pytest.raises(ValueError):
        translate_document('hello', 'invalid')
