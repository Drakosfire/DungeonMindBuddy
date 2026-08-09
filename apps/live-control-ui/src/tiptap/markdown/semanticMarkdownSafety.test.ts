import { describe, expect, it } from "vitest";

import { semanticMarkdownSerializationDiagnostics } from "./semanticMarkdownSafety";

describe("semanticMarkdownSerializationDiagnostics", () => {
  it("accepts the bounded semantic Markdown document shape", () => {
    expect(semanticMarkdownSerializationDiagnostics({
      type: "doc",
      content: [
        { type: "heading", attrs: { level: 4 }, content: [{ type: "text", text: "Threats" }] },
        {
          type: "callout",
          attrs: { kind: "gm-note" },
          content: [{ type: "paragraph", content: [{ type: "text", text: "Hold the wall", marks: [{ type: "bold" }] }] }],
        },
        {
          type: "table",
          content: [
            {
              type: "tableRow",
              content: [
                { type: "tableHeader", attrs: { colspan: 1, rowspan: 1, colwidth: null }, content: [{ type: "paragraph", content: [{ type: "text", text: "Threat" }] }] },
                { type: "tableHeader", attrs: { colspan: 1, rowspan: 1, colwidth: null }, content: [{ type: "paragraph", content: [{ type: "text", text: "HP" }] }] },
              ],
            },
          ],
        },
      ],
    })).toEqual([]);
  });

  it("rejects StarterKit nodes that the Markdown serializer would flatten", () => {
    const diagnostics = semanticMarkdownSerializationDiagnostics({
      type: "doc",
      content: [
        { type: "blockquote", content: [{ type: "paragraph", content: [{ type: "text", text: "Quote" }] }] },
        { type: "codeBlock", content: [{ type: "text", text: "const x = 1" }] },
      ],
    });

    expect(diagnostics.map((diagnostic) => diagnostic.nodeType)).toEqual(["blockquote", "codeBlock"]);
  });

  it("rejects hard breaks, nested list blocks, and merged table cells", () => {
    const diagnostics = semanticMarkdownSerializationDiagnostics({
      type: "doc",
      content: [
        {
          type: "paragraph",
          content: [{ type: "text", text: "A" }, { type: "hardBreak" }, { type: "text", text: "B" }],
        },
        {
          type: "bulletList",
          content: [{
            type: "listItem",
            content: [
              { type: "paragraph", content: [{ type: "text", text: "Parent" }] },
              { type: "bulletList", content: [{ type: "listItem", content: [{ type: "paragraph", content: [{ type: "text", text: "Child" }] }] }] },
            ],
          }],
        },
        {
          type: "table",
          content: [{
            type: "tableRow",
            content: [{
              type: "tableCell",
              attrs: { colspan: 2, rowspan: 1, colwidth: null },
              content: [{ type: "paragraph", content: [{ type: "text", text: "Merged" }] }],
            }],
          }],
        },
      ],
    });

    expect(diagnostics.some((diagnostic) => diagnostic.nodeType === "hardBreak")).toBe(true);
    expect(diagnostics.some((diagnostic) => diagnostic.message.includes("List items must contain exactly one paragraph"))).toBe(true);
    expect(diagnostics.some((diagnostic) => diagnostic.message.includes("Merged or width-constrained"))).toBe(true);
  });

  it("rejects marks that are not mounted by the editor schema", () => {
    const diagnostics = semanticMarkdownSerializationDiagnostics({
      type: "doc",
      content: [{
        type: "paragraph",
        content: [{ type: "text", text: "Link", marks: [{ type: "link", attrs: { href: "https://example.com" } }] }],
      }],
    });

    expect(diagnostics).toEqual(expect.arrayContaining([
      expect.objectContaining({ level: "warning", nodeType: "text" }),
    ]));
  });
});
