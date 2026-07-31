import type {
  GraphReferenceProjectionBinding,
  GraphReferenceProjectionState,
  GraphReferenceResolution,
} from "../../graphReference/types";
import type { GraphReviewLiveStateContextValue } from "../graphReviewWorkbench/GraphReviewLiveStateContext";

/** Neutral graph-reference binding exposed through Plan projection host. */
export type PlanReferenceProjectionBinding = GraphReferenceProjectionBinding;
export type PlanGraphProjectionState = GraphReferenceProjectionState;
export type PlanReferenceResolution = GraphReferenceResolution;

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

export type { GraphReferenceProjectionBinding, GraphReferenceResolution };
