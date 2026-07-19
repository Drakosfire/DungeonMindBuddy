import type { GraphProjectionNodeView } from "../../api/types";
import {
  setGraphNodeChipRuntimeState,
  useGraphNodeChipRuntime,
  type GraphNodeChipDeltaPresentation,
  type GraphNodeChipRuntimeValue,
} from "../../graphReference";

/** @deprecated Prefer GraphNodeChipDeltaPresentation from graphReference. */
export type RecapGraphNodeDeltaPresentation = GraphNodeChipDeltaPresentation;

/** @deprecated Prefer GraphNodeChipRuntimeValue from graphReference. */
export type RecapGraphNodeRuntimeState = GraphNodeChipRuntimeValue;

/** @deprecated Prefer GraphNodeChipRuntimeProvider / setGraphNodeChipRuntimeState. */
export function setRecapGraphNodeRuntimeState(next: RecapGraphNodeRuntimeState): void {
  setGraphNodeChipRuntimeState(next);
}

export function getRecapGraphNodeRuntimeState(): RecapGraphNodeRuntimeState {
  // Transitional: TipTap views should use useGraphNodeChipRuntime.
  return {
    nodeViews: {} as Record<string, GraphProjectionNodeView>,
    activeNodeId: null,
    onSelectNode: () => undefined,
    deltaByNodeId: {},
  };
}

/** @deprecated Prefer useGraphNodeChipRuntime from graphReference. */
export function useRecapGraphNodeRuntimeState(): RecapGraphNodeRuntimeState {
  return useGraphNodeChipRuntime();
}
