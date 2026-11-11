import {useState} from "react";
import type {PdfLocator} from "../api/retainedPdfRegions";

export function PdfStatblockCandidate({text, locator}: {text: string; locator: PdfLocator}) {
  const [opened, setOpened] = useState(false);
  if (!opened) return <button type="button" onClick={() => setOpened(true)}>Preview statblock fields</button>;

  const armor = Array.from(text.matchAll(/^[ \t]*Armor Class[ \t]*:?[ \t]*(\d(?:[ \t]*\d)*)/gim));
  const hp = Array.from(text.matchAll(/^[ \t]*Hit Points[ \t]*:?[ \t]*(\d(?:[ \t]*\d)*)/gim));
  return <section aria-label="Extracted statblock fields">
    <h4>Statblock candidate</h4>
    <p>Page {locator.page} · {locator.source_revision_id}</p>
    {armor.length === 1 && hp.length === 1 ? <dl>
      <dt>Armor Class</dt><dd>{armor[0][1].replace(/\s/g, "")}</dd>
      <dt>Hit Points</dt><dd>{hp[0][1].replace(/\s/g, "")}</dd>
    </dl> : <p>Select a region with one labeled Armor Class and one labeled Hit Points entry.</p>}
  </section>;
}
