# Contributing to GoTranslate

Thanks for helping improve GoTranslate. Bug reports, documentation fixes,
accessibility improvements, tests, and focused code changes are welcome.

## Before opening a change

1. Search existing issues and pull requests to avoid duplicate work.
2. Open an issue before a large feature or architectural change so its scope can
   be discussed.
3. Keep pull requests focused and explain the user-visible behavior they change.

## Development

Use Python 3.11. Install the Python and frontend dependencies:

```sh
python -m venv .venv
python -m pip install -r requirements.txt -r requirements-dev.txt
cd frontend
npm ci
```

The full OCR models are large. Most tests use deterministic substitutes and do
not require those models:

```sh
python -m pytest -m "not slow" -q
cd frontend
npm test -- --watchAll=false --runInBand
npm run build
```

Run the slow OCR tests when changing OCR adapters or image preprocessing.

## Pull requests

- Add tests for behavior changes and bug fixes.
- Preserve keyboard access, visible focus, readable contrast, and reduced-motion
  behavior in interface changes.
- Never commit documents containing personal data, model downloads, dictionary
  databases, credentials, build output, or virtual environments.
- Document new environment variables and external service behavior.
- Confirm that `git diff --check` and the relevant test commands pass.

By contributing, you agree that your contributions are licensed under the MIT
License in this repository.
