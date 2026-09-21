import type {
  GraphProjectionAdjacencyCandidate,
  GraphProjectionNodeView,
} from "../../api/types";
import type { GraphNodeChipDeltaPresentation } from "../../graphReference";
import type { GraphAuthoringSelection } from "./graphAuthoringSelection";
import type {
  GraphObjectAuthoringLinkExistingProposal,
  GraphObjectAuthoringObjectProposal,
  GraphObjectAuthoringObjectRef,
  GraphObjectAuthoringProposal,
  GraphObjectAuthoringRelationshipProposal,
} from "./graphObjectAuthoringDraft";

export interface PublishedRecapWorkingProjection {
  /** A presentation-only Markdown projection. The canonical recap is never changed. */
  markdown: string;
  nodeViews: Record<string, GraphProjectionNodeView>;
  nodeDeltaPresentations: Record<string, GraphNodeChipDeltaPresentation>;
  diagnostics: string[];
  localNodeIds: string[];
}

interface MarkdownReplacement {
  start: number;
  end: number;
  value: string;
}

interface MarkdownBlock {
  start: number;
  end: number;
  text: string;
  paragraphOrdinal: number | null;
}

const LOCAL_AUTHORING_SOURCE = "local_authoring";

function normalizeText(value: string | null | undefined): string {
  return (value ?? "").replace(/\s+/g, " ").trim().toLowerCase();
}

function localNodeId(proposalId: string): string {
  return `local-authoring:${proposalId}`;
}

function manualReferenceNodeId(label: string): string {
  return `local-authoring:reference:${normalizeText(label).replace(/[^a-z0-9]+/g, "-")}`;
}

function objectRefNodeId(ref: GraphObjectAuthoringObjectRef): string | null {
  if (ref.refKind === "existing_graph_node") {
    return ref.nodeId?.trim() || null;
  }
  if (ref.refKind === "local_proposal") {
    return ref.localProposalId ? localNodeId(ref.localProposalId) : null;
  }
  const label = ref.label.trim();
  return label ? manualReferenceNodeId(label) : null;
}

function graphKind(ref: GraphObjectAuthoringObjectRef): string {
  return ref.kind?.trim() || "unknown";
}

function graphRole(ref: GraphObjectAuthoringObjectRef): string {
  return ref.role?.trim() || graphKind(ref);
}

function createWorkingNodeView(
  nodeId: string,
  ref: GraphObjectAuthoringObjectRef,
  options: { local: boolean; summary?: string | null; sourceAnchorText?: string | null },
): GraphProjectionNodeView {
  return {
    node_id: nodeId,
    label: ref.label.trim() || nodeId,
    kind: graphKind(ref),
    role: graphRole(ref),
    aliases: [],
    source_domains: options.local ? [LOCAL_AUTHORING_SOURCE] : [],
    evidence_badges: [],
    adjacency: [],
    suggested_expansions: [],
    anchored_to_focus_session: true,
    summary: options.summary?.trim() || null,
    source: options.local ? LOCAL_AUTHORING_SOURCE : "existing_reference",
    authored: options.local,
    visibility: ref.visibility ?? null,
    graph_scope: ref.graphScope ? [ref.graphScope] : options.local ? ["recap_graph"] : null,
    source_anchor_text: options.sourceAnchorText ?? null,
  };
}

function objectProposalRef(proposal: GraphObjectAuthoringObjectProposal): GraphObjectAuthoringObjectRef {
  return {
    refKind: "local_proposal",
    localProposalId: proposal.localProposalId,
    label: proposal.objectRef.label,
    kind: proposal.objectRef.kind,
    role: proposal.objectRef.role ?? null,
    visibility: proposal.visibility.visibility,
  };
}

function objectProposalNodeView(
  proposal: GraphObjectAuthoringObjectProposal,
): GraphProjectionNodeView {
  const ref = objectProposalRef(proposal);
  return createWorkingNodeView(localNodeId(proposal.localProposalId), ref, {
    local: true,
    summary: proposal.objectRef.summary,
    sourceAnchorText: proposal.selection.selectedText || null,
  });
}

function ensureNodeView(
  nodeViews: Record<string, GraphProjectionNodeView>,
  ref: GraphObjectAuthoringObjectRef,
  options: { local: boolean; summary?: string | null; sourceAnchorText?: string | null },
): string | null {
  const nodeId = objectRefNodeId(ref);
  if (!nodeId) return null;
  if (!nodeViews[nodeId]) {
    nodeViews[nodeId] = createWorkingNodeView(nodeId, ref, options);
  }
  return nodeId;
}

function addRelationship(
  nodeViews: Record<string, GraphProjectionNodeView>,
  sourceId: string,
  targetId: string,
  targetRef: GraphObjectAuthoringObjectRef,
  proposal: GraphObjectAuthoringRelationshipProposal,
  direction: "outgoing" | "incoming" | "related",
  edgeSuffix: string,
  sessionId: string,
): void {
  const source = nodeViews[sourceId];
  if (!source) return;
  const edgeId = `local-authoring:${proposal.localProposalId}:${edgeSuffix}`;
  if (source.adjacency.some((edge) => edge.edge_id === edgeId)) return;

  const edge: GraphProjectionAdjacencyCandidate = {
    edge_id: edgeId,
    node_id: targetId,
    label: targetRef.label.trim() || targetId,
    kind: graphKind(targetRef),
    predicate: proposal.relationshipType,
    direction,
    anchored_to_focus_session: true,
    source_domains: [LOCAL_AUTHORING_SOURCE],
    evidence_ref_ids: [],
    session_ids: [sessionId],
    campaign_scope: proposal.selection?.campaignId ?? null,
    related_summary: proposal.summary?.trim() || null,
    source_excerpt: null,
    source_excerpt_is_full_paragraph: false,
    source_excerpt_highlight_spans: [],
  };

  source.adjacency = [...source.adjacency, edge];
  source.suggested_expansions = [...(source.suggested_expansions ?? []), {
    ...edge,
    rank: (source.suggested_expansions?.length ?? 0) + 1,
    rank_reason: "local adjudication",
  }];
}

function addObjectOverlay(
  nodeViews: Record<string, GraphProjectionNodeView>,
  nodeDeltaPresentations: Record<string, GraphNodeChipDeltaPresentation>,
  proposal: GraphObjectAuthoringObjectProposal,
): void {
  const node = objectProposalNodeView(proposal);
  nodeViews[node.node_id] = {
    ...nodeViews[node.node_id],
    ...node,
  };
  nodeDeltaPresentations[node.node_id] = {
    status: "live_only",
    label: "Local · uncommitted",
    summary: proposal.objectRef.summary ?? "Staged local object; no World node exists yet.",
  };
}

function addLinkOverlay(
  nodeViews: Record<string, GraphProjectionNodeView>,
  proposal: GraphObjectAuthoringLinkExistingProposal,
): string | null {
  const ref = proposal.existingObjectRef;
  const nodeId = ensureNodeView(nodeViews, ref, { local: false });
  if (!nodeId) return null;
  // Existing-node tags already communicate their identity through the pill.
  // Keep the working projection local-only without adding a second badge to
  // the same recap occurrence; new local objects retain their explicit badge.
  return nodeId;
}

function markdownBlocks(markdown: string): MarkdownBlock[] {
  const blocks: MarkdownBlock[] = [];
  const blockPattern = /(?:^|\n)([^\n]*(?:\n(?!\s*$)[^\n]*)*)/g;
  let paragraphOrdinal = 0;
  let match: RegExpExecArray | null;

  while ((match = blockPattern.exec(markdown))) {
    const text = match[1] ?? "";
    const start = match.index + (match[0].startsWith("\n") ? 1 : 0);
    const end = start + text.length;
    if (!text.trim()) continue;
    const isHeading = text.trimStart().startsWith("#");
    if (!isHeading) paragraphOrdinal += 1;
    blocks.push({
      start,
      end,
      text,
      paragraphOrdinal: isHeading ? null : paragraphOrdinal,
    });
  }

  return blocks;
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function linkRangeForText(
  block: MarkdownBlock,
  selection: GraphAuthoringSelection,
  preferredNodeId?: string | null,
): { start: number; end: number } | null {
  const selected = escapeRegExp(selection.selectedText.trim());
  if (!selected) return null;
  const preferredSuffix = preferredNodeId
    ? `dmb-node:${escapeRegExp(preferredNodeId)}`
    : "dmb-node:[^)]+";
  const pattern = new RegExp(`\\[${selected}\\]\\(${preferredSuffix}\\)`, "gi");
  const match = pattern.exec(block.text);
  if (!match || match.index === undefined) return null;
  return {
    start: block.start + match.index,
    end: block.start + match.index + match[0].length,
  };
}

function findMarkdownOccurrence(
  markdown: string,
  selection: GraphAuthoringSelection,
  preferredNodeId?: string | null,
): { start: number; end: number } | null {
  const selected = selection.selectedText.trim();
  if (!selected) return null;

  const blocks = markdownBlocks(markdown);
  const preferredBlocks = selection.paragraphOrdinal
    ? blocks.filter((block) => block.paragraphOrdinal === selection.paragraphOrdinal)
    : blocks;
  const candidates = preferredBlocks.length ? preferredBlocks : blocks;

  if (selection.selectionKind === "graph_node_reference" || preferredNodeId) {
    const exactLink = candidates
      .map((block) => linkRangeForText(block, selection, preferredNodeId))
      .find((range): range is { start: number; end: number } => Boolean(range));
    if (exactLink) return exactLink;
  }

  const occurrences = candidates.flatMap((block) => {
    const ranges: Array<{ start: number; end: number; block: MarkdownBlock }> = [];
    let offset = 0;
    while (offset <= block.text.length - selected.length) {
      const index = block.text.indexOf(selected, offset);
      if (index < 0) break;
      ranges.push({
        start: block.start + index,
        end: block.start + index + selected.length,
        block,
      });
      offset = index + Math.max(1, selected.length);
    }
    return ranges;
  });

  if (occurrences.length === 1) {
    return { start: occurrences[0]!.start, end: occurrences[0]!.end };
  }

  const before = normalizeText(selection.surroundingTextBefore);
  const after = normalizeText(selection.surroundingTextAfter);
  const contextual = occurrences.filter((candidate) => {
    const blockOffset = candidate.start - candidate.block.start;
    const beforeText = normalizeText(candidate.block.text.slice(0, blockOffset));
    const afterText = normalizeText(candidate.block.text.slice(blockOffset + selected.length));
    return (
      (!before || beforeText.endsWith(before.slice(-32))) &&
      (!after || afterText.startsWith(after.slice(0, 32)))
    );
  });

  return contextual.length === 1
    ? { start: contextual[0]!.start, end: contextual[0]!.end }
    : null;
}

function applyReplacements(markdown: string, replacements: MarkdownReplacement[]): string {
  const ordered = [...replacements]
    .sort((left, right) => right.start - left.start)
    .filter((replacement, index, all) => {
      const later = all.slice(index + 1);
      return !later.some(
        (other) => replacement.start < other.end && other.start < replacement.end,
      );
    });

  return ordered.reduce(
    (current, replacement) =>
      `${current.slice(0, replacement.start)}${replacement.value}${current.slice(replacement.end)}`,
    markdown,
  );
}

function addRelationshipOverlay(
  nodeViews: Record<string, GraphProjectionNodeView>,
  proposal: GraphObjectAuthoringRelationshipProposal,
  sessionId: string,
): void {
  const sourceId = ensureNodeView(nodeViews, proposal.sourceObjectRef, {
    local: proposal.sourceObjectRef.refKind !== "existing_graph_node",
  });
  const targetId = ensureNodeView(nodeViews, proposal.targetObjectRef, {
    local: proposal.targetObjectRef.refKind !== "existing_graph_node",
  });
  if (!sourceId || !targetId || sourceId === targetId) return;

  if (proposal.direction === "undirected") {
    addRelationship(
      nodeViews,
      sourceId,
      targetId,
      proposal.targetObjectRef,
      proposal,
      "related",
      "source",
      sessionId,
    );
    addRelationship(
      nodeViews,
      targetId,
      sourceId,
      proposal.sourceObjectRef,
      proposal,
      "related",
      "target",
      sessionId,
    );
    return;
  }

  addRelationship(
    nodeViews,
    sourceId,
    targetId,
    proposal.targetObjectRef,
    proposal,
    "outgoing",
    "source",
    sessionId,
  );
  addRelationship(
    nodeViews,
    targetId,
    sourceId,
    proposal.sourceObjectRef,
    proposal,
    "incoming",
    "target",
    sessionId,
  );
}

function proposalSelection(
  proposal: GraphObjectAuthoringProposal,
): GraphAuthoringSelection | null {
  return proposal.proposalKind === "merge_objects" ? null : proposal.selection ?? null;
}

export function derivePublishedRecapWorkingProjection(input: {
  markdown: string;
  nodeViews: Record<string, GraphProjectionNodeView>;
  proposals: GraphObjectAuthoringProposal[];
  sessionId: string;
}): PublishedRecapWorkingProjection {
  const nodeViews: Record<string, GraphProjectionNodeView> = Object.fromEntries(
    Object.entries(input.nodeViews).map(([nodeId, node]) => [nodeId, { ...node, adjacency: [...node.adjacency], suggested_expansions: [...(node.suggested_expansions ?? [])] }]),
  );
  const nodeDeltaPresentations: Record<string, GraphNodeChipDeltaPresentation> = {};
  const replacements: MarkdownReplacement[] = [];
  const diagnostics: string[] = [];
  const localNodeIds: string[] = [];

  for (const proposal of input.proposals) {
    if (proposal.status !== "staged_local") continue;

    if (proposal.proposalKind === "object") {
      addObjectOverlay(nodeViews, nodeDeltaPresentations, proposal);
      localNodeIds.push(localNodeId(proposal.localProposalId));
    }

    if (proposal.proposalKind === "relationship") {
      addRelationshipOverlay(nodeViews, proposal, input.sessionId);
    }

    if (proposal.proposalKind !== "object" && proposal.proposalKind !== "link_existing") {
      continue;
    }

    const targetId = proposal.proposalKind === "object"
      ? localNodeId(proposal.localProposalId)
      : addLinkOverlay(nodeViews, proposal);
    const selectedText = proposal.proposalKind === "object"
      ? proposal.selection.selectedText
      : proposal.selectedText;
    if (!targetId || !selectedText.trim()) continue;

    const selection = proposalSelection(proposal);
    if (!selection) continue;
    const occurrence = findMarkdownOccurrence(
      input.markdown,
      selection,
      selection.existingNodeId ?? null,
    );
    if (!occurrence) {
      diagnostics.push(
        `Could not safely replay “${selectedText}” for local proposal ${proposal.localProposalId}; the source occurrence was ambiguous or unavailable.`,
      );
      continue;
    }
    replacements.push({
      ...occurrence,
      value: `[${selectedText}](dmb-node:${targetId})`,
    });
  }

  return {
    markdown: applyReplacements(input.markdown, replacements),
    nodeViews,
    nodeDeltaPresentations,
    diagnostics,
    localNodeIds: [...new Set(localNodeIds)],
  };
}
