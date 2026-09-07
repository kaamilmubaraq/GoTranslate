import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from backend import app as api


def test_upload_validation(monkeypatch):
    client = TestClient(api.app)
    assert client.post('/process', files={'file': ('bad.exe', b'x')}).status_code == 400
    assert client.post('/process', files={'file': ('empty.pdf', b'')}).status_code == 400
    monkeypatch.setattr(api, 'MAX_UPLOAD_BYTES', 3)
    assert client.post('/process', files={'file': ('large.pdf', b'1234')}).status_code == 413


def test_document_request_passes_mode_and_language(monkeypatch):
    calls = []
    def process(*args):
        calls.append(args)
        return {'source_text': 'source', 'translated_text': 'result', 'vocabulary': []}
    monkeypatch.setattr(api, 'process_document', process)
    response = TestClient(api.app).post('/process', files={'file': ('report.pdf', b'data')}, data={'mode': 'document', 'target_lang': 'ko'})
    assert response.status_code == 200
    assert calls[0][-2:] == ('ko', 'document')


def test_busy_returns_retryable_status(monkeypatch):
    monkeypatch.setattr(api, '_busy', True)
    response = TestClient(api.app).post('/process', files={'file': ('report.pdf', b'data')})
    assert response.status_code == 503


def test_processing_error_does_not_expose_internal_details(monkeypatch):
    def fail(*args):
        raise RuntimeError('private internal detail')
    monkeypatch.setattr(api, 'process_document', fail)
    response = TestClient(api.app).post('/process', files={'file': ('report.pdf', b'data')})
    assert response.status_code == 500
    assert 'private' not in response.text


def test_cancelled_request_keeps_worker_busy_until_finished(monkeypatch):
    import asyncio
    import io
    import threading
    from fastapi import UploadFile
    started, finish = threading.Event(), threading.Event()
    def process(*args):
        started.set()
        assert finish.wait(5)
        return {'vocabulary': []}
    monkeypatch.setattr(api, 'process_document', process)
    async def scenario():
        task = asyncio.create_task(api.process_upload(UploadFile(filename='file.pdf', file=io.BytesIO(b'data')), 'paddleocr', 'en', 'document'))
        try:
            await asyncio.to_thread(started.wait, 2)
            assert started.is_set()
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            assert api._busy is True
        finally:
            finish.set()
            for _ in range(100):
                if not api._busy:
                    break
                await asyncio.sleep(.01)
        assert api._busy is False
    asyncio.run(scenario())
