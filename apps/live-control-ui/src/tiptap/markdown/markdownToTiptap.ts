import { normalizeCalloutKind } from "./calloutMarkdown";
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
  doc: {
    type: "doc";
    content: unknown[];
  };
  diagnostics: MarkdownImportDiagnostic[];
};

type TiptapNode = {
  type: string;
  attrs?: Record<string, unknown>;
  content?: unknown[];
  text?: string;
};

const typedReferencePattern = /\[([^\]]+)\]\(#dmb-(ref|action):([a-z][a-z0-9-]*):([a-z0-9][a-z0-9_-]*)\)/g;
const headingPattern = /^(#{1,3})\s+(.+)$/;
const bulletListPattern = /^-\s+(.+)$/;
const orderedListPattern = /^(\d+)[.)]\s+(.+)$/;
const calloutMarkerPattern = /^>\s*\[!([^\]]+)\]\s*(.*)$/;

function textNode(text: string): TiptapNode | null {
  return text ? { type: "text", text } : null;
}

function parseInlineContent(text: string): unknown[] {
  const content: unknown[] = [];
  let lastIndex = 0;

  for (const match of text.matchAll(typedReferencePattern)) {
    const index = match.index ?? 0;
    const leading = textNode(text.slice(lastIndex, index));
    if (leading) content.push(leading);

    const [, label, kind, refType, refId] = match;
    const attrs: RunbookReferenceAttrs = normalizeRunbookReferenceAttrs({ kind, refType, refId, label } as RunbookReferenceAttrs);
    if (isSupportedRunbookReference(attrs)) {
      content.push({ type: "runbookReference", attrs });
    } else {
      content.push({ type: "text", text: match[0] });
    }
    lastIndex = index + match[0].length;
  }

  const trailing = textNode(text.slice(lastIndex));
  if (trailing) content.push(trailing);
  return content;
}

function paragraph(text: string): TiptapNode {
  return { type: "paragraph", content: parseInlineContent(text) };
}

function listItem(text: string): TiptapNode {
  return { type: "listItem", content: [paragraph(text)] };
}

function isBlank(line: string): boolean {
  return line.trim() === "";
}

function isBlockStart(line: string): boolean {
  return headingPattern.test(line)
    || calloutMarkerPattern.test(line)
    || bulletListPattern.test(line)
    || orderedListPattern.test(line);
}

function parseCalloutBody(lines: string[]): unknown[] {
  const content: unknown[] = [];
  let index = 0;

  while (index < lines.length) {
    if (isBlank(lines[index])) {
      index += 1;
      continue;
    }

    const bullet = lines[index].match(bulletListPattern);
    if (bullet) {
      const items: unknown[] = [];
      while (index < lines.length) {
        const item = lines[index].match(bulletListPattern);
        if (!item) break;
        items.push(listItem(item[1]));
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
        items.push(listItem(item[2]));
        index += 1;
      }
      content.push({ type: "orderedList", attrs: { start }, content: items });
      continue;
    }

    const paragraphLines: string[] = [];
    while (index < lines.length && !isBlank(lines[index]) && !bulletListPattern.test(lines[index]) && !orderedListPattern.test(lines[index])) {
      paragraphLines.push(lines[index]);
      index += 1;
    }
    content.push(paragraph(paragraphLines.join(" ").trim()));
  }

  return content.length > 0 ? content : [paragraph("")];
}

export function markdownToTiptapDoc(markdown: string): MarkdownImportResult {
  const lines = markdown.replace(/\r\n?/g, "\n").split("\n");
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
      content.push({ type: "heading", attrs: { level: heading[1].length }, content: parseInlineContent(heading[2].trim()) });
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
      content.push({
        type: "callout",
        attrs: { kind: normalizeCalloutKind(marker), ...(rawLabel.trim() ? { label: rawLabel.trim() } : {}) },
        content: parseCalloutBody(bodyLines),
      });
      continue;
    }

    const bullet = line.match(bulletListPattern);
    if (bullet) {
      const items: unknown[] = [];
      while (index < lines.length) {
        const item = lines[index].match(bulletListPattern);
        if (!item) break;
        items.push(listItem(item[1]));
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
        items.push(listItem(item[2]));
        index += 1;
      }
      content.push({ type: "orderedList", attrs: { start }, content: items });
      continue;
    }

    if (/^\s*</.test(line) || /^\s*\|/.test(line) || /^\s*!\[/.test(line) || /^---\s*$/.test(line)) {
      diagnostics.push({ level: "warning", message: "Unsupported Markdown block imported as paragraph.", line: lineNumber });
    }

    const paragraphLines: string[] = [];
    while (index < lines.length && !isBlank(lines[index]) && !isBlockStart(lines[index])) {
      paragraphLines.push(lines[index].trim());
      index += 1;
    }
    content.push(paragraph(paragraphLines.join(" ").trim()));
  }

  return { doc: { type: "doc", content }, diagnostics };
}
