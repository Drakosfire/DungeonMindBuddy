import { useMemo, type MouseEvent } from "react";
import { generateHTML, mergeAttributes, type JSONContent } from "@tiptap/core";
import { DEFAULT_MARKDOWN_EDITOR_EXTENSIONS } from "../tiptap/MarkdownEditorCore";
import { GraphNodeReferenceNode } from "../tiptap/extensions/GraphNodeReferenceNode";
import { classifyImageUrl, classifyLinkUrl } from "./markdownReaderUrlPolicy";

function graphNodeReferenceExtension(activatable: boolean) {
  return GraphNodeReferenceNode.extend({
    renderHTML({ node, HTMLAttributes }) {
      const attrs = node.attrs as { nodeId?: unknown; label?: unknown };
      const nodeId = typeof attrs.nodeId === "string" ? attrs.nodeId : "";
      const label = typeof attrs.label === "string" ? attrs.label : "";
      return [
        activatable ? "button" : "span",
        mergeAttributes(HTMLAttributes, {
          class: "graph-node-reference-pill recap-node-token",
          "data-graph-node-id": nodeId,
          "data-plan-card-reference": "graph",
          ...(activatable ? { type: "button", "data-graph-node-activation": "enabled" } : {}),
          contenteditable: "false",
        }),
        label,
      ];
    },
  });
}

function readOnlyBodyExtensions(activatable: boolean) {
  const graphReferenceExtension = graphNodeReferenceExtension(activatable);
  return DEFAULT_MARKDOWN_EDITOR_EXTENSIONS.map((extension) => (
    extension.name === GraphNodeReferenceNode.name ? graphReferenceExtension : extension
  ));
}

const READ_ONLY_BODY_EXTENSIONS = readOnlyBodyExtensions(false);
const ACTIVATABLE_READ_ONLY_BODY_EXTENSIONS = readOnlyBodyExtensions(true);
const SUPPORTED_BODY_MARKS = new Set(["bold", "italic", "strike", "code", "link"]);

function unsupportedBodyContentReason(content: readonly JSONContent[]): string | null {
  const inspect = (node: unknown): string | null => {
    if (node == null || typeof node !== "object" || Array.isArray(node)) return "malformed content";
    const record = node as { type?: unknown; attrs?: unknown; marks?: unknown; content?: unknown };
    if (typeof record.type !== "string" || record.type.length === 0) return "missing node type";
    const attrs = record.attrs == null
      ? {}
      : typeof record.attrs === "object" && !Array.isArray(record.attrs)
        ? record.attrs as Record<string, unknown>
        : null;
    if (attrs == null) return "malformed node attributes";

    if (["image", "video", "audio", "iframe", "embed"].includes(record.type)) {
      const src = typeof attrs.src === "string" ? attrs.src : "";
      return classifyImageUrl(src) === "unsafe"
        ? "unsafe embedded media"
        : "embedded media is not supported in read-only content";
    }
    if ("src" in attrs || "href" in attrs) return "unsupported URL-bearing node";

    if (record.type === "graphNodeReference") {
      if (typeof attrs.nodeId !== "string" || attrs.nodeId.length === 0
        || typeof attrs.label !== "string" || attrs.label.length === 0) {
        return "malformed Graph reference";
      }
    }
    if (record.type === "runbookReference") {
      if ((attrs.kind !== undefined && attrs.kind !== "ref" && attrs.kind !== "action")
        || typeof attrs.refType !== "string" || attrs.refType.length === 0
        || typeof attrs.refId !== "string" || attrs.refId.length === 0
        || typeof attrs.label !== "string" || attrs.label.length === 0) {
        return "malformed Runbook reference";
      }
    }

    if (record.marks !== undefined && !Array.isArray(record.marks)) return "malformed marks";
    if (Array.isArray(record.marks)) {
      for (const mark of record.marks) {
        if (mark == null || typeof mark !== "object" || Array.isArray(mark)) return "malformed mark";
        const markRecord = mark as { type?: unknown; attrs?: unknown };
        const markAttrs = markRecord.attrs == null
          ? {}
          : typeof markRecord.attrs === "object" && !Array.isArray(markRecord.attrs)
            ? markRecord.attrs as Record<string, unknown>
            : null;
        if (typeof markRecord.type !== "string" || markAttrs == null) return "malformed mark";
        if (!SUPPORTED_BODY_MARKS.has(markRecord.type)) return "unsupported authored mark";
        if (markRecord.type === "link") {
          if (typeof markAttrs.href !== "string") return "malformed link";
          const linkKind = classifyLinkUrl(markAttrs.href);
          if (linkKind === "unsafe" || linkKind === "relative_visible") {
            return "link destination is not safe to navigate from read-only content";
          }
        } else if ("href" in markAttrs || "src" in markAttrs) {
          return "unsupported URL-bearing mark";
        }
      }
    }

    if (record.content !== undefined && !Array.isArray(record.content)) return "malformed child content";
    if (Array.isArray(record.content)) {
      for (const child of record.content) {
        const reason = inspect(child);
        if (reason) return reason;
      }
    }
    return null;
  };

  for (const node of content) {
    const reason = inspect(node);
    if (reason) return reason;
  }
  return null;
}

export function ReadOnlyBodyContent({
  content,
  fallbackText,
  className,
  unsupportedMessage,
  testId,
  onActivateGraphNode,
}: {
  content?: readonly JSONContent[];
  fallbackText?: string;
  className?: string;
  unsupportedMessage?: string;
  testId?: string;
  /** Opt-in only; callers without a World-scoped handler retain inert reference spans. */
  onActivateGraphNode?: (nodeId: string, trigger?: HTMLElement) => void;
}) {
  const activatable = typeof onActivateGraphNode === "function";
  const contentKey = useMemo(() => JSON.stringify(content), [content]);
  const html = useMemo(() => {
    if (!content?.length) return null;
    if (unsupportedBodyContentReason(content)) return "";
    try {
      return generateHTML(
        { type: "doc", content: [...content] },
        activatable ? ACTIVATABLE_READ_ONLY_BODY_EXTENSIONS : READ_ONLY_BODY_EXTENSIONS,
      );
    } catch {
      return "";
    }
  }, [activatable, contentKey]);

  const handleClick = (event: MouseEvent<HTMLDivElement>) => {
    if (!onActivateGraphNode || !(event.target instanceof Element)) return;
    const reference = event.target.closest<HTMLButtonElement>(
      'button[data-plan-card-reference="graph"][data-graph-node-activation="enabled"]',
    );
    if (!reference || !event.currentTarget.contains(reference)) return;
    const nodeId = reference.dataset.graphNodeId;
    if (nodeId) onActivateGraphNode(nodeId, reference);
  };

  if (html === null && content !== undefined && fallbackText) {
    return (
      <p className={`${className ?? ""} read-only-body-content__unavailable`.trim()} role="status" data-testid={testId}>
        The captured authored structure is empty, so its flattened text is not shown here.
      </p>
    );
  }
  if (html === "") {
    return (
      <p className={`${className ?? ""} read-only-body-content__unavailable`.trim()} role="status" data-testid={testId}>
        {unsupportedMessage ?? "This authored content includes a format that cannot be displayed safely here."}
      </p>
    );
  }
  if (html) return (
    <div
      className={className}
      data-testid={testId}
      onClick={activatable ? handleClick : undefined}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
  if (fallbackText) return <p className={className} data-testid={testId}>{fallbackText}</p>;
  return null;
}
