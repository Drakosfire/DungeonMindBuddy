import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

const repoRoot = resolve(process.cwd(), "../..");
const livePlayPath = resolve(repoRoot, "evals/c2_live_prep/mireward-prep/live-play.html");
const runbookPath = resolve(repoRoot, "evals/c2_live_prep/mireward-prep/content/tiptap/north-gate-session-runbook.md");
const prepJsPath = resolve(repoRoot, "evals/c2_live_prep/mireward-prep/assets/prep.js");

describe("Live Play North Gate runbook surface", () => {
  it("presents the Tiptap-backed runbook as the table-facing surface", () => {
    const html = readFileSync(livePlayPath, "utf8");

    expect(html).toContain("content/tiptap/north-gate-session-runbook.md");
    expect(html).toContain("/tiptap-callout-spike");
    expect(html).not.toMatch(/\/tiptap-callout-spike\?doc=/);
    expect(html).not.toContain("dogfood runbook");
    expect(html).toContain("Edit runbook");
    expect(html).not.toContain("data-open-toolbox");
    expect(html).not.toContain("Ingest recap");
    expect(html).toContain("combat.html");
    expect(html).toContain("roll-tables.html");
    expect(html).toContain("npcs.html");
    expect(html).toContain("statblocks.html");
    expect(html).toContain("Editing workflow: open editor → import committed Markdown → edit locally → prepare file write → commit reviewed Markdown → reload Live Play.");
  });

  it("retires the prototype command toolbox chrome", () => {
    const js = readFileSync(prepJsPath, "utf8");

    expect(js).toContain("retireToolboxChrome");
    expect(js).toMatch(/function initToolbox\(\)\s*\{[\s\S]*?retireToolboxChrome\(\)/);
    expect(js).not.toMatch(/bootMirewardPrepChrome\(\)\s*\{[\s\S]*?initToolbox\(\)/);
  });

  it("keeps the North Gate runbook artifact contract", () => {
    const markdown = readFileSync(runbookPath, "utf8");

    expect(markdown).toContain("# C2S23 Mireward Reach North Gate Runbook");
    expect(markdown).toContain("> [!READ-ALOUD]");
    expect(markdown).toContain("> [!GM-NOTE]");
    expect(markdown).toContain("> [!RULES]");
    expect(markdown).toContain("> [!WARNING]");
    expect(markdown).toContain("#dmb-ref:npc:lysandro-ironveil");
    expect(markdown).toContain("#dmb-ref:statblock:sewer-meat-creature");
    expect(markdown).toContain("#dmb-ref:roll-table:gate-dilemma-d12");
    expect(markdown).toContain("#dmb-ref:citation:c2s23-memory");
    expect(markdown).toContain("#dmb-action:combat:north-gate-combat");
    expect(markdown).toContain("Hard boundaries");
  });
});
