import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MarkdownDocumentOutline, markdownDocumentHeadings } from "./MarkdownDocumentOutline";
import { MarkdownDocumentReader } from "./MarkdownDocumentReader";

 describe("shared document outline", () => {
  it("matches reader anchors for duplicate formatted headings and frontmatter", () => {
    const markdown = "---\ntitle: ignored\n---\n# Population\n## **Population**\n### Guard headquarters";
    render(<><MarkdownDocumentOutline markdown={markdown} /><MarkdownDocumentReader markdown={markdown} /></>);
    for (const heading of markdownDocumentHeadings(markdown)) expect(document.getElementById(heading.id)).not.toBeNull();
    expect(screen.getAllByRole("link").map(link => link.getAttribute("href"))).toEqual(["#population", "#population-1", "#guard-headquarters"]);
  });
});
