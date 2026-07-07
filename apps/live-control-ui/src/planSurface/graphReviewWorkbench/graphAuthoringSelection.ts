import type { Editor } from "@tiptap/core";
import type { Node as ProseMirrorNode } from "@tiptap/pm/model";
import { NodeSelection } from "@tiptap/pm/state";

import type { GraphNodeReferenceAttrs } from "../../tiptap/extensions/GraphNodeReferenceNode";

export type GraphAuthoringSelectionKind =
  | "text_span"
  | "graph_node_reference"
  | "block"
  | "relationship";

export type GraphAuthoringLaneRole = "gold" | "live" | "authored";

export type GraphAuthoringAction = "author_object";

export interface GraphAuthoringContext {
  campaignId: string;
  sessionId: string;
  graphId?: string | null;
  laneRole?: GraphAuthoringLaneRole | null;
  sourceArtifactPath?: string | null;
  sourceArtifactSha256?: string | null;
}

export interface GraphAuthoringSelection {
  campaignId: string;
  sessionId: string;
  sourceArtifactPath?: string | null;
  sourceArtifactSha256?: string | null;

  selectionKind: GraphAuthoringSelectionKind;
  selectedText: string;
  normalizedSelectedText: string;
  surroundingTextBefore?: string | null;
  surroundingTextAfter?: string | null;
  paragraphOrdinal?: number | null;
  sourceSpanRefId?: string | null;

  tiptapFrom?: number | null;
  tiptapTo?: number | null;

  existingNodeId?: string | null;
  existingLabel?: string | null;

  graphId?: string | null;
  laneRole?: GraphAuthoringLaneRole | null;
}

export const MAX_AUTHORING_SELECTED_TEXT_LENGTH = 200;
export const MAX_SURROUNDING_TEXT_LENGTH = 80;

export function normalizeAuthoringSelectedText(text: string): string {
  return text.replace(/\s+/g, " ").trim();
}

export function graphAuthoringSelectionsEqual(
  left: GraphAuthoringSelection | null,
  right: GraphAuthoringSelection | null,
): boolean {
  if (left === right) {
    return true;
  }
  if (!left || !right) {
    return false;
  }
  return (
    left.selectionKind === right.selectionKind &&
    left.selectedText === right.selectedText &&
    left.normalizedSelectedText === right.normalizedSelectedText &&
    left.tiptapFrom === right.tiptapFrom &&
    left.tiptapTo === right.tiptapTo &&
    left.existingNodeId === right.existingNodeId &&
    left.campaignId === right.campaignId &&
    left.sessionId === right.sessionId &&
    left.graphId === right.graphId &&
    left.laneRole === right.laneRole
  );
}

function tailBoundedText(text: string, maxLength: number): string {
  const trimmed = text.trim();
  if (trimmed.length <= maxLength) {
    return trimmed;
  }
  return trimmed.slice(-maxLength);
}

function headBoundedText(text: string, maxLength: number): string {
  const trimmed = text.trim();
  if (trimmed.length <= maxLength) {
    return trimmed;
  }
  return trimmed.slice(0, maxLength);
}

function findParagraphOrdinal(doc: ProseMirrorNode, position: number): number | null {
  let ordinal = 0;
  let found: number | null = null;

  doc.descendants((node, nodePos) => {
    if (found !== null) {
      return false;
    }
    if (node.type.name === "paragraph") {
      ordinal += 1;
      const nodeEnd = nodePos + node.nodeSize;
      if (position >= nodePos && position <= nodeEnd) {
        found = ordinal;
        return false;
      }
    }
    return true;
  });

  return found;
}

function baseSelectionFields(
  context: GraphAuthoringContext,
): Pick<
  GraphAuthoringSelection,
  | "campaignId"
  | "sessionId"
  | "sourceArtifactPath"
  | "sourceArtifactSha256"
  | "graphId"
  | "laneRole"
> {
  return {
    campaignId: context.campaignId,
    sessionId: context.sessionId,
    sourceArtifactPath: context.sourceArtifactPath ?? null,
    sourceArtifactSha256: context.sourceArtifactSha256 ?? null,
    graphId: context.graphId ?? null,
    laneRole: context.laneRole ?? null,
  };
}

function buildGraphNodeReferenceSelection(
  editor: Editor,
  context: GraphAuthoringContext,
  attrs: GraphNodeReferenceAttrs,
  from: number,
  to: number,
): GraphAuthoringSelection {
  const label = attrs.label || attrs.nodeId;
  return {
    ...baseSelectionFields(context),
    selectionKind: "graph_node_reference",
    selectedText: label,
    normalizedSelectedText: normalizeAuthoringSelectedText(label),
    existingNodeId: attrs.nodeId,
    existingLabel: attrs.label || attrs.nodeId,
    tiptapFrom: from,
    tiptapTo: to,
    paragraphOrdinal: findParagraphOrdinal(editor.state.doc, from),
  };
}

export function buildGraphAuthoringSelectionFromEditor(
  editor: Editor,
  context: GraphAuthoringContext,
): GraphAuthoringSelection | null {
  const { selection, doc } = editor.state;

  if (selection instanceof NodeSelection) {
    const node = selection.node;
    if (node.type.name !== "graphNodeReference") {
      return null;
    }
    return buildGraphNodeReferenceSelection(
      editor,
      context,
      node.attrs as GraphNodeReferenceAttrs,
      selection.from,
      selection.to,
    );
  }

  if (selection.empty) {
    return null;
  }

  const from = selection.from;
  const to = selection.to;
  const selectedText = doc.textBetween(from, to, " ");
  const trimmed = selectedText.trim();
  if (!trimmed) {
    return null;
  }
  if (trimmed.length > MAX_AUTHORING_SELECTED_TEXT_LENGTH) {
    return null;
  }

  const beforeStart = Math.max(0, from - MAX_SURROUNDING_TEXT_LENGTH * 2);
  const afterEnd = Math.min(doc.content.size, to + MAX_SURROUNDING_TEXT_LENGTH * 2);
  const surroundingTextBefore = tailBoundedText(
    doc.textBetween(beforeStart, from, " "),
    MAX_SURROUNDING_TEXT_LENGTH,
  );
  const surroundingTextAfter = headBoundedText(
    doc.textBetween(to, afterEnd, " "),
    MAX_SURROUNDING_TEXT_LENGTH,
  );

  return {
    ...baseSelectionFields(context),
    selectionKind: "text_span",
    selectedText: trimmed,
    normalizedSelectedText: normalizeAuthoringSelectedText(trimmed),
    surroundingTextBefore: surroundingTextBefore || null,
    surroundingTextAfter: surroundingTextAfter || null,
    paragraphOrdinal: findParagraphOrdinal(doc, from),
    tiptapFrom: from,
    tiptapTo: to,
  };
}

export function buildGraphAuthoringSelectionFromRecapNode(input: {
  campaignId: string;
  sessionId: string;
  graphId?: string | null;
  sourceArtifactPath?: string | null;
  laneRole?: GraphAuthoringLaneRole | null;
  node: {
    node_id: string;
    label: string;
    source_anchor_text?: string | null;
  };
}): GraphAuthoringSelection {
  const selectedText =
    input.node.source_anchor_text?.trim() ||
    input.node.label.trim() ||
    input.node.node_id;

  return {
    campaignId: input.campaignId,
    sessionId: input.sessionId,
    sourceArtifactPath: input.sourceArtifactPath ?? null,
    selectionKind: "graph_node_reference",
    selectedText,
    normalizedSelectedText: normalizeAuthoringSelectedText(selectedText),
    existingNodeId: input.node.node_id,
    existingLabel: input.node.label,
    graphId: input.graphId ?? null,
    laneRole: input.laneRole ?? "live",
  };
}
