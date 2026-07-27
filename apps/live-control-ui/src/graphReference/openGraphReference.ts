import type { RunbookReferenceAttrs } from "../tiptap/references/runbookReferences";
import type {
  PlanGraphProjectionState,
  PlanReferenceResolution,
} from "../planSurface/reference/graphAwareReferenceResolver";
import { mapPlanResolutionToGraphReferenceResolution } from "./mapPlanResolutionToGraphReferenceResolution";

export interface OpenGraphReferenceProjectionApi {
  openPlanReferenceResolution: (
    resolution: PlanReferenceResolution,
    projectionState?: PlanGraphProjectionState | null,
  ) => void;
  openContentFromChip: (
    ref: RunbookReferenceAttrs,
    resolution: PlanReferenceResolution,
    glanceOnly?: boolean,
    projectionState?: PlanGraphProjectionState | null,
  ) => void;
}

function runbookRefFromPlanResolution(
  resolution: PlanReferenceResolution,
): RunbookReferenceAttrs {
  return {
    kind: "ref",
    refType: resolution.refType ?? "npc",
    refId: resolution.refId ?? resolution.locator,
    label:
      resolution.graphObject?.label
      ?? resolution.fallback?.ref.label
      ?? resolution.locator,
  };
}

/**
 * Open a graph reference in the projection host.
 *
 * Resolved graph nodes and corpus fallbacks use full reference projection.
 * Ambiguous and unresolved states open a compact content glance with truthful
 * resolution — never auto-selecting the first ambiguous candidate.
 */
export function openGraphReference(
  projectionApi: OpenGraphReferenceProjectionApi,
  input: {
    planResolution: PlanReferenceResolution;
    projectionState?: PlanGraphProjectionState | null;
    ref?: RunbookReferenceAttrs;
  },
): void {
  const graphResolution = mapPlanResolutionToGraphReferenceResolution(input.planResolution);
  const projectionState =
    input.projectionState ?? input.planResolution.graphProjectionState ?? null;

  if (
    graphResolution.kind === "resolved_graph"
    || graphResolution.kind === "resolved_corpus_fallback"
  ) {
    projectionApi.openPlanReferenceResolution(input.planResolution, projectionState);
    return;
  }

  const ref = input.ref ?? runbookRefFromPlanResolution(input.planResolution);
  projectionApi.openContentFromChip(ref, input.planResolution, true, projectionState);
}
