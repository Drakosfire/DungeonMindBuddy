import {
  normalizeRunbookReferenceAttrs,
  runbookReferenceHref,
} from "../references/runbookReferences";

export const CALLOUT_KINDS = ["read-aloud", "gm-note", "rules", "warning"] as const;

export type CalloutKind = (typeof CALLOUT_KINDS)[number];

export interface CalloutAttrs {
  kind: CalloutKind;
  label?: string | null;
}

type JsonNode = {
  type?: unknown;
  attrs?: Record<string, unknown> | null;
  content?: unknown;
  marks?: unknown;
  text?: unknown;
};

type JsonMark = {
  type?: unknown;
  attrs?: Record<string, unknown> | null;
};

const KIND_ALIASES: Record<string, CalloutKind> = {
  "read-aloud": "read-aloud",
  "read-aloud-text": "read-aloud",
  readaloud: "read-aloud",
  read: "read-aloud",
  "gm-note": "gm-note",
  gmnote: "gm-note",
  gm: "gm-note",
  dm: "gm-note",
  "dm-note": "gm-note",
  rules: "rules",
  "rules-note": "rules",
  rule: "rules",
  warning: "warning",
  warn: "warning",
  danger: "warning",
  caution: "warning",
};

export function normalizeCalloutKind(input: unknown): CalloutKind {
  if (typeof input !== "string") return "warning";
  const key = input.trim().toLowerCase().replace(/[\s_]+/g, "-");
  return KIND_ALIASES[key] ?? "warning";
}

export function defaultCalloutLabel(kind: CalloutKind): string {
  return {
    "read-aloud": "Read aloud",
    "gm-note": "GM note",
    rules: "Rules",
    warning: "Warning",
  }[kind];
}

export function calloutKindToMarkdownMarker(kind: CalloutKind): string {
  return kind.toUpperCase();
}

function asNode(value: unknown): JsonNode | null {
  return value !== null && typeof value === "object" ? (value as JsonNode) : null;
}

function childNodes(node: JsonNode): JsonNode[] {
  if (!Array.isArray(node.content)) return [];
  return node.content.map(asNode).filter((child): child is JsonNode => child !== null);
}

function markdownMarks(value: unknown): JsonMark[] {
  if (!Array.isArray(value)) return [];
  return value.map(asNode).filter((mark): mark is JsonMark => mark !== null);
}

function escapeMarkdownLineStart(line: string): string {
  return line
    .replace(/^(\s{0,3})(#{1,6})(\s|$)/, "$1\\$2$3")
    .replace(/^(\s{0,3})(>)/, "$1\\$2")
    .replace(/^(\s{0,3})(-{3,})(\s*)$/, "$1\\$2$3")
    .replace(/^(\s{0,3})(=+)(\s*)$/, "$1\\$2$3")
    .replace(/^(\s{0,3})([-+=])(\s|$)/, "$1\\$2$3")
    .replace(/^(\s{0,3})(\d+)([.)])(\s|$)/, "$1$2\\$3$4");
}

function escapeMarkdownText(text: string): string {
  return text
    .replace(/[\\`*[\]()]/g, "\\$&")
    .split("\n")
    .map(escapeMarkdownLineStart)
    .join("\n");
}

function normalizeSingleLineText(value: string): string {
  return value.replace(/\s+/g, " ").trim();
}

function calloutLabel(value: unknown): string {
  if (typeof value !== "string") return "";
  return escapeMarkdownText(normalizeSingleLineText(value)).replace(/>/g, "\\>");
}

function codeSpan(text: string): string {
  const longestBacktickRun = Math.max(0, ...Array.from(text.matchAll(/`+/g), (match) => match[0].length));
  const delimiter = "`".repeat(longestBacktickRun + 1);
  const padding = text.startsWith("`") || text.endsWith("`") ? " " : "";
  return `${delimiter}${padding}${text}${padding}${delimiter}`;
}

function escapeMarkdownHref(href: string): string {
  return href.replace(/ /g, "%20").replace(/[()]/g, "\\$&");
}

function safeMarkdownHref(value: unknown): string | null {
  if (typeof value !== "string") return null;

  const href = value.trim();
  if (!href || /[\u0000-\u001F\u007F]/.test(href) || href.startsWith("//")) return null;

  const schemeMatch = href.match(/^([a-z][a-z0-9+.-]*):/i);
  if (schemeMatch && !["http", "https", "mailto"].includes(schemeMatch[1].toLowerCase())) {
    return null;
  }

  return escapeMarkdownHref(href);
}

function serializeTextWithMarks(text: string, marks: JsonMark[]): string {
  const markTypes = new Set(marks.map((mark) => mark.type).filter((type): type is string => typeof type === "string"));
  let result = markTypes.has("code") ? codeSpan(text) : escapeMarkdownText(text);

  if (!markTypes.has("code")) {
    if (markTypes.has("bold")) result = `**${result}**`;
    if (markTypes.has("italic")) result = `*${result}*`;
    if (markTypes.has("strike")) result = `~~${result}~~`;
  }

  const link = marks.find((mark) => mark.type === "link");
  const href = safeMarkdownHref(link?.attrs?.href);
  return href ? `[${result}](${href})` : result;
}

function inlineMarkdown(node: JsonNode): string {
  if (node.type === "text") {
    return serializeTextWithMarks(
      typeof node.text === "string" ? node.text : "",
      markdownMarks(node.marks),
    );
  }
  if (node.type === "hardBreak") return "\n";
  if (node.type === "runbookReference") {
    const attrs = normalizeRunbookReferenceAttrs(node.attrs ?? {});
    const label = escapeMarkdownText(attrs.label);
    const hasKnownKind = node.attrs?.kind === "ref" || node.attrs?.kind === "action";
    const href = hasKnownKind ? runbookReferenceHref(attrs) : null;
    return href ? `[${label}](${href})` : label;
  }
  if (node.type === "graphNodeReference") {
    const nodeId = typeof node.attrs?.nodeId === "string" ? node.attrs.nodeId : "";
    const label = escapeMarkdownText(
      typeof node.attrs?.label === "string" && node.attrs.label.trim()
        ? node.attrs.label
        : nodeId,
    );
    return nodeId ? `[${label}](dmb-node:${nodeId})` : label;
  }
  return childNodes(node).map(inlineMarkdown).join("");
}

function indentLines(value: string, prefix: string): string {
  return value
    .split("\n")
    .map((line) => `${prefix}${line}`)
    .join("\n");
}

function serializeListItem(node: JsonNode, marker: string): string {
  const parts = childNodes(node).map(serializeNode).filter(Boolean);
  if (parts.length === 0) return marker.trimEnd();
  const [first, ...rest] = parts;
  const continuation = rest.length > 0 ? `\n${indentLines(rest.join("\n"), "  ")}` : "";
  return `${marker}${first}${continuation}`;
}

function serializeTableCell(node: JsonNode): string {
  const text = childNodes(node)
    .map((child) => serializeNode(child))
    .filter(Boolean)
    .join(" ")
    .replace(/\s*\n\s*/g, " ")
    .trim();
  return text.replace(/\|/g, "\\|");
}

function serializeTable(node: JsonNode): string {
  const rows = childNodes(node);
  if (rows.length === 0) return "";

  const width = Math.max(1, ...rows.map((row) => childNodes(row).length));
  const serializedRows = rows.map((row) => {
    const cells = childNodes(row).map(serializeTableCell);
    while (cells.length < width) cells.push("");
    return `| ${cells.join(" | ")} |`;
  });
  const separator = `| ${Array.from({ length: width }, () => "---").join(" | ")} |`;
  return [serializedRows[0], separator, ...serializedRows.slice(1)].join("\n");
}

function serializeCallout(node: JsonNode): string {
  const kind = normalizeCalloutKind(node.attrs?.kind);
  const label = calloutLabel(node.attrs?.label);
  const marker = `> [!${calloutKindToMarkdownMarker(kind)}]${label ? ` ${label}` : ""}`;
  const body = childNodes(node).map(serializeNode).filter(Boolean).join("\n\n");
  return body ? `${marker}\n${indentLines(body, "> ")}` : marker;
}

function serializeNode(node: JsonNode): string {
  switch (node.type) {
    case "doc":
      return childNodes(node).map(serializeNode).filter(Boolean).join("\n\n");
    case "text":
      return inlineMarkdown(node);
    case "hardBreak":
      return "\n";
    case "runbookReference":
    case "graphNodeReference":
      return inlineMarkdown(node);
    case "paragraph":
      return childNodes(node).map(inlineMarkdown).join("");
    case "heading": {
      const requestedLevel = Number(node.attrs?.level);
      const level = Number.isInteger(requestedLevel) ? Math.min(6, Math.max(1, requestedLevel)) : 2;
      return `${"#".repeat(level)} ${childNodes(node).map(inlineMarkdown).join("")}`;
    }
    case "horizontalRule":
      return "---";
    case "bulletList":
      return childNodes(node).map((child) => serializeListItem(child, "- ")).join("\n");
    case "orderedList": {
      const start = Number(node.attrs?.start);
      const first = Number.isInteger(start) ? start : 1;
      return childNodes(node)
        .map((child, index) => serializeListItem(child, `${first + index}. `))
        .join("\n");
    }
    case "listItem":
      return childNodes(node).map(serializeNode).filter(Boolean).join("\n");
    case "table":
      return serializeTable(node);
    case "tableRow":
    case "tableHeader":
    case "tableCell":
      return childNodes(node).map(serializeNode).filter(Boolean).join(" ");
    case "callout":
      return serializeCallout(node);
    default: {
      const text = inlineMarkdown(node);
      return text || `[Unsupported ${typeof node.type === "string" ? node.type : "node"}]`;
    }
  }
}

export function tiptapJsonToSemanticMarkdown(doc: unknown): string {
  const node = asNode(doc);
  if (!node) return "";
  return `${serializeNode(node).trim()}\n`;
}
