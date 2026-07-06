const LEADING_FRONTMATTER_PATTERN =
  /^---[ \t]*\r?\n([\s\S]*?)\r?\n---[ \t]*(?:\r?\n|$)/;
const YAML_KEY_PATTERN = /(?:^|\r?\n)[A-Za-z0-9_.-]+:\s*/;

export function stripLeadingYamlFrontmatter(markdown: string): {
  markdown: string;
  removedLength: number;
} {
  const match = markdown.match(LEADING_FRONTMATTER_PATTERN);
  if (!match) return { markdown, removedLength: 0 };
  const frontmatterBody = match[1] ?? "";
  if (!YAML_KEY_PATTERN.test(frontmatterBody)) {
    return { markdown, removedLength: 0 };
  }
  return {
    markdown: markdown.slice(match[0].length),
    removedLength: match[0].length,
  };
}
