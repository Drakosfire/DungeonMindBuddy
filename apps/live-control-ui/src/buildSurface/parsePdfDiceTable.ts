export type PdfRegionTextRun = {
  text: string;
  left: number;
  right: number;
  top: number;
  bottom: number;
};

export type PdfDiceTable = {
  title: string;
  columns: string[];
  rows: string[][];
};

type Row = { runs: PdfRegionTextRun[]; centerY: number };
type Cell = { text: string; left: number; right: number };

function median(values: number[]): number {
  const sorted = values.filter(value => Number.isFinite(value) && value > 0).sort((a, b) => a - b);
  return sorted.length ? sorted[Math.floor(sorted.length / 2)] : 0;
}

function normalizeRepeatedText(value: string): string {
  const cleaned = value.trim().replace(/\s+/g, " ");
  const tokens = cleaned.split(" ");
  const tokenHalf = tokens.length / 2;
  if (Number.isInteger(tokenHalf) && tokenHalf > 0
    && tokens.slice(0, tokenHalf).join(" ") === tokens.slice(tokenHalf).join(" ")) {
    return tokens.slice(0, tokenHalf).join(" ");
  }
  const characterHalf = cleaned.length / 2;
  if (Number.isInteger(characterHalf) && characterHalf > 0
    && cleaned.slice(0, characterHalf) === cleaned.slice(characterHalf)) {
    return cleaned.slice(0, characterHalf).trim();
  }
  return cleaned;
}

function uniqueRuns(items: PdfRegionTextRun[]): PdfRegionTextRun[] {
  const seen = new Set<string>();
  return items.filter(item => {
    if (!item.text.trim() || ![item.left, item.right, item.top, item.bottom].every(Number.isFinite)) return false;
    const key = [item.text, item.left, item.right, item.top, item.bottom]
      .map(value => typeof value === "number" ? value.toFixed(5) : value).join("\u0000");
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  }).sort((a, b) => a.top - b.top || a.left - b.left);
}

function groupRows(items: PdfRegionTextRun[]): Row[] {
  const rowTolerance = median(items.map(item => item.bottom - item.top)) * 0.55;
  const rows: Row[] = [];
  for (const item of items) {
    const centerY = (item.top + item.bottom) / 2;
    const row = rows.find(candidate => Math.abs(candidate.centerY - centerY) <= rowTolerance);
    if (!row) {
      rows.push({ runs: [item], centerY });
      continue;
    }
    row.centerY = (row.centerY * row.runs.length + centerY) / (row.runs.length + 1);
    row.runs.push(item);
  }
  return rows.sort((a, b) => a.centerY - b.centerY);
}

function rowCells(row: Row, gapLimit: number): Cell[] {
  const sorted = [...row.runs].sort((a, b) => a.left - b.left);
  const cells: Cell[] = [];
  for (const item of sorted) {
    const previous = cells.at(-1);
    if (!previous || item.left - previous.right > gapLimit) {
      cells.push({ text: item.text, left: item.left, right: item.right });
    } else {
      previous.text += ` ${item.text}`;
      previous.right = Math.max(previous.right, item.right);
    }
  }
  return cells.map(cell => ({ ...cell, text: normalizeRepeatedText(cell.text) }));
}

function rollValue(value: string): boolean {
  return /^\d+(?:\s*[-–—]\s*\d+)?$/.test(value.trim());
}

function isRollColumn(value: string): boolean {
  return /^(?:\d*d\d+|d\d+|roll|rolls)$/i.test(value.replace(/\s/g, ""));
}

function textInCell(runs: PdfRegionTextRun[]): string {
  return [...runs].sort((a, b) => a.left - b.left).map(item => item.text.trim()).filter(Boolean).join(" ");
}

function rowValues(row: Row, anchors: number[]): string[] | undefined {
  const boundaries = anchors.slice(1).map((anchor, index) => (anchors[index] + anchor) / 2);
  const columns: PdfRegionTextRun[][] = anchors.map(() => []);
  for (const item of row.runs) {
    const center = (item.left + item.right) / 2;
    const crossesBoundary = boundaries.some(boundary => item.left < boundary && item.right > boundary);
    if (crossesBoundary) return undefined;
    let column = boundaries.findIndex(boundary => center < boundary);
    if (column < 0) column = anchors.length - 1;
    columns[column].push(item);
  }
  return columns.map(textInCell);
}

export function parsePdfDiceTable(items: PdfRegionTextRun[]): PdfDiceTable | undefined {
  const runs = uniqueRuns(items);
  if (runs.length < 6) return undefined;
  const typicalHeight = median(runs.map(item => item.bottom - item.top));
  if (!typicalHeight) return undefined;
  const rows = groupRows(runs);
  const headerIndex = rows.findIndex(row => {
    const cells = rowCells(row, typicalHeight * 1.5);
    return cells.length >= 2 && isRollColumn(cells[0].text);
  });
  if (headerIndex < 1) return undefined;

  const header = rowCells(rows[headerIndex], typicalHeight * 1.5);
  const anchors = header.map(cell => (cell.left + cell.right) / 2);
  if (anchors.length < 2 || anchors.some((anchor, index) => index > 0 && anchor <= anchors[index - 1])) {
    return undefined;
  }
  const columns = header.map(cell => cell.text);
  if (columns.some(column => !column)) return undefined;

  const values: string[][] = [];
  const rollValues = new Set<string>();
  for (const row of rows.slice(headerIndex + 1)) {
    const cells = rowValues(row, anchors);
    if (!cells) return undefined;
    if (!rollValue(cells[0])) break;
    if (!cells[1]) return undefined;
    if (rollValues.has(cells[0])) return undefined;
    rollValues.add(cells[0]);
    values.push(cells);
  }
  if (values.length < 3) return undefined;

  const title = textInCell(rows[headerIndex - 1].runs);
  return { title: normalizeRepeatedText(title) || "Extracted table", columns, rows: values };
}
