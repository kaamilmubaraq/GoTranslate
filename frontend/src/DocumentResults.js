import Icon from "./Icon";
export default function DocumentResults({
  result,
  copyText,
  download,
  exporting,
}) {
  return (
    <>
      <div className="document-columns">
        <article className="document-pane">
          <div className="pane-heading">
            <h3>Original</h3>
            <span>Japanese</span>
          </div>
          <div className="document-text" lang="ja">
            {result.source_text || "No readable text found."}
          </div>
        </article>
        <article className="document-pane translated">
          <div className="pane-heading">
            <h3>Translation</h3>
            <span>{result.label}</span>
          </div>
          <div className="document-text" lang={result.target_lang}>
            {result.translated_text || "Try a clearer document to begin."}
          </div>
        </article>
      </div>
      <div className="result-actions">
        <span>Machine translation · Review before use</span>
        <div>
          <button
            className="button quiet"
            onClick={copyText}
            disabled={!result.translated_text}
          >
            <Icon name="copy" size={16} />
            Copy text
          </button>
          <button
            className="button secondary"
            onClick={download}
            disabled={!result.translated_text || exporting}
          >
            <Icon name="download" size={16} />
            {exporting ? "Exporting…" : "Export Word"}
          </button>
        </div>
      </div>
    </>
  );
}
