# ── Stage 1: Build React ─────────────────────────────────────────────────────
FROM node:20-slim AS frontend

WORKDIR /build
COPY frontend/package*.json ./
RUN npm install --quiet
COPY frontend/ ./
RUN npm run build


# ── Stage 2: Python runtime ───────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# System libraries required by OpenCV (headless), PyMuPDF, and PaddlePaddle
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install PaddlePaddle (CPU) and PyTorch (CPU) first so pip doesn't pull GPU variants.
# PaddlePaddle  → PaddleOCR  (normal model)
# PyTorch       → yomitoku   (advanced model)
RUN pip install --no-cache-dir paddlepaddle==2.6.2
RUN pip install --no-cache-dir \
        torch torchvision \
        --index-url https://download.pytorch.org/whl/cpu

# Install the rest of the dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Pre-download all OCR models into the image (no internet needed at runtime) ─
# Uses a build script so Docker's parser doesn't misread Python as Dockerfile instructions.
# PaddleOCR: urllib+tarfile (no inference engine init → no /dev/shm segfault)
# yomitoku:  huggingface_hub.snapshot_download (weights only, no model load)
COPY scripts/download_models.py /tmp/download_models.py
RUN python3 /tmp/download_models.py && rm /tmp/download_models.py

RUN useradd -m -u 1000 user

# Copy library code and backend
COPY libraries/ ./libraries/
COPY backend/   ./backend/

# Copy the React production build from stage 1
COPY --from=frontend /build/build ./frontend/build/
USER user
EXPOSE 7860

CMD ["python", "backend/app.py"]
