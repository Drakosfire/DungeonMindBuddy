import { describe, expect, it } from "vitest";

import {
  preserveLeadingYamlFrontmatter,
  splitLeadingYamlFrontmatter,
  stripLeadingYamlFrontmatter,
} from "./stripLeadingYamlFrontmatter";

describe("leading YAML frontmatter", () => {
  it("strips only leading YAML frontmatter from the editable body", () => {
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

  it("preserves the source envelope byte-for-byte when replacing the body", () => {
    const input = "---\r\ntitle: Session 2 Prep\r\nsession: 2\r\n---\r\n# Old body\r\n";
    const split = splitLeadingYamlFrontmatter(input);

    expect(split.frontmatter).toBe("---\r\ntitle: Session 2 Prep\r\nsession: 2\r\n---\r\n");
    expect(preserveLeadingYamlFrontmatter(input, "# New body\n")).toBe(
      "---\r\ntitle: Session 2 Prep\r\nsession: 2\r\n---\r\n# New body\n",
    );
  });

  it("does not invent frontmatter for body-only drafts", () => {
    expect(preserveLeadingYamlFrontmatter("# Old\n", "# New\n")).toBe("# New\n");
  });
});
