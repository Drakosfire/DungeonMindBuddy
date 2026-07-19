import type { GraphProjectionNodeView, RecapGraphChip } from "../api/types";

/** Surface-agnostic glance model for CSS hover cards on graph chips. */
export interface GraphNodeGlanceThreadHint {
  nodeId: string;
  label: string;
  edgeLabel: string;
  anchoredToFocusSession: boolean;
  rankReason?: string;
}

export interface GraphNodeGlancePresentation {
  nodeId: string;
  label: string;
  kind: string;
  role: string;
  summary: string | null;
  whyNow: string | null;
  knownBefore: string | null;
  planningChips: RecapGraphChip[];
  threadHints: GraphNodeGlanceThreadHint[];
}

export interface GraphNodeChipDeltaPresentation {
  status: "matched" | "live_only" | "comparator_uncertain" | "unclassified";
  label: string;
  summary?: string | null;
}

export interface GraphNodeChipRuntimeValue {
  nodeViews: Record<string, GraphProjectionNodeView>;
  activeNodeId: string | null;
  onSelectNode: (nodeId: string) => void;
  deltaByNodeId?: Record<string, GraphNodeChipDeltaPresentation>;
}
