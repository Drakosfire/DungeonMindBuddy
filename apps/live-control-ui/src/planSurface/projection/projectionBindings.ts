import type {
  GraphReferenceProjectionBinding,
  GraphReferenceProjectionState,
  GraphReferenceResolution,
} from "../../graphReference/types";
import type { GraphReviewLiveStateContextValue } from "../graphReviewWorkbench/GraphReviewLiveStateContext";
import type { PlanContextDescriptor, SurfaceConfig } from "../types";

export {
  GRAPH_REFERENCE_BINDING_ID,
  GRAPH_REFERENCE_PROJECTION_STATE_BINDING_ID,
  GRAPH_REFERENCE_RESOLUTION_BINDING_ID,
  readGraphReferenceBinding,
  readGraphReferenceProjectionStateBinding,
  readGraphReferenceResolutionBinding,
} from "../../graphReference/projectionBindings";

export const PLAN_CONTEXT_BINDING_ID = "plan-context" as const;
export const PLAN_SURFACE_CONFIG_BINDING_ID = "plan-surface-config" as const;
export const GRAPH_REVIEW_DIAGNOSTICS_BINDING_ID = "graph-review-diagnostics-payload" as const;

function assertBindingPresent<T>(
  bindings: Readonly<Record<string, unknown>>,
  bindingId: string,
): T {
  if (!Object.prototype.hasOwnProperty.call(bindings, bindingId)) {
    throw new Error(`Missing required projection binding: ${bindingId}`);
  }
  const value = bindings[bindingId];
  if (value === null || value === undefined) {
    throw new Error(`Required projection binding is null: ${bindingId}`);
  }
  return value as T;
}

export function readPlanContextBinding(
  bindings: Readonly<Record<string, unknown>>,
): PlanContextDescriptor {
  return assertBindingPresent<PlanContextDescriptor>(bindings, PLAN_CONTEXT_BINDING_ID);
}

export function readPlanSurfaceConfigBinding(
  bindings: Readonly<Record<string, unknown>>,
): SurfaceConfig {
  return assertBindingPresent<SurfaceConfig>(bindings, PLAN_SURFACE_CONFIG_BINDING_ID);
}

export function readGraphReviewDiagnosticsBinding(
  bindings: Readonly<Record<string, unknown>>,
): GraphReviewDiagnosticsProjectionPayload {
  return assertBindingPresent<GraphReviewDiagnosticsProjectionPayload>(
    bindings,
    GRAPH_REVIEW_DIAGNOSTICS_BINDING_ID,
  );
}

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

/**
 * Collision-free membership comparison for published projection IDs.
 * Compares full string IDs via Set equality — never delimiter-composes identity.
 */
export function sameStringSetMembership(
  left: ReadonlySet<string>,
  right: ReadonlySet<string>,
): boolean {
  if (left.size !== right.size) return false;
  for (const value of left) {
    if (!right.has(value)) return false;
  }
  return true;
}

/**
 * Return `previous` when membership is unchanged so React deps stay stable across
 * same-identity preferredSize updates that rebuild the descriptor array.
 */
export function stabilizeStringSetMembership(
  previous: ReadonlySet<string>,
  nextIds: readonly string[],
): ReadonlySet<string> {
  const next = new Set(nextIds);
  return sameStringSetMembership(previous, next) ? previous : next;
}
