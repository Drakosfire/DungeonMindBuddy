import { describe, expect, it } from "vitest";

import { stripLeadingYamlFrontmatter } from "./stripLeadingYamlFrontmatter";

describe("stripLeadingYamlFrontmatter", () => {
  it("strips only leading YAML frontmatter", () => {
    const input = [
      "---",
      'title: "Session 26 Prep"',
      "session: 26",
      "---",
      "",
      "# Body",
      "",
      "---",
      "",
      "Still body.",
      "",
    ].join("\n");

    const result = stripLeadingYamlFrontmatter(input);
    expect(result.removedLength).toBeGreaterThan(0);
    expect(result.markdown.trimStart().startsWith("# Body")).toBe(true);
    expect(result.markdown).toContain("---\n\nStill body.");
  });

  it("keeps markdown horizontal rules that are not YAML frontmatter", () => {
    const input = "# Title\n\n---\n\nBody\n";
    expect(stripLeadingYamlFrontmatter(input)).toEqual({
      markdown: input,
      removedLength: 0,
    });
  });
});
