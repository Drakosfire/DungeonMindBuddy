import {PreparedTableNode} from "../preparedTables/PreparedTableNode";
import {parseTableFence} from "../preparedTables/tableGrammar";
import { useLayoutEffect, useMemo, useRef, useState, type MouseEvent } from "react";
import { createPortal } from "react-dom";
import { SavedMediaImage } from "../media/SavedMediaImage";
import { imagePresentation, MEDIA_ASSET_ID } from "../media/mediaReferences";
import { generateHTML, mergeAttributes, Node, type AnyExtension, type JSONContent } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import { CalloutNode } from "../tiptap/extensions/CalloutNode";
import { DECISION_CONSEQUENCE_EXTENSIONS } from "../tiptap/extensions/DecisionConsequenceNode";
import { PLAN_TABLE_EXTENSIONS } from "../tiptap/extensions/planTableExtensions";
import { PlayableElementHeadingAttributes } from "../tiptap/extensions/PlayableElementHeadingAttributes";
import { WebSourceLink } from "../tiptap/extensions/WebSourceLink";
import { isSupportedRunbookReference, normalizeRunbookReferenceAttrs, runbookReferenceClasses } from "../tiptap/references/runbookReferences";
import { classifyImageUrl, classifyLinkUrl } from "./markdownReaderUrlPolicy";

function graphNodeReferenceExtension(activatable: boolean): AnyExtension {
  return Node.create({
    name: "graphNodeReference", group: "inline", inline: true, atom: true, selectable: true,
    addAttributes: () => ({ nodeId: { default: "", rendered: false }, label: { default: "", rendered: false } }),
    parseHTML: () => [{
      tag: "button[data-graph-node-id]",
      getAttrs: element => {
        if (!(element instanceof HTMLElement)) return false;
        const nodeId = element.dataset.graphNodeId;
        return nodeId ? { nodeId, label: element.textContent?.trim() || nodeId } : false;
      },
    }],
    renderHTML({ node, HTMLAttributes }) {
      const nodeId = typeof node.attrs.nodeId === "string" ? node.attrs.nodeId : "";
      const label = typeof node.attrs.label === "string" ? node.attrs.label : "";
      return [activatable ? "button" : "span", mergeAttributes(HTMLAttributes, {
        class: "graph-node-reference-pill recap-node-token",
        "data-graph-node-id": nodeId,
        "data-plan-card-reference": "graph",
        ...(activatable ? { type: "button", "data-graph-node-activation": "enabled" } : {}),
        contenteditable: "false",
      }), label];
    },
  });
}

const READ_ONLY_RUNBOOK_REFERENCE = Node.create({
  name: "runbookReference", group: "inline", inline: true, atom: true, selectable: true,
  addAttributes: () => ({
    kind: { default: "ref", rendered: false }, refType: { default: "npc", rendered: false },
    refId: { default: "", rendered: false }, label: { default: "", rendered: false },
  }),
  renderHTML({ node, HTMLAttributes }) {
    const attrs = normalizeRunbookReferenceAttrs(node.attrs, { labelSource: "semantic" });
    const valid = (node.attrs.kind === "ref" || node.attrs.kind === "action") && isSupportedRunbookReference(attrs);
    return ["span", mergeAttributes(HTMLAttributes, {
      class: valid ? runbookReferenceClasses(attrs) : "md-ref-invalid",
      "data-md-ref-kind": valid ? attrs.kind : "invalid",
      "data-md-ref-type": attrs.refType,
      "data-md-ref-id": attrs.refId,
      contenteditable: "false",
      title: valid ? undefined : "Invalid runbook reference",
    }), attrs.label];
  },
});

function mediaImageExtension(): AnyExtension {
  return Node.create({
    name: "mediaImage", group: "inline", inline: true, atom: true, selectable: true,
    addAttributes: () => ({
      assetId: { default: "", rendered: false }, alt: { default: "", rendered: false },
      width: { default: null, rendered: false }, collapsed: { default: null, rendered: false },
    }),
    renderHTML({ node }) {
      return ["span", {
        "data-media-asset-id": node.attrs.assetId,
        "data-media-alt": node.attrs.alt,
        ...(node.attrs.width != null || node.attrs.collapsed != null
          ? { "data-media-presentation": `dmb-image:v1 width=${node.attrs.width} collapsed=${node.attrs.collapsed}` } : {}),
      }];
    },
  });
}

function readOnlyBodyExtensions(activatable: boolean): AnyExtension[] {
  return [StarterKit, PreparedTableNode, WebSourceLink, PlayableElementHeadingAttributes, CalloutNode,
    ...DECISION_CONSEQUENCE_EXTENSIONS, ...PLAN_TABLE_EXTENSIONS, READ_ONLY_RUNBOOK_REFERENCE,
    graphNodeReferenceExtension(activatable), mediaImageExtension()];
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
    if(record.type === 'preparedTable') {
      try {parseTableFence(String(attrs.source));} catch {return 'invalid prepared table';}
    }

    if (["image", "video", "audio", "iframe", "embed"].includes(record.type)) {
      const src = typeof attrs.src === "string" ? attrs.src : "";
      return classifyImageUrl(src) === "unsafe"
        ? "unsafe embedded media"
        : "embedded media is not supported in read-only content";
    }
    if ("src" in attrs || "href" in attrs) return "unsupported URL-bearing node";

    if (record.type === "mediaImage") {
      if (typeof attrs.assetId !== "string" || !MEDIA_ASSET_ID.test(attrs.assetId)
        || typeof attrs.alt !== "string") return "malformed saved media reference";
      if ((attrs.width != null || attrs.collapsed != null)
        && !imagePresentation(`dmb-image:v1 width=${attrs.width} collapsed=${attrs.collapsed}`)) {
        return "malformed saved media presentation";
      }
    }

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

/** Thumbnail previews use the same safety and registered schema as the full reader. */
export function isReadableBodyContent(content: readonly JSONContent[]): boolean {
  if (unsupportedBodyContentReason(content)) return false;
  try {
    generateHTML({ type: "doc", content: [...content] }, READ_ONLY_BODY_EXTENSIONS);
    return true;
  } catch { return false; }
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

  const renderedHtml = useMemo(() => ({ __html: html ?? "" }), [html]);
  const body = useRef<HTMLDivElement>(null);
  const [slots, setSlots] = useState<{ html: string; elements: HTMLElement[] } | null>(null);
  useLayoutEffect(() => {
    if (!html || !body.current) { setSlots(null); return; }
    setSlots({ html, elements: Array.from(body.current.querySelectorAll<HTMLElement>("span[data-media-asset-id]")) });
  }, [html]);

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
    <>
    <div
      ref={body}
      className={className}
      data-testid={testId}
      onClick={activatable ? handleClick : undefined}
      dangerouslySetInnerHTML={renderedHtml}
    />
    {slots?.html === html ? slots.elements.map((element, index) => {
      const presentation = imagePresentation(element.dataset.mediaPresentation);
      return createPortal(<SavedMediaImage assetId={element.dataset.mediaAssetId ?? ""}
        alt={element.dataset.mediaAlt ?? ""} {...(presentation ?? {})} />, element, `${html}:${index}`);
    }) : null}
    </>
  );
  if (fallbackText) return <p className={className} data-testid={testId}>{fallbackText}</p>;
  return null;
}
