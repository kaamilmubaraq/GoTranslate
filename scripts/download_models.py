"""
Download all OCR models into the Docker image at build time.

PaddleOCR: fetched via urllib + tarfile — no inference engine initialised,
           so no /dev/shm requirement and no segfault.

yomitoku: fetched via huggingface_hub.snapshot_download — weights only,
          no model loading.
"""
import urllib.request
import tarfile
import os


def dl(url, dest):
    """Download a tar and extract its contents flat into dest (strips top-level dir)."""
    os.makedirs(dest, exist_ok=True)
    fname = os.path.join(dest, url.rsplit("/", 1)[-1])
    print(f"[build] Downloading {url}")
    urllib.request.urlretrieve(url, fname)
    with tarfile.open(fname) as tf:
        for member in tf.getmembers():
            # Strip the first path component so files land directly in dest
            parts = member.name.split("/", 1)
            if len(parts) < 2 or not parts[1]:
                continue  # skip the top-level directory entry itself
            member.name = parts[1]
            tf.extract(member, dest)
    os.remove(fname)
    print(f"[build] Extracted to {dest}")


# PaddleOCR models
dl(
    "https://paddleocr.bj.bcebos.com/PP-OCRv3/multilingual/Multilingual_PP-OCRv3_det_infer.tar",
    "/root/.cache/paddleocr/det",
)
dl(
    "https://paddleocr.bj.bcebos.com/PP-OCRv4/multilingual/japan_PP-OCRv4_rec_infer.tar",
    "/root/.cache/paddleocr/rec",
)
dl(
    "https://paddleocr.bj.bcebos.com/dygraph_v2.0/ch/ch_ppocr_mobile_v2.0_cls_infer.tar",
    "/root/.cache/paddleocr/cls",
)
print("[build] PaddleOCR models ready.")

# yomitoku models (HuggingFace)
from huggingface_hub import snapshot_download

snapshot_download("KotaroKinoshita/yomitoku-text-detector-dbnet-v2")
snapshot_download("KotaroKinoshita/yomitoku-text-recognizer-parseq-open-beta")
print("[build] yomitoku models ready.")
