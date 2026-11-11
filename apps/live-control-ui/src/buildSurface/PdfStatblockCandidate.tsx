import {useState} from "react";
import type {PdfLocator} from "../api/retainedPdfRegions";

const abilities = ["STR", "DEX", "CON", "INT", "WIS", "CHA"];

function readAbilityScores(text: string): string[] {
  const rows = [...text.matchAll(/^[ 	]*STR[ 	]+DEX[ 	]+CON[ 	]+INT[ 	]+WIS[ 	]+CHA[ 	]*\r?\n([ 	0-9()+-]+)$/gim)];
  if (rows.length !== 1) return [];
  const scores = rows[0][1].replace(/\([+-]?\d+\)/g, "").trim().split(/[ 	]+/);
  return scores.length === abilities.length && scores.every(score => /^\d+$/.test(score)) ? scores : [];
}

function readRulesSections(text: string) {
  const heading = /^[ \t]*(Traits|Actions|Bonus Actions|Reactions|Legendary Actions|Regional Effects|Lair Actions(?: \(Cont\.\))?)[ \t]*$/gim;
  const headings = [...text.matchAll(heading)];
  return headings.flatMap((match, index) => {
    const start = match.index + match[0].length;
    const end = headings[index + 1]?.index ?? text.length;
    const body = text.slice(start, end).trim();
    return body ? [{ title: match[1], body }] : [];
  });
}

export function PdfStatblockCandidate({text, locator}: {text: string; locator: PdfLocator}) {
  const [opened, setOpened] = useState(false);
  if (!opened) return <button type="button" onClick={() => setOpened(true)}>Preview statblock fields</button>;

  const armor = Array.from(text.matchAll(/^[ \t]*Armor Class[ \t]*:?[ \t]*(\d(?:[ \t]*\d)*)/gim));
  const hp = Array.from(text.matchAll(/^[ \t]*Hit Points[ \t]*:?[ \t]*(\d(?:[ \t]*\d)*)/gim));
  const scores = readAbilityScores(text);
  const sections = armor.length === 1 && hp.length === 1 ? readRulesSections(text) : [];
  return <section aria-label="Extracted statblock fields">
    <h4>Statblock candidate</h4>
    <p>Page {locator.page} · {locator.source_revision_id}</p>
    {armor.length === 1 && hp.length === 1 ? <dl>
      <dt>Armor Class</dt><dd>{armor[0][1].replace(/\s/g, "")}</dd>
      <dt>Hit Points</dt><dd>{hp[0][1].replace(/\s/g, "")}</dd>
      {scores.map((score, index) => <div key={abilities[index]}>
        <dt>{abilities[index]}</dt><dd>{score}</dd>
      </div>)}
    </dl> : <p>Select a region with one labeled Armor Class and one labeled Hit Points entry.</p>}
    {sections.map(({ title, body }, index) => (
      <details key={index}>
        <summary>{title} · captured text</summary>
        <p style={{ whiteSpace: "pre-wrap" }}>{body}</p>
      </details>
    ))}
  </section>;
}
