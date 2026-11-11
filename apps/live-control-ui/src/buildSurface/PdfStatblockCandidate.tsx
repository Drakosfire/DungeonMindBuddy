import {useState} from "react";
import type {PdfLocator} from "../api/retainedPdfRegions";

export function PdfStatblockCandidate({text, locator}: {text: string; locator: PdfLocator}) {
  const [opened, setOpened] = useState(false);
  if (!opened) return <button type="button" onClick={() => setOpened(true)}>Preview statblock fields</button>;

  const armor = text.match(/^[ \t]*Armor Class\s*:?\s*(\d+)/im)?.[1];
  const hp = text.match(/^[ \t]*Hit Points\s*:?\s*(\d+)/im)?.[1];
  const name = text.trim().split(/\r?\n/, 1)[0];
  return <section aria-label="Extracted statblock fields">
    <h4>Statblock candidate</h4>
    <p>Page {locator.page} · {locator.source_revision_id}</p>
    {armor && hp ? <dl>
      <dt>First line</dt><dd>{name}</dd>
      <dt>Armor Class</dt><dd>{armor}</dd>
      <dt>Hit Points</dt><dd>{hp}</dd>
    </dl> : <p>No statblock with labeled armor class and hit points was found in this capture.</p>}
  </section>;
}
