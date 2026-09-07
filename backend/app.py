import asyncio
import sys
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "libraries"))

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from ocr_pipeline import _get_engine, warmup
from document import process_document

ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp", ".pdf"}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
# Shared OCR models and dictionary handles must stay on a single worker thread.
_worker = ThreadPoolExecutor(max_workers=1)
_busy = False


@asynccontextmanager
async def lifespan(app):
    # Load the OCR model during startup so the first upload doesn't pay the
    # cold-start penalty (~20-40 s of model initialisation).
    loop = asyncio.get_event_loop()
    if os.environ.get("GOTRANSLATE_WARMUP", "1") != "0":
        await loop.run_in_executor(_worker, warmup)
    yield


app = FastAPI(lifespan=lifespan)

# CORS is only needed when the frontend runs on a different port (local dev).
# In the container both are served from port 8000 so CORS is a no-op there.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── API ───────────────────────────────────────────────────────────────────────

ALLOWED_ENGINES = {"paddleocr", "yomitoku"}
ALLOWED_LANGS   = {"en", "zh-CN", "lo", "th", "mn", "ko"}

@app.post("/process")
async def process_upload(
    file: UploadFile = File(...),
    engine: str = Form("paddleocr"),
    target_lang: str = Form("en"),
    mode: str = Form("vocabulary"),
):
    global _busy
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")

    if engine not in ALLOWED_ENGINES:
        raise HTTPException(status_code=400, detail=f"Unknown engine: {engine}")

    if target_lang not in ALLOWED_LANGS:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {target_lang}")

    if mode not in {"document", "vocabulary"}:
        raise HTTPException(status_code=400, detail="Unsupported processing mode")
    if _busy:
        raise HTTPException(status_code=503, detail="Another document is being processed. Please try again shortly.")

    data = await file.read(MAX_UPLOAD_BYTES + 1)
    await file.close()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Files must be 20 MB or smaller.")
    if not data:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    # Recheck after the upload read, which can yield to another request.
    if _busy:
        raise HTTPException(status_code=503, detail="Another document is being processed. Please try again shortly.")
    _busy = True

    loop = asyncio.get_running_loop()
    def release(_):
        global _busy
        _busy = False
        if not _.cancelled():
            _.exception()  # Retrieve failures even if the HTTP request was cancelled.
    future = loop.run_in_executor(
        _worker, lambda: process_document(data, suffix, _get_engine(engine), target_lang, mode)
    )
    future.add_done_callback(release)
    try:
        result = await asyncio.shield(future)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        logging.exception("Document processing failed")
        raise HTTPException(status_code=500, detail="Document processing failed. Try another file or OCR option.")

    return JSONResponse(content=result)


# ── Serve React build (production / container) ────────────────────────────────

_BUILD = Path(__file__).parent.parent / "frontend" / "build"

if (_BUILD / "index.html").is_file() and (_BUILD / "static").is_dir():
    app.mount("/static", StaticFiles(directory=str(_BUILD / "static")), name="static")

    @app.get("/favicon.ico",   include_in_schema=False)
    async def favicon():   return FileResponse(str(_BUILD / "favicon.ico"))

    @app.get("/favicon.svg", include_in_schema=False)
    async def favicon_svg(): return FileResponse(str(_BUILD / "favicon.svg"))

    @app.get("/manifest.json", include_in_schema=False)
    async def manifest():  return FileResponse(str(_BUILD / "manifest.json"))

    @app.get("/robots.txt",    include_in_schema=False)
    async def robots():    return FileResponse(str(_BUILD / "robots.txt"))

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str = ""):
        return FileResponse(str(_BUILD / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
