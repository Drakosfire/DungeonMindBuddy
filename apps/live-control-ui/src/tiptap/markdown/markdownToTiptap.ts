import type { JSONContent } from "@tiptap/core";
import { isDecisionConsequenceMarker, normalizeCalloutKind } from "./calloutMarkdown";
import { stripLeadingYamlFrontmatter } from "./stripLeadingYamlFrontmatter";
import {
  healRunbookReferenceLabel,
  isSupportedRunbookReference,
  normalizeRunbookReferenceAttrs,
  type RunbookReferenceAttrs,
} from "../references/runbookReferences";

export type MarkdownImportDiagnostic = {
  level: "info" | "warning";
  message: string;
  line?: number;
};

export type MarkdownImportResult = {
  doc: JSONContent;
  diagnostics: MarkdownImportDiagnostic[];
};

export type MarkdownImportOptions = {
  parseGraphNodeLinks?: boolean;
};

type TiptapNode = {
  type: string;
  attrs?: Record<string, unknown>;
  content?: unknown[];
  text?: string;
  marks?: Array<{ type: string; attrs?: Record<string, unknown> }>;
};

/** refId may include colons for graph-native durable IDs (`threat:tripod-null-calf`). */
const typedReferencePattern =
  /\[([^\]]+)\]\(#dmb-(ref|action):([a-z][a-z0-9-]*):([a-z0-9][a-z0-9_.:-]*)\)/g;
const graphNodeReferencePattern = /\[([^\]]+)\]\(dmb-node:([^)]+)\)/g;
const headingPattern = /^(#{1,3})\s+(.+)$/;
/** Flush or indented bullets — Plan Board serializes nested blocks with leading spaces. */
const bulletListPattern = /^(\s*)-\s+(.*)$/;
const orderedListPattern = /^(\s*)(\d+)[.)]\s+(.*)$/;
/** Callout markers may be indented when nested under list items after save. */
const calloutMarkerPattern = /^\s*>\s*\[!([^\]]+)\]\s*(.*)$/;
const quoteLinePattern = /^\s*>/;

function textNode(text: string, marks?: Array<{ type: string }>): TiptapNode | null {
  if (!text) return null;
  return marks && marks.length > 0 ? { type: "text", text, marks } : { type: "text", text };
}

function unescapeMarkdownText(text: string): string {
  return text.replace(/\\([\\`*_{}[\]()#+.!|>~-])/g, "$1");
}

/** Parse `**bold**` / `*italic*` / `` `code` `` / `~~strike~~` into TipTap text marks. */
function parseTextWithMarks(text: string): unknown[] {
  if (!text) return [];

  const pattern =
    /(`+)((?:(?!\1).)+?)\1|\*\*((?:(?!\*\*).)+?)\*\*|__((?:(?!__).)+?)__|(?<!\*)\*((?:(?!\*).)+?)\*(?!\*)|(?<!_)_((?:(?!_).)+?)_(?!_)|~~((?:(?!~~).)+?)~~/g;
  const content: unknown[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      const leading = textNode(unescapeMarkdownText(text.slice(lastIndex, match.index)));
      if (leading) content.push(leading);
    }

    const codeTicks = match[1];
    const codeBody = match[2];
    const boldStar = match[3];
    const boldUnderscore = match[4];
    const italicStar = match[5];
    const italicUnderscore = match[6];
    const strikeBody = match[7];

    if (codeTicks && codeBody !== undefined) {
      const node = textNode(codeBody, [{ type: "code" }]);
      if (node) content.push(node);
    } else if (boldStar !== undefined || boldUnderscore !== undefined) {
      const inner = boldStar ?? boldUnderscore ?? "";
      for (const child of parseTextWithMarks(inner)) {
        const childNode = child as TiptapNode;
        if (childNode.type === "text") {
          const marks = [...(Array.isArray(childNode.marks) ? childNode.marks : []), { type: "bold" }];
          content.push({ ...childNode, marks });
        } else {
          content.push(child);
        }
      }
    } else if (italicStar !== undefined || italicUnderscore !== undefined) {
      const inner = italicStar ?? italicUnderscore ?? "";
      for (const child of parseTextWithMarks(inner)) {
        const childNode = child as TiptapNode;
        if (childNode.type === "text") {
          const marks = [...(Array.isArray(childNode.marks) ? childNode.marks : []), { type: "italic" }];
          content.push({ ...childNode, marks });
        } else {
          content.push(child);
        }
      }
    } else if (strikeBody !== undefined) {
      const node = textNode(unescapeMarkdownText(strikeBody), [{ type: "strike" }]);
      if (node) content.push(node);
    }

    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    const trailing = textNode(unescapeMarkdownText(text.slice(lastIndex)));
    if (trailing) content.push(trailing);
  }

  return content;
}

function parseInlineContent(text: string, options: MarkdownImportOptions = {}): unknown[] {
  const matches = [
    ...[...text.matchAll(typedReferencePattern)].map((match) => ({
      match,
      index: match.index ?? 0,
      length: match[0].length,
      kind: "runbook" as const,
    })),
    ...(options.parseGraphNodeLinks
      ? [...text.matchAll(graphNodeReferencePattern)].map((match) => ({
        match,
        index: match.index ?? 0,
        length: match[0].length,
        kind: "graphNode" as const,
      }))
      : []),
  ].sort((left, right) => left.index - right.index);

  const content: unknown[] = [];
  let lastIndex = 0;

  for (const item of matches) {
    if (item.index < lastIndex) continue;
    content.push(...parseTextWithMarks(text.slice(lastIndex, item.index)));

    if (item.kind === "graphNode") {
      const [, label, nodeId] = item.match;
      content.push({
        type: "graphNodeReference",
        attrs: { nodeId, label: healRunbookReferenceLabel(label) || nodeId },
      });
    } else {
      const [, label, kind, refType, refId] = item.match;
      const attrs: RunbookReferenceAttrs = normalizeRunbookReferenceAttrs({
        kind,
        refType,
        refId,
        label: healRunbookReferenceLabel(label) || refId,
      } as RunbookReferenceAttrs);
      if (isSupportedRunbookReference(attrs)) {
        content.push({ type: "runbookReference", attrs });
      } else {
        content.push(...parseTextWithMarks(item.match[0]));
      }
    }
    lastIndex = item.index + item.length;
  }

  content.push(...parseTextWithMarks(text.slice(lastIndex)));
  return content;
}

function paragraph(text: string, options: MarkdownImportOptions = {}): TiptapNode {
  return { type: "paragraph", content: parseInlineContent(text, options) };
}

function isBlank(line: string): boolean {
  return line.trim() === "";
}

function leadingIndent(line: string): number {
  const match = line.match(/^[ \t]*/);
  return match ? match[0].length : 0;
}

function isTableRowLine(line: string): boolean {
  return /^\s*\|/.test(line);
}

function isTableSeparatorLine(line: string): boolean {
  return /^\s*\|?[\s:-]+\|[\s|:-]*$/.test(line.trim());
}

function parseTableRowCells(line: string): string[] {
  const trimmed = line.trim().replace(/^\|/, "").replace(/\|$/, "");
  return trimmed.split("|").map((cell) => cell.trim());
}

function parseMarkdownTable(lines: string[], options: MarkdownImportOptions = {}): TiptapNode | null {
  if (lines.length === 0) return null;
  const headerCells = parseTableRowCells(lines[0]);
  if (headerCells.length === 0) return null;
  const bodyStart = lines.length > 1 && isTableSeparatorLine(lines[1]) ? 2 : 1;
  const rows: unknown[] = [
    {
      type: "tableRow",
      content: headerCells.map((cell) => ({
        type: "tableHeader",
        content: [paragraph(cell, options)],
      })),
    },
  ];

  for (let index = bodyStart; index < lines.length; index += 1) {
    if (!isTableRowLine(lines[index]) || isTableSeparatorLine(lines[index])) continue;
    const cells = parseTableRowCells(lines[index]);
    rows.push({
      type: "tableRow",
      content: headerCells.map((_, cellIndex) => ({
        type: "tableCell",
        content: [paragraph(cells[cellIndex] ?? "", options)],
      })),
    });
  }

  return { type: "table", content: rows };
}

function stripQuotePrefix(line: string): string {
  return line.replace(/^\s*> ?/, "");
}

function isCalloutMarkerLine(line: string): boolean {
  return calloutMarkerPattern.test(line);
}

function isQuoteLine(line: string): boolean {
  return quoteLinePattern.test(line);
}

/** Text after `- ` / `1. ` that itself opens a callout (`- > [!READ-ALOUD]`). */
function isCalloutMarkerText(text: string): boolean {
  return calloutMarkerPattern.test(text.trimStart());
}

function isBlockStart(line: string): boolean {
  const trimmed = line.trimStart();
  return headingPattern.test(trimmed)
    || isCalloutMarkerLine(line)
    || bulletListPattern.test(line)
    || orderedListPattern.test(line)
    || isTableRowLine(line);
}

const paneHeadingPattern = /^#{1,3}\s+(decision|consequence)\s*$/i;

function splitDecisionConsequenceBody(lines: string[]): { decision: string[]; consequence: string[] } {
  const decision: string[] = [];
  const consequence: string[] = [];
  let target: "decision" | "consequence" | null = null;

  for (const line of lines) {
    const heading = line.match(paneHeadingPattern);
    if (heading) {
      target = heading[1].toLowerCase() as "decision" | "consequence";
      continue;
    }
    if (target === "decision") {
      decision.push(line);
    } else if (target === "consequence") {
      consequence.push(line);
    } else if (!isBlank(line)) {
      // Content before the first pane heading lands in Decision.
      target = "decision";
      decision.push(line);
    }
  }

  return { decision, consequence };
}

type ParseCursor = { node: TiptapNode; nextIndex: number };

function parseCalloutAt(
  lines: string[],
  startIndex: number,
  options: MarkdownImportOptions,
  markerSourceLine?: string,
): ParseCursor {
  const markerLine = markerSourceLine ?? lines[startIndex];
  const callout = markerLine.match(calloutMarkerPattern);
  if (!callout) {
    return {
      node: paragraph(markerLine.trim(), options),
      nextIndex: markerSourceLine ? startIndex : startIndex + 1,
    };
  }

  const [, marker, rawLabel] = callout;
  const bodyLines: string[] = [];
  let index = markerSourceLine ? startIndex : startIndex + 1;

  while (index < lines.length && isQuoteLine(lines[index])) {
    // Stacked callouts (common after list serialization) start a new block.
    if (isCalloutMarkerLine(lines[index])) break;
    bodyLines.push(stripQuotePrefix(lines[index]));
    index += 1;
  }

  if (isDecisionConsequenceMarker(marker)) {
    return {
      node: {
        type: "decisionConsequence",
        content: parseDecisionConsequenceBody(bodyLines, options),
      },
      nextIndex: index,
    };
  }

  return {
    node: {
      type: "callout",
      attrs: {
        kind: normalizeCalloutKind(marker),
        ...(rawLabel.trim() ? { label: rawLabel.trim() } : {}),
      },
      content: parseCalloutBody(bodyLines, options),
    },
    nextIndex: index,
  };
}

function parseCalloutBody(lines: string[], options: MarkdownImportOptions = {}): unknown[] {
  const content: unknown[] = [];
  let index = 0;

  while (index < lines.length) {
    if (isBlank(lines[index])) {
      index += 1;
      continue;
    }

    if (isTableRowLine(lines[index])) {
      const tableLines: string[] = [];
      while (index < lines.length && isTableRowLine(lines[index])) {
        tableLines.push(lines[index]);
        index += 1;
      }
      const table = parseMarkdownTable(tableLines, options);
      if (table) content.push(table);
      continue;
    }

    const bullet = lines[index].match(bulletListPattern);
    if (bullet) {
      const parsed = parseListAt(lines, index, bullet[1].length, "bullet", options);
      content.push(parsed.node);
      index = parsed.nextIndex;
      continue;
    }

    const ordered = lines[index].match(orderedListPattern);
    if (ordered) {
      const parsed = parseListAt(lines, index, ordered[1].length, "ordered", options);
      content.push(parsed.node);
      index = parsed.nextIndex;
      continue;
    }

    const paragraphLines: string[] = [];
    while (
      index < lines.length
      && !isBlank(lines[index])
      && !bulletListPattern.test(lines[index])
      && !orderedListPattern.test(lines[index])
      && !isTableRowLine(lines[index])
      && !isCalloutMarkerLine(lines[index])
    ) {
      paragraphLines.push(lines[index]);
      index += 1;
    }
    content.push(paragraph(paragraphLines.join(" ").trim(), options));
  }

  return content.length > 0 ? content : [paragraph("")];
}

function parseDecisionConsequenceBody(lines: string[], options: MarkdownImportOptions = {}): unknown[] {
  const { decision, consequence } = splitDecisionConsequenceBody(lines);
  return [
    {
      type: "decisionPane",
      content: parseCalloutBody(decision, options),
    },
    {
      type: "consequencePane",
      content: parseCalloutBody(consequence, options),
    },
  ];
}

function peekNonBlank(lines: string[], index: number): number {
  let look = index;
  while (look < lines.length && isBlank(lines[look])) look += 1;
  return look;
}

function parseListAt(
  lines: string[],
  startIndex: number,
  baseIndent: number,
  kind: "bullet" | "ordered",
  options: MarkdownImportOptions,
): ParseCursor {
  const items: unknown[] = [];
  let index = startIndex;
  let orderedStart = 1;

  while (index < lines.length) {
    if (isBlank(lines[index])) {
      const look = peekNonBlank(lines, index + 1);
      if (look >= lines.length) break;
      const nextBullet = lines[look].match(bulletListPattern);
      const nextOrdered = lines[look].match(orderedListPattern);
      const nextIndent = nextBullet
        ? nextBullet[1].length
        : nextOrdered
          ? nextOrdered[1].length
          : leadingIndent(lines[look]);
      if (
        (kind === "bullet" && nextBullet && nextBullet[1].length === baseIndent)
        || (kind === "ordered" && nextOrdered && nextOrdered[1].length === baseIndent)
        || nextIndent > baseIndent
      ) {
        index = look;
        continue;
      }
      break;
    }

    const bullet = lines[index].match(bulletListPattern);
    const ordered = lines[index].match(orderedListPattern);

    if (kind === "bullet") {
      if (!bullet || bullet[1].length !== baseIndent) break;
    } else {
      if (!ordered || ordered[1].length !== baseIndent) break;
      if (items.length === 0) orderedStart = Number(ordered[2]);
    }

    const headText = kind === "bullet" ? bullet![2] : ordered![3];
    index += 1;

    const itemContent: unknown[] = [];

    if (isCalloutMarkerText(headText)) {
      const parsed = parseCalloutAt(lines, index, options, headText.trimStart());
      itemContent.push(parsed.node);
      index = parsed.nextIndex;
    } else if (headText.trim()) {
      // Serializer escapes headings inside list items as `\## Title` (schema forbids
      // heading nodes there). Import the title text, not raw hash markers.
      const unescapedHead = unescapeMarkdownText(headText);
      const headingLike = unescapedHead.match(/^(#{1,6})\s+(.+)$/);
      itemContent.push(paragraph(headingLike ? headingLike[2] : headText, options));
    }

    // Indented continuations: nested lists, callouts, or prose under this item.
    while (index < lines.length) {
      if (isBlank(lines[index])) {
        const look = peekNonBlank(lines, index + 1);
        if (look >= lines.length) break;
        if (leadingIndent(lines[look]) > baseIndent) {
          index = look;
          continue;
        }
        break;
      }

      const indent = leadingIndent(lines[index]);
      if (indent <= baseIndent) break;

      const nestedBullet = lines[index].match(bulletListPattern);
      const nestedOrdered = lines[index].match(orderedListPattern);

      if (nestedBullet && nestedBullet[1].length > baseIndent) {
        const nested = parseListAt(lines, index, nestedBullet[1].length, "bullet", options);
        itemContent.push(nested.node);
        index = nested.nextIndex;
        continue;
      }

      if (nestedOrdered && nestedOrdered[1].length > baseIndent) {
        const nested = parseListAt(lines, index, nestedOrdered[1].length, "ordered", options);
        itemContent.push(nested.node);
        index = nested.nextIndex;
        continue;
      }

      if (isCalloutMarkerLine(lines[index])) {
        const parsed = parseCalloutAt(lines, index, options);
        itemContent.push(parsed.node);
        index = parsed.nextIndex;
        continue;
      }

      if (isTableRowLine(lines[index])) {
        const tableLines: string[] = [];
        while (index < lines.length && isTableRowLine(lines[index]) && leadingIndent(lines[index]) > baseIndent) {
          tableLines.push(lines[index]);
          index += 1;
        }
        const table = parseMarkdownTable(tableLines, options);
        if (table) itemContent.push(table);
        continue;
      }

      const paragraphLines: string[] = [];
      while (
        index < lines.length
        && !isBlank(lines[index])
        && leadingIndent(lines[index]) > baseIndent
        && !bulletListPattern.test(lines[index])
        && !orderedListPattern.test(lines[index])
        && !isCalloutMarkerLine(lines[index])
        && !isTableRowLine(lines[index])
      ) {
        paragraphLines.push(lines[index].trim());
        index += 1;
      }
      if (paragraphLines.length > 0) {
        itemContent.push(paragraph(paragraphLines.join(" ").trim(), options));
      } else {
        break;
      }
    }

    items.push({
      type: "listItem",
      content: itemContent.length > 0 ? itemContent : [paragraph("")],
    });
  }

  if (kind === "ordered") {
    return {
      node: { type: "orderedList", attrs: { start: orderedStart }, content: items },
      nextIndex: index,
    };
  }

  return {
    node: { type: "bulletList", content: items },
    nextIndex: index,
  };
}

export function markdownToTiptapDoc(markdown: string, options: MarkdownImportOptions = {}): MarkdownImportResult {
  const stripped = stripLeadingYamlFrontmatter(markdown).markdown;
  const lines = stripped.replace(/\r\n?/g, "\n").split("\n");
  const content: unknown[] = [];
  const diagnostics: MarkdownImportDiagnostic[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    const lineNumber = index + 1;
    if (isBlank(line)) {
      index += 1;
      continue;
    }

    const heading = line.trimStart().match(headingPattern);
    if (heading && leadingIndent(line) === 0) {
      content.push({
        type: "heading",
        attrs: { level: heading[1].length },
        content: parseInlineContent(heading[2].trim(), options),
      });
      index += 1;
      continue;
    }

    if (isCalloutMarkerLine(line)) {
      const parsed = parseCalloutAt(lines, index, options);
      content.push(parsed.node);
      index = parsed.nextIndex;
      continue;
    }

    const bullet = line.match(bulletListPattern);
    if (bullet) {
      const parsed = parseListAt(lines, index, bullet[1].length, "bullet", options);
      content.push(parsed.node);
      index = parsed.nextIndex;
      continue;
    }

    const ordered = line.match(orderedListPattern);
    if (ordered) {
      const parsed = parseListAt(lines, index, ordered[1].length, "ordered", options);
      content.push(parsed.node);
      index = parsed.nextIndex;
      continue;
    }

    if (isTableRowLine(line)) {
      const tableLines: string[] = [];
      while (index < lines.length && isTableRowLine(lines[index])) {
        tableLines.push(lines[index]);
        index += 1;
      }
      const table = parseMarkdownTable(tableLines, options);
      if (table) {
        content.push(table);
      } else {
        diagnostics.push({ level: "warning", message: "Malformed Markdown table imported as paragraphs.", line: lineNumber });
        for (const tableLine of tableLines) {
          content.push(paragraph(tableLine.trim(), options));
        }
      }
      continue;
    }

    if (/^\s*</.test(line) || /^\s*!\[/.test(line) || /^---\s*$/.test(line)) {
      diagnostics.push({ level: "warning", message: "Unsupported Markdown block imported as paragraph.", line: lineNumber });
    }

    const paragraphLines: string[] = [];
    while (index < lines.length && !isBlank(lines[index]) && !isBlockStart(lines[index])) {
      paragraphLines.push(lines[index].trim());
      index += 1;
    }
    content.push(paragraph(paragraphLines.join(" ").trim(), options));
  }

  return { doc: { type: "doc", content } as JSONContent, diagnostics };
}
