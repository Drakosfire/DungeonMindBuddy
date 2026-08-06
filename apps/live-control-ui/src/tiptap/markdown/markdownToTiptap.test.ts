import { readFileSync } from "node:fs";

import { tiptapJsonToSemanticMarkdown } from "./calloutMarkdown";
import { markdownToTiptapDoc } from "./markdownToTiptap";

const NULL_SCOPE = {
  graphWorldId: null,
  graphCampaignId: null,
  graphScopeMode: null,
  graphRevisionId: null,
} as const;

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
            attrs: {
              kind: "ref",
              refType: "npc",
              refId: "lysandro-ironveil",
              label: "Lysandro Ironveil",
              ...NULL_SCOPE,
            },
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

  it("imports graph node links only when requested", () => {
    const markdown = "Inspect [Caelynn](dmb-node:pc_caelynn).";
    const defaultImport = markdownToTiptapDoc(markdown);
    const graphImport = markdownToTiptapDoc(markdown, { parseGraphNodeLinks: true });

    expect(defaultImport.doc.content).toEqual([
      { type: "paragraph", content: [{ type: "text", text: markdown }] },
    ]);
    expect(graphImport.doc.content).toEqual([
      {
        type: "paragraph",
        content: [
          { type: "text", text: "Inspect " },
          {
            type: "graphNodeReference",
            attrs: { nodeId: "pc_caelynn", label: "Caelynn" },
          },
          { type: "text", text: "." },
        ],
      },
    ]);
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
                { type: "runbookReference", attrs: { kind: "ref", refType: "roll-table", refId: "gate-dilemma-d12", label: "Gate Dilemma d12", ...NULL_SCOPE } },
              ],
            }],
          },
        ],
      },
    ]);
  });

  it("imports complete scoped graph-node refs", () => {
    const markdown =
      "Track [Mireward Latchling](#dmb-ref:graph-node:threat:authored:d16d43d376833e38caf46dd19b1dd17f?world=eldyrwild&campaign=longmont-c2&scope=campaign&revision=rev%3A3413bf6f5044cf2680233f5e37c90dcf).";
    const result = markdownToTiptapDoc(markdown);
    const paragraph = result.doc.content[0] as { content: Array<{ type: string; attrs?: Record<string, unknown> }> };

    expect(paragraph.content[1]).toEqual({
      type: "runbookReference",
      attrs: {
        kind: "ref",
        refType: "graph-node",
        refId: "threat:authored:d16d43d376833e38caf46dd19b1dd17f",
        label: "Mireward Latchling",
        graphWorldId: "eldyrwild",
        graphCampaignId: "longmont-c2",
        graphScopeMode: "campaign",
        graphRevisionId: "rev:3413bf6f5044cf2680233f5e37c90dcf",
      },
    });
  });

  it("keeps partial or invalid scoped refs as plain text", () => {
    const partial =
      "Broken [Latchling](#dmb-ref:graph-node:threat:authored:abc?world=eldyrwild&campaign=longmont-c2&scope=campaign).";
    const duplicate =
      "Broken [Latchling](#dmb-ref:graph-node:threat:authored:abc?world=a&world=b&campaign=c&scope=campaign&revision=rev%3A1).";
    const npcScoped =
      "Broken [Lysandro](#dmb-ref:npc:lysandro-ironveil?world=eldyrwild&campaign=longmont-c2&scope=campaign&revision=rev%3A1).";

    for (const markdown of [partial, duplicate, npcScoped]) {
      const result = markdownToTiptapDoc(markdown);
      const paragraph = result.doc.content[0] as { content: Array<{ type: string; text?: string }> };
      expect(paragraph.content.every((node) => node.type === "text")).toBe(true);
      expect(paragraph.content.map((node) => node.text ?? "").join("")).toBe(markdown);
    }
  });

  it("imports and re-exports the real north gate runbook smoke fixture", () => {
    const markdown = readFileSync("../../evals/c2_live_prep/mireward-prep/content/tiptap/north-gate-session-runbook.md", "utf8");
    const imported = markdownToTiptapDoc(markdown);
    const exported = tiptapJsonToSemanticMarkdown(imported.doc);

    expect(exported).toContain("# C2S23 Mireward Reach North Gate Runbook");
    expect(exported).toContain("#dmb-ref:npc:lysandro-ironveil");
    expect(exported).toContain("#dmb-ref:statblock:sewer-meat-creature");
    expect(exported).toContain("#dmb-ref:roll-table:gate-dilemma-d12");
    expect(exported).toContain("#dmb-ref:citation:c2s23-memory");
    expect(exported).toContain("#dmb-action:combat:north-gate-combat");
    expect(exported).toContain("> [!READ-ALOUD]");
    expect(exported).toContain("> [!GM-NOTE]");
    expect(exported).toContain("> [!RULES]");
    expect(exported).toContain("> [!WARNING]");
  });
});
