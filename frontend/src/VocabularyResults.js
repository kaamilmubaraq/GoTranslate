import Icon from "./Icon";
import { POS_LABELS } from "./constants";
export default function VocabularyResults({
  result,
  query,
  setQuery,
  level,
  setLevel,
  page,
  setPage,
  pages,
  filtered,
  download,
  exporting,
}) {
  return (
    <>
      <div className="vocab-tools">
        <label className="search-box">
          <Icon name="search" size={17} />
          <input
            aria-label="Search vocabulary"
            placeholder="Search words, readings, definitions…"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setPage(1);
            }}
          />
        </label>
        <select
          aria-label="Filter by JLPT level"
          value={level}
          onChange={(e) => {
            setLevel(e.target.value);
            setPage(1);
          }}
        >
          <option value="all">All JLPT levels</option>
          {["N5", "N4", "N3", "N2", "N1"].map((l) => (
            <option key={l}>{l}</option>
          ))}
        </select>
      </div>
      <div className="table-scroll">
        <table>
          <caption>
            {filtered.length} of {result.vocabulary.length} words · Definitions
            in {result.label}
          </caption>
          <thead>
            <tr>
              <th>Word / reading</th>
              <th>Type</th>
              <th>Definition</th>
            </tr>
          </thead>
          <tbody>
            {filtered.slice((page - 1) * 50, page * 50).map((entry, index) => (
              <tr key={`${entry.word}-${index}`}>
                <td lang="ja">
                  <strong>{entry.word}</strong>
                  <small>{entry.reading}</small>
                </td>
                <td>
                  {POS_LABELS[entry.pos] || entry.pos}
                  {entry.jlpt && <span className="jlpt">{entry.jlpt}</span>}
                </td>
                <td>{entry.english.join(" / ") || "No definition found"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!filtered.length && (
          <p className="no-results">
            {result.vocabulary.length
              ? "No words match your filters."
              : "No vocabulary found. Try a clearer document."}
          </p>
        )}
      </div>
      <div className="result-actions">
        <div className="pagination">
          <button
            className="button quiet"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            Previous
          </button>
          <span>
            {page} / {pages}
          </span>
          <button
            className="button quiet"
            disabled={page >= pages}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </button>
        </div>
        <button
          className="button secondary"
          onClick={download}
          disabled={!filtered.length || exporting}
        >
          <Icon name="download" size={16} />
          {exporting ? "Exporting…" : "Export filtered words"}
        </button>
      </div>
    </>
  );
}
