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

  it("imports H1-H6 symmetrically with the serializer", () => {
    const markdown = ["# One", "## Two", "### Three", "#### Four", "##### Five", "###### Six", ""].join("\n");
    const imported = markdownToTiptapDoc(markdown);
    expect(imported.doc.content?.map((node) => Number(node.attrs?.level))).toEqual([1, 2, 3, 4, 5, 6]);
    const exported = tiptapJsonToSemanticMarkdown(imported.doc);
    expect(markdownToTiptapDoc(exported).doc).toEqual(imported.doc);
  });

  it("keeps YAML frontmatter outside the TipTap document", () => {
    const imported = markdownToTiptapDoc("---\ntitle: Session 2 Prep\nsession: 2\n---\n# Body\n");
    expect(imported.diagnostics).toEqual([]);
    expect(imported.doc.content).toEqual([
      { type: "heading", attrs: { level: 1 }, content: [{ type: "text", text: "Body" }] },
    ]);
  });

  it("imports the inline marks mounted by StarterKit", () => {
    const imported = markdownToTiptapDoc("**Bold** *italic* ~~strike~~ `code`");
    const paragraph = imported.doc.content?.[0] as {
      content?: Array<{ text?: string; marks?: Array<{ type: string }> }>;
    };
    expect(paragraph.content?.find((node) => node.text === "Bold")?.marks).toEqual([{ type: "bold" }]);
    expect(paragraph.content?.find((node) => node.text === "italic")?.marks).toEqual([{ type: "italic" }]);
    expect(paragraph.content?.find((node) => node.text === "strike")?.marks).toEqual([{ type: "strike" }]);
    expect(paragraph.content?.find((node) => node.text === "code")?.marks).toEqual([{ type: "code" }]);
  });

  it("fails closed on ordinary Markdown links instead of emitting an unmounted link mark", () => {
    const imported = markdownToTiptapDoc("Read [the rules](https://example.com/rules).");
    expect(imported.diagnostics).toEqual(expect.arrayContaining([
      expect.objectContaining({ level: "warning", line: 1 }),
    ]));
    expect(JSON.stringify(imported.doc)).not.toContain('"type":"link"');
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
    const paragraph = result.doc.content?.[0] as { content: Array<{ attrs?: Record<string, unknown> }> };
    expect(paragraph.content[1].attrs).toMatchObject({ kind: "action", refType: "combat", refId: "north-gate-combat" });
  });

  it("imports graph node links by default and round-trips through export", () => {
    const markdown = "Inspect [Caelynn](dmb-node:pc_caelynn).";
    const imported = markdownToTiptapDoc(markdown);
    expect(imported.diagnostics).toEqual([]);
    expect(imported.doc.content).toEqual([
      {
        type: "paragraph",
        content: [
          { type: "text", text: "Inspect " },
          { type: "graphNodeReference", attrs: { nodeId: "pc_caelynn", label: "Caelynn" } },
          { type: "text", text: "." },
        ],
      },
    ]);
    expect(tiptapJsonToSemanticMarkdown(imported.doc)).toBe(`${markdown}\n`);
  });

  it("warns when graph node links are explicitly disabled", () => {
    const markdown = "Inspect [Caelynn](dmb-node:pc_caelynn).";
    const imported = markdownToTiptapDoc(markdown, { parseGraphNodeLinks: false });
    expect(imported.diagnostics).toEqual(expect.arrayContaining([
      expect.objectContaining({ level: "warning", line: 1 }),
    ]));
    expect(imported.doc.content).toEqual([
      { type: "paragraph", content: [{ type: "text", text: markdown }] },
    ]);
  });

  it("keeps snake_case identifiers as literal text without intraword underscore emphasis", () => {
    const markdown = "Use snake_case_value here and _italic_ emphasis.";
    const imported = markdownToTiptapDoc(markdown);
    const paragraph = imported.doc.content?.[0] as {
      content?: Array<{ text?: string; marks?: Array<{ type: string }> }>;
    };
    expect(paragraph.content?.find((node) => node.text === "snake_case_value")?.marks).toBeUndefined();
    expect(paragraph.content?.find((node) => node.text === "italic")?.marks).toEqual([{ type: "italic" }]);
    expect(tiptapJsonToSemanticMarkdown(imported.doc)).toBe("Use snake_case_value here and *italic* emphasis.\n");
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

  it("keeps stacked sibling callouts as separate semantic blocks", () => {
    const result = markdownToTiptapDoc([
      "> [!GM-NOTE]",
      "> First note.",
      "> [!WARNING]",
      "> Second note.",
      "",
    ].join("\n"));
    expect(result.diagnostics).toEqual([]);
    expect(result.doc.content?.map((node) => node.type)).toEqual(["callout", "callout"]);
    expect(tiptapJsonToSemanticMarkdown(result.doc)).toContain(
      "> [!GM-NOTE]\n> First note.\n\n> [!WARNING]\n> Second note.",
    );
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

  it("round-trips horizontal rules instead of treating them as unsafe source", () => {
    const markdown = "# Before\n\n---\n\n## After\n";
    const imported = markdownToTiptapDoc(markdown);
    expect(imported.diagnostics).toEqual([]);
    expect(imported.doc.content?.[1]).toEqual({ type: "horizontalRule" });
    expect(tiptapJsonToSemanticMarkdown(imported.doc)).toBe(markdown);
  });

  it("round-trips GFM tables without splitting escaped pipes", () => {
    const markdown = [
      "Threat | Note",
      "--- | ---",
      "Latchling | A \\| B",
      "Meat Mind | `range | aura`",
      "",
    ].join("\n");
    const imported = markdownToTiptapDoc(markdown);
    const table = imported.doc.content?.[0] as { content?: Array<{ content?: unknown[] }> };
    expect(imported.diagnostics).toEqual([]);
    expect(table.content?.length).toBe(3);
    expect((table.content?.[1].content ?? []).length).toBe(2);

    const exported = tiptapJsonToSemanticMarkdown(imported.doc);
    expect(exported).toContain("Latchling | A \\| B");
    expect(exported).toContain("Meat Mind | `range \\| aura`");

    const reimported = markdownToTiptapDoc(exported);
    const reimportedTable = reimported.doc.content?.[0] as { content?: Array<{ content?: unknown[] }> };
    expect((reimportedTable.content?.[1].content ?? []).length).toBe(2);
    expect((reimportedTable.content?.[2].content ?? []).length).toBe(2);
  });

  it("fails closed when table alignment would be lost", () => {
    const imported = markdownToTiptapDoc("Name | Role\n:--- | ---:\nLysandra | Captain\n");
    expect(imported.diagnostics).toEqual(expect.arrayContaining([
      expect.objectContaining({ level: "warning", line: 2 }),
    ]));
  });

  it("fails closed when an uneven table row would be truncated or padded", () => {
    const imported = markdownToTiptapDoc("Name | Role\n--- | ---\nLysandra | Captain | Guard\n");
    expect(imported.diagnostics).toEqual(expect.arrayContaining([
      expect.objectContaining({ level: "warning", line: 3 }),
    ]));
  });

  it("fails closed on aligned tables inside callouts via the table parse path", () => {
    const imported = markdownToTiptapDoc([
      "> [!GM-NOTE]",
      "> Name | Role",
      "> :--- | ---:",
      "> Lysandra | Captain",
      "",
    ].join("\n"));
    expect(imported.diagnostics).toEqual(expect.arrayContaining([
      expect.objectContaining({ level: "warning", line: 3 }),
    ]));
  });

  it("fails closed on uneven table rows inside callouts via the table parse path", () => {
    const imported = markdownToTiptapDoc([
      "> [!GM-NOTE]",
      "> Name | Role",
      "> --- | ---",
      "> Lysandra | Captain | Guard",
      "",
    ].join("\n"));
    expect(imported.diagnostics).toEqual(expect.arrayContaining([
      expect.objectContaining({ level: "warning", line: 4 }),
    ]));
  });

  it("emits blocking diagnostics for source blocks the rich editor cannot preserve", () => {
    const imported = markdownToTiptapDoc("# Prep\n\n```json\n{\"hp\": 95}\n```\n");
    expect(imported.diagnostics).toEqual(expect.arrayContaining([
      expect.objectContaining({ level: "warning", line: 3 }),
    ]));
  });

  it("fails closed on Setext headings and explicit hard breaks", () => {
    const imported = markdownToTiptapDoc("Legacy title\n===\n\nLine one  \nLine two\n");
    expect(imported.diagnostics).toEqual(expect.arrayContaining([
      expect.objectContaining({ level: "warning", line: 2 }),
      expect.objectContaining({ level: "warning", line: 4 }),
    ]));
  });

  it("fails closed on Session-26 structures owned by the next semantic polish slice", () => {
    const imported = markdownToTiptapDoc([
      "- Decision forks",
      "  - > [!DECISION-CONSEQUENCE]",
      "    > ### Decision",
      "    > Hold the wall",
      "",
    ].join("\n"));
    expect(imported.diagnostics).toEqual(expect.arrayContaining([
      expect.objectContaining({ level: "warning", line: 2 }),
      expect.objectContaining({ level: "warning", line: 3 }),
    ]));
  });

  it("fails closed on an unknown top-level callout marker", () => {
    const imported = markdownToTiptapDoc("> [!DECISION-CONSEQUENCE]\n> ### Decision\n> Hold the wall\n");
    expect(imported.diagnostics).toEqual(expect.arrayContaining([
      expect.objectContaining({ level: "warning", line: 1 }),
    ]));
  });

  it("keeps the real Session 2 Prep corpus structure safely editable", () => {
    const markdown = readFileSync(
      "../../corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/Session 2 Prep.md",
      "utf8",
    );
    const imported = markdownToTiptapDoc(markdown);
    const exportedBody = tiptapJsonToSemanticMarkdown(imported.doc);
    const reimported = markdownToTiptapDoc(exportedBody);
    expect(imported.diagnostics).toEqual([]);
    expect(exportedBody).toContain("#### 🪕 5:00 PM – Bardic Showcase at the Glimmering Globe");
    expect(reimported.doc).toEqual(imported.doc);
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
