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
    expect(html).toContain("/tiptap-callout-spike?doc=north-gate-session-runbook");
    expect(html).not.toContain("dogfood runbook");
    expect(html).toContain("Edit runbook");
    expect(html).toContain('data-open-toolbox="ingestion"');
    expect(html).toContain("Ingest recap");
    expect(html).toContain("combat.html");
    expect(html).toContain("roll-tables.html");
    expect(html).toContain("npcs.html");
    expect(html).toContain("statblocks.html");
    expect(html).toContain("Editing workflow: open editor → import committed Markdown → edit locally → prepare file write → commit reviewed Markdown → reload Live Play.");
  });

  it("mounts recap ingestion as the default toolbox tool", () => {
    const js = readFileSync(prepJsPath, "utf8");

    expect(js).toContain('data-toolbox-tool="ingestion"');
    expect(js).toContain("Raw recap text");
    expect(js).toContain("Rendered markdown preview");
    expect(js).toContain('get("toolboxTool", "ingestion")');
    expect(js).toContain('data-toolbox-tool="statblock"');
    expect(js).toContain("Statblock generator");
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
