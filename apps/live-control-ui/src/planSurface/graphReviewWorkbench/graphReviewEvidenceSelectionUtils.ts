import type { GraphReviewContextualDelta, GraphReviewLaneObjectRef } from "./graphReviewDeltaTypes";

export type GraphReviewEvidenceSelectionStatus =
  | "queryable"
  | "live_only_no_gold"
  | "no_object_ref"
  | "unsupported_object_kind";

export interface GraphReviewEvidenceSelection {
  status: GraphReviewEvidenceSelectionStatus;
  delta: GraphReviewContextualDelta | null;
  queryObjectKind?: string | null;
  queryObjectId?: string | null;
  preferredRef?: GraphReviewLaneObjectRef | null;
  goldRef?: GraphReviewLaneObjectRef | null;
  liveRef?: GraphReviewLaneObjectRef | null;
  reason: string;
}

const EVIDENCE_API_OBJECT_KIND_BY_LOCAL_KIND: Record<string, string> = {
  node: "nodes",
  edge: "edges",
  beat: "beats",
  write: "proposed_writes",
  ignored_item: "ignored_items",
  deferred_item: "deferred_items",
};

export function evidenceApiObjectKind(kind: string): string {
  return EVIDENCE_API_OBJECT_KIND_BY_LOCAL_KIND[kind] ?? kind;
}

function isSupportedEvidenceObjectKind(kind: string): boolean {
  return Object.prototype.hasOwnProperty.call(EVIDENCE_API_OBJECT_KIND_BY_LOCAL_KIND, kind);
}

export function buildEvidenceSelectionForDelta(
  delta: GraphReviewContextualDelta | null,
): GraphReviewEvidenceSelection {
  if (!delta) {
    return {
      status: "no_object_ref",
      delta: null,
      reason: "Select a delta, graph pill, or source-span attached delta to inspect gold/live evidence.",
    };
  }

  const goldRef = delta.laneObjectRefs.find((ref) => ref.laneRole === "gold") ?? null;
  const liveRef = delta.laneObjectRefs.find((ref) => ref.laneRole === "live") ?? null;

  if (goldRef) {
    if (!isSupportedEvidenceObjectKind(goldRef.objectKind)) {
      return {
        status: "unsupported_object_kind",
        delta,
        preferredRef: goldRef,
        goldRef,
        liveRef,
        reason: `Gold object kind ${goldRef.objectKind} is not supported by the evidence inspector.`,
      };
    }
    return {
      status: "queryable",
      delta,
      queryObjectKind: evidenceApiObjectKind(goldRef.objectKind),
      queryObjectId: goldRef.objectId,
      preferredRef: goldRef,
      goldRef,
      liveRef,
      reason: "Gold object evidence can be queried for this delta.",
    };
  }

  if (liveRef) {
    return {
      status: "live_only_no_gold",
      delta,
      preferredRef: liveRef,
      goldRef,
      liveRef,
      reason: "No gold evidence object is available for this live-only delta.",
    };
  }

  return {
    status: "no_object_ref",
    delta,
    goldRef,
    liveRef,
    reason: delta.comparatorReason || "This delta does not contain an inspectable object reference.",
  };
}
