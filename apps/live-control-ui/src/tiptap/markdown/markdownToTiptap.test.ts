import { readFileSync } from "node:fs";

import { tiptapJsonToSemanticMarkdown } from "./calloutMarkdown";
import { markdownToTiptapDoc } from "./markdownToTiptap";
import { semanticMarkdownSerializationDiagnostics } from "./semanticMarkdownSafety";

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

  it("fails closed on graph node links with an empty node id instead of dropping the link on save", () => {
    const markdown = "See [x](dmb-node:) here.";
    const imported = markdownToTiptapDoc(markdown);
    expect(imported.diagnostics).toEqual(expect.arrayContaining([
      expect.objectContaining({
        level: "warning",
        line: 1,
        message: "Graph node links must target a valid, non-empty node id.",
      }),
    ]));
    // Sealed projection: literal source text, no opaque reference node.
    expect(JSON.stringify(imported.doc)).not.toContain("graphNodeReference");
    const exported = tiptapJsonToSemanticMarkdown(imported.doc);
    expect(exported).toContain("dmb-node:");
    const reimported = markdownToTiptapDoc(exported);
    expect(reimported.doc).toEqual(imported.doc);
  });

  it("fails closed on reference labels whose formatting the opaque nodes cannot preserve", () => {
    const cases = [
      "Inspect [**Caelynn**](dmb-node:pc_caelynn).",
      "Talk to [**Lysandro**](#dmb-ref:npc:lysandro-ironveil).",
      "Launch [`North Gate`](#dmb-action:combat:north-gate-combat).",
    ];
    for (const markdown of cases) {
      const imported = markdownToTiptapDoc(markdown);
      expect(imported.diagnostics).toEqual(expect.arrayContaining([
        expect.objectContaining({
          level: "warning",
          line: 1,
          message: "Formatted link labels are not represented by DungeonBuddy reference nodes.",
        }),
      ]));
      const serialized = JSON.stringify(imported.doc);
      expect(serialized).not.toContain("graphNodeReference");
      expect(serialized).not.toContain("runbookReference");
      // The sealed source spelling survives export as escaped literal text.
      const reimported = markdownToTiptapDoc(tiptapJsonToSemanticMarkdown(imported.doc));
      expect(reimported.doc).toEqual(imported.doc);
    }
  });

  it("fails closed on empty or whitespace-only reference labels instead of inventing an id label", () => {
    const cases = [
      "[](dmb-node:pc_caelynn)",
      "[ ](dmb-node:pc_caelynn)",
      "[](#dmb-ref:npc:lysandro-ironveil)",
      "[  ](#dmb-ref:npc:lysandro-ironveil)",
      "[](#dmb-action:combat:north-gate-combat)",
    ];
    for (const markdown of cases) {
      const imported = markdownToTiptapDoc(markdown);
      expect(imported.diagnostics).toEqual(expect.arrayContaining([
        expect.objectContaining({
          level: "warning",
          line: 1,
          message: "Empty reference labels are not preserved by DungeonBuddy reference nodes.",
        }),
      ]));
      const serialized = JSON.stringify(imported.doc);
      expect(serialized).not.toContain("graphNodeReference");
      expect(serialized).not.toContain("runbookReference");
      // Empty-label rewrite class: without sealing, save would emit [id](...).
      const exported = tiptapJsonToSemanticMarkdown(imported.doc);
      expect(exported).not.toMatch(/\[pc_caelynn\]\(dmb-node:pc_caelynn\)/);
      expect(exported).not.toMatch(/\[lysandro-ironveil\]\(#dmb-ref:npc:lysandro-ironveil\)/);
      expect(exported).not.toMatch(/\[north-gate-combat\]\(#dmb-action:combat:north-gate-combat\)/);
      const reimported = markdownToTiptapDoc(exported);
      expect(reimported.doc).toEqual(imported.doc);
    }
  });

  it("preserves parser-decoded literal emphasis characters in reference labels", () => {
    const cases = [
      {
        markdown: String.raw`Inspect [\*\*Meat Mind\*\*](dmb-node:threat:meat-mind).`,
        expectedLabel: "**Meat Mind**",
        nodeType: "graphNodeReference",
      },
      {
        markdown: String.raw`Inspect [\_\_Meat Mind\_\_](dmb-node:threat:meat-mind).`,
        expectedLabel: "__Meat Mind__",
        nodeType: "graphNodeReference",
      },
      {
        markdown: String.raw`Talk to [\*\*Lysandro\*\*](#dmb-ref:npc:lysandro-ironveil).`,
        expectedLabel: "**Lysandro**",
        nodeType: "runbookReference",
      },
      {
        markdown: String.raw`Talk to [\_\_Lysandro\_\_](#dmb-ref:npc:lysandro-ironveil).`,
        expectedLabel: "__Lysandro__",
        nodeType: "runbookReference",
      },
      {
        markdown: String.raw`Launch [\*\*North Gate\*\*](#dmb-action:combat:north-gate-combat).`,
        expectedLabel: "**North Gate**",
        nodeType: "runbookReference",
      },
      {
        markdown: String.raw`Launch [\_\_North Gate\_\_](#dmb-action:combat:north-gate-combat).`,
        expectedLabel: "__North Gate__",
        nodeType: "runbookReference",
      },
    ] as const;

    for (const { markdown, expectedLabel, nodeType } of cases) {
      const imported = markdownToTiptapDoc(markdown);
      expect(imported.diagnostics).toEqual([]);
      const paragraph = imported.doc.content?.[0] as {
        content?: Array<{ type?: string; attrs?: { label?: string } }>;
      };
      const ref = paragraph.content?.find((node) => node.type === nodeType);
      expect(ref?.attrs?.label).toBe(expectedLabel);
      // Serializer must re-escape literal * / _ rather than dropping them.
      const exported = tiptapJsonToSemanticMarkdown(imported.doc);
      expect(exported).toContain(expectedLabel.replaceAll("*", "\\*").replaceAll("_", "\\_"));
      expect(exported).not.toContain(`[${expectedLabel.replace(/^\*+|\*+$/g, "").replace(/^_+|_+$/g, "")}]`);
      const reimported = markdownToTiptapDoc(exported);
      expect(reimported.doc).toEqual(imported.doc);
      expect(reimported.diagnostics).toEqual([]);
    }
  });

  it("keeps snake_case identifiers as literal text without intraword underscore emphasis", () => {
    const markdown = "Use snake_case_value here and _italic_ emphasis.";
    const imported = markdownToTiptapDoc(markdown);
    const paragraph = imported.doc.content?.[0] as {
      content?: Array<{ text?: string; marks?: Array<{ type: string }> }>;
    };
    expect(paragraph.content?.find((node) => node.text === "snake_case_value")?.marks).toBeUndefined();
    expect(paragraph.content?.find((node) => node.text === "italic")?.marks).toEqual([{ type: "italic" }]);
    // Serializer escapes literal underscores so reimport cannot gain emphasis.
    expect(tiptapJsonToSemanticMarkdown(imported.doc)).toBe(
      "Use snake\\_case\\_value here and *italic* emphasis.\n",
    );
    const reimported = markdownToTiptapDoc(tiptapJsonToSemanticMarkdown(imported.doc));
    expect(reimported.doc).toEqual(imported.doc);
  });

  it("keeps double-underscore identifiers as literal text without intraword bold", () => {
    const markdown = "Use foo__bar__baz here and __bold__ emphasis.";
    const imported = markdownToTiptapDoc(markdown);
    const paragraph = imported.doc.content?.[0] as {
      content?: Array<{ text?: string; marks?: Array<{ type: string }> }>;
    };
    expect(paragraph.content?.find((node) => node.text === "foo__bar__baz")?.marks).toBeUndefined();
    expect(paragraph.content?.find((node) => node.text === "bold")?.marks).toEqual([{ type: "bold" }]);
    expect(tiptapJsonToSemanticMarkdown(imported.doc)).toBe(
      "Use foo\\_\\_bar\\_\\_baz here and **bold** emphasis.\n",
    );
    const reimported = markdownToTiptapDoc(tiptapJsonToSemanticMarkdown(imported.doc));
    expect(reimported.doc).toEqual(imported.doc);
  });

  it("keeps escaped underscore and tilde literals stable across import → serialize → reimport", () => {
    const underscoreSource = String.raw`Keep \_literal\_ unmarked.`;
    const tildeSource = String.raw`Keep \~\~literal\~\~ unmarked.`;
    for (const markdown of [underscoreSource, tildeSource]) {
      const imported = markdownToTiptapDoc(markdown);
      const paragraph = imported.doc.content?.[0] as {
        content?: Array<{ text?: string; marks?: Array<{ type: string }> }>;
      };
      const text = paragraph.content?.map((node) => node.text ?? "").join("") ?? "";
      expect(text.includes("literal")).toBe(true);
      expect(paragraph.content?.some((node) => node.marks?.length)).toBeFalsy();
      const exported = tiptapJsonToSemanticMarkdown(imported.doc);
      const reimported = markdownToTiptapDoc(exported);
      expect(reimported.doc).toEqual(imported.doc);
      expect(reimported.diagnostics).toEqual([]);
    }
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

  it("fails closed on non-canonical thematic break spellings instead of reinterpreting them as prose", () => {
    for (const markdown of ["***", "___", "- - -"]) {
      const imported = markdownToTiptapDoc(markdown);
      expect(imported.diagnostics).toEqual(expect.arrayContaining([
        expect.objectContaining({
          level: "warning",
          line: 1,
          message: "Only --- thematic breaks are supported by this editor slice.",
        }),
      ]));
      // Sealed projection: literal source text, never a horizontalRule.
      expect(imported.doc.content).toEqual([
        { type: "paragraph", content: [{ type: "text", text: markdown }] },
      ]);
      // The serializer escapes the sealed text so it reimports stably as text.
      const reimported = markdownToTiptapDoc(tiptapJsonToSemanticMarkdown(imported.doc));
      expect(reimported.doc).toEqual(imported.doc);
    }
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

  it("fails closed when ordinary links inside table cells would be destroyed on export", () => {
    const imported = markdownToTiptapDoc([
      "Threat | Note",
      "--- | ---",
      "Latchling | See [wiki](https://example.com/latchling)",
      "",
    ].join("\n"));
    expect(imported.diagnostics).toEqual(expect.arrayContaining([
      expect.objectContaining({
        level: "warning",
        line: 3,
        message: expect.stringContaining("Ordinary Markdown links"),
      }),
    ]));
    const exported = tiptapJsonToSemanticMarkdown(imported.doc);
    expect(exported).not.toContain("](https://example.com/latchling)");
  });

  it("fails closed when ordinary links inside callout table cells would be destroyed", () => {
    const imported = markdownToTiptapDoc([
      "> [!GM-NOTE]",
      "> Threat | Note",
      "> --- | ---",
      "> Latchling | See [wiki](https://example.com/latchling)",
      "",
    ].join("\n"));
    expect(imported.diagnostics).toEqual(expect.arrayContaining([
      expect.objectContaining({
        level: "warning",
        line: 4,
        message: expect.stringContaining("Ordinary Markdown links"),
      }),
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

  it("imports canonical top-level Decision/Consequence with two ordered panes", () => {
    const imported = markdownToTiptapDoc([
      "> [!DECISION-CONSEQUENCE]",
      "> ### Decision",
      "> Hold the wall",
      ">",
      "> ### Consequence",
      "> - Pressure stays at the gate.",
      "",
    ].join("\n"));
    expect(imported.diagnostics).toEqual([]);
    expect(imported.doc.content).toEqual([
      {
        type: "decisionConsequence",
        content: [
          {
            type: "decisionPane",
            content: [{ type: "paragraph", content: [{ type: "text", text: "Hold the wall" }] }],
          },
          {
            type: "consequencePane",
            content: [{
              type: "bulletList",
              content: [{
                type: "listItem",
                content: [{ type: "paragraph", content: [{ type: "text", text: "Pressure stays at the gate." }] }],
              }],
            }],
          },
        ],
      },
    ]);
    const exported = tiptapJsonToSemanticMarkdown(imported.doc);
    expect(exported).toBe([
      "> [!DECISION-CONSEQUENCE]",
      "> ### Decision",
      "> Hold the wall",
      ">",
      "> ### Consequence",
      "> - Pressure stays at the gate.",
      "",
    ].join("\n"));
    const reimported = markdownToTiptapDoc(exported);
    expect(reimported.diagnostics).toEqual([]);
    expect(reimported.doc).toEqual(imported.doc);
  });

  it("fails closed on malformed Decision/Consequence blocks", () => {
    const malformedMessage =
      "Decision/Consequence blocks must contain exactly one Decision pane and one Consequence pane.";
    const cases: Array<{ name: string; markdown: string; message: string }> = [
      {
        name: "missing Consequence",
        markdown: "> [!DECISION-CONSEQUENCE]\n> ### Decision\n> Hold the wall\n",
        message: malformedMessage,
      },
      {
        name: "missing Decision",
        markdown: "> [!DECISION-CONSEQUENCE]\n> ### Consequence\n> Fall back\n",
        message: malformedMessage,
      },
      {
        name: "reversed panes",
        markdown: "> [!DECISION-CONSEQUENCE]\n> ### Consequence\n> B\n>\n> ### Decision\n> A\n",
        message: "Decision must precede Consequence in Decision/Consequence blocks.",
      },
      {
        name: "duplicate Decision",
        markdown: "> [!DECISION-CONSEQUENCE]\n> ### Decision\n> A\n>\n> ### Decision\n> B\n>\n> ### Consequence\n> C\n",
        message: malformedMessage,
      },
      {
        name: "wrong heading level",
        markdown: "> [!DECISION-CONSEQUENCE]\n> ## Decision\n> A\n>\n> ### Consequence\n> B\n",
        message: "Decision/Consequence pane headings must be level-3 headings with exact labels.",
      },
      {
        name: "near-match heading",
        markdown: "> [!DECISION-CONSEQUENCE]\n> ### Decision-ish\n> A\n>\n> ### Consequence\n> B\n",
        message: "Decision/Consequence pane headings must be level-3 headings with exact labels.",
      },
    ];
    for (const testCase of cases) {
      const imported = markdownToTiptapDoc(testCase.markdown);
      expect(imported.diagnostics, testCase.name).toEqual(expect.arrayContaining([
        expect.objectContaining({ level: "warning", message: testCase.message }),
      ]));
      expect(JSON.stringify(imported.doc), testCase.name).not.toContain('"type":"decisionConsequence"');
    }
  });

  it("imports nested bullet lists inside list items cleanly", () => {
    const imported = markdownToTiptapDoc("- Parent\n  - Child\n");
    expect(imported.diagnostics).toEqual([]);
    expect(imported.doc.content).toEqual([{
      type: "bulletList",
      content: [{
        type: "listItem",
        content: [
          { type: "paragraph", content: [{ type: "text", text: "Parent" }] },
          {
            type: "bulletList",
            content: [{
              type: "listItem",
              content: [{ type: "paragraph", content: [{ type: "text", text: "Child" }] }],
            }],
          },
        ],
      }],
    }]);
  });

  it("imports supported GM-NOTE callout inside list item cleanly", () => {
    const imported = markdownToTiptapDoc("- Choice\n  > [!GM-NOTE]\n  > Something changes.\n");
    expect(imported.diagnostics).toEqual([]);
    const listItem = (imported.doc.content?.[0] as { content?: unknown[] }).content?.[0] as { content?: unknown[] };
    const callout = listItem.content?.[1] as { type?: string; attrs?: unknown };
    expect(callout.type).toBe("callout");
    expect(callout.attrs).toMatchObject({ kind: "gm-note" });
  });

  it("still blocks plain blockquote inside list item", () => {
    const imported = markdownToTiptapDoc("- Parent\n  > plain blockquote\n");
    expect(imported.diagnostics).toEqual(expect.arrayContaining([
      expect.objectContaining({ level: "warning", message: "Plain blockquotes are not supported yet." }),
    ]));
  });

  it("still blocks nested callout inside callout", () => {
    const imported = markdownToTiptapDoc("> [!GM-NOTE]\n>> [!WARNING]\n>> nested\n");
    expect(imported.diagnostics).toEqual(expect.arrayContaining([
      expect.objectContaining({ level: "warning", message: "Nested callouts are not supported yet." }),
    ]));
  });

  it("imports Session-26 nested list + Decision/Consequence structure cleanly", () => {
    const markdown = [
      "## North Gate",
      "",
      "- If the party holds position:",
      "  - > [!DECISION-CONSEQUENCE]",
      "    > ### Decision",
      "    > Hold the gate and keep the refugees behind the wall.",
      "    >",
      "    > ### Consequence",
      "    > - The pressure remains concentrated at the gate.",
      "    > - Lysandra can reposition the reserve.",
      "",
      "- If the party abandons the gate:",
      "  > [!GM-NOTE]",
      "  > Advance the breach clock.",
      "",
    ].join("\n");
    const imported = markdownToTiptapDoc(markdown);
    expect(imported.diagnostics).toEqual([]);
    const heading = imported.doc.content?.[0] as { type?: string; content?: unknown[] };
    expect(heading.type).toBe("heading");
    const list = imported.doc.content?.[1] as { content?: unknown[] };
    const holdItem = list?.content?.[0] as { content?: unknown[] };
    const innerList = holdItem?.content?.[1] as { content?: unknown[] };
    const innerItem = innerList?.content?.[0] as { content?: unknown[] };
    const dc = innerItem?.content?.[0] as { type?: string; content?: unknown[] };
    expect(dc?.type).toBe("decisionConsequence");
    expect(dc?.content?.map((pane) => (pane as { type?: string }).type)).toEqual(["decisionPane", "consequencePane"]);
    const exported = tiptapJsonToSemanticMarkdown(imported.doc);
    const reimported = markdownToTiptapDoc(exported);
    expect(reimported.diagnostics).toEqual([]);
    expect(reimported.doc).toEqual(imported.doc);
  });

  it("round-trips nested bullet lists with marker-width continuation indent", () => {
    const imported = markdownToTiptapDoc("- Parent\n  - Child\n");
    expect(imported.diagnostics).toEqual([]);
    const exported = tiptapJsonToSemanticMarkdown(imported.doc);
    const reimported = markdownToTiptapDoc(exported);
    expect(reimported.diagnostics).toEqual([]);
    expect(reimported.doc).toEqual(imported.doc);
  });

  it("round-trips list-item GM-NOTE callouts", () => {
    const markdown = "- Choice\n  > [!GM-NOTE]\n  > Something changes.\n";
    const imported = markdownToTiptapDoc(markdown);
    expect(imported.diagnostics).toEqual([]);
    const exported = tiptapJsonToSemanticMarkdown(imported.doc);
    const reimported = markdownToTiptapDoc(exported);
    expect(reimported.diagnostics).toEqual([]);
    expect(reimported.doc).toEqual(imported.doc);
  });

  it("fails closed on Decision/Consequence marker labels that the schema cannot preserve", () => {
    const cases = [
      {
        name: "top-level",
        markdown: [
          "> [!DECISION-CONSEQUENCE] Secret fork",
          "> ### Decision",
          "> Hold",
          ">",
          "> ### Consequence",
          "> Fall back",
          "",
        ].join("\n"),
        line: 1,
      },
      {
        name: "list-item",
        markdown: [
          "- > [!DECISION-CONSEQUENCE] Secret fork",
          "  > ### Decision",
          "  > Hold",
          "  >",
          "  > ### Consequence",
          "  > Fall back",
          "",
        ].join("\n"),
        line: 1,
      },
    ];
    for (const testCase of cases) {
      const imported = markdownToTiptapDoc(testCase.markdown);
      expect(imported.diagnostics, testCase.name).toEqual(expect.arrayContaining([
        expect.objectContaining({
          level: "warning",
          line: testCase.line,
          message: "Decision/Consequence marker labels are not preserved by this editor slice.",
        }),
      ]));
      expect(JSON.stringify(imported.doc), testCase.name).not.toContain('"type":"decisionConsequence"');
    }
  });

  it("imports list-item Decision/Consequence pane ATX headings without false source-form diagnostics", () => {
    const markdown = [
      "- > [!DECISION-CONSEQUENCE]",
      "  > ### Decision",
      "  > #### Detail",
      "  > Hold",
      "  >",
      "  > ### Consequence",
      "  > Fall back",
      "",
    ].join("\n");
    const imported = markdownToTiptapDoc(markdown);
    expect(imported.diagnostics).toEqual([]);
    const listItem = (imported.doc.content?.[0] as { content?: unknown[] }).content?.[0] as {
      content?: Array<{ type?: string; content?: Array<{ type?: string; content?: unknown[] }> }>;
    };
    const dc = listItem.content?.[0];
    expect(dc?.type).toBe("decisionConsequence");
    const decisionPane = dc?.content?.[0];
    expect(decisionPane?.content?.map((node) => node.type)).toEqual(["heading", "paragraph"]);
    expect((decisionPane?.content?.[0] as { attrs?: { level?: number } }).attrs?.level).toBe(4);
  });

  it("imports supported callout inside Decision pane cleanly and keeps Save safety green", () => {
    const markdown = [
      "> [!DECISION-CONSEQUENCE]",
      "> ### Decision",
      "> > [!GM-NOTE]",
      "> > Hold notes.",
      ">",
      "> ### Consequence",
      "> Fall back",
      "",
    ].join("\n");
    const imported = markdownToTiptapDoc(markdown);
    expect(imported.diagnostics).toEqual([]);
    expect(semanticMarkdownSerializationDiagnostics(imported.doc)).toEqual([]);
    const exported = tiptapJsonToSemanticMarkdown(imported.doc);
    const reimported = markdownToTiptapDoc(exported);
    expect(reimported.diagnostics).toEqual([]);
    expect(reimported.doc).toEqual(imported.doc);
  });

  it("fails closed on an unknown top-level callout marker", () => {
    const imported = markdownToTiptapDoc("> [!UNKNOWN-MARKER]\n> Body text\n");
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
