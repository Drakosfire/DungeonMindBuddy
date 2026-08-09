const LEADING_FRONTMATTER_PATTERN =
  /^---[ \t]*(?:\r\n|\n)([\s\S]*?)(?:\r\n|\n)---[ \t]*(?:(?:\r\n|\n)|$)/;
const YAML_KEY_PATTERN = /(?:^|\r?\n)[A-Za-z0-9_.-]+:\s*/;

export interface LeadingYamlFrontmatterSplit {
  markdown: string;
  frontmatter: string;
  removedLength: number;
}

/**
 * Split a leading YAML frontmatter envelope from the editable Markdown body.
 *
 * The envelope is returned byte-for-byte so authoring can keep metadata outside
 * TipTap while still reattaching it unchanged on every local export and durable
 * save. A thematic break is not treated as frontmatter unless the enclosed body
 * contains at least one YAML-style key.
 */
export function splitLeadingYamlFrontmatter(markdown: string): LeadingYamlFrontmatterSplit {
  const match = markdown.match(LEADING_FRONTMATTER_PATTERN);
  if (!match) return { markdown, frontmatter: "", removedLength: 0 };
  const frontmatterBody = match[1] ?? "";
  if (!YAML_KEY_PATTERN.test(frontmatterBody)) {
    return { markdown, frontmatter: "", removedLength: 0 };
  }
  return {
    markdown: markdown.slice(match[0].length),
    frontmatter: match[0],
    removedLength: match[0].length,
  };
}

/** Strip leading YAML frontmatter from a Markdown body for editor/projection parsing. */
export function stripLeadingYamlFrontmatter(markdown: string): {
  markdown: string;
  removedLength: number;
} {
  const split = splitLeadingYamlFrontmatter(markdown);
  return { markdown: split.markdown, removedLength: split.removedLength };
}

/**
 * Replace only the editable body while preserving an existing leading YAML
 * envelope byte-for-byte. New documents without frontmatter remain body-only.
 */
export function preserveLeadingYamlFrontmatter(
  sourceMarkdown: string,
  editableBodyMarkdown: string,
): string {
  const split = splitLeadingYamlFrontmatter(sourceMarkdown);
  return `${split.frontmatter}${editableBodyMarkdown}`;
}
