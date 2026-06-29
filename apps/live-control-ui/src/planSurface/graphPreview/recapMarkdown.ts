export type RecapInlineSegment =
  | { type: "text"; text: string }
  | { type: "node"; text: string; href: string; objectId: string };

const NODE_LINK_PATTERN = /\[([^\]]+)\]\((dmb-node:[^)]+)\)/g;

export function parseRecapInlineSegments(markdown: string): RecapInlineSegment[] {
  const segments: RecapInlineSegment[] = [];
  let cursor = 0;

  for (const match of markdown.matchAll(NODE_LINK_PATTERN)) {
    const index = match.index ?? 0;
    if (index > cursor) {
      segments.push({ type: "text", text: markdown.slice(cursor, index) });
    }
    const href = match[2];
    segments.push({
      type: "node",
      text: match[1].replace(/\\]/g, "]").replace(/\\\\/g, "\\"),
      href,
      objectId: href.replace(/^dmb-node:/, ""),
    });
    cursor = index + match[0].length;
  }

  if (cursor < markdown.length) {
    segments.push({ type: "text", text: markdown.slice(cursor) });
  }

  return segments.length ? segments : [{ type: "text", text: markdown }];
}

export function splitRecapBlocks(markdown: string): string[] {
  return markdown
    .split(/\n+/)
    .map((block) => block.trim())
    .filter(Boolean);
}
