"""
test_pipeline.py — Quick test for ocr_pipeline.py

Usage:
    python test_pipeline.py path/to/image.jpg
    python test_pipeline.py path/to/document.pdf
"""

import sys
import json
from pathlib import Path
from ocr_pipeline import process_file


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_pipeline.py <image_or_pdf_path>")
        sys.exit(1)

    file_path = sys.argv[1]
    print(f"Processing: {file_path}")

    result = process_file(file_path)
    vocabulary = result["vocabulary"]

    out_dir = Path("test_output")
    out_dir.mkdir(exist_ok=True)

    out_path = out_dir / "vocabulary.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(vocabulary, f, ensure_ascii=False, indent=2)

    print(f"Vocabulary ({len(vocabulary)} words) saved to: {out_path.resolve()}")


if __name__ == "__main__":
    main()
