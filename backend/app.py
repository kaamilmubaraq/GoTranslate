import asyncio
import sys
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "libraries"))

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from ocr_pipeline import process_bytes, warmup

ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp", ".pdf"}


@asynccontextmanager
async def lifespan(app):
    # Load the OCR model during startup so the first upload doesn't pay the
    # cold-start penalty (~20-40 s of model initialisation).
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, warmup)
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
):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")

    if engine not in ALLOWED_ENGINES:
        raise HTTPException(status_code=400, detail=f"Unknown engine: {engine}")

    if target_lang not in ALLOWED_LANGS:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {target_lang}")

    data = await file.read()

    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            None, lambda: process_bytes(data, suffix, engine=engine, target_lang=target_lang)
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return JSONResponse(content=result)


# ── Serve React build (production / container) ────────────────────────────────

_BUILD = Path(__file__).parent.parent / "frontend" / "build"

if _BUILD.exists():
    app.mount("/static", StaticFiles(directory=str(_BUILD / "static")), name="static")

    @app.get("/favicon.ico",   include_in_schema=False)
    async def favicon():   return FileResponse(str(_BUILD / "favicon.ico"))

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
