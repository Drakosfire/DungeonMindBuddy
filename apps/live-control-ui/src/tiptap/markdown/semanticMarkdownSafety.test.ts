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

  it("accepts nested list and Decision/Consequence prep structures", () => {
    expect(semanticMarkdownSerializationDiagnostics({
      type: "doc",
      content: [{
        type: "bulletList",
        content: [{
          type: "listItem",
          content: [
            { type: "paragraph", content: [{ type: "text", text: "Decision forks" }] },
            {
              type: "bulletList",
              content: [{
                type: "listItem",
                content: [{
                  type: "decisionConsequence",
                  content: [
                    {
                      type: "decisionPane",
                      content: [{
                        type: "orderedList",
                        content: [{
                          type: "listItem",
                          content: [{ type: "paragraph", content: [{ type: "text", text: "Defend" }] }],
                        }],
                      }],
                    },
                    {
                      type: "consequencePane",
                      content: [{
                        type: "bulletList",
                        content: [{
                          type: "listItem",
                          content: [{ type: "paragraph", content: [{ type: "text", text: "Escalation" }] }],
                        }],
                      }],
                    },
                  ],
                }],
              }],
            },
          ],
        }],
      }],
    })).toEqual([]);
  });

  it("rejects orphan decision panes outside a paired block", () => {
    const diagnostics = semanticMarkdownSerializationDiagnostics({
      type: "doc",
      content: [{ type: "decisionPane", content: [{ type: "paragraph", content: [{ type: "text", text: "Orphan" }] }] }],
    });
    expect(diagnostics.some((diagnostic) => diagnostic.nodeType === "decisionPane")).toBe(true);
  });

  it("rejects hard breaks, unsupported nested list blocks, and merged table cells", () => {
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
              { type: "blockquote", content: [{ type: "paragraph", content: [{ type: "text", text: "Nested quote" }] }] },
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
    expect(diagnostics.some((diagnostic) => diagnostic.message.includes("List item child"))).toBe(true);
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
