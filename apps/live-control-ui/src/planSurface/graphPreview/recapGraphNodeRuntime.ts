import { createContext, createElement, useContext, type ReactNode } from "react";

import type { GraphProjectionNodeView } from "../../api/types";

export interface RecapGraphNodeDeltaPresentation {
  // Left as a plain string (rather than importing the graph-review-workbench
  // delta status union) so this shared runtime doesn't take a dependency on a
  // specific feature's vocabulary. Callers own the status taxonomy; this
  // module just carries it through to presentation.
  status: string;
  label: string;
  summary?: string | null;
  counterpartNodeId?: string | null;
}

export interface RecapGraphNodeRuntimeState {
  nodeViews: Record<string, GraphProjectionNodeView>;
  activeNodeId: string | null;
  onSelectNode: (nodeId: string) => void;
  deltaByNodeId?: Record<string, RecapGraphNodeDeltaPresentation>;
  highlightedNodeId?: string | null;
  onHoverNode?: (nodeId: string | null) => void;
}

const defaultState: RecapGraphNodeRuntimeState = {
  nodeViews: {},
  activeNodeId: null,
  onSelectNode: () => undefined,
  deltaByNodeId: {},
  highlightedNodeId: null,
  onHoverNode: () => undefined,
};

// Scoped per-reader context. This used to be a module-level singleton store,
// which silently clobbered state across multiple GraphProjectionReader
// instances mounted at once (e.g. the gold + live two-lane review): whichever
// instance's effect ran last would "win" for every rendered node token, gold
// and live alike. A Context provided by each GraphProjectionReader instance
// keeps every reader's node views/active selection/delta presentation
// isolated to its own subtree, while still letting @tiptap/react's
// ReactNodeViewRenderer portal-rendered node views read it (React Context
// propagates through portals along the component tree, not the DOM tree).
const RecapGraphNodeRuntimeContext = createContext<RecapGraphNodeRuntimeState>(defaultState);

export function RecapGraphNodeRuntimeProvider({
  value,
  children,
}: {
  value: RecapGraphNodeRuntimeState;
  children: ReactNode;
}) {
  return createElement(RecapGraphNodeRuntimeContext.Provider, { value }, children);
}

export function useRecapGraphNodeRuntimeState(): RecapGraphNodeRuntimeState {
  return useContext(RecapGraphNodeRuntimeContext);
}
