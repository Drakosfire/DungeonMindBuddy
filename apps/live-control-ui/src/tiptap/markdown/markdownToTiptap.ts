import type { JSONContent } from "@tiptap/core";
import { isDecisionConsequenceMarker, normalizeCalloutKind } from "./calloutMarkdown";
import { stripLeadingYamlFrontmatter } from "./stripLeadingYamlFrontmatter";
import {
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
const bulletListPattern = /^-\s+(.+)$/;
const orderedListPattern = /^(\d+)[.)]\s+(.+)$/;
const calloutMarkerPattern = /^>\s*\[!([^\]]+)\]\s*(.*)$/;

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
      content.push({ type: "graphNodeReference", attrs: { nodeId, label } });
    } else {
      const [, label, kind, refType, refId] = item.match;
      const attrs: RunbookReferenceAttrs = normalizeRunbookReferenceAttrs({ kind, refType, refId, label } as RunbookReferenceAttrs);
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

function listItem(text: string, options: MarkdownImportOptions = {}): TiptapNode {
  return { type: "listItem", content: [paragraph(text, options)] };
}

function isBlank(line: string): boolean {
  return line.trim() === "";
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

function isBlockStart(line: string): boolean {
  return headingPattern.test(line)
    || calloutMarkerPattern.test(line)
    || bulletListPattern.test(line)
    || orderedListPattern.test(line)
    || isTableRowLine(line);
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
      const items: unknown[] = [];
      while (index < lines.length) {
        const item = lines[index].match(bulletListPattern);
        if (!item) break;
        items.push(listItem(item[1], options));
        index += 1;
      }
      content.push({ type: "bulletList", content: items });
      continue;
    }

    const ordered = lines[index].match(orderedListPattern);
    if (ordered) {
      const start = Number(ordered[1]);
      const items: unknown[] = [];
      while (index < lines.length) {
        const item = lines[index].match(orderedListPattern);
        if (!item) break;
        items.push(listItem(item[2], options));
        index += 1;
      }
      content.push({ type: "orderedList", attrs: { start }, content: items });
      continue;
    }

    const paragraphLines: string[] = [];
    while (
      index < lines.length
      && !isBlank(lines[index])
      && !bulletListPattern.test(lines[index])
      && !orderedListPattern.test(lines[index])
      && !isTableRowLine(lines[index])
    ) {
      paragraphLines.push(lines[index]);
      index += 1;
    }
    content.push(paragraph(paragraphLines.join(" ").trim(), options));
  }

  return content.length > 0 ? content : [paragraph("")];
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

    const heading = line.match(headingPattern);
    if (heading) {
      content.push({ type: "heading", attrs: { level: heading[1].length }, content: parseInlineContent(heading[2].trim(), options) });
      index += 1;
      continue;
    }

    const callout = line.match(calloutMarkerPattern);
    if (callout) {
      const [, marker, rawLabel] = callout;
      const bodyLines: string[] = [];
      index += 1;
      while (index < lines.length && lines[index].startsWith(">")) {
        bodyLines.push(lines[index].replace(/^> ?/, ""));
        index += 1;
      }
      if (isDecisionConsequenceMarker(marker)) {
        content.push({
          type: "decisionConsequence",
          content: parseDecisionConsequenceBody(bodyLines, options),
        });
      } else {
        content.push({
          type: "callout",
          attrs: { kind: normalizeCalloutKind(marker), ...(rawLabel.trim() ? { label: rawLabel.trim() } : {}) },
          content: parseCalloutBody(bodyLines, options),
        });
      }
      continue;
    }

    const bullet = line.match(bulletListPattern);
    if (bullet) {
      const items: unknown[] = [];
      while (index < lines.length) {
        const item = lines[index].match(bulletListPattern);
        if (!item) break;
        items.push(listItem(item[1], options));
        index += 1;
      }
      content.push({ type: "bulletList", content: items });
      continue;
    }

    const ordered = line.match(orderedListPattern);
    if (ordered) {
      const start = Number(ordered[1]);
      const items: unknown[] = [];
      while (index < lines.length) {
        const item = lines[index].match(orderedListPattern);
        if (!item) break;
        items.push(listItem(item[2], options));
        index += 1;
      }
      content.push({ type: "orderedList", attrs: { start }, content: items });
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
