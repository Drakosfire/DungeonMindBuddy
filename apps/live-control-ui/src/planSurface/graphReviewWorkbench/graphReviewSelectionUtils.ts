import type {
  GoldGraphProjectionResponse,
  GraphProjectionAdjacencyCandidate,
  GraphProjectionNodeView,
  UnionSupergraphProjectionResponse,
} from "../../api/types";
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
  sourceLabel: string,
  adjacency: GraphProjectionAdjacencyCandidate,
): string {
  const predicate = adjacency.edge_label || adjacency.predicate || "relates to";
  if (adjacency.direction === "incoming") return `${adjacency.label} ${predicate} ${sourceLabel}`;
  return `${sourceLabel} ${predicate} ${adjacency.label}`;
}

export function formatGraphObjectType(
  kind?: string | null,
  role?: string | null,
): string {
  const values = [kind, role]
    .map((value) => value?.trim())
    .filter((value): value is string => Boolean(value));
  const uniqueValues = [...new Set(values)];
  return uniqueValues.join(" / ") || "Graph object";
}

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

  const contextLine =
    count > 1
      ? "Old links to those nodes now open this survivor. Evidence and relationships from merged duplicates are shown on this card."
      : "Evidence and relationships from the duplicate are now shown here.";

  return { foldedLine, contextLine };
}

export function gameSummaryForNode(node: GraphProjectionNodeView): string {
  if (node.summary?.trim()) return node.summary;
  const kind = (node.kind || "object").toLowerCase();
  const connectionCount = node.adjacency.length;
  if (connectionCount > 0) {
    return `This ${kind} has ${connectionCount} connected campaign relationship${connectionCount === 1 ? "" : "s"} in this session.`;
  }
  if (node.aliases.length) {
    return `This ${kind} is also known as ${node.aliases.join(", ")}.`;
  }
  return "No campaign summary has been authored yet.";
}
