import { readFileSync } from "node:fs";

import { tiptapJsonToSemanticMarkdown } from "./calloutMarkdown";
import { markdownToTiptapDoc } from "./markdownToTiptap";

describe("markdownToTiptapDoc", () => {
  it("imports headings and paragraphs", () => {
    const result = markdownToTiptapDoc("# Title\n\n## Section\n\nA normal paragraph.");

    expect(result.doc.content).toEqual([
      { type: "heading", attrs: { level: 1 }, content: [{ type: "text", text: "Title" }] },
      { type: "heading", attrs: { level: 2 }, content: [{ type: "text", text: "Section" }] },
      { type: "paragraph", content: [{ type: "text", text: "A normal paragraph." }] },
    ]);
  });

  it("imports typed ref links as runbookReference nodes", () => {
    const result = markdownToTiptapDoc("Talk to [Lysandro Ironveil](#dmb-ref:npc:lysandro-ironveil).");

    expect(result.doc.content).toEqual([
      {
        type: "paragraph",
        content: [
          { type: "text", text: "Talk to " },
          {
            type: "runbookReference",
            attrs: { kind: "ref", refType: "npc", refId: "lysandro-ironveil", label: "Lysandro Ironveil" },
          },
          { type: "text", text: "." },
        ],
      },
    ]);
  });

  it("imports action links as runbookReference nodes", () => {
    const result = markdownToTiptapDoc("Launch [North Gate Combat](#dmb-action:combat:north-gate-combat).");
    const paragraph = result.doc.content[0] as { content: Array<{ attrs?: Record<string, unknown> }> };

    expect(paragraph.content[1].attrs).toMatchObject({ kind: "action", refType: "combat", refId: "north-gate-combat" });
  });

  it("imports semantic callouts", () => {
    const result = markdownToTiptapDoc("> [!GM-NOTE]\n> Keep this about triage.");

    expect(result.doc.content).toEqual([
      {
        type: "callout",
        attrs: { kind: "gm-note" },
        content: [{ type: "paragraph", content: [{ type: "text", text: "Keep this about triage." }] }],
      },
    ]);
  });

  it("imports bullet lists and preserves references in items", () => {
    const result = markdownToTiptapDoc("- First\n- Use [Gate Dilemma d12](#dmb-ref:roll-table:gate-dilemma-d12)");

    expect(result.doc.content).toEqual([
      {
        type: "bulletList",
        content: [
          { type: "listItem", content: [{ type: "paragraph", content: [{ type: "text", text: "First" }] }] },
          {
            type: "listItem",
            content: [{
              type: "paragraph",
              content: [
                { type: "text", text: "Use " },
                { type: "runbookReference", attrs: { kind: "ref", refType: "roll-table", refId: "gate-dilemma-d12", label: "Gate Dilemma d12" } },
              ],
            }],
          },
        ],
      },
    ]);
  });

  it("imports and re-exports the real north gate runbook smoke fixture", () => {
    const markdown = readFileSync("../../evals/c2_live_prep/mireward-prep/content/tiptap/north-gate-session-runbook.md", "utf8");
    const imported = markdownToTiptapDoc(markdown);
    const exported = tiptapJsonToSemanticMarkdown(imported.doc);

    expect(exported).toContain("# C2S23 North Gate Session Runbook");
    expect(exported).toContain("#dmb-ref:npc:lysandro-ironveil");
    expect(exported).toContain("#dmb-ref:location:north-reach-gate");
    expect(exported).toContain("#dmb-ref:statblock:sewer-meat-creature");
    expect(exported).toContain("#dmb-ref:roll-table:gate-dilemma-d12");
    expect(exported).toContain("#dmb-ref:citation:c2s22-ending");
    expect(exported).toContain("#dmb-action:combat:north-gate-combat");
    expect(exported).toContain("> [!READ-ALOUD]");
    expect(exported).toContain("> [!GM-NOTE]");
    expect(exported).toContain("> [!RULES]");
    expect(exported).toContain("> [!WARNING]");
  });
});
