import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { markdownDocumentHeadings } from "./MarkdownDocumentOutline";
import { MarkdownDocumentReader } from "./MarkdownDocumentReader";

 describe("shared document outline", () => {
  it("matches reader anchors for duplicate formatted headings and frontmatter", () => {
    const markdown = "---\ntitle: ignored\n---\n# Population\n## **Population**\n### Guard headquarters";
    render(<MarkdownDocumentReader markdown={markdown} />);
    for (const heading of markdownDocumentHeadings(markdown)) expect(document.getElementById(heading.id)).not.toBeNull();
    expect(markdownDocumentHeadings(markdown).map(heading => heading.id)).toEqual(["population", "population-1", "guard-headquarters"]);
  });
});
