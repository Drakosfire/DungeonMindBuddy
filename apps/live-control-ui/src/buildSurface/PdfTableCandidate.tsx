import { useState } from "react";
import type { PdfLocator } from "../api/retainedPdfRegions";
import { parsePdfDiceTable, type PdfRegionTextRun } from "./parsePdfDiceTable";

export function PdfTableCandidate({
  items, locator, clipped = false,
}: { items: PdfRegionTextRun[]; locator: PdfLocator; clipped?: boolean }) {
  const candidate = clipped ? undefined : parsePdfDiceTable(items);
  const [opened, setOpened] = useState(false);
  if (!candidate) return null;
  if (!opened) return <button type="button" onClick={() => setOpened(true)}>Preview table rows</button>;

  return <section aria-label="Extracted PDF table candidate">
    <button type="button" onClick={() => setOpened(false)}>Collapse table preview</button>
    <h4>{candidate.title}</h4>
    <p>Page {locator.page} · {locator.source_revision_id} · region {locator.left.toFixed(3)}, {locator.top.toFixed(3)}–{locator.right.toFixed(3)}, {locator.bottom.toFixed(3)}</p>
    <table>
      <caption>Candidate read from the selected PDF region</caption>
      <thead><tr>{candidate.columns.map((column, index) => <th key={index} scope="col">{column}</th>)}</tr></thead>
      <tbody>{candidate.rows.map((row, rowIndex) => <tr key={rowIndex}>
        {row.map((cell, columnIndex) => <td key={columnIndex}>{cell}</td>)}
      </tr>)}</tbody>
    </table>
  </section>;
}
