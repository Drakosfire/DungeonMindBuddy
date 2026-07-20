import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useSyncExternalStore,
  type ReactNode,
} from "react";

import type { GraphNodeChipRuntimeValue } from "./types";

const defaultRuntime: GraphNodeChipRuntimeValue = {
  nodeViews: {},
  activeNodeId: null,
  onSelectNode: () => undefined,
  deltaByNodeId: {},
};

let storeState: GraphNodeChipRuntimeValue = defaultRuntime;
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

function publishRuntime(next: GraphNodeChipRuntimeValue) {
  storeState = {
    nodeViews: next.nodeViews,
    activeNodeId: next.activeNodeId,
    onSelectNode: next.onSelectNode,
    deltaByNodeId: next.deltaByNodeId ?? {},
  };
  emit();
}

const GraphNodeChipRuntimeContext = createContext<GraphNodeChipRuntimeValue | null>(null);

/**
 * Publishes chip runtime for TipTap NodeViews and React consumers.
 * TipTap node views subscribe via the module store (reliable across portals);
 * React children can also read context.
 */
export function GraphNodeChipRuntimeProvider({
  value,
  children,
}: {
  value: GraphNodeChipRuntimeValue;
  children: ReactNode;
}) {
  const memoized = useMemo(
    () => ({
      nodeViews: value.nodeViews,
      activeNodeId: value.activeNodeId,
      onSelectNode: value.onSelectNode,
      deltaByNodeId: value.deltaByNodeId ?? {},
    }),
    [value.activeNodeId, value.deltaByNodeId, value.nodeViews, value.onSelectNode],
  );

  useEffect(() => {
    publishRuntime(memoized);
    return () => {
      publishRuntime(defaultRuntime);
    };
  }, [memoized]);

  return (
    <GraphNodeChipRuntimeContext.Provider value={memoized}>
      {children}
    </GraphNodeChipRuntimeContext.Provider>
  );
}

export function useGraphNodeChipRuntime(): GraphNodeChipRuntimeValue {
  const fromContext = useContext(GraphNodeChipRuntimeContext);
  const fromStore = useSyncExternalStore(subscribe, () => storeState, () => defaultRuntime);
  return fromContext ?? fromStore;
}

/** @deprecated Prefer GraphNodeChipRuntimeProvider; kept for transitional call sites. */
export function setGraphNodeChipRuntimeState(next: GraphNodeChipRuntimeValue): void {
  publishRuntime(next);
}
