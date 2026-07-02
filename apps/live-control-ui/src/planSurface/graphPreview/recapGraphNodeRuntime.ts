import { useSyncExternalStore } from "react";

import type { GraphProjectionNodeView } from "../../api/types";

export interface RecapGraphNodeDeltaPresentation {
  status: "matched" | "live_only" | "comparator_uncertain" | "unclassified";
  label: string;
  summary?: string | null;
}

export interface RecapGraphNodeRuntimeState {
  nodeViews: Record<string, GraphProjectionNodeView>;
  activeNodeId: string | null;
  onSelectNode: (nodeId: string) => void;
  deltaByNodeId?: Record<string, RecapGraphNodeDeltaPresentation>;
}

const defaultState: RecapGraphNodeRuntimeState = {
  nodeViews: {},
  activeNodeId: null,
  onSelectNode: () => undefined,
  deltaByNodeId: {},
};

let runtimeState: RecapGraphNodeRuntimeState = defaultState;
const listeners = new Set<() => void>();

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function emit() {
  for (const listener of listeners) {
    listener();
  }
}

export function setRecapGraphNodeRuntimeState(next: RecapGraphNodeRuntimeState): void {
  runtimeState = next;
  emit();
}

export function getRecapGraphNodeRuntimeState(): RecapGraphNodeRuntimeState {
  return runtimeState;
}

export function useRecapGraphNodeRuntimeState(): RecapGraphNodeRuntimeState {
  return useSyncExternalStore(subscribe, getRecapGraphNodeRuntimeState, getRecapGraphNodeRuntimeState);
}
