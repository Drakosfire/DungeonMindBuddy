import { describe, expect, it } from "vitest";

import { looksLikeSemanticMarkdown } from "./SemanticMarkdownPaste";

describe("looksLikeSemanticMarkdown", () => {
  it("detects headings, callouts, and frontmatter", () => {
    expect(looksLikeSemanticMarkdown("# Title\n\nBody")).toBe(true);
    expect(looksLikeSemanticMarkdown("> [!GM-NOTE]\n> Note")).toBe(true);
    expect(
      looksLikeSemanticMarkdown(['---', 'title: "x"', "---", "", "# Body"].join("\n")),
    ).toBe(true);
  });

  it("rejects plain prose", () => {
    expect(looksLikeSemanticMarkdown("Just a sentence about the wall.")).toBe(false);
    expect(looksLikeSemanticMarkdown("")).toBe(false);
  });
});
