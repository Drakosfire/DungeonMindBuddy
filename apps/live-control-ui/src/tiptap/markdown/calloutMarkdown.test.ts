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
});
