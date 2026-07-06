import { describe, expect, it } from "vitest";

import { stripLeadingYamlFrontmatter } from "./projectionMarkdownPreprocessing";

describe("projectionMarkdownPreprocessing", () => {
  it("strips only leading YAML frontmatter", () => {
    const markdown =
      '---\ntitle: "Session 1"\ncanon_layer: campaign\n---\n\nThe recap begins.';

    expect(stripLeadingYamlFrontmatter(markdown)).toEqual({
      markdown: "\nThe recap begins.",
      removedLength:
        '---\ntitle: "Session 1"\ncanon_layer: campaign\n---\n'.length,
    });
  });

  it("keeps markdown horizontal rules that are not YAML frontmatter", () => {
    const markdown = "The first beat.\n\n---\n\nThe second beat.";

    expect(stripLeadingYamlFrontmatter(markdown)).toEqual({
      markdown,
      removedLength: 0,
    });
  });
});
