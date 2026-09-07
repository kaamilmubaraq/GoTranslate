import {
  Document,
  Packer,
  Paragraph,
  Table,
  TableRow,
  TableCell,
  TextRun,
  HeadingLevel,
  AlignmentType,
  WidthType,
  BorderStyle,
  ShadingType,
} from "docx";
import { saveAs } from "file-saver";
import { POS_LABELS } from "./constants";

const BORDER = { style: BorderStyle.SINGLE, size: 4, color: "E5E7EB" };
const TABLE_BORDERS = {
  top: BORDER,
  bottom: BORDER,
  left: BORDER,
  right: BORDER,
  insideH: BORDER,
  insideV: BORDER,
};

function makeHeaderCell(text) {
  return new TableCell({
    shading: { type: ShadingType.SOLID, color: "1A1A2E" },
    borders: TABLE_BORDERS,
    children: [
      new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [
          new TextRun({ text, bold: true, color: "FFFFFF", size: 20 }),
        ],
      }),
    ],
  });
}

function makeCell(text, opts = {}) {
  return new TableCell({
    borders: TABLE_BORDERS,
    children: [
      new Paragraph({
        alignment: opts.center ? AlignmentType.CENTER : AlignmentType.LEFT,
        children: [
          new TextRun({
            text: text || "—",
            size: opts.size || 20,
            ...opts.run,
          }),
        ],
      }),
    ],
  });
}

export async function downloadAsWord(
  vocabulary,
  filename,
  definitionLabel = "English",
) {
  const headerRow = new TableRow({
    tableHeader: true,
    children: [
      makeHeaderCell("Word"),
      makeHeaderCell("Reading"),
      makeHeaderCell("Part of Speech"),
      makeHeaderCell(definitionLabel),
    ],
  });

  const dataRows = vocabulary.map(
    (entry) =>
      new TableRow({
        children: [
          makeCell(entry.word, {
            center: true,
            size: 28,
            run: { font: "Noto Serif JP" },
          }),
          makeCell(entry.reading, {
            center: true,
            run: { color: "C0392B", font: "Noto Sans JP" },
          }),
          makeCell(POS_LABELS[entry.pos] || entry.pos, { center: true }),
          makeCell(entry.english.slice(0, 3).join(" / ") || "—"),
        ],
      }),
  );

  const doc = new Document({
    sections: [
      {
        children: [
          new Paragraph({
            text: "GoTranslate — Vocabulary List",
            heading: HeadingLevel.HEADING_1,
            spacing: { after: 200 },
          }),
          new Paragraph({
            children: [
              new TextRun({
                text: `Source: ${filename}  •  ${vocabulary.length} words`,
                size: 18,
                color: "6B7280",
              }),
            ],
            spacing: { after: 300 },
          }),
          new Table({
            width: { size: 100, type: WidthType.PERCENTAGE },
            columnWidths: [15, 15, 15, 55],
            rows: [headerRow, ...dataRows],
          }),
        ],
      },
    ],
  });

  const blob = await Packer.toBlob(doc);
  const stem = filename.replace(/\.[^.]+$/, "");
  saveAs(blob, `${stem}_vocabulary.docx`);
}

// ── Components ────────────────────────────────────────────────────────────────

export async function downloadDocument(result) {
  const paragraphs = (text) =>
    text
      .split("\n")
      .map((line) => new Paragraph({ text: line, spacing: { after: 120 } }));
  const doc = new Document({
    sections: [
      {
        children: [
          new Paragraph({
            text: result.filename,
            heading: HeadingLevel.HEADING_1,
          }),
          new Paragraph({
            text: `Japanese to ${result.label} · ${result.translation_status} · Machine translation`,
          }),
          ...(result.warnings || []).map((text) => new Paragraph({ text })),
          new Paragraph({
            text: "Translation",
            heading: HeadingLevel.HEADING_2,
          }),
          ...paragraphs(result.translated_text),
          new Paragraph({
            text: "Japanese source",
            heading: HeadingLevel.HEADING_2,
          }),
          ...paragraphs(result.source_text),
        ],
      },
    ],
  });
  saveAs(
    await Packer.toBlob(doc),
    `${result.filename.replace(/\.[^.]+$/, "")}_translation.docx`,
  );
}
