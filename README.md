---
title: GoTranslate
emoji: 🈳
sdk: docker
app_port: 7860
short_description: Japanese document OCR and translation / 日本語文書のOCR・翻訳ツール
tags:
  - japanese
  - ocr
  - translation
  - pdf
---

# GoTranslate

[![License: MIT](https://img.shields.io/badge/License-MIT-b6382d.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-19-20242c.svg)](https://react.dev/)

GoTranslate is an open-source workspace for extracting and translating Japanese
documents. It supports digital and scanned PDFs, common image formats,
side-by-side review, Word export, and vocabulary analysis.

GoTranslateは、日本語文書の文字抽出と翻訳を行うオープンソースのワークスペースです。
デジタルPDF、スキャンPDF、一般的な画像形式に対応し、原文と翻訳の比較、Word出力、
語彙分析を利用できます。

**Live app / アプリ:** [Hugging Face Spaces](https://huggingface.co/spaces/codekmh/GoTranslate)<br>
**Source code / ソースコード:** [GitHub](https://github.com/kaamilmubaraq/GoTranslate)

## Product tour / 製品ツアー

| Empty workspace / 空のワークスペース | Document ready / 文書の準備完了 |
| --- | --- |
| ![GoTranslate empty workspace](docs/screenshots/empty-state.png) | ![A one-page Japanese academic PDF uploaded to GoTranslate](docs/screenshots/uploaded-file.png) |

| Side-by-side result / 原文・翻訳結果 | Vocabulary analysis / 語彙分析 |
| --- | --- |
| ![GoTranslate side-by-side document result](docs/screenshots/translation-results.png) | ![Japanese vocabulary with readings, definitions, and JLPT levels](docs/screenshots/vocabulary-view.png) |

| Search and filter / 検索・絞り込み | Mobile workspace / モバイル表示 |
| --- | --- |
| ![Vocabulary filtered by an English definition](docs/screenshots/search-filter-results.png) | ![GoTranslate responsive mobile workspace](docs/screenshots/mobile-view.png) |

The screenshots use a one-page Japanese phonetics conference abstract published
through J-STAGE. Vocabulary extraction produced 281 terms with readings and English
definitions. The translation image also demonstrates the reviewable fallback shown
when the external machine-translation service is unavailable.

スクリーンショットには、J-STAGEで公開されている日本語音声学の1ページの
学会発表要旨を使用しています。語彙抽出では、読み方と英語定義を含む281語を
取得しました。翻訳画像では、外部の機械翻訳サービスを利用できない場合に表示される
確認可能なフォールバックも示しています。

## Document workspace

GoTranslate extracts Japanese text from PDFs and images and provides full-document
machine translation into English, Chinese, Korean, Thai, Lao, or Mongolian. A
separate vocabulary mode returns dictionary definitions, readings, and JLPT tags.

- Compare original and translated text, copy the translation, or export both to Word.
- Search and filter vocabulary; export all filtered words, not just the visible page.
- Digital PDF pages use embedded text. Image-bearing pages use OCR, preserving page order.
- Upload limit: 20 MB. PDF processing is limited to the first 20 pages and reports truncation.
- Partial translation failures are marked in the output and in Word exports.

### Local development

Use Python 3.11 and install `requirements.txt` and `requirements-dev.txt` in a
virtual environment. OCR models are downloaded on first use; Docker preloads them.
If `jamdict-data` installation fails on Windows, run `python install-db.py` from
`libraries/` to install the dictionary locally.

```sh
python backend/app.py
cd frontend
npm ci
npm start
```

The React development server proxies API requests to `http://127.0.0.1:7860`.
Set `REACT_APP_API_URL` at build time if the API runs elsewhere. Build with
`npm run build`; FastAPI serves `frontend/build` when present.

`GOTRANSLATE_WARMUP=0` skips startup OCR loading for embedded-text PDF development.
Image uploads still require the OCR dependencies and models. One document is
processed per server process, protecting the shared OCR and dictionary resources;
concurrent requests receive a retryable 503. Stopping a request in the browser
stops waiting but does not interrupt inference already running on the server.

### Verification

```sh
python -m pytest -m "not slow" -q
cd frontend
npm test -- --watchAll=false --runInBand
npm run build
```

Slow tests require OCR models. Translation tests stub the external service.

### Translation boundaries

Machine translation uses Google's unofficial web translation service. Text leaves
the server for translation; documents and translations are not cached across
requests. The service can fail or rate-limit, and is not an enterprise translation
SLA. Output preserves text order and paragraph separation, not original PDF layout.
Review source and translation before use. Vocabulary definitions fall back to
English with a warning when translation fails.

### Contributing and license

Contributions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening
a pull request and report security issues according to [SECURITY.md](SECURITY.md).

GoTranslate's original source code is available under the [MIT License](LICENSE).
Bundled third-party data retains its own license; see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
