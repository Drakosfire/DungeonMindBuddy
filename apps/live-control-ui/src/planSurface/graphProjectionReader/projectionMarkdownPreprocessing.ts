export interface ProjectionMentionOffsets {
  start_offset?: number | null;
  end_offset?: number | null;
}

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

function shiftMentionOffsets<T extends ProjectionMentionOffsets>(
  mention: T,
  removedLength: number,
): T {
  const start = mention.start_offset;
  const end = mention.end_offset;
  if (typeof start !== "number" || typeof end !== "number") return mention;
  if (start < removedLength) {
    return { ...mention, start_offset: null, end_offset: null };
  }
  return {
    ...mention,
    start_offset: start - removedLength,
    end_offset: end - removedLength,
  };
}

export function normalizeProjectionMarkdown<T extends ProjectionMentionOffsets>(
  markdown: string,
  mentions: readonly T[],
): { markdown: string; mentions: T[]; removedLength: number } {
  const stripped = stripLeadingYamlFrontmatter(markdown);
  if (!stripped.removedLength) {
    return { markdown, mentions: [...mentions], removedLength: 0 };
  }
  return {
    markdown: stripped.markdown,
    mentions: mentions.map((mention) =>
      shiftMentionOffsets(mention, stripped.removedLength),
    ),
    removedLength: stripped.removedLength,
  };
}
