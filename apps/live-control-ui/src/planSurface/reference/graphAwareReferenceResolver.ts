import type { ReferenceResolution } from "./referenceResolver";
import {
  resolveGraphReference,
  type ResolveGraphReferenceInput,
} from "../../graphReference/resolveGraphReference";
import type {
  GraphReferenceCorpusFallback,
  GraphReferenceProjectionState,
  GraphReferenceResolution,
} from "../../graphReference/types";

export {
  buildWorldGraphNodeIndex,
  findGraphNodeInProjection,
  isCorpusFallbackAllowed,
  isExactGraphNodeLocator,
  isGraphNativeInput,
  isGraphNativeReference,
  parseGraphNodeLocator,
  resolveGraphReference,
  type ResolveGraphReferenceInput,
  type WorldGraphNodeIndex,
} from "../../graphReference/resolveGraphReference";

export type PlanGraphProjectionState = GraphReferenceProjectionState;
export type PlanReferenceResolution = GraphReferenceResolution;

export function mapReferenceResolutionToCorpusFallback(
  resolution: ReferenceResolution,
): GraphReferenceCorpusFallback {
  return {
    status: resolution.status,
    ref: resolution.ref,
    message: resolution.message,
    source: resolution.source,
    item: resolution.item,
    sourcePath: resolution.sourcePath,
  };
}

export interface ResolvePlanReferenceFromGraphProjectionInput
  extends Omit<ResolveGraphReferenceInput, "corpusFallback"> {
  /** Precomputed corpus-index resolution from `resolveReference()` — not fetched here. */
  fallbackResolution?: ReferenceResolution | null;
}

export function resolvePlanReferenceFromGraphProjection(
  input: ResolvePlanReferenceFromGraphProjectionInput,
): GraphReferenceResolution {
  return resolveGraphReference({
    ...input,
    corpusFallback: input.fallbackResolution
      ? mapReferenceResolutionToCorpusFallback(input.fallbackResolution)
      : null,
  });
}
