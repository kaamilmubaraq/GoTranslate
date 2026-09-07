# Verification — 2026-09-07

- Python: 76 tests passed; 9 model-dependent tests deselected.
- React: 6 interaction tests passed, including upload validation, cancellation,
  failed server responses, translation rendering, and vocabulary search.
- Final production frontend compilation passed after component extraction and
  dependency updates. Initial JavaScript is 65.86 kB gzip; Word export loads lazily.
- Live smoke test: a generated Japanese PDF was submitted through `/process` and
  translated into English, with zero OCR calls for its embedded text.
- The external translation service also returned transient failures during smoke
  checks. Failed passages remained explicitly marked; the source stayed intact.
- npm audit: compatible dependency updates reduced findings from 55 (including
  2 critical) to 32 (14 high, 9 moderate, 9 low). Remaining findings involve the
  existing Create React App build/test dependency tree. No forced breaking
  dependency replacement was applied.
- The in-app browser reported no available browser instances. Desktop/mobile
  visual verification was not performed. OCR inference with Paddle/Yomitoku was
  not run locally; extraction routing is covered with deterministic fake engines.

The translation provider is an unofficial web service. The implementation does
not preserve PDF layout, provide an enterprise SLA, or claim independently
measured improvements in OCR model accuracy.
