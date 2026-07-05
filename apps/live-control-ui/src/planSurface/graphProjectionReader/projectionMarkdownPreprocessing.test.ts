import { describe, expect, it } from "vitest";

import {
  normalizeProjectionMarkdown,
  stripLeadingYamlFrontmatter,
} from "./projectionMarkdownPreprocessing";

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

  it("shifts structured mention offsets after stripping frontmatter", () => {
    const frontmatter =
      '---\ntitle: "Session 1"\ndocument_class: play\n---\n\n';
    const body = "The Tripod Null-Calf threatened the North Gate.";
    const mentionStart = frontmatter.length + 4;
    const mentionEnd = frontmatter.length + 21;

    const normalized = normalizeProjectionMarkdown(`${frontmatter}${body}`, [
      {
        mention_id: "m1",
        start_offset: mentionStart,
        end_offset: mentionEnd,
      },
    ]);

    expect(normalized.markdown).toBe(`\n${body}`);
    expect(normalized.mentions[0]).toMatchObject({
      start_offset: 5,
      end_offset: 22,
    });
  });
});
