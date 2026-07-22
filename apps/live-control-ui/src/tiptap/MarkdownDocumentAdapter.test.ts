import { defaultMarkdownDocumentAdapter } from "./MarkdownDocumentAdapter";

describe("MarkdownDocumentAdapter", () => {
  it("imports supported markdown into a TipTap doc with diagnostics", () => {
    const result = defaultMarkdownDocumentAdapter.importMarkdown(
      "# Title\n\nA normal paragraph.",
    );

    expect(result.doc.type).toBe("doc");
    expect(result.doc.content).toEqual([
      { type: "heading", attrs: { level: 1 }, content: [{ type: "text", text: "Title" }] },
      { type: "paragraph", content: [{ type: "text", text: "A normal paragraph." }] },
    ]);
    expect(Array.isArray(result.diagnostics)).toBe(true);
  });

  it("exports TipTap JSON to semantic markdown", () => {
    const markdown = defaultMarkdownDocumentAdapter.exportMarkdown({
      type: "doc",
      content: [
        { type: "heading", attrs: { level: 1 }, content: [{ type: "text", text: "Title" }] },
        { type: "paragraph", content: [{ type: "text", text: "Body copy." }] },
      ],
    });

    expect(markdown).toContain("# Title");
    expect(markdown).toContain("Body copy.");
  });

  it("surfaces unsupported markdown diagnostics without inventing blocks", () => {
    const result = defaultMarkdownDocumentAdapter.importMarkdown("| a | b |\n| --- | --- |\n| 1 | 2 |");

    expect(result.diagnostics.some((entry) => entry.level === "warning")).toBe(true);
  });

  it("round-trips supported markdown deterministically through the adapter", () => {
    const source = "# Title\n\nTalk to [Lysandro Ironveil](#dmb-ref:npc:lysandro-ironveil).";
    const first = defaultMarkdownDocumentAdapter.importMarkdown(source);
    const exported = defaultMarkdownDocumentAdapter.exportMarkdown(first.doc);
    const second = defaultMarkdownDocumentAdapter.importMarkdown(exported);

    expect(second.doc).toEqual(first.doc);
    expect(second.diagnostics).toEqual(first.diagnostics);
  });
});
