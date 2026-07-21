import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
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

type RuntimeStackEntry = {
  ownerId: symbol;
  value: GraphNodeChipRuntimeValue;
};

let storeState: GraphNodeChipRuntimeValue = defaultRuntime;
/**
 * Mount-order stack keyed by stable owner id.
 * Value updates mutate the owner's slot in place so an earlier provider
 * re-render cannot leapfrog a still-mounted later sibling to the top.
 */
const runtimeStack: RuntimeStackEntry[] = [];
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

function publishTopOfStack() {
  const top =
    runtimeStack.length > 0 ? runtimeStack[runtimeStack.length - 1]!.value : defaultRuntime;
  publishRuntime(top);
}

const GraphNodeChipRuntimeContext = createContext<GraphNodeChipRuntimeValue | null>(null);

/**
 * Publishes chip runtime for TipTap NodeViews and React consumers.
 * TipTap node views subscribe via the module store (reliable across portals);
 * React children can also read context.
 *
 * Concurrent providers (Plan canvas + graph-reader tool) register by owner id.
 * Unmount restores the previous owner; value updates keep stack order.
 */
export function GraphNodeChipRuntimeProvider({
  value,
  children,
}: {
  value: GraphNodeChipRuntimeValue;
  children: ReactNode;
}) {
  const ownerId = useRef(Symbol("graph-node-chip-runtime-owner")).current;
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
    runtimeStack.push({ ownerId, value: memoized });
    publishTopOfStack();
    return () => {
      const index = runtimeStack.findIndex((entry) => entry.ownerId === ownerId);
      if (index >= 0) {
        runtimeStack.splice(index, 1);
      }
      publishTopOfStack();
    };
    // Mount/unmount only — value updates must not re-push (would reorder the stack).
    // eslint-disable-next-line react-hooks/exhaustive-deps -- ownerId is stable; memoized synced below
  }, [ownerId]);

  useEffect(() => {
    const entry = runtimeStack.find((candidate) => candidate.ownerId === ownerId);
    if (!entry) return;
    entry.value = memoized;
    publishTopOfStack();
  }, [ownerId, memoized]);

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

/** Test-only: reset module store + stack between cases. */
export function __resetGraphNodeChipRuntimeForTests(): void {
  runtimeStack.length = 0;
  publishRuntime(defaultRuntime);
}
