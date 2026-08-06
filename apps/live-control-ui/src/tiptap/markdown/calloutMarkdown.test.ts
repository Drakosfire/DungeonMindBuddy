import { describe, expect, it } from "vitest";

import { tiptapJsonToSemanticMarkdown } from "./calloutMarkdown";

describe("Tiptap rich text Markdown export", () => {
  it.each([
    ["bold", "Gate", "**Gate**"],
    ["italic", "glassy civilians", "*glassy civilians*"],
    ["code", "Cure Line", "`Cure Line`"],
    ["strike", "wrong count", "~~wrong count~~"],
  ])("serializes the %s mark", (type, text, expected) => {
    expect(
      tiptapJsonToSemanticMarkdown({
        type: "paragraph",
        content: [{ type: "text", text, marks: [{ type }] }],
      }),
    ).toBe(`${expected}\n`);
  });

  it("serializes a link mark when it has an href", () => {
    expect(
      tiptapJsonToSemanticMarkdown({
        type: "paragraph",
        content: [
          {
            type: "text",
            text: "Planning notes",
            marks: [
              {
                type: "link",
                attrs: { href: "Docs/Plans/C2S23-MIREWARD-PLANNING-SESSION-NOTES.md" },
              },
            ],
          },
        ],
      }),
    ).toBe("[Planning notes](Docs/Plans/C2S23-MIREWARD-PLANNING-SESSION-NOTES.md)\n");
  });

  it("preserves marks inside a semantic callout body", () => {
    expect(
      tiptapJsonToSemanticMarkdown({
        type: "callout",
        attrs: { kind: "rules" },
        content: [
          {
            type: "paragraph",
            content: [
              { type: "text", text: "Gate", marks: [{ type: "bold" }] },
              { type: "text", text: ", " },
              { type: "text", text: "Civilians", marks: [{ type: "italic" }] },
              { type: "text", text: ", and " },
              { type: "text", text: "Cure Line", marks: [{ type: "code" }] },
            ],
          },
        ],
      }),
    ).toBe("> [!RULES]\n> **Gate**, *Civilians*, and `Cure Line`\n");
  });

  it("escapes Markdown controls and hardens code spans containing backticks", () => {
    expect(
      tiptapJsonToSemanticMarkdown({
        type: "doc",
        content: [
          { type: "paragraph", content: [{ type: "text", text: String.raw`Use *[x](y)* and \ paths` }] },
          {
            type: "paragraph",
            content: [{ type: "text", text: "call `gate`", marks: [{ type: "code" }] }],
          },
        ],
      }),
    ).toBe(["Use \\*\\[x\\]\\(y\\)\\* and \\\\ paths", "", "`` call `gate` ``", ""].join("\n"));
  });

  it("keeps inline code exclusive while allowing an outer link", () => {
    expect(
      tiptapJsonToSemanticMarkdown({
        type: "paragraph",
        content: [
          {
            type: "text",
            text: "Gate",
            marks: [
              { type: "bold" },
              { type: "italic" },
              { type: "strike" },
              { type: "code" },
              { type: "link", attrs: { href: "Docs/My Plan(1).md" } },
            ],
          },
        ],
      }),
    ).toBe("[`Gate`](Docs/My%20Plan\\(1\\).md)\n");
  });

  it("escapes Markdown controls in custom callout labels", () => {
    expect(
      tiptapJsonToSemanticMarkdown({
        type: "callout",
        attrs: { kind: "warning", label: "Breach [clock](bad)" },
        content: [{ type: "paragraph", content: [{ type: "text", text: "Gate fails." }] }],
      }),
    ).toBe("> [!WARNING] Breach \\[clock\\]\\(bad\\)\n> Gate fails.\n");
  });

  it("collapses multiline callout labels into one safe marker line", () => {
    const markdown = tiptapJsonToSemanticMarkdown({
      type: "callout",
      attrs: { kind: "warning", label: "Breach clock\n> [!GM-NOTE]" },
      content: [{ type: "paragraph", content: [{ type: "text", text: "Gate fails." }] }],
    });

    expect(markdown).toBe("> [!WARNING] Breach clock \\> \\[!GM-NOTE\\]\n> Gate fails.\n");
    expect(markdown).not.toMatch(/^> \[!GM-NOTE\]/m);
  });

  it.each([
    ["javascript:alert(1)", "Click me"],
    ["data:text/html,<script>alert(1)</script>", "Payload"],
    ["file:///tmp/secret", "Local file"],
    ["//example.com/path", "Protocol relative"],
    ["Docs/Plan\u0000.md", "Control character"],
  ])("drops an unsafe %s link wrapper while preserving visible text", (href, text) => {
    expect(
      tiptapJsonToSemanticMarkdown({
        type: "paragraph",
        content: [{ type: "text", text, marks: [{ type: "link", attrs: { href } }] }],
      }),
    ).toBe(`${text}\n`);
  });

  it.each([
    ["Docs/Plans/C2S23-MIREWARD-PLANNING-SESSION-NOTES.md", "Planning notes"],
    ["#north-gate", "Jump"],
    ["https://example.com/path?q=gate", "Reference"],
    ["/evals/c2_live_prep/mireward-prep/live-play.html", "Live play"],
    ["mailto:gm@example.com", "Email"],
  ])("allows the safe href %s", (href, text) => {
    expect(
      tiptapJsonToSemanticMarkdown({
        type: "paragraph",
        content: [{ type: "text", text, marks: [{ type: "link", attrs: { href } }] }],
      }),
    ).toBe(`[${text}](${href})\n`);
  });

  it("encodes spaces and escapes parentheses in safe hrefs", () => {
    expect(
      tiptapJsonToSemanticMarkdown({
        type: "paragraph",
        content: [
          {
            type: "text",
            text: "Plan",
            marks: [{ type: "link", attrs: { href: "Docs/My Plan(1).md" } }],
          },
        ],
      }),
    ).toBe("[Plan](Docs/My%20Plan\\(1\\).md)\n");
  });

  it("escapes Markdown block markers at paragraph line starts", () => {
    expect(
      tiptapJsonToSemanticMarkdown({
        type: "paragraph",
        content: [
          {
            type: "text",
            text: "# Not heading\n- Not list\n+ Not list\n> Not quote\n1. Not ordered\n2) Also not ordered\n---\nTitle\n===\n***",
          },
        ],
      }),
    ).toBe(
      "\\# Not heading\n\\- Not list\n\\+ Not list\n\\> Not quote\n1\\. Not ordered\n2\\) Also not ordered\n\\---\nTitle\n\\===\n\\*\\*\\*\n",
    );
  });

  it("serializes legacy runbook refs unchanged", () => {
    expect(
      tiptapJsonToSemanticMarkdown({
        type: "paragraph",
        content: [{
          type: "runbookReference",
          attrs: {
            kind: "ref",
            refType: "npc",
            refId: "lysandro-ironveil",
            label: "Lysandro Ironveil",
            graphWorldId: null,
            graphCampaignId: null,
            graphScopeMode: null,
            graphRevisionId: null,
          },
        }],
      }),
    ).toBe("[Lysandro Ironveil](#dmb-ref:npc:lysandro-ironveil)\n");
  });

  it("serializes complete scoped graph-node refs with canonical query", () => {
    expect(
      tiptapJsonToSemanticMarkdown({
        type: "paragraph",
        content: [{
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
        }],
      }),
    ).toBe(
      "[Mireward Latchling](#dmb-ref:graph-node:threat:authored:d16d43d376833e38caf46dd19b1dd17f?world=eldyrwild&campaign=longmont-c2&scope=campaign&revision=rev%3A3413bf6f5044cf2680233f5e37c90dcf)\n",
    );
  });

  it("exports partial scoped refs as label-only text", () => {
    expect(
      tiptapJsonToSemanticMarkdown({
        type: "paragraph",
        content: [{
          type: "runbookReference",
          attrs: {
            kind: "ref",
            refType: "graph-node",
            refId: "threat:tripod-null-calf",
            label: "Tripod Null Calf",
            graphWorldId: "eldyrwild",
            graphCampaignId: null,
            graphScopeMode: null,
            graphRevisionId: null,
          },
        }],
      }),
    ).toBe("Tripod Null Calf\n");
  });

  it("matches the hardened DungeonBuddy semantic Markdown golden export", () => {
    expect(
      tiptapJsonToSemanticMarkdown({
        type: "doc",
        content: [
          {
            type: "heading",
            attrs: { level: 2 },
            content: [{ type: "text", text: "North Gate" }],
          },
          {
            type: "paragraph",
            content: [
              { type: "text", text: "The ", marks: [] },
              { type: "text", text: "breach clock", marks: [{ type: "bold" }] },
              { type: "text", text: " uses " },
              { type: "text", text: "2d6", marks: [{ type: "code" }] },
              { type: "text", text: "; see " },
              {
                type: "text",
                text: "planning notes",
                marks: [{ type: "link", attrs: { href: "Docs/Plans/North Gate.md" } }],
              },
              { type: "text", text: "." },
            ],
          },
          {
            type: "callout",
            attrs: { kind: "warning", label: "Breach [clock]\n> [!GM-NOTE]" },
            content: [{ type: "paragraph", content: [{ type: "text", text: "The gate fails." }] }],
          },
          {
            type: "callout",
            attrs: { kind: "rules" },
            content: [
              {
                type: "paragraph",
                content: [
                  { type: "text", text: "Roll ", marks: [] },
                  { type: "text", text: "Cure Line", marks: [{ type: "italic" }] },
                  { type: "text", text: " immediately." },
                ],
              },
            ],
          },
          {
            type: "paragraph",
            content: [
              {
                type: "text",
                text: "Do not open",
                marks: [{ type: "link", attrs: { href: "javascript:alert(1)" } }],
              },
            ],
          },
        ],
      }),
    ).toBe(
      [
        "## North Gate",
        "",
        "The **breach clock** uses `2d6`; see [planning notes](Docs/Plans/North%20Gate.md).",
        "",
        "> [!WARNING] Breach \\[clock\\] \\> \\[!GM-NOTE\\]",
        "> The gate fails.",
        "",
        "> [!RULES]",
        "> Roll *Cure Line* immediately.",
        "",
        "Do not open",
        "",
      ].join("\n"),
    );
  });
});
