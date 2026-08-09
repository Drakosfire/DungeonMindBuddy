import type { JSONContent } from "@tiptap/core";
import { normalizeCalloutKind } from "./calloutMarkdown";
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
  /** Default true; set false to leave dmb-node links as plain text (emits a warning). */
  parseGraphNodeLinks?: boolean;
};

type ParseContext = {
  options: MarkdownImportOptions;
  diagnostics: MarkdownImportDiagnostic[];
  lineNumberForIndex: (index: number) => number;
};

function shouldParseGraphNodeLinks(options: MarkdownImportOptions): boolean {
  return options.parseGraphNodeLinks !== false;
}

export function hasBlockingMarkdownImportDiagnostics(markdown: string): boolean {
  return markdownToTiptapDoc(markdown).diagnostics.some((diagnostic) => diagnostic.level === "warning");
}

type TiptapMark = { type: string; attrs?: Record<string, unknown> };
type TiptapNode = {
  type: string;
  attrs?: Record<string, unknown>;
  content?: unknown[];
  text?: string;
  marks?: TiptapMark[];
};

const typedReferencePattern =
  /\[([^\]]+)\]\(#dmb-(ref|action):([a-z][a-z0-9-]*):([a-z0-9][a-z0-9_.:-]*)\)/g;
const graphNodeReferencePattern = /\[([^\]]+)\]\(dmb-node:([^)]+)\)/g;
const ordinaryLinkPattern = /(?<!!)\[[^\]]+\]\((?!#dmb-|dmb-node:)[^)]+\)/;
const referenceStyleLinkPattern = /\[[^\]]+\]\[[^\]]+\]/;
const headingPattern = /^(#{1,6})\s+(.+)$/;
const bulletListPattern = /^-\s+(.+)$/;
const orderedListPattern = /^(\d+)[.)]\s+(.+)$/;
const calloutMarkerPattern = /^>\s*\[!([^\]]+)\]\s*(.*)$/;
const horizontalRulePattern = /^\s*---\s*$/;
const setextUnderlinePattern = /^\s*(?:=+|-+)\s*$/;
const supportedCalloutMarkers = new Set(["READ-ALOUD", "GM-NOTE", "RULES", "WARNING"]);

function textNode(text: string, marks?: TiptapMark[]): TiptapNode | null {
  if (!text) return null;
  return marks && marks.length > 0 ? { type: "text", text, marks } : { type: "text", text };
}

function unescapeMarkdownText(text: string): string {
  return text.replace(/\\([\\`*_{}[\]()#+.!|>~-])/g, "$1");
}

function addMark(content: unknown[], mark: TiptapMark): unknown[] {
  return content.map((value) => {
    const node = value as TiptapNode;
    if (node.type !== "text") return value;
    return { ...node, marks: [...(node.marks ?? []), mark] };
  });
}

/** Parse only inline marks mounted by StarterKit and emitted by our serializer. */
function parseTextWithMarks(text: string): unknown[] {
  if (!text) return [];
  // Underscore bold/italic require CommonMark-ish non-word boundaries so identifiers
  // like snake_case_value / foo__bar__baz are not rewritten as emphasis.
  const tokenPattern = /(`+)([\s\S]*?)\1|\*\*([\s\S]+?)\*\*|(?<!\w)__([^_\n]+?)__(?!\w)|~~([\s\S]+?)~~|(?<!\\)\*([^*\n]+?)\*|(?<!\\)(?<!\w)_([^_\n]+?)_(?!\w)/g;
  const content: unknown[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = tokenPattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      const leading = textNode(unescapeMarkdownText(text.slice(lastIndex, match.index)));
      if (leading) content.push(leading);
    }
    if (match[1] !== undefined) {
      const node = textNode(match[2] ?? "", [{ type: "code" }]);
      if (node) content.push(node);
    } else if (match[3] !== undefined || match[4] !== undefined) {
      content.push(...addMark(parseTextWithMarks(match[3] ?? match[4] ?? ""), { type: "bold" }));
    } else if (match[5] !== undefined) {
      content.push(...addMark(parseTextWithMarks(match[5]), { type: "strike" }));
    } else if (match[6] !== undefined || match[7] !== undefined) {
      content.push(...addMark(parseTextWithMarks(match[6] ?? match[7] ?? ""), { type: "italic" }));
    }
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    const trailing = textNode(unescapeMarkdownText(text.slice(lastIndex)));
    if (trailing) content.push(trailing);
  }
  return content;
}

function parseInlineContent(text: string, ctx: ParseContext): unknown[] {
  const matches = [
    ...[...text.matchAll(typedReferencePattern)].map((match) => ({
      match,
      index: match.index ?? 0,
      length: match[0].length,
      kind: "runbook" as const,
    })),
    ...(shouldParseGraphNodeLinks(ctx.options)
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

function paragraph(text: string, ctx: ParseContext): TiptapNode {
  return { type: "paragraph", content: parseInlineContent(text, ctx) };
}

function listItem(text: string, ctx: ParseContext): TiptapNode {
  return { type: "listItem", content: [paragraph(text, ctx)] };
}

function isBlank(line: string): boolean {
  return line.trim() === "";
}

function unsafeDiagnostic(message: string, line: number): MarkdownImportDiagnostic {
  return { level: "warning", message, line };
}

function parseTableCells(line: string): string[] {
  const cells: string[] = [];
  let cell = "";
  let escaped = false;
  let codeTicks = 0;
  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    if (escaped) {
      cell += char;
      escaped = false;
      continue;
    }
    if (char === "\\") {
      escaped = true;
      cell += char;
      continue;
    }
    if (char === "`") {
      let run = 1;
      while (index + run < line.length && line[index + run] === "`") run += 1;
      if (codeTicks === 0) codeTicks = run;
      else if (codeTicks === run) codeTicks = 0;
      cell += "`".repeat(run);
      index += run - 1;
      continue;
    }
    if (char === "|" && codeTicks === 0) {
      cells.push(cell.trim());
      cell = "";
      continue;
    }
    cell += char;
  }
  cells.push(cell.trim());
  if (cells[0] === "") cells.shift();
  if (cells.at(-1) === "") cells.pop();
  return cells.map((value) => value.replace(/\\\|/g, "|"));
}

function isTableSeparatorLine(line: string): boolean {
  const cells = parseTableCells(line);
  return cells.length > 0 && cells.every((cell) => /^:?-{3,}:?$/.test(cell.replace(/\s+/g, "")));
}

function beginsMarkdownTable(lines: string[], index: number): boolean {
  if (index + 1 >= lines.length) return false;
  const header = parseTableCells(lines[index]);
  return header.length > 0 && lines[index].includes("|") && isTableSeparatorLine(lines[index + 1]);
}

function hasExplicitHardBreak(line: string): boolean {
  return / {2}$/.test(line) || /\\$/.test(line);
}

function collectTableStructureDiagnostics(
  lines: string[],
  startIndex: number,
  ctx: ParseContext,
): void {
  const headerCells = parseTableCells(lines[startIndex]);
  const headerWidth = headerCells.length;
  const headerLine = ctx.lineNumberForIndex(startIndex);
  for (const cell of headerCells) {
    ctx.diagnostics.push(...collectUnsupportedInlineDiagnostics(cell, headerLine, ctx.options));
  }
  const separatorCells = parseTableCells(lines[startIndex + 1]);
  if (separatorCells.some((cell) => cell.includes(":"))) {
    ctx.diagnostics.push(unsafeDiagnostic(
      "GFM table alignment markers are not represented by the current editor table model.",
      ctx.lineNumberForIndex(startIndex + 1),
    ));
  }
  let rowIndex = startIndex + 2;
  while (rowIndex < lines.length && !isBlank(lines[rowIndex]) && lines[rowIndex].includes("|")) {
    const cells = parseTableCells(lines[rowIndex]);
    const lineNumber = ctx.lineNumberForIndex(rowIndex);
    if (cells.length !== headerWidth) {
      ctx.diagnostics.push(unsafeDiagnostic(
        "GFM table rows must have the same number of cells as the header for safe editing.",
        lineNumber,
      ));
    }
    for (const cell of cells) {
      ctx.diagnostics.push(...collectUnsupportedInlineDiagnostics(cell, lineNumber, ctx.options));
    }
    rowIndex += 1;
  }
}

function graphNodeLinkDiagnostics(text: string, lineNumber: number, options: MarkdownImportOptions): MarkdownImportDiagnostic[] {
  if (shouldParseGraphNodeLinks(options)) return [];
  const diagnostics: MarkdownImportDiagnostic[] = [];
  for (const _match of text.matchAll(graphNodeReferencePattern)) {
    diagnostics.push(unsafeDiagnostic(
      "Graph node links (dmb-node:) cannot be preserved safely when graph link parsing is disabled.",
      lineNumber,
    ));
  }
  return diagnostics;
}

function hasUnsupportedInlineLink(line: string): boolean {
  return ordinaryLinkPattern.test(line) || referenceStyleLinkPattern.test(line);
}

/** Inline constructs the cell/paragraph parse path cannot round-trip. */
function collectUnsupportedInlineDiagnostics(
  text: string,
  lineNumber: number,
  options: MarkdownImportOptions,
): MarkdownImportDiagnostic[] {
  const diagnostics: MarkdownImportDiagnostic[] = [];
  if (/!\[[^\]]*\]\([^)]+\)/.test(text)) {
    diagnostics.push(unsafeDiagnostic("Markdown images are not supported yet.", lineNumber));
  }
  if (hasExplicitHardBreak(text)) {
    diagnostics.push(unsafeDiagnostic("Explicit Markdown hard breaks are not supported yet.", lineNumber));
  }
  if (hasUnsupportedInlineLink(text)) {
    diagnostics.push(unsafeDiagnostic(
      "Ordinary Markdown links are not supported by the mounted editor schema.",
      lineNumber,
    ));
  }
  diagnostics.push(...graphNodeLinkDiagnostics(text, lineNumber, options));
  return diagnostics;
}

/** Detect source forms that the bounded editor grammar cannot reproduce safely. */
function sourceSafetyDiagnostics(lines: string[], options: MarkdownImportOptions = {}): MarkdownImportDiagnostic[] {
  const diagnostics: MarkdownImportDiagnostic[] = [];
  let inTopLevelCallout = false;

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    const lineNumber = index + 1;
    const previousLine = index > 0 ? lines[index - 1] : "";
    const topLevelCallout = line.match(calloutMarkerPattern);

    if (beginsMarkdownTable(lines, index)) {
      // Structure + cell inline diagnostics come from collectTableStructureDiagnostics
      // on the shared table parse path (top-level and callout interiors).
      let rowIndex = index + 2;
      while (rowIndex < lines.length && !isBlank(lines[rowIndex]) && lines[rowIndex].includes("|")) {
        rowIndex += 1;
      }
      index = Math.max(index, rowIndex - 1);
      inTopLevelCallout = false;
      continue;
    }

    if (topLevelCallout) {
      inTopLevelCallout = true;
      if (!supportedCalloutMarkers.has(topLevelCallout[1].trim().toUpperCase())) {
        diagnostics.push(unsafeDiagnostic(
          `Callout marker ${topLevelCallout[1]} is not supported by this editor slice.`,
          lineNumber,
        ));
      }
      continue;
    }

    if (inTopLevelCallout && line.startsWith(">")) {
      const body = line.replace(/^> ?/, "");
      if (/^\s{2,}(?:[-+*]\s+|\d+[.)]\s+)/.test(body)) {
        diagnostics.push(unsafeDiagnostic("Nested lists inside callouts are not supported yet.", lineNumber));
      }
      if (/^\s*\[![^\]]+\]/.test(body)) {
        diagnostics.push(unsafeDiagnostic("Nested callouts are not supported yet.", lineNumber));
      }
      if (/^\s*(?:```|~~~)/.test(body)) {
        diagnostics.push(unsafeDiagnostic("Fenced code blocks are not supported yet.", lineNumber));
      }
      diagnostics.push(...collectUnsupportedInlineDiagnostics(body, lineNumber, options));
      continue;
    }

    inTopLevelCallout = false;

    if (
      setextUnderlinePattern.test(line)
      && !isBlank(previousLine)
      && !headingPattern.test(previousLine)
      && !calloutMarkerPattern.test(previousLine)
    ) {
      diagnostics.push(unsafeDiagnostic("Setext-style headings are not supported; use ATX # headings.", lineNumber));
      continue;
    }
    if (hasExplicitHardBreak(line)) {
      diagnostics.push(unsafeDiagnostic("Explicit Markdown hard breaks are not supported yet.", lineNumber));
      continue;
    }
    if (/^(?:\t| {2,})\S/.test(line)) {
      diagnostics.push(unsafeDiagnostic("Indented Markdown blocks and list continuations are not supported yet.", lineNumber));
      continue;
    }
    if (/^\s+>/.test(line)) {
      diagnostics.push(unsafeDiagnostic("Indented or list-nested blockquotes/callouts are not supported yet.", lineNumber));
      continue;
    }
    if (/^>/.test(line)) {
      diagnostics.push(unsafeDiagnostic("Plain blockquotes are not supported yet.", lineNumber));
      continue;
    }
    if (/^\s+(?:[-+*]\s+|\d+[.)]\s+)/.test(line)) {
      diagnostics.push(unsafeDiagnostic("Nested lists are not supported yet.", lineNumber));
      continue;
    }
    if (/^(?:[-+*]\s+|\d+[.)]\s+)>\s*\[!/.test(line)) {
      diagnostics.push(unsafeDiagnostic("Callouts nested in list items are not supported yet.", lineNumber));
      continue;
    }
    if (/^[+*]\s+/.test(line)) {
      diagnostics.push(unsafeDiagnostic("Only hyphen bullet markers are supported by this editor slice.", lineNumber));
      continue;
    }
    if (/^\s*-\s+\[[ xX]\]\s+/.test(line)) {
      diagnostics.push(unsafeDiagnostic("Task-list items are not supported yet.", lineNumber));
      continue;
    }
    if (/^\s*(?:```|~~~)/.test(line)) {
      diagnostics.push(unsafeDiagnostic("Fenced code blocks are not supported yet.", lineNumber));
      continue;
    }
    if (/^\s{0,3}\[[^\]]+\]:\s+\S+/.test(line)) {
      diagnostics.push(unsafeDiagnostic("Reference-style link definitions are not supported yet.", lineNumber));
      continue;
    }
    if (/^\s*</.test(line)) {
      diagnostics.push(unsafeDiagnostic("Raw HTML blocks are not supported yet.", lineNumber));
      continue;
    }
    diagnostics.push(...collectUnsupportedInlineDiagnostics(line, lineNumber, options));
  }

  return diagnostics;
}

function parseMarkdownTable(
  lines: string[],
  startIndex: number,
  ctx: ParseContext,
): { node: TiptapNode; nextIndex: number } {
  collectTableStructureDiagnostics(lines, startIndex, ctx);
  const headerCells = parseTableCells(lines[startIndex]);
  const rows: unknown[] = [{
    type: "tableRow",
    content: headerCells.map((cell) => ({
      type: "tableHeader",
      content: [paragraph(cell, ctx)],
    })),
  }];
  let index = startIndex + 2;
  while (index < lines.length && !isBlank(lines[index]) && lines[index].includes("|")) {
    const cells = parseTableCells(lines[index]);
    rows.push({
      type: "tableRow",
      content: headerCells.map((_, cellIndex) => ({
        type: "tableCell",
        content: [paragraph(cells[cellIndex] ?? "", ctx)],
      })),
    });
    index += 1;
  }
  return { node: { type: "table", content: rows }, nextIndex: index };
}

function isBlockStart(lines: string[], index: number): boolean {
  const line = lines[index] ?? "";
  return headingPattern.test(line)
    || calloutMarkerPattern.test(line)
    || bulletListPattern.test(line)
    || orderedListPattern.test(line)
    || horizontalRulePattern.test(line)
    || beginsMarkdownTable(lines, index);
}

function parseCalloutBody(lines: string[], ctx: ParseContext): unknown[] {
  const content: unknown[] = [];
  let index = 0;
  while (index < lines.length) {
    if (isBlank(lines[index])) {
      index += 1;
      continue;
    }
    const heading = lines[index].match(headingPattern);
    if (heading) {
      content.push({
        type: "heading",
        attrs: { level: heading[1].length },
        content: parseInlineContent(heading[2].trim(), ctx),
      });
      index += 1;
      continue;
    }
    if (horizontalRulePattern.test(lines[index])) {
      content.push({ type: "horizontalRule" });
      index += 1;
      continue;
    }
    if (beginsMarkdownTable(lines, index)) {
      const table = parseMarkdownTable(lines, index, ctx);
      content.push(table.node);
      index = table.nextIndex;
      continue;
    }
    const bullet = lines[index].match(bulletListPattern);
    if (bullet) {
      const items: unknown[] = [];
      while (index < lines.length) {
        const item = lines[index].match(bulletListPattern);
        if (!item) break;
        items.push(listItem(item[1], ctx));
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
        items.push(listItem(item[2], ctx));
        index += 1;
      }
      content.push({ type: "orderedList", attrs: { start }, content: items });
      continue;
    }
    const paragraphLines: string[] = [];
    while (
      index < lines.length
      && !isBlank(lines[index])
      && !headingPattern.test(lines[index])
      && !bulletListPattern.test(lines[index])
      && !orderedListPattern.test(lines[index])
      && !horizontalRulePattern.test(lines[index])
      && !beginsMarkdownTable(lines, index)
    ) {
      paragraphLines.push(lines[index]);
      index += 1;
    }
    content.push(paragraph(paragraphLines.join(" ").trim(), ctx));
  }
  return content.length > 0 ? content : [paragraph("", ctx)];
}

function parseCalloutAt(
  lines: string[],
  startIndex: number,
  ctx: ParseContext,
): { node: TiptapNode; nextIndex: number } {
  const match = lines[startIndex].match(calloutMarkerPattern);
  if (!match) return { node: paragraph(lines[startIndex], ctx), nextIndex: startIndex + 1 };
  const [, marker, rawLabel] = match;
  const bodyLines: string[] = [];
  let index = startIndex + 1;
  while (index < lines.length && lines[index].startsWith(">")) {
    if (calloutMarkerPattern.test(lines[index])) break;
    bodyLines.push(lines[index].replace(/^> ?/, ""));
    index += 1;
  }
  const bodyCtx: ParseContext = {
    ...ctx,
    lineNumberForIndex: (bodyIndex) => startIndex + 2 + bodyIndex,
  };
  return {
    node: {
      type: "callout",
      attrs: {
        kind: normalizeCalloutKind(marker),
        ...(rawLabel.trim() ? { label: rawLabel.trim() } : {}),
      },
      content: parseCalloutBody(bodyLines, bodyCtx),
    },
    nextIndex: index,
  };
}

export function markdownToTiptapDoc(
  markdown: string,
  options: MarkdownImportOptions = {},
): MarkdownImportResult {
  const stripped = stripLeadingYamlFrontmatter(markdown).markdown;
  const lines = stripped.replace(/\r\n?/g, "\n").split("\n");
  const content: unknown[] = [];
  const parseDiagnostics: MarkdownImportDiagnostic[] = [];
  const ctx: ParseContext = {
    options,
    diagnostics: parseDiagnostics,
    lineNumberForIndex: (index) => index + 1,
  };
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    if (isBlank(line)) {
      index += 1;
      continue;
    }
    const heading = line.match(headingPattern);
    if (heading) {
      content.push({
        type: "heading",
        attrs: { level: heading[1].length },
        content: parseInlineContent(heading[2].trim(), ctx),
      });
      index += 1;
      continue;
    }
    if (calloutMarkerPattern.test(line)) {
      const parsed = parseCalloutAt(lines, index, ctx);
      content.push(parsed.node);
      index = parsed.nextIndex;
      continue;
    }
    if (horizontalRulePattern.test(line)) {
      content.push({ type: "horizontalRule" });
      index += 1;
      continue;
    }
    if (beginsMarkdownTable(lines, index)) {
      const table = parseMarkdownTable(lines, index, ctx);
      content.push(table.node);
      index = table.nextIndex;
      continue;
    }
    const bullet = line.match(bulletListPattern);
    if (bullet) {
      const items: unknown[] = [];
      while (index < lines.length) {
        const item = lines[index].match(bulletListPattern);
        if (!item) break;
        items.push(listItem(item[1], ctx));
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
        items.push(listItem(item[2], ctx));
        index += 1;
      }
      content.push({ type: "orderedList", attrs: { start }, content: items });
      continue;
    }
    const paragraphLines: string[] = [];
    while (index < lines.length && !isBlank(lines[index]) && !isBlockStart(lines, index)) {
      paragraphLines.push(lines[index].trim());
      index += 1;
    }
    content.push(paragraph(paragraphLines.join(" ").trim(), ctx));
  }

  const diagnostics = [...sourceSafetyDiagnostics(lines, options), ...parseDiagnostics];
  return { doc: { type: "doc", content } as JSONContent, diagnostics };
}
