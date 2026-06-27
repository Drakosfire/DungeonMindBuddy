import type { GraphPreviewAnchorQuoteMatch } from "../../api/types";

export function sectionLabel(section: string): string {
  switch (section) {
    case "nodes":
      return "Nodes";
    case "edges":
      return "Edges";
    case "beats":
      return "Beats";
    case "ignored_items":
      return "Ignored";
    case "deferred_items":
      return "Deferred";
    default:
      return section;
  }
}

export interface HighlightSegment {
  text: string;
  highlighted: boolean;
}

export function buildHighlightSegments(
  paragraph: string,
  matches: GraphPreviewAnchorQuoteMatch[],
): HighlightSegment[] {
  if (!paragraph) return [];
  if (!matches.length) {
    return [{ text: paragraph, highlighted: false }];
  }
  const sorted = [...matches].sort((a, b) => a.char_start - b.char_start);
  const segments: HighlightSegment[] = [];
  let cursor = 0;
  for (const match of sorted) {
    const start = Math.max(0, Math.min(match.char_start, paragraph.length));
    const end = Math.max(start, Math.min(match.char_end, paragraph.length));
    if (start > cursor) {
      segments.push({ text: paragraph.slice(cursor, start), highlighted: false });
    }
    if (end > start) {
      segments.push({ text: paragraph.slice(start, end), highlighted: true });
    }
    cursor = Math.max(cursor, end);
  }
  if (cursor < paragraph.length) {
    segments.push({ text: paragraph.slice(cursor), highlighted: false });
  }
  return segments.length ? segments : [{ text: paragraph, highlighted: false }];
}

export function lineRangeLabel(lineStart?: number | null, lineEnd?: number | null): string {
  if (lineStart == null && lineEnd == null) return "lines n/a";
  if (lineStart != null && lineEnd != null && lineStart !== lineEnd) {
    return `lines ${lineStart}–${lineEnd}`;
  }
  return `line ${lineStart ?? lineEnd}`;
}

/**
 * Turn a span ref id like "spref:session-22:p014" into a human label
 * "Session 22 · ¶14". Falls back to the raw id when the shape is unexpected.
 */
export function spanRefLabel(spanRefId?: string | null): string | null {
  if (!spanRefId) return null;
  const match = spanRefId.match(/session-(\d+):p0*(\d+)/i);
  if (match) {
    return `Session ${Number(match[1])} · ¶${Number(match[2])}`;
  }
  return spanRefId;
}
