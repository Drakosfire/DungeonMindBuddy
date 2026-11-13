import {useState} from "react";
import type {PdfLocator} from "../api/retainedPdfRegions";

const abilities = ["STR", "DEX", "CON", "INT", "WIS", "CHA"];

function normalizeExtractedText(text: string): string {
  return text
    .replace(/<\/(?:td|th)\s*>\s*(?=<(?:td|th)\b)/gi, "\t")
    .replace(/<\/(?:td|th)\s*>/gi, "\t")
    .replace(/<\/tr\s*>/gi, "\n")
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<[^>]*>/g, " ")
    .replace(/&nbsp;|&#160;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/\n[ \t]*\n/g, "\n");
}

function readAbilityScores(text: string): string[] {
  text = normalizeExtractedText(text);
  const rows = [...text.matchAll(/^[ 	]*STR[ 	]+DEX[ 	]+CON[ 	]+INT[ 	]+WIS[ 	]+CHA[ 	]*\r?\n([ 	0-9()+-]+)$/gim)];
  if (rows.length !== 1) return [];
  const row = rows[0][1].trim();
  const scoredCells = /([0-9](?:[ \t]*[0-9])*)[ \t]*\([ \t]*[+-]?[0-9]+[ \t]*\)/g;
  const cells = [...row.matchAll(scoredCells)];
  const scores = cells.length > 0
    ? (row.replace(scoredCells, "").trim() ? [] : cells.map(cell => cell[1].replace(/[ \t]/g, "")))
    : row.split(/[ \t]+/);
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

export function looksLikePdfStatblock(text: string): boolean {
  return /^\s*Armor Class\s*:?[ \t]*\d/im.test(text)
    || /^\s*Hit Points\s*:?[ \t]*\d/im.test(text)
    || /^\s*STR\s+DEX\s+CON\s+INT\s+WIS\s+CHA\s*$/im.test(text);
}

export function hasRecognizablePdfStatblockStructure(text: string): boolean {
  text = normalizeExtractedText(text);
  const lines = text.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
  const armor = Array.from(text.matchAll(/^[ \t]*Armor Class[ \t]*:?[ \t]*\d/gim));
  const hp = Array.from(text.matchAll(/^[ \t]*Hit Points[ \t]*:?[ \t]*\d/gim));
  const armorIndex = lines.findIndex(line => /^Armor Class\s*:?[ \t]*\d/i.test(line));
  const creatureType = /^(\w+)\b.+,\s*[^,]+$/i;
  const sizes = ["tiny", "small", "medium", "large", "huge", "gargantuan"];
  const typeLineIndices = lines.slice(0, Math.max(0, armorIndex)).flatMap((line, index) => {
    const size = creatureType.exec(line)?.[1].toLowerCase();
    if (!size) return [];
    return sizes.some(expected => expected.length === size.length &&
      [...expected].filter((character, position) => character !== size[position]).length <= 1)
      ? [index] : [];
  });
  const typeLineIndex = typeLineIndices.length === 1 ? typeLineIndices[0] : -1;
  const hpIndex = lines.findIndex(line => /^Hit Points\s*:?[ \t]*\d/i.test(line));
  const abilityIndex = lines.findIndex(line => /^STR\s+DEX\s+CON\s+INT\s+WIS\s+CHA$/i.test(line));

  return armor.length === 1
    && hp.length === 1
    && readAbilityScores(text).length === abilities.length
    && typeLineIndices.length === 1
    && armorIndex > typeLineIndex
    && hpIndex > armorIndex
    && abilityIndex > hpIndex;
}

export function PdfStatblockCandidate({text, locator}: {text: string; locator: PdfLocator}) {
  const [opened, setOpened] = useState(false);
  text = normalizeExtractedText(text);
  const armor = Array.from(text.matchAll(/^[ \t]*Armor Class[ \t]*:?[ \t]*(\d(?:[ \t]*\d)*)/gim));
  const hp = Array.from(text.matchAll(/^[ \t]*Hit Points[ \t]*:?[ \t]*(\d(?:[ \t]*\d)*)(?:[ \t]*\(([ \t]*\d(?:[ \t]*\d)*[ \t]*d[ \t]*\d(?:[ \t]*\d)*(?:[ \t]*[+−-][ \t]*\d(?:[ \t]*\d)*)?[ \t]*)\))?/gim));
  if (!looksLikePdfStatblock(text)) return null;
  if (!opened) return <button type="button" onClick={() => setOpened(true)}>Preview statblock fields</button>;

  const scores = readAbilityScores(text);
  const structured = hasRecognizablePdfStatblockStructure(text);
  const sections = structured && armor.length === 1 && hp.length === 1 ? readRulesSections(text) : [];
  return <section aria-label="Extracted statblock fields">
    <h4>Statblock candidate</h4>
    <p>Page {locator.page} · {locator.source_revision_id}</p>
    {structured ? <dl>
      <dt>Armor Class</dt><dd>{armor[0][1].replace(/\s/g, "")}</dd>
      <dt>Hit Points</dt><dd>{hp[0][1].replace(/\s/g, "")}{hp[0][2] && ` (${hp[0][2].trim().replace(/(\d)[ \t]+(?=\d)/g, "$1")})`}</dd>
      {scores.map((score, index) => <div key={abilities[index]}>
        <dt>{abilities[index]}</dt><dd>{score}</dd>
      </div>)}
    </dl> : <p>Select a region containing a creature type, Armor Class, Hit Points and all six ability scores.</p>}
    {sections.map(({ title, body }, index) => (
      <details key={index}>
        <summary>{title} · captured text</summary>
        <p style={{ whiteSpace: "pre-wrap" }}>{body}</p>
      </details>
    ))}
  </section>;
}
