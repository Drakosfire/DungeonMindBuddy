import type {
  GoldGraphProjectionResponse,
  GraphProjectionAdjacencyCandidate,
  GraphProjectionNodeView,
  UnionSupergraphProjectionResponse,
} from "../../api/types";
import {
  displayAliasesForNode,
  isPlaceholderNodeSummary,
  primaryGameSummaryForNode,
} from "../../graphObjectCard";
import type { GraphReviewProjectionLaneRole } from "./GraphReviewProjectionLane";
import type { GraphReviewDeltaIndex, GraphReviewDeltaStatus } from "./graphReviewDeltaTypes";

export interface GraphReviewSelectedNode {
  laneRole: GraphReviewProjectionLaneRole;
  nodeId: string;
}

export interface GraphReviewSelectedRelationship {
  laneRole: GraphReviewProjectionLaneRole;
  sourceNodeId: string;
  adjacentNodeId: string;
  edgeId?: string | null;
}

export interface GraphReviewSelectedNodeViewModel {
  laneRole: GraphReviewProjectionLaneRole;
  node: GraphProjectionNodeView;
  status: GraphReviewDeltaStatus | "unknown";
  deltaId?: string | null;
  counterpart?: {
    laneRole: GraphReviewProjectionLaneRole;
    nodeId: string;
    label: string;
    node?: GraphProjectionNodeView | null;
  } | null;
}

export interface GraphReviewProjectionPair {
  goldProjection: GoldGraphProjectionResponse | null;
  liveProjection: UnionSupergraphProjectionResponse | null;
}

function nodeViewsForLane(projections: GraphReviewProjectionPair, laneRole: GraphReviewProjectionLaneRole) {
  return laneRole === "gold" ? projections.goldProjection?.node_views : projections.liveProjection?.node_views;
}

export function resolveGraphReviewSelectedNode(
  selection: GraphReviewSelectedNode | null,
  projections: GraphReviewProjectionPair,
  deltaIndex: GraphReviewDeltaIndex,
): GraphReviewSelectedNodeViewModel | null {
  if (!selection) return null;
  const node = nodeViewsForLane(projections, selection.laneRole)?.[selection.nodeId];
  if (!node) return null;

  const delta = deltaIndex.deltas.find((candidate) =>
    candidate.laneObjectRefs.some(
      (ref) => ref.laneRole === selection.laneRole && ref.objectKind === "node" && ref.objectId === selection.nodeId,
    ),
  );
  const counterpartRole: GraphReviewProjectionLaneRole = selection.laneRole === "gold" ? "live" : "gold";
  const counterpartRef = delta?.laneObjectRefs.find(
    (ref) => ref.laneRole === counterpartRole && ref.objectKind === "node",
  );
  const counterpartNode = counterpartRef ? nodeViewsForLane(projections, counterpartRole)?.[counterpartRef.objectId] ?? null : null;

  return {
    laneRole: selection.laneRole,
    node,
    status: delta?.status ?? "unknown",
    deltaId: delta?.deltaId ?? null,
    counterpart: counterpartRef
      ? {
          laneRole: counterpartRole,
          nodeId: counterpartRef.objectId,
          label: counterpartNode?.label ?? counterpartRef.label ?? counterpartRef.objectId,
          node: counterpartNode,
        }
      : null,
  };
}

export function findSelectedAdjacency(
  node: GraphProjectionNodeView | null | undefined,
  selection: GraphReviewSelectedRelationship | null,
): GraphProjectionAdjacencyCandidate | null {
  if (!node || !selection || selection.sourceNodeId !== node.node_id) return null;
  return (
    node.adjacency.find(
      (candidate) =>
        candidate.node_id === selection.adjacentNodeId &&
        (!selection.edgeId || candidate.edge_id === selection.edgeId),
    ) ?? null
  );
}

export function formatGraphReviewRelationshipStatement(
  _sourceLabel: string,
  adjacency: GraphProjectionAdjacencyCandidate,
): string {
  const predicate = relationshipPredicateLabel(adjacency);
  const summary = relatedSummaryForRelationship(adjacency);
  if (summary) return `${adjacency.label} · ${predicate} · ${summary}`;
  return `${adjacency.label} · ${predicate}`;
}

export function humanizeRelationshipPredicate(predicate: string): string {
  return predicate.replace(/_/g, " ").trim() || "connected";
}

export function relationshipPredicateLabel(
  adjacency: GraphProjectionAdjacencyCandidate,
): string {
  const edgeLabel = adjacency.edge_label?.trim();
  if (edgeLabel && edgeLabel.toLowerCase() !== "related") {
    return humanizeRelationshipPredicate(edgeLabel);
  }
  const predicate = adjacency.predicate?.trim();
  if (!predicate || predicate.toLowerCase() === "related") {
    return "connected";
  }
  return humanizeRelationshipPredicate(predicate);
}

export function relatedSummaryForRelationship(
  adjacency: GraphProjectionAdjacencyCandidate,
): string | null {
  const related = adjacency.related_summary?.trim();
  if (related && !isPlaceholderNodeSummary(related)) return related;
  return null;
}

export function relationshipSourceExcerpt(
  adjacency: GraphProjectionAdjacencyCandidate,
): string | null {
  const excerpt = adjacency.source_excerpt?.trim();
  return excerpt || null;
}

export function relationshipSourceExcerptIsFullParagraph(
  adjacency: GraphProjectionAdjacencyCandidate,
): boolean {
  return Boolean(adjacency.source_excerpt_is_full_paragraph);
}

export interface RelationshipSourceExcerptSegment {
  text: string;
  highlighted: boolean;
}

/**
 * Split a relationship's source excerpt into segments so the UI can visually
 * mark the fragments that actually ground this relationship (only populated
 * when the excerpt resolved to the full source paragraph).
 */
export function relationshipSourceExcerptSegments(
  adjacency: GraphProjectionAdjacencyCandidate,
): RelationshipSourceExcerptSegment[] {
  const excerpt = relationshipSourceExcerpt(adjacency);
  if (!excerpt) return [];
  const spans = (adjacency.source_excerpt_highlight_spans ?? [])
    .filter((span) => span.end > span.start && span.start >= 0 && span.end <= excerpt.length)
    .sort((left, right) => left.start - right.start);
  if (!spans.length) return [{ text: excerpt, highlighted: false }];

  const segments: RelationshipSourceExcerptSegment[] = [];
  let cursor = 0;
  for (const span of spans) {
    if (span.start < cursor) continue;
    if (span.start > cursor) {
      segments.push({ text: excerpt.slice(cursor, span.start), highlighted: false });
    }
    segments.push({ text: excerpt.slice(span.start, span.end), highlighted: true });
    cursor = span.end;
  }
  if (cursor < excerpt.length) {
    segments.push({ text: excerpt.slice(cursor), highlighted: false });
  }
  return segments;
}

export function relationshipMetaLine(
  adjacency: GraphProjectionAdjacencyCandidate,
): string | null {
  const parts: string[] = [relationshipPredicateLabel(adjacency)];
  const kind = adjacency.kind?.trim();
  if (kind) parts.push(kind);
  const summary = relatedSummaryForRelationship(adjacency);
  if (summary) parts.push(summary);
  return parts.join(" · ");
}

export interface GraphReviewRelationshipGroup {
  key: string;
  members: GraphProjectionAdjacencyCandidate[];
}

/**
 * Signature identifying relationships grounded in the exact same source
 * phrase: same predicate/direction from the focus node, and the identical
 * highlighted fragment within an identical excerpt. Returns null when there
 * isn't a resolved highlighted phrase to compare, so relationships are only
 * ever grouped on a real shared-evidence signal (never merged just because
 * both lack an excerpt).
 */
function relationshipEvidenceSignature(
  adjacency: GraphProjectionAdjacencyCandidate,
): string | null {
  const excerpt = relationshipSourceExcerpt(adjacency);
  if (!excerpt) return null;
  const highlighted = relationshipSourceExcerptSegments(adjacency)
    .filter((segment) => segment.highlighted)
    .map((segment) => segment.text.trim().toLowerCase())
    .filter(Boolean);
  if (!highlighted.length) return null;
  const predicate = adjacency.predicate?.trim().toLowerCase() ?? "";
  const direction = adjacency.direction?.trim().toLowerCase() ?? "";
  return `${direction}|${predicate}|${excerpt}|${highlighted.join("¦")}`;
}

/**
 * Groups adjacency candidates that are grounded in the identical source
 * phrase (same paragraph, same highlighted fragment) into a single row, so
 * e.g. "Bonogo" and "Karsemine" both attested by "Bonogo and Karsemine
 * slipped past the guards" collapse into one relationship instead of
 * repeating the same excerpt twice.
 */
export function groupRelationshipsByEvidence(
  relationships: GraphProjectionAdjacencyCandidate[],
): GraphReviewRelationshipGroup[] {
  const groups: GraphReviewRelationshipGroup[] = [];
  const groupIndexBySignature = new Map<string, number>();

  for (const relationship of relationships) {
    const signature = relationshipEvidenceSignature(relationship);
    const existingIndex = signature ? groupIndexBySignature.get(signature) : undefined;
    if (existingIndex !== undefined) {
      groups[existingIndex].members.push(relationship);
      continue;
    }
    const index = groups.length;
    groups.push({
      key: signature ?? `${relationship.edge_id}:${relationship.node_id}`,
      members: [relationship],
    });
    if (signature) groupIndexBySignature.set(signature, index);
  }
  return groups;
}

export function relationshipGroupLabel(
  members: GraphProjectionAdjacencyCandidate[],
): string {
  const labels = [...new Set(members.map((member) => member.label))];
  if (labels.length <= 1) return labels[0] ?? "";
  if (labels.length === 2) return `${labels[0]} & ${labels[1]}`;
  return `${labels.slice(0, -1).join(", ")} & ${labels[labels.length - 1]}`;
}

export function relationshipGroupMetaLine(
  members: GraphProjectionAdjacencyCandidate[],
): string | null {
  const first = members[0];
  if (!first) return null;
  if (members.length === 1) return relationshipMetaLine(first);

  // Multiple related objects: their individual summaries differ (shown per
  // object in the expanded detail instead), so the row meta line only
  // states what's true for the whole group.
  const parts: string[] = [relationshipPredicateLabel(first)];
  const kinds = [...new Set(members.map((member) => member.kind?.trim()).filter(Boolean))];
  if (kinds.length === 1) parts.push(kinds[0] as string);
  return parts.join(" · ");
}

export {
  displayAliasesForNode,
  formatGraphObjectType,
  graphObjectSecondaryRoleLabel,
  graphObjectTypeBadgeLabel,
  isPlaceholderNodeSummary,
  primaryGameSummaryForNode,
} from "../../graphObjectCard";

export type DurableIdentitySummary = {
  mergedAwayIds: string[];
  mergeAssertionIds: string[];
  redirectIds: string[];
  mergeRecordIds: string[];
  foldedIdentityCount: number;
};

export function stringList(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter(
        (item): item is string => typeof item === "string" && item.trim().length > 0,
      )
    : [];
}

export function durableIdentitySummaryForNode(
  node: GraphProjectionNodeView,
): DurableIdentitySummary | null {
  const mergedAwayIds = stringList(node.merged_away_ids);
  const mergeAssertionIds = stringList(node.merge_assertion_ids);
  const redirectIds = stringList(node.identity_redirect_ids);
  const mergeRecordIds = stringList(node.identity_merge_record_ids);

  if (
    !mergedAwayIds.length &&
    !mergeAssertionIds.length &&
    !redirectIds.length &&
    !mergeRecordIds.length
  ) {
    return null;
  }

  return {
    mergedAwayIds,
    mergeAssertionIds,
    redirectIds,
    mergeRecordIds,
    foldedIdentityCount: mergedAwayIds.length,
  };
}

function humanLabelFromMergedAwayId(mergedAwayId: string): string {
  const suffix = mergedAwayId.split(":").pop() ?? mergedAwayId;
  return suffix
    .split(/[_-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function foldedIdentityLabels(
  mergedAwayIds: string[],
  aliases: string[],
): string[] {
  const normalizedAliases = aliases.map((alias) => alias.trim()).filter(Boolean);
  return mergedAwayIds.map((mergedAwayId) => {
    const suffix = (mergedAwayId.split(":").pop() ?? mergedAwayId).toLowerCase();
    const exactMatch = normalizedAliases.find((alias) => alias.toLowerCase() === suffix);
    if (exactMatch) return exactMatch;
    const containingAliases = normalizedAliases.filter((alias) =>
      alias.toLowerCase().includes(suffix),
    );
    if (containingAliases.length) {
      return containingAliases.sort((left, right) => left.length - right.length)[0];
    }
    return humanLabelFromMergedAwayId(mergedAwayId);
  });
}

export function mergedIdentityNoteCopy(
  summary: DurableIdentitySummary,
  aliases: string[],
  options?: { adjacencyCount?: number; evidenceCount?: number },
): { foldedLine: string; contextLine: string } {
  const count = summary.foldedIdentityCount;
  const names = foldedIdentityLabels(summary.mergedAwayIds, aliases);
  const uniqueNames = [...new Set(names)];

  let foldedLine: string;
  if (count > 0 && uniqueNames.length > 0) {
    const nameList =
      uniqueNames.length <= 3
        ? uniqueNames.join(", ")
        : `${uniqueNames.slice(0, 3).join(", ")} and others`;
    foldedLine =
      count === 1
        ? `Folded in 1 prior identity: ${nameList}.`
        : `Folded in ${count} prior identities: ${nameList}.`;
  } else if (count > 0) {
    foldedLine =
      count === 1
        ? "Folded in 1 prior identity."
        : `Folded in ${count} prior identities.`;
  } else {
    foldedLine = "This node includes durable merged identity context.";
  }

  const adjacencyCount = options?.adjacencyCount ?? 0;
  const evidenceCount = options?.evidenceCount ?? 0;
  let contextLine: string;
  if (count > 1) {
    if (adjacencyCount > 0 && evidenceCount > 0) {
      contextLine =
        "Old links to those nodes now open this survivor. Evidence and relationships from merged duplicates are shown on this card.";
    } else if (adjacencyCount > 0) {
      contextLine =
        "Old links to those nodes now open this survivor. Relationships from merged duplicates are shown on this card.";
    } else if (evidenceCount > 0) {
      contextLine =
        "Old links to those nodes now open this survivor. Evidence from merged duplicates is shown on this card.";
    } else {
      contextLine = "Old links to those nodes now open this survivor.";
    }
  } else if (adjacencyCount > 0 && evidenceCount > 0) {
    contextLine = "Evidence and relationships from the duplicate are now shown here.";
  } else if (adjacencyCount > 0) {
    contextLine = "Relationships from the duplicate are now shown here.";
  } else if (evidenceCount > 0) {
    contextLine = "Evidence from the duplicate is now shown here.";
  } else {
    contextLine = "This node absorbed the duplicate identity.";
  }

  return { foldedLine, contextLine };
}

export function detailsConnectionContextForNode(node: GraphProjectionNodeView): string | null {
  if (primaryGameSummaryForNode(node)) return null;
  const kind = (node.kind || "object").toLowerCase();
  const connectionCount = node.adjacency.length;
  if (connectionCount > 0) {
    return `This ${kind} has ${connectionCount} connected campaign relationship${connectionCount === 1 ? "" : "s"} in this session.`;
  }
  return null;
}

export function gameSummaryForNode(node: GraphProjectionNodeView): string | null {
  const primary = primaryGameSummaryForNode(node);
  if (primary) return primary;
  const connectionContext = detailsConnectionContextForNode(node);
  if (connectionContext) return connectionContext;
  const aliases = displayAliasesForNode(node);
  if (aliases.length) {
    const kind = (node.kind || "object").toLowerCase();
    return `This ${kind} is also known as ${aliases.join(", ")}.`;
  }
  return null;
}
