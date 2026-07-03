import type { GraphReviewLaneRole } from "../../api/types";

// Which side of the two-lane review a projected node/relationship belongs to.
// Lives here (rather than on a specific lane-rendering component) because
// delta indexing, selection state, and the authoring workflow all need it
// independent of which component renders a given lane.
export type GraphReviewProjectionLaneRole = "gold" | "live";

export type GraphReviewDeltaStatus =
  | "matched"
  | "gold_only"
  | "live_only"
  | "changed_type"
  | "changed_label"
  | "changed_evidence"
  | "changed_edges"
  | "comparator_uncertain";

export type GraphReviewDeltaObjectKind =
  | "node"
  | "edge"
  | "mention"
  | "source_span"
  | "beat"
  | "write"
  | "ignored_item"
  | "deferred_item"
  | "unknown";

export interface GraphReviewLaneObjectRef {
  laneId: string;
  laneRole: GraphReviewLaneRole;
  objectKind: GraphReviewDeltaObjectKind;
  objectId: string;
  label?: string | null;
  matchScore?: number | null;
}

export interface GraphReviewContextualDelta {
  deltaId: string;
  objectKind: GraphReviewDeltaObjectKind;
  status: GraphReviewDeltaStatus;
  laneObjectRefs: GraphReviewLaneObjectRef[];
  label?: string | null;
  summary: string;
  comparatorReason?: string | null;
  sourceSpanRefIds: string[];
  primarySourceSpanRefId?: string | null;
  evidenceRefIds: string[];
  confidence?: "high" | "medium" | "low";
  metadata?: Record<string, string | number | boolean | null>;
}

export interface GraphReviewDeltaIndex {
  schemaVersion: "dmb_graph_review_contextual_delta_index_v1";
  campaignId: string;
  sessionId: string;
  goldLaneId?: string | null;
  liveLaneId?: string | null;
  liveRunManifestPath?: string | null;
  deltas: GraphReviewContextualDelta[];
  countsByStatus: Record<GraphReviewDeltaStatus, number>;
  countsByObjectKind: Record<GraphReviewDeltaObjectKind, number>;
  warnings: string[];
}

export const GRAPH_REVIEW_DELTA_STATUSES: GraphReviewDeltaStatus[] = [
  "matched",
  "gold_only",
  "live_only",
  "changed_type",
  "changed_label",
  "changed_evidence",
  "changed_edges",
  "comparator_uncertain",
];

export const GRAPH_REVIEW_DELTA_OBJECT_KINDS: GraphReviewDeltaObjectKind[] = [
  "node",
  "edge",
  "mention",
  "source_span",
  "beat",
  "write",
  "ignored_item",
  "deferred_item",
  "unknown",
];
