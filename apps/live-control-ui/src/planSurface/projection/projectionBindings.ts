import type { GraphObjectRelationshipViewModel } from "../../graphObjectCard";
import type { GraphReviewLiveStateContextValue } from "../graphReviewWorkbench/GraphReviewLiveStateContext";
import type { PlanGraphProjectionState, PlanReferenceResolution } from "../reference/graphAwareReferenceResolver";

/** In-memory Plan reference actions for projected content (not durable). */
export interface PlanReferenceProjectionBinding {
  resolverState: PlanGraphProjectionState | null;

  resolveRelationship(
    relationship: GraphObjectRelationshipViewModel,
  ): Promise<PlanReferenceResolution>;

  openResolvedReference(
    resolution: PlanReferenceResolution,
    projectionState?: PlanGraphProjectionState | null,
  ): void;

  openTool(toolId: string): void;
}

/**
 * Exact fields consumed by GraphReviewDiagnosticsToolPanel.
 * Do not widen to the full live-state context.
 */
export type GraphReviewDiagnosticsProjectionPayload = Pick<
  GraphReviewLiveStateContextValue,
  | "campaignId"
  | "sessionId"
  | "liveRun"
  | "projection"
  | "projectionStatus"
  | "compareStatus"
  | "compare"
  | "compareError"
  | "selection"
  | "onSelectSelection"
  | "deltaIndex"
  | "sourceSpanDeltaIndex"
  | "selectedDeltaNodeId"
  | "setSelectedEvidenceDeltaId"
  | "selectedEvidenceDeltaId"
  | "selectedSourceSpanId"
  | "setSelectedSourceSpanId"
  | "evidenceSelection"
  | "evidenceDiff"
  | "evidenceStatus"
  | "evidenceError"
  | "manualBeds"
  | "manualBedsStatus"
  | "manualBedsError"
  | "selectedManualBed"
  | "selectedVariantLaneView"
  | "selectedManualVariant"
  | "onSelectManualBedId"
  | "onSelectManualVariantName"
  | "variantInventoryIndex"
  | "selectedVariantInventoryRowId"
  | "setSelectedVariantInventoryRowId"
  | "selectedVariantInventoryRow"
>;

export const GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID = "graph-review-diagnostics" as const;

export type ToolProjectionPayloadMap = {
  [GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID]: GraphReviewDiagnosticsProjectionPayload;
};

export type RegisterableToolProjectionId = keyof ToolProjectionPayloadMap;
