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

  it("strips leading YAML frontmatter so callouts and headings render", () => {
    const markdown = [
      "---",
      'title: "Session 26 Prep"',
      "session: 26",
      "---",
      "",
      "# C2 Session 26 Prep",
      "",
      "> [!READ-ALOUD]",
      "> The bells feel far away.",
      "",
    ].join("\n");

    const result = markdownToTiptapDoc(markdown);
    const types = (result.doc.content ?? []).map((node) => (node as { type: string }).type);
    expect(types).toEqual(["heading", "callout"]);
    expect(JSON.stringify(result.doc)).not.toContain("document_class");
    expect(JSON.stringify(result.doc)).toContain("The bells feel far away.");
  });

  it("imports recovered Session 26 Prep without leaking frontmatter into the board", () => {
    const markdown = readFileSync(
      "../../corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/Session 26 Prep.md",
      "utf8",
    );
    const { doc } = markdownToTiptapDoc(markdown);
    const types = (doc.content ?? []).map((node) => (node as { type: string }).type);
    expect(types[0]).toBe("heading");
    expect(types).toContain("callout");
    expect(JSON.stringify(doc)).not.toContain("document_class");
    expect(JSON.stringify(doc)).toContain("doom is approaching");
    expect(JSON.stringify(doc)).toContain('"type":"table"');
    expect(JSON.stringify(doc)).toContain("Stafl");
  });

  it("imports bold/italic/code marks instead of raw markdown tokens", () => {
    const result = markdownToTiptapDoc("Keep **Stafl** on the *wall* with `Eldritch Blast`.");
    expect(result.doc.content).toEqual([
      {
        type: "paragraph",
        content: [
          { type: "text", text: "Keep " },
          { type: "text", text: "Stafl", marks: [{ type: "bold" }] },
          { type: "text", text: " on the " },
          { type: "text", text: "wall", marks: [{ type: "italic" }] },
          { type: "text", text: " with " },
          { type: "text", text: "Eldritch Blast", marks: [{ type: "code" }] },
          { type: "text", text: "." },
        ],
      },
    ]);
  });

  it("imports GFM tables inside GM-NOTE callouts with bold cells", () => {
    const markdown = [
      "> [!GM-NOTE]",
      "> **Who/Where during the hybrid fight**",
      ">",
      "> | Who | Position |",
      "> | --- | --- |",
      "> | **Stafl** | On the wall |",
      "> | **Thrin** | Field scout |",
      "",
    ].join("\n");

    const { doc } = markdownToTiptapDoc(markdown);
    const callout = doc.content?.[0] as {
      type: string;
      content: Array<{ type: string; content?: unknown[] }>;
    };
    expect(callout.type).toBe("callout");
    expect(callout.content[0]).toMatchObject({
      type: "paragraph",
      content: [{ type: "text", text: "Who/Where during the hybrid fight", marks: [{ type: "bold" }] }],
    });
    expect(callout.content[1]?.type).toBe("table");

    const exported = tiptapJsonToSemanticMarkdown(doc);
    expect(exported).toContain("| Who | Position |");
    expect(exported).toContain("| **Stafl** | On the wall |");
    expect(exported).toContain("| **Thrin** | Field scout |");
  });
});
