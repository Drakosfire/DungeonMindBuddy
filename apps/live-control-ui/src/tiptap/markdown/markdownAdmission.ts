import type {
  Blockquote,
  Heading,
  Link,
  List,
  ListItem,
  PhrasingContent,
  RootContent,
  Table,
  TableRow,
  ThematicBreak,
} from "mdast";

import {
  healRunbookReferenceLabel,
  isSupportedRunbookReference,
  isValidGraphNodeId,
  normalizeRunbookReferenceAttrs,
  type RunbookReferenceAttrs,
} from "../references/runbookReferences";
import { normalizeCalloutKind } from "./calloutMarkdown";
import { parseMarkdownAst } from "./parseMarkdownAst";

export type MarkdownImportDiagnostic = {
  level: "info" | "warning";
  message: string;
  line?: number;
};

export type MarkdownImportOptions = {
  /** Default true; set false to leave dmb-node links as plain text (emits a warning). */
  parseGraphNodeLinks?: boolean;
};

/**
 * AST admission + projection visitor (handoff §8).
 *
 * One traversal decides BOTH whether a parsed node is supported AND how a
 * supported node projects into TipTap. There is deliberately no second
 * structural walk: a node cannot be projected as supported unless the
 * admission logic for that exact node/context accepted it.
 *
 * The mdast parser owns Markdown structure. DungeonBuddy-owned recognizers
 * are limited to app semantics on parsed structure (handoff §9/§23):
 * classifying a link destination as a typed/graph reference, classifying a
 * blockquote as a canonical callout, and validating serializer-canonical
 * source spellings (ATX heading, `---` thematic break, `-` bullet marker).
 *
 * Contexts:
 * - "document": root level; source lines are free of container prefixes.
 * - "callout":  inside a canonical callout body. Bodies are re-parsed from
 *               dedented source lines, so source-form checks remain valid.
 * - "listItem": direct child of a list item. Span lines carry the item
 *               marker/indent, so only the blunt continuation-indent guard
 *               runs; container-nested structures are diagnosed by type.
 * - "nested":   parsed-children projection of an already-sealed nested
 *               blockquote. Source lines carry container prefixes, so all
 *               source-form checks are skipped; structural diagnostics stay.
 * - "tableCell": synthesized cell paragraphs; no source span of their own.
 */
type AdmissionContext = "document" | "callout" | "listItem" | "tableCell" | "nested";

type VisitorState = {
  /** Source lines of the current parse space (document body or a dedented callout segment). */
  lines: string[];
  /** Added to AST line numbers so diagnostics point at the original document (frontmatter offset). */
  lineOffset: number;
  options: MarkdownImportOptions;
  diagnostics: MarkdownImportDiagnostic[];
};

type TiptapMark = { type: string; attrs?: Record<string, unknown> };
type TiptapNode = {
  type: string;
  attrs?: Record<string, unknown>;
  content?: unknown[];
  text?: string;
  marks?: TiptapMark[];
};

const SUPPORTED_CALLOUT_MARKERS = new Set(["READ-ALOUD", "GM-NOTE", "RULES", "WARNING"]);
const DMB_REFERENCE_URL_PATTERN = /^#dmb-(ref|action):([a-z][a-z0-9-]*):([a-z0-9][a-z0-9_.:-]*)$/;
const GRAPH_NODE_URL_PREFIX = "dmb-node:";
const CALLOUT_MARKER_LINE_PATTERN = /^\s{0,3}\[!([^\]]+)\]\s*(.*)$/;
const LEADING_INDENT_PATTERN = /^(?:\t| {2,})\S/;
/**
 * Fail-closed detector for source that LOOKS like a GFM table but did not
 * parse as one (e.g. an unescaped pipe inside a header code span makes the
 * header/delimiter widths disagree, so micromark falls back to a paragraph).
 * This never builds structure; it only refuses to silently flatten.
 */
const TABLE_DELIMITER_ROW_PATTERN = /^\s{0,3}\|?\s*:?-+:?\s*(?:\|\s*:?-+:?\s*)+\|?\s*$/;

function shouldParseGraphNodeLinks(options: MarkdownImportOptions): boolean {
  return options.parseGraphNodeLinks !== false;
}

/** True when the context's source lines are free of container prefixes. */
function allowsSourceFormChecks(context: AdmissionContext): boolean {
  return context === "document" || context === "callout";
}

function warn(state: VisitorState, message: string, line: number): void {
  state.diagnostics.push({ level: "warning", message, line: line + state.lineOffset });
}

function nodeStartLine(node: RootContent | PhrasingContent | ListItem | TableRow): number {
  return node.position?.start.line ?? 1;
}

function nodeEndLine(node: RootContent | PhrasingContent | ListItem | TableRow): number {
  return node.position?.end.line ?? nodeStartLine(node);
}

/** Full source lines covered by a parsed node (positions come from the parser). */
function spanLines(
  node: RootContent | PhrasingContent | ListItem | TableRow | Blockquote,
  state: VisitorState,
): string[] {
  const start = nodeStartLine(node) - 1;
  return state.lines.slice(start, nodeEndLine(node));
}

/** Raw source text of a parsed node — used for provenance checks and sealed-view projections. */
function sourceSlice(node: RootContent | PhrasingContent, state: VisitorState): string {
  const position = node.position;
  if (!position) return "";
  if (position.start.line === position.end.line) {
    return (state.lines[position.start.line - 1] ?? "").slice(position.start.column - 1, position.end.column - 1);
  }
  const parts: string[] = [];
  for (let line = position.start.line; line <= position.end.line; line += 1) {
    const text = state.lines[line - 1] ?? "";
    if (line === position.start.line) parts.push(text.slice(position.start.column - 1));
    else if (line === position.end.line) parts.push(text.slice(0, position.end.column - 1));
    else parts.push(text);
  }
  return parts.join("\n");
}

function textNode(text: string, marks?: TiptapMark[]): TiptapNode | null {
  if (!text) return null;
  return marks && marks.length > 0 ? { type: "text", text, marks } : { type: "text", text };
}

/** Soft-wrapped source lines join with a single space, matching the legacy importer. */
function normalizeWrappedText(text: string): string {
  return text.replace(/\s*\n\s*/g, " ");
}

function paragraphFromText(text: string): TiptapNode {
  const node = textNode(normalizeWrappedText(text).trim());
  return { type: "paragraph", content: node ? [node] : [] };
}

/** Best-effort sealed-view projection for unsupported inline constructs: the source spelling as text. */
function sourceTextNodes(node: RootContent | PhrasingContent, state: VisitorState): TiptapNode[] {
  const nodeText = textNode(normalizeWrappedText(sourceSlice(node, state)).trim());
  return nodeText ? [nodeText] : [];
}

function withMark(nodes: TiptapNode[], mark: TiptapMark): TiptapNode[] {
  return nodes.map((node) => (node.type === "text"
    ? { ...node, marks: [...(node.marks ?? []), mark] }
    : node));
}

function sameMarks(left: TiptapNode, right: TiptapNode): boolean {
  return JSON.stringify(left.marks ?? null) === JSON.stringify(right.marks ?? null);
}

/** Merge adjacent text runs with identical marks (the legacy regex importer emitted single runs). */
function mergeAdjacentText(nodes: TiptapNode[]): TiptapNode[] {
  const merged: TiptapNode[] = [];
  for (const node of nodes) {
    const previous = merged.at(-1);
    if (node.type === "text" && previous?.type === "text" && sameMarks(previous, node)) {
      merged[merged.length - 1] = { ...previous, text: `${previous.text ?? ""}${node.text ?? ""}` };
    } else {
      merged.push(node);
    }
  }
  return merged;
}

function collectLabelText(children: PhrasingContent[]): string {
  const parts: string[] = [];
  for (const child of children) {
    if (child.type === "text" || child.type === "inlineCode") {
      parts.push(child.value);
    } else if ("children" in child && Array.isArray(child.children)) {
      parts.push(collectLabelText(child.children as PhrasingContent[]));
    }
  }
  return parts.join("");
}

/**
 * Reference nodes are opaque atoms with a single plain-text label: only a
 * label whose parsed children are pure text survives projection. Marked,
 * code, or otherwise structured labels would be silently flattened, so the
 * link seals instead of importing lossily.
 */
function hasRepresentableReferenceLabel(node: Link): boolean {
  return node.children.every((child) => child.type === "text");
}

function visitLink(node: Link, state: VisitorState): TiptapNode[] {
  const url = node.url ?? "";
  const label = healRunbookReferenceLabel(collectLabelText(node.children).trim());

  if (url.startsWith(GRAPH_NODE_URL_PREFIX)) {
    if (node.title != null) {
      warn(state, "Link titles are not represented by DungeonBuddy reference nodes.", nodeStartLine(node));
      return sourceTextNodes(node, state);
    }
    if (!shouldParseGraphNodeLinks(state.options)) {
      warn(
        state,
        "Graph node links (dmb-node:) cannot be preserved safely when graph link parsing is disabled.",
        nodeStartLine(node),
      );
      return sourceTextNodes(node, state);
    }
    const nodeId = url.slice(GRAPH_NODE_URL_PREFIX.length);
    if (!isValidGraphNodeId(nodeId)) {
      // An empty/invalid id serializes as bare label text: the link disappears.
      warn(state, "Graph node links must target a valid, non-empty node id.", nodeStartLine(node));
      return sourceTextNodes(node, state);
    }
    if (!hasRepresentableReferenceLabel(node)) {
      warn(state, "Formatted link labels are not represented by DungeonBuddy reference nodes.", nodeStartLine(node));
      return sourceTextNodes(node, state);
    }
    return [{ type: "graphNodeReference", attrs: { nodeId, label: label || nodeId } }];
  }

  const referenceMatch = url.match(DMB_REFERENCE_URL_PATTERN);
  if (referenceMatch && node.title == null) {
    const [, kind, refType, refId] = referenceMatch;
    const attrs: RunbookReferenceAttrs = normalizeRunbookReferenceAttrs({
      kind,
      refType,
      refId,
      label: label || refId,
    } as RunbookReferenceAttrs);
    if (isSupportedRunbookReference(attrs)) {
      if (!hasRepresentableReferenceLabel(node)) {
        warn(state, "Formatted link labels are not represented by DungeonBuddy reference nodes.", nodeStartLine(node));
        return sourceTextNodes(node, state);
      }
      return [{ type: "runbookReference", attrs: { ...attrs } }];
    }
  }
  if (url.startsWith("#dmb-")) {
    warn(
      state,
      node.title != null
        ? "Link titles are not represented by DungeonBuddy reference nodes."
        : `DungeonBuddy reference ${url} is not supported by the mounted editor schema.`,
      nodeStartLine(node),
    );
    return sourceTextNodes(node, state);
  }

  warn(state, "Ordinary Markdown links are not supported by the mounted editor schema.", nodeStartLine(node));
  return sourceTextNodes(node, state);
}

function visitInlineNode(node: PhrasingContent, state: VisitorState): TiptapNode[] {
  switch (node.type) {
    case "text": {
      const text = textNode(normalizeWrappedText(node.value));
      return text ? [text] : [];
    }
    case "inlineCode": {
      const text = textNode(normalizeWrappedText(node.value), [{ type: "code" }]);
      return text ? [text] : [];
    }
    case "emphasis":
      return withMark(visitInlineChildren(node.children, state), { type: "italic" });
    case "strong":
      return withMark(visitInlineChildren(node.children, state), { type: "bold" });
    case "delete":
      return withMark(visitInlineChildren(node.children, state), { type: "strike" });
    case "break": {
      warn(state, "Explicit Markdown hard breaks are not supported yet.", nodeStartLine(node));
      const text = textNode(" ");
      return text ? [text] : [];
    }
    case "link":
      return visitLink(node, state);
    case "linkReference": {
      warn(state, "Ordinary Markdown links are not supported by the mounted editor schema.", nodeStartLine(node));
      return sourceTextNodes(node, state);
    }
    case "image":
    case "imageReference": {
      warn(state, "Markdown images are not supported yet.", nodeStartLine(node));
      return sourceTextNodes(node, state);
    }
    case "html": {
      warn(state, "Raw HTML is not supported yet.", nodeStartLine(node));
      return sourceTextNodes(node, state);
    }
    default: {
      warn(state, `Unsupported Markdown inline node ${String(node.type)}.`, nodeStartLine(node));
      return sourceTextNodes(node, state);
    }
  }
}

function visitInlineChildren(nodes: PhrasingContent[], state: VisitorState): TiptapNode[] {
  return mergeAdjacentText(nodes.flatMap((node) => visitInlineNode(node, state)));
}

/** Parse an isolated inline fragment (a repaired table cell) with the same parser. */
function visitInlineFragment(text: string, state: VisitorState): TiptapNode[] {
  const fragment = parseMarkdownAst(text);
  const only = fragment.children[0];
  if (fragment.children.length !== 1 || only?.type !== "paragraph") {
    const node = textNode(text.trim());
    return node ? [node] : [];
  }
  return visitInlineChildren(only.children, state);
}

function visitParagraph(
  node: RootContent & { type: "paragraph" },
  context: AdmissionContext,
  state: VisitorState,
): TiptapNode {
  if (context !== "nested" && context !== "tableCell") {
    // Blunt indent guard carried over from the line grammar: any span line that
    // begins with a tab or 2+ spaces is source the serializer would normalize.
    spanLines(node, state).forEach((line, index) => {
      if (LEADING_INDENT_PATTERN.test(line)) {
        warn(
          state,
          "Indented Markdown blocks and list continuations are not supported yet.",
          nodeStartLine(node) + index,
        );
      }
    });
  }
  if (allowsSourceFormChecks(context)) {
    spanLines(node, state).forEach((line, index) => {
      if (TABLE_DELIMITER_ROW_PATTERN.test(line)) {
        warn(
          state,
          "This source looks like a GFM table but did not parse as one (check for unescaped pipes inside code spans); it cannot be imported safely.",
          nodeStartLine(node) + index,
        );
      }
    });
  }
  return { type: "paragraph", content: visitInlineChildren(node.children, state) };
}

function visitHeading(node: Heading, context: AdmissionContext, state: VisitorState): TiptapNode {
  if (context === "listItem" || context === "tableCell") {
    warn(state, "Headings nested inside list items or table cells are not supported yet.", nodeStartLine(node));
  }
  if (allowsSourceFormChecks(context)) {
    const firstLine = spanLines(node, state)[0] ?? "";
    if (!firstLine.startsWith("#")) {
      if (/^\s{1,3}#/.test(firstLine)) {
        warn(state, "Indented Markdown blocks and list continuations are not supported yet.", nodeStartLine(node));
      } else {
        // Setext heading: the parser established the heading; only its spelling is unsupported.
        warn(state, "Setext-style headings are not supported; use ATX # headings.", nodeEndLine(node));
      }
    }
  }
  return { type: "heading", attrs: { level: node.depth }, content: visitInlineChildren(node.children, state) };
}

function visitThematicBreak(node: ThematicBreak, context: AdmissionContext, state: VisitorState): TiptapNode[] {
  if (allowsSourceFormChecks(context)) {
    const firstLine = spanLines(node, state)[0] ?? "";
    if (/^---[ \t]*$/.test(firstLine)) {
      return [{ type: "horizontalRule" }];
    }
    if (/^\s+---[ \t]*$/.test(firstLine)) {
      warn(state, "Indented Markdown blocks and list continuations are not supported yet.", nodeStartLine(node));
      return [{ type: "horizontalRule" }];
    }
    // The parser established a thematic break; only canonical `---` is
    // admitted. Reinterpreting *** / ___ / - - - as literal prose would
    // silently change the source's meaning, so non-canonical spellings seal.
    warn(state, "Only --- thematic breaks are supported by this editor slice.", nodeStartLine(node));
    return [paragraphFromText(sourceSlice(node, state))];
  }
  if (context === "listItem" || context === "tableCell") {
    warn(state, "Thematic breaks nested inside list items or table cells are not supported yet.", nodeStartLine(node));
  }
  return [paragraphFromText(sourceSlice(node, state))];
}

type CalloutSegment = {
  marker: string;
  label: string;
  markerLine: number;
  bodyLines: string[];
  bodyStartLine: number;
};

/**
 * Classify a parser-established root blockquote as DungeonBuddy callout
 * segment(s). A marker line starts a new sibling segment (stacked sibling
 * callouts are existing clean behavior); content before any marker makes the
 * whole blockquote an unsupported plain quote.
 */
function splitCalloutSegments(node: Blockquote, state: VisitorState): CalloutSegment[] | null {
  const stripped = spanLines(node, state).map((line) => line.replace(/^\s{0,3}> ?/, ""));
  const segments: CalloutSegment[] = [];
  let current: CalloutSegment | null = null;
  let sawOrphanContent = false;
  stripped.forEach((line, index) => {
    const markerMatch = line.match(CALLOUT_MARKER_LINE_PATTERN);
    if (markerMatch) {
      current = {
        marker: markerMatch[1].trim(),
        label: (markerMatch[2] ?? "").trim(),
        markerLine: nodeStartLine(node) + index,
        bodyLines: [],
        bodyStartLine: nodeStartLine(node) + index + 1,
      };
      segments.push(current);
      return;
    }
    if (current) {
      current.bodyLines.push(line);
    } else if (line.trim() !== "") {
      sawOrphanContent = true;
    }
  });
  return sawOrphanContent ? null : segments;
}

/** Marker classification for a nested blockquote, read from its parsed first paragraph. */
function leadingCalloutMarker(node: Blockquote): string | null {
  const first = node.children?.[0];
  if (first?.type !== "paragraph") return null;
  const firstChild = first.children?.[0];
  if (firstChild?.type !== "text") return null;
  const match = firstChild.value.match(/^\s{0,3}\[!([^\]]+)\]/);
  return match?.[1] ?? null;
}

function visitCalloutSegment(segment: CalloutSegment, state: VisitorState): TiptapNode {
  const kind = SUPPORTED_CALLOUT_MARKERS.has(segment.marker.toUpperCase())
    ? normalizeCalloutKind(segment.marker)
    : null;
  if (kind === null) {
    warn(state, `Callout marker ${segment.marker} is not supported by this editor slice.`, segment.markerLine);
    // Handoff §13: never normalize an unknown marker into a WARNING callout.
    return paragraphFromText(
      [`[!${segment.marker}]${segment.label ? ` ${segment.label}` : ""}`, ...segment.bodyLines].join("\n"),
    );
  }

  // The callout body is re-parsed from its dedented source lines so nested
  // blocks (tables, lists, headings) get real structure and source-form
  // checks see prefix-free lines. Diagnostic lines shift by the body offset.
  const bodyText = segment.bodyLines.join("\n");
  const bodyState: VisitorState = {
    lines: bodyText.split("\n"),
    lineOffset: state.lineOffset + segment.bodyStartLine - 1,
    options: state.options,
    diagnostics: state.diagnostics,
  };
  const content = visitBlockChildren(parseMarkdownAst(bodyText).children, "callout", bodyState);
  return {
    type: "callout",
    attrs: { kind, ...(segment.label ? { label: segment.label } : {}) },
    content: content.length > 0 ? content : [{ type: "paragraph", content: [] }],
  };
}

function visitBlockquote(node: Blockquote, context: AdmissionContext, state: VisitorState): TiptapNode[] {
  if (context === "document") {
    if ((node.position?.start.column ?? 1) !== 1) {
      warn(state, "Indented or list-nested blockquotes/callouts are not supported yet.", nodeStartLine(node));
    }
    const segments = splitCalloutSegments(node, state);
    if (segments === null || segments.length === 0) {
      warn(state, "Plain blockquotes are not supported yet.", nodeStartLine(node));
      const stripped = spanLines(node, state).map((line) => line.replace(/^\s{0,3}> ?/, ""));
      return [paragraphFromText(stripped.join("\n"))];
    }
    return segments.map((segment) => visitCalloutSegment(segment, state));
  }

  // Nested container: the parser already owns the dedented structure, and its
  // source lines carry container prefixes. Diagnose by parsed shape, then
  // project the parsed children for sealed viewing.
  const marker = leadingCalloutMarker(node);
  if (context === "callout" || context === "nested") {
    warn(state, "Nested callouts are not supported yet.", nodeStartLine(node));
  } else {
    warn(
      state,
      marker !== null
        ? "Callouts nested in list items are not supported yet."
        : "Plain blockquotes are not supported yet.",
      nodeStartLine(node),
    );
  }
  const content = visitBlockChildren(node.children ?? [], "nested", state);
  return content.length > 0 ? content : [{ type: "paragraph", content: [] }];
}

function visitListItem(item: ListItem, list: List, context: AdmissionContext, state: VisitorState): TiptapNode {
  if (context !== "nested" && context !== "tableCell" && !list.ordered) {
    // Bullet-marker spelling: the parser established the list; only `-` is canonical.
    const marker = (state.lines[nodeStartLine(item) - 1] ?? "").trimStart().charAt(0);
    if (marker !== "-") {
      warn(state, "Only hyphen bullet markers are supported by this editor slice.", nodeStartLine(item));
    }
  }
  if (item.checked !== null && item.checked !== undefined) {
    warn(state, "Task-list items are not supported yet.", nodeStartLine(item));
  }
  const content: unknown[] = [];
  for (const child of item.children ?? []) {
    if (child.type === "list") {
      warn(state, "Nested lists are not supported yet.", nodeStartLine(child));
    }
    content.push(...visitBlockNode(child, "listItem", state));
  }
  if (content.length === 0) {
    content.push({ type: "paragraph", content: [] });
  }
  return { type: "listItem", content };
}

function visitList(node: List, context: AdmissionContext, state: VisitorState): TiptapNode[] {
  // A list nested inside a list item is diagnosed by the owning visitListItem.
  if (context === "document" && (node.position?.start.column ?? 1) !== 1) {
    warn(state, "Indented Markdown blocks and list continuations are not supported yet.", nodeStartLine(node));
  }
  const items = (node.children ?? []).map((item) => visitListItem(item, node, context, state));
  return [{
    type: node.ordered ? "orderedList" : "bulletList",
    ...(node.ordered ? { attrs: { start: node.start ?? 1 } } : {}),
    content: items,
  }];
}

/**
 * Split a table row source line on unescaped pipes outside code spans.
 * GFM requires escaped pipes even inside code spans; DungeonBuddy's admitted
 * subset (pre-rescue executable behavior) also allows raw pipes inside code
 * spans, so rows that mdast over-split get one source-form repair attempt.
 */
function splitTableRowSourcePreservingCodeSpans(line: string): string[] {
  const trimmed = line.trim().replace(/^\|/, "").replace(/\|\s*$/, "");
  const cells: string[] = [];
  let current = "";
  let openTicks = 0;
  let index = 0;
  while (index < trimmed.length) {
    const char = trimmed[index];
    if (char === "\\" && index + 1 < trimmed.length) {
      current += char + trimmed[index + 1];
      index += 2;
      continue;
    }
    if (char === "`") {
      let run = 0;
      while (trimmed[index + run] === "`") run += 1;
      if (openTicks === 0) openTicks = run;
      else if (run === openTicks) openTicks = 0;
      current += "`".repeat(run);
      index += run;
      continue;
    }
    if (char === "|" && openTicks === 0) {
      cells.push(current.trim());
      current = "";
      index += 1;
      continue;
    }
    current += char;
    index += 1;
  }
  cells.push(current.trim());
  return cells;
}

/**
 * Repair a row whose mdast cell count disagrees with the header because GFM
 * split a pipe inside a code span. Returns per-cell inline projections when
 * the code-span-aware source split matches the header width exactly;
 * otherwise null so the caller emits the uneven-row diagnostic.
 */
function repairUnevenTableRow(row: TableRow, width: number, state: VisitorState): TiptapNode[][] | null {
  const line = spanLines(row, state)[0] ?? "";
  const rawCells = splitTableRowSourcePreservingCodeSpans(line);
  if (rawCells.length !== width) return null;
  return rawCells.map((cellText) => {
    const cellState: VisitorState = {
      ...state,
      lines: [cellText],
      lineOffset: state.lineOffset + nodeStartLine(row) - 1,
    };
    return visitInlineFragment(cellText, cellState);
  });
}

function visitTableRow(
  row: TableRow,
  width: number,
  cellType: "tableHeader" | "tableCell",
  state: VisitorState,
  repairedCells?: TiptapNode[][],
): TiptapNode {
  const cells = row.children ?? [];
  return {
    type: "tableRow",
    content: Array.from({ length: Math.max(1, width) }, (_, index) => ({
      type: cellType,
      content: [{
        type: "paragraph",
        content: repairedCells?.[index] ?? (cells[index] ? visitInlineChildren(cells[index].children, state) : []),
      }],
    })),
  };
}

function visitTable(node: Table, context: AdmissionContext, state: VisitorState): TiptapNode[] {
  if (context === "listItem" || context === "tableCell" || context === "nested") {
    warn(state, "Tables nested inside list items or table cells are not supported yet.", nodeStartLine(node));
  }
  if (context === "document" && (node.position?.start.column ?? 1) !== 1) {
    warn(state, "Indented Markdown blocks and list continuations are not supported yet.", nodeStartLine(node));
  }
  const rows = node.children ?? [];
  const header = rows[0];
  const width = header?.children.length ?? 1;
  if ((node.align ?? []).some((align) => align != null)) {
    // The delimiter row is not an AST node; it is the source line after the header row.
    warn(
      state,
      "GFM table alignment markers are not represented by the current editor table model.",
      (header ? nodeEndLine(header) : nodeStartLine(node)) + 1,
    );
  }
  const repairedRows = new Map<number, TiptapNode[][]>();
  rows.slice(1).forEach((row, index) => {
    if ((row.children ?? []).length === width) return;
    const repaired = repairUnevenTableRow(row, width, state);
    if (repaired) {
      repairedRows.set(index + 1, repaired);
    } else {
      warn(
        state,
        "GFM table rows must have the same number of cells as the header for safe editing.",
        nodeStartLine(row),
      );
    }
  });
  if (!header) return [{ type: "paragraph", content: [] }];
  return [{
    type: "table",
    content: [
      visitTableRow(header, width, "tableHeader", state),
      ...rows.slice(1).map((row, index) => visitTableRow(row, width, "tableCell", state, repairedRows.get(index + 1))),
    ],
  }];
}

function visitBlockNode(node: RootContent, context: AdmissionContext, state: VisitorState): TiptapNode[] {
  switch (node.type) {
    case "paragraph":
      return [visitParagraph(node, context, state)];
    case "heading":
      return [visitHeading(node, context, state)];
    case "thematicBreak":
      return visitThematicBreak(node, context, state);
    case "list":
      return visitList(node, context, state);
    case "blockquote":
      return visitBlockquote(node, context, state);
    case "table":
      return visitTable(node, context, state);
    case "code": {
      const firstLine = spanLines(node, state)[0] ?? "";
      const fenced = node.lang != null || /`{3,}|~{3,}/.test(firstLine);
      warn(
        state,
        fenced
          ? "Fenced code blocks are not supported yet."
          : "Indented Markdown blocks and list continuations are not supported yet.",
        nodeStartLine(node),
      );
      return [paragraphFromText(node.value)];
    }
    case "html": {
      warn(state, "Raw HTML blocks are not supported yet.", nodeStartLine(node));
      return [paragraphFromText(sourceSlice(node, state))];
    }
    case "definition": {
      // Every spelling — zero-space, split destination, escaped label — arrives
      // here as a parsed node. No DungeonBuddy regex recognizes definitions.
      warn(state, "Reference-style link definitions are not supported yet.", nodeStartLine(node));
      return [paragraphFromText(sourceSlice(node, state))];
    }
    default: {
      warn(state, `Unsupported Markdown block node ${String(node.type)}.`, nodeStartLine(node));
      return [paragraphFromText(sourceSlice(node, state))];
    }
  }
}

function visitBlockChildren(
  nodes: RootContent[],
  context: AdmissionContext,
  state: VisitorState,
): TiptapNode[] {
  return nodes.flatMap((node) => visitBlockNode(node, context, state));
}

function dedupeDiagnostics(diagnostics: MarkdownImportDiagnostic[]): MarkdownImportDiagnostic[] {
  const seen = new Set<string>();
  return diagnostics.filter((diagnostic) => {
    const key = `${diagnostic.line ?? 0} ${diagnostic.message}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

export type MarkdownAdmissionResult = {
  content: TiptapNode[];
  diagnostics: MarkdownImportDiagnostic[];
};

/**
 * Parse a frontmatter-free, newline-normalized Markdown body with the single
 * structural parser, then admit + project it into TipTap content. `lineOffset`
 * shifts diagnostic line numbers back into original-document coordinates when
 * leading frontmatter was stripped upstream (handoff §7).
 */
export function analyzeMarkdownBody(
  markdownBody: string,
  options: MarkdownImportOptions = {},
  lineOffset = 0,
): MarkdownAdmissionResult {
  const state: VisitorState = {
    lines: markdownBody.split("\n"),
    lineOffset,
    options,
    diagnostics: [],
  };
  const content = visitBlockChildren(parseMarkdownAst(markdownBody).children, "document", state);
  return { content, diagnostics: dedupeDiagnostics(state.diagnostics) };
}
