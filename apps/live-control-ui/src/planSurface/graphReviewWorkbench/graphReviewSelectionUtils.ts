import type {
  GoldGraphProjectionResponse,
  GraphProjectionAdjacencyCandidate,
  GraphProjectionNodeView,
  UnionSupergraphProjectionResponse,
} from "../../api/types";
import type {
  GraphReviewDeltaIndex,
  GraphReviewDeltaStatus,
  GraphReviewProjectionLaneRole,
} from "./graphReviewDeltaTypes";

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

export function gameSummaryForNode(node: GraphProjectionNodeView): string {
  if (node.summary?.trim()) return node.summary;
  const kind = node.kind || "Graph object";
  const role = node.role ? ` / ${node.role}` : "";
  const connectionCount = node.adjacency.length;
  return `${kind}${role} candidate with ${connectionCount} projected connection${connectionCount === 1 ? "" : "s"} in this session.`;
}
