import Icon from "./Icon";
import DocumentResults from "./DocumentResults";
import VocabularyResults from "./VocabularyResults";
import { useEffect, useMemo, useRef, useState } from "react";
import { ACCEPT, LANGUAGES, validateFile } from "./constants";
import "./App.css";

export default function App() {
  const [file, setFile] = useState(null);
  const [mode, setMode] = useState("document");
  const [engine, setEngine] = useState("paddleocr");
  const [language, setLanguage] = useState("en");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [dragging, setDragging] = useState(false);
  const [query, setQuery] = useState("");
  const [level, setLevel] = useState("all");
  const [page, setPage] = useState(1);
  const [exporting, setExporting] = useState(false);
  const request = useRef(null);
  const input = useRef(null);
  const resultsHeading = useRef(null);
  useEffect(() => () => request.current?.abort(), []);
  const langLabel = LANGUAGES.find((l) => l.value === language)?.label;
  const filtered = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase();
    return (result?.vocabulary || []).filter(
      (entry) =>
        (level === "all" || entry.jlpt === level) &&
        [entry.word, entry.reading, ...(entry.english || [])]
          .join(" ")
          .toLocaleLowerCase()
          .includes(needle),
    );
  }, [result, query, level]);
  const pages = Math.max(1, Math.ceil(filtered.length / 50));

  function chooseFile(next) {
    if (loading) return;
    const message = validateFile(next);
    setError(message);
    if (message) return;
    setFile(next);
    setResult(null);
    setNotice("");
    setQuery("");
    setLevel("all");
    setPage(1);
  }
  function reset() {
    if (loading) return;
    chooseFile(null);
    if (input.current) input.current.value = "";
  }
  async function processFile(event) {
    event.preventDefault();
    if (!file || request.current) return;
    const controller = new AbortController();
    request.current = controller;
    const form = new FormData();
    form.append("file", file);
    form.append("engine", engine);
    form.append("target_lang", language);
    form.append("mode", mode);
    setLoading(true);
    setError("");
    setNotice("");
    try {
      const base = (process.env.REACT_APP_API_URL || "").replace(/\/$/, "");
      const response = await fetch(`${base}/process`, {
        method: "POST",
        body: form,
        signal: controller.signal,
      });
      const data = await response.json().catch(() => null);
      if (!response.ok)
        throw new Error(
          typeof data?.detail === "string"
            ? data.detail
            : `Processing failed (${response.status}). Please try again.`,
        );
      if (
        !data ||
        !Array.isArray(data.vocabulary) ||
        typeof data.source_text !== "string" ||
        (mode === "document" && typeof data.translated_text !== "string")
      )
        throw new Error(
          "The server returned an incomplete result. Please try again.",
        );
      if (request.current !== controller) return;
      setResult({ ...data, mode, filename: file.name, label: langLabel });
      setQuery("");
      setLevel("all");
      setPage(1);
      setTimeout(() => resultsHeading.current?.focus(), 0);
    } catch (err) {
      if (err.name !== "AbortError" && request.current === controller)
        setError(
          err.message === "Failed to fetch"
            ? "Could not reach the server. Check your connection and try again."
            : err.message,
        );
    } finally {
      if (request.current === controller) {
        request.current = null;
        setLoading(false);
      }
    }
  }
  function cancel() {
    request.current?.abort();
    request.current = null;
    setLoading(false);
    setNotice(
      "Stopped waiting. The server may still be finishing this document.",
    );
  }
  async function copyText() {
    try {
      await navigator.clipboard.writeText(result.translated_text);
      setNotice("Translation copied.");
    } catch {
      setError(
        "Copy was unavailable. Select the text manually or download it.",
      );
    }
  }
  async function download() {
    setExporting(true);
    setError("");
    try {
      if (result.mode === "vocabulary") {
        const { downloadAsWord } = await import("./export");
        await downloadAsWord(filtered, result.filename, result.label);
      } else {
        const { downloadDocument } = await import("./export");
        await downloadDocument(result);
      }
      setNotice("Your Word document is ready.");
    } catch {
      setError("The export could not be created. Please try again.");
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="app-shell">
      <a className="skip-link" href="#workspace">
        Skip to workspace
      </a>
      <header className="app-header">
        <a className="brand" href="/" aria-label="GoTranslate home">
          <span className="brand-mark" lang="ja">
            訳
          </span>
          <span>GoTranslate</span>
        </a>
        <span className="header-divider" />
        <span className="header-caption">Document workspace</span>
        <span className="language-pair">
          <span lang="ja">日本語</span>
          <Icon name="arrow" size={15} />
          {langLabel}
        </span>
      </header>
      <main id="workspace" className="workspace">
        <div className="page-heading">
          <div>
            <h1>Make every document readable.</h1>
            <p>
              Japanese documents, translated with the original always in view.
            </p>
          </div>
          <button
            className="button quiet"
            onClick={reset}
            disabled={!file || loading}
          >
            New document <span aria-hidden="true">+</span>
          </button>
        </div>
        <div className="workspace-grid">
          <aside className="sidebar" aria-label="Document settings">
            <form onSubmit={processFile}>
              <div className="section-title">
                <Icon name="file" />
                <h2>Your document</h2>
              </div>
              <div
                className={`upload-zone ${dragging ? "dragging" : ""} ${file ? "has-file" : ""}`}
                onDragOver={(e) => {
                  e.preventDefault();
                  if (!loading) setDragging(true);
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setDragging(false);
                  if (e.dataTransfer.files.length > 1)
                    setError("Choose one document at a time.");
                  else if (e.dataTransfer.files[0])
                    chooseFile(e.dataTransfer.files[0]);
                }}
              >
                <input
                  ref={input}
                  id="document-upload"
                  type="file"
                  accept={ACCEPT}
                  disabled={loading}
                  aria-label="Upload Japanese document"
                  onChange={(e) => {
                    if (e.target.files[0]) chooseFile(e.target.files[0]);
                    e.target.value = "";
                  }}
                />
                <span className="upload-symbol">
                  <Icon name={file ? "file" : "upload"} size={26} />
                </span>
                <strong>{file ? file.name : "Drop a document here"}</strong>
                <span>
                  {file ? (
                    `${(file.size / 1024 / 1024).toFixed(2)} MB · Click to replace`
                  ) : (
                    <>
                      or <span className="text-link">browse files</span>
                    </>
                  )}
                </span>
                {!file && (
                  <small>
                    PDF, JPG, PNG, WebP, BMP, TIFF
                    <br />
                    Up to 20 MB · First 20 PDF pages
                  </small>
                )}
              </div>
              {file && (
                <button
                  type="button"
                  className="remove-file"
                  disabled={loading}
                  onClick={reset}
                >
                  Remove file
                </button>
              )}
              <div className="settings">
                <label htmlFor="output-mode">Output</label>
                <select
                  id="output-mode"
                  value={mode}
                  disabled={loading}
                  onChange={(e) => setMode(e.target.value)}
                >
                  <option value="document">Full-document translation</option>
                  <option value="vocabulary">Vocabulary & definitions</option>
                </select>
                <label htmlFor="language">Translate into</label>
                <select
                  id="language"
                  value={language}
                  disabled={loading}
                  onChange={(e) => setLanguage(e.target.value)}
                >
                  {LANGUAGES.map((lang) => (
                    <option value={lang.value} key={lang.value}>
                      {lang.label}
                    </option>
                  ))}
                </select>
                <fieldset disabled={loading}>
                  <legend>Text recognition</legend>
                  <div className="engine-options">
                    <label>
                      <input
                        type="radio"
                        name="engine"
                        checked={engine === "paddleocr"}
                        onChange={() => setEngine("paddleocr")}
                      />
                      <span>
                        <strong>Standard</strong>
                        <small>Everyday documents</small>
                      </span>
                    </label>
                    <label>
                      <input
                        type="radio"
                        name="engine"
                        checked={engine === "yomitoku"}
                        onChange={() => setEngine("yomitoku")}
                      />
                      <span>
                        <strong>Detailed</strong>
                        <small>Complex page layouts</small>
                      </span>
                    </label>
                  </div>
                </fieldset>
                {engine === "yomitoku" && (
                  <p className="setting-note">
                    Detailed recognition takes longer, especially on first use.
                  </p>
                )}
              </div>
              <button
                className="button primary"
                type="submit"
                disabled={!file || loading}
              >
                {loading
                  ? "Processing document…"
                  : mode === "document"
                    ? "Translate document"
                    : "Extract vocabulary"}
                {!loading && <Icon name="arrow" size={18} />}
              </button>
              {loading && (
                <button
                  type="button"
                  className="button quiet cancel"
                  onClick={cancel}
                >
                  Stop waiting
                </button>
              )}
              <p className="privacy-note">
                {mode === "document" || language !== "en"
                  ? "Text is sent to Google Translate for machine translation. Original page formatting is not preserved."
                  : "Extract Japanese terms with dictionary definitions and readings."}
              </p>
            </form>
            <div className="workflow-note">
              <h3>Better input. Better results.</h3>
              <p>
                Use a straight, well-lit scan with readable text. Review the
                translation against the source before sharing.
              </p>
            </div>
          </aside>
          <section
            className="results-workspace"
            aria-labelledby="results-title"
            aria-busy={loading}
          >
            <div className="results-toolbar">
              <div>
                <h2 ref={resultsHeading} tabIndex={-1} id="results-title">
                  {result
                    ? result.mode === "document"
                      ? "Document translation"
                      : "Vocabulary"
                    : "Translation"}
                </h2>
                <span className="result-subtitle">
                  {result
                    ? `${result.filename} · ${result.pages_processed ?? 1} page(s)`
                    : "Your results will appear here"}
                </span>
              </div>
              {result && (
                <span
                  className={`status-badge ${result.translation_status === "partial" || result.translation_status === "failed" ? "warning" : ""}`}
                >
                  <Icon name="check" size={13} />
                  {result.translation_status === "partial"
                    ? "Partially translated"
                    : result.translation_status === "failed"
                      ? "Translation failed"
                      : result.source_text
                        ? "Processed"
                        : "No text found"}
                </span>
              )}
            </div>
            {error && (
              <div className="message error" role="alert">
                {error}
              </div>
            )}
            {notice && (
              <div className="message info" role="status">
                {notice}
              </div>
            )}
            {loading ? (
              <div className="processing" role="status">
                <div className="processing-track" />
                <h3>Reading your document</h3>
                <p>
                  Extracting text
                  {mode === "document"
                    ? ` and translating into ${langLabel}`
                    : " and looking up vocabulary"}
                  . Larger documents can take a few minutes.
                </p>
                <div className="skeleton-lines" aria-hidden="true">
                  <i />
                  <i />
                  <i />
                  <i />
                </div>
              </div>
            ) : !result ? (
              <div className="empty-workspace">
                <div className="document-symbol">
                  <Icon name="file" size={38} />
                  <span lang="ja">あ</span>
                </div>
                <h3>From Japanese to your language.</h3>
                <p>
                  Upload a document to get a readable translation, compare it
                  with the source, and take your work with you.
                </p>
                <div className="empty-steps">
                  <span>Upload a file</span>
                  <Icon name="arrow" size={15} />
                  <span>Review translation</span>
                  <Icon name="arrow" size={15} />
                  <span>Export</span>
                </div>
              </div>
            ) : (
              <>
                {(result.warnings || []).map((warning, i) => (
                  <div className="message warning" key={i}>
                    {warning}
                  </div>
                ))}
                {["partial", "failed"].includes(result.translation_status) && (
                  <div className="message warning" role="alert">
                    {result.translation_failures} passage(s) could not be
                    translated. They are marked in the output. Try processing
                    again.
                  </div>
                )}
                {result.mode === "document" ? (
                  <DocumentResults
                    result={result}
                    copyText={copyText}
                    download={download}
                    exporting={exporting}
                  />
                ) : (
                  <VocabularyResults
                    result={result}
                    query={query}
                    setQuery={setQuery}
                    level={level}
                    setLevel={setLevel}
                    page={page}
                    setPage={setPage}
                    pages={pages}
                    filtered={filtered}
                    download={download}
                    exporting={exporting}
                  />
                )}
              </>
            )}
          </section>
        </div>
        <footer className="workspace-footer">
          <span>GoTranslate · Japanese document tools</span>
          <span>PDF & image extraction / 6 translation languages</span>
        </footer>
      </main>
    </div>
  );
}
