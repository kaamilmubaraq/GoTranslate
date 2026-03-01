import { useState, useCallback } from 'react';
import {
  Document, Packer, Paragraph, Table, TableRow, TableCell,
  TextRun, HeadingLevel, AlignmentType, WidthType, BorderStyle,
  ShadingType,
} from 'docx';
import { saveAs } from 'file-saver';
import './App.css';

const POS_LABELS = {
  '名詞': 'Noun',
  '動詞': 'Verb',
  '形容詞': 'i-Adj',
  '形状詞': 'na-Adj',
  '副詞': 'Adverb',
};

// ── Word document export ──────────────────────────────────────────────────────

const BORDER = { style: BorderStyle.SINGLE, size: 4, color: 'E5E7EB' };
const TABLE_BORDERS = { top: BORDER, bottom: BORDER, left: BORDER, right: BORDER, insideH: BORDER, insideV: BORDER };

function makeHeaderCell(text) {
  return new TableCell({
    shading: { type: ShadingType.SOLID, color: '1A1A2E' },
    borders: TABLE_BORDERS,
    children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text, bold: true, color: 'FFFFFF', size: 20 })],
    })],
  });
}

function makeCell(text, opts = {}) {
  return new TableCell({
    borders: TABLE_BORDERS,
    children: [new Paragraph({
      alignment: opts.center ? AlignmentType.CENTER : AlignmentType.LEFT,
      children: [new TextRun({ text: text || '—', size: opts.size || 20, ...opts.run })],
    })],
  });
}

async function downloadAsWord(vocabulary, filename) {
  const headerRow = new TableRow({
    tableHeader: true,
    children: [
      makeHeaderCell('Word'),
      makeHeaderCell('Reading'),
      makeHeaderCell('Part of Speech'),
      makeHeaderCell('English'),
    ],
  });

  const dataRows = vocabulary.map((entry) =>
    new TableRow({
      children: [
        makeCell(entry.word,    { center: true, size: 28, run: { font: 'Noto Serif JP' } }),
        makeCell(entry.reading, { center: true, run: { color: 'C0392B', font: 'Noto Sans JP' } }),
        makeCell(POS_LABELS[entry.pos] || entry.pos, { center: true }),
        makeCell(entry.english.slice(0, 3).join(' / ') || '—'),
      ],
    })
  );

  const doc = new Document({
    sections: [{
      children: [
        new Paragraph({
          text: 'GoTranslate — Vocabulary List',
          heading: HeadingLevel.HEADING_1,
          spacing: { after: 200 },
        }),
        new Paragraph({
          children: [new TextRun({ text: `Source: ${filename}  •  ${vocabulary.length} words`, size: 18, color: '6B7280' })],
          spacing: { after: 300 },
        }),
        new Table({
          width: { size: 100, type: WidthType.PERCENTAGE },
          columnWidths: [15, 15, 15, 55],
          rows: [headerRow, ...dataRows],
        }),
      ],
    }],
  });

  const blob = await Packer.toBlob(doc);
  const stem = filename.replace(/\.[^.]+$/, '');
  saveAs(blob, `${stem}_vocabulary.docx`);
}

// ── Components ────────────────────────────────────────────────────────────────

function VocabCard({ entry, index }) {
  const posLabel = POS_LABELS[entry.pos] || entry.pos;
  const posClass = POS_LABELS[entry.pos] ? `card-pos pos-${entry.pos}` : 'card-pos pos-other';
  const meanings = entry.english.slice(0, 3);
  const delay = Math.min(index, 20) * 45;

  return (
    <div className="vocab-card" style={{ animationDelay: `${delay}ms` }}>
      <div className="card-word">{entry.word}</div>
      <div className="card-reading">{entry.reading}</div>
      <span className={posClass}>{posLabel}</span>
      <hr className="card-divider" />
      {meanings.length > 0 ? (
        <ul className="card-meanings">
          {meanings.map((m, i) => (
            <li key={i} className="card-meaning">
              <span className="meaning-num">{i + 1}</span>
              <span>{m}</span>
            </li>
          ))}
        </ul>
      ) : (
        <span className="no-meaning">No definition found</span>
      )}
    </div>
  );
}

// ── App ───────────────────────────────────────────────────────────────────────

export default function App() {
  const [file, setFile] = useState(null);
  const [vocabulary, setVocabulary] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [advanced, setAdvanced] = useState(false);

  const applyFile = (f) => {
    setFile(f);
    setVocabulary(null);
    setError('');
  };

  const handleFileChange = (e) => {
    if (e.target.files[0]) applyFile(e.target.files[0]);
  };

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) applyFile(f);
  }, []);

  const handleDragOver  = (e) => { e.preventDefault(); setDragOver(true); };
  const handleDragLeave = () => setDragOver(false);

  const handleProcess = async () => {
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    formData.append('engine', advanced ? 'yomitoku' : 'paddleocr');

    setLoading(true);
    setError('');
    setVocabulary(null);

    try {
      const base = process.env.REACT_APP_API_URL || '';
      const res  = await fetch(`${base}/process`, { method: 'POST', body: formData });
      const data = await res.json();
      if (res.ok) {
        setVocabulary(data.vocabulary);
      } else {
        setError(data.detail || 'Processing failed.');
      }
    } catch {
      setError('Could not connect to the server. Make sure the backend is running.');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (vocabulary && file) downloadAsWord(vocabulary, file.name);
  };

  return (
    <div>
      <header className="header">
        <span className="header-title">GoTranslate</span>
        <span className="header-ja">語翻訳</span>
        <span className="header-badge">Japanese OCR</span>
      </header>

      <main className="main">

        {/* Upload */}
        <div
          className={`upload-zone${dragOver ? ' drag-over' : ''}`}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
        >
          <input type="file" accept="image/*,.pdf" onChange={handleFileChange} />
          <span className="upload-icon">🗂️</span>
          <div className="upload-title">Drop your file here, or click to browse</div>
          <div className="upload-sub">Upload a Japanese image or document to extract vocabulary</div>
          <div className="format-chips">
            {['JPG', 'PNG', 'WEBP', 'BMP', 'TIFF', 'PDF'].map(f => (
              <span key={f} className="format-chip">{f}</span>
            ))}
          </div>
        </div>

        {file && !loading && (
          <div className="file-banner">
            <span className="file-banner-icon">📎</span>
            <span className="file-banner-name">{file.name}</span>
            <button className="file-banner-clear" onClick={() => { setFile(null); setVocabulary(null); setError(''); }}>✕</button>
          </div>
        )}

        {error && <div className="error-box">⚠️ {error}</div>}

        {/* Engine toggle */}
        <div className="engine-toggle">
          <span className={`engine-label${!advanced ? ' active' : ''}`}>Normal</span>
          <button
            className={`toggle-track${advanced ? ' on' : ''}`}
            onClick={() => setAdvanced(v => !v)}
            aria-label="Switch OCR model"
          >
            <span className="toggle-thumb" />
          </button>
          <span className={`engine-label${advanced ? ' active' : ''}`}>Advanced</span>
          {advanced && (
            <span className="engine-note">First use loads a larger model (~30 s)</span>
          )}
        </div>

        <button className="process-btn" onClick={handleProcess} disabled={!file || loading}>
          {loading ? 'Analyzing…' : 'Extract Vocabulary'}
        </button>

        {/* Loading */}
        {loading && (
          <div className="loading-section">
            <div className="spinner" />
            <div className="loading-text">Running OCR and analyzing text…</div>
            <div className="loading-ja">解析中...</div>
          </div>
        )}

        {/* Results */}
        {vocabulary && !loading && (
          <>
            <div className="results-bar">
              <div className="results-bar-left">
                <span className="results-title">Vocabulary Found</span>
                <span className="results-count">{vocabulary.length} words</span>
              </div>
              {vocabulary.length > 0 && (
                <button className="download-btn" onClick={handleDownload}>
                  <span className="download-icon">📄</span>
                  <span>Download as Word</span>
                  <span className="download-ext">.docx</span>
                </button>
              )}
            </div>

            {vocabulary.length === 0 ? (
              <div className="empty-state">
                <span className="empty-icon">🔍</span>
                <div>No vocabulary words found in this document.</div>
              </div>
            ) : (
              <div className="vocab-grid">
                {vocabulary.map((entry, i) => (
                  <VocabCard key={i} entry={entry} index={i} />
                ))}
              </div>
            )}
          </>
        )}

      </main>
    </div>
  );
}
