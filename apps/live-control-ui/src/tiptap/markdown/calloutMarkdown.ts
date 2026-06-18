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
  text?: unknown;
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

function inlineText(node: JsonNode): string {
  if (node.type === "text") return typeof node.text === "string" ? node.text : "";
  if (node.type === "hardBreak") return "\n";
  return childNodes(node).map(inlineText).join("");
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

function serializeCallout(node: JsonNode): string {
  const kind = normalizeCalloutKind(node.attrs?.kind);
  const label = typeof node.attrs?.label === "string" ? node.attrs.label.trim() : "";
  const marker = `> [!${calloutKindToMarkdownMarker(kind)}]${label ? ` ${label}` : ""}`;
  const body = childNodes(node).map(serializeNode).filter(Boolean).join("\n\n");
  return body ? `${marker}\n${indentLines(body, "> ")}` : marker;
}

function serializeNode(node: JsonNode): string {
  switch (node.type) {
    case "doc":
      return childNodes(node).map(serializeNode).filter(Boolean).join("\n\n");
    case "text":
      return typeof node.text === "string" ? node.text : "";
    case "hardBreak":
      return "\n";
    case "paragraph":
      return childNodes(node).map(inlineText).join("");
    case "heading": {
      const requestedLevel = Number(node.attrs?.level);
      const level = Number.isInteger(requestedLevel) ? Math.min(6, Math.max(1, requestedLevel)) : 2;
      return `${"#".repeat(level)} ${childNodes(node).map(inlineText).join("")}`;
    }
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
    case "callout":
      return serializeCallout(node);
    default: {
      const text = inlineText(node);
      return text || `[Unsupported ${typeof node.type === "string" ? node.type : "node"}]`;
    }
  }
}

export function tiptapJsonToSemanticMarkdown(doc: unknown): string {
  const node = asNode(doc);
  if (!node) return "";
  return `${serializeNode(node).trim()}\n`;
}
