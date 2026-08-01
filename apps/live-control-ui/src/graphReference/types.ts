import type { GraphProjectionNodeView, RecapGraphChip } from "../api/types";
import type { GraphObjectCardViewModel } from "../graphObjectCard";
import type { RunbookReferenceAttrs } from "../tiptap/references/runbookReferences";

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

export type GraphReferenceProjectionState =
  | "loading"
  | "ready"
  | "unavailable"
  | "error";

/** Structurally mirrors corpus ReferenceResolution without importing plan adapters. */
export interface GraphReferenceCorpusFallback {
  status: "resolved" | "unresolved" | "error";
  ref: RunbookReferenceAttrs;
  message: string;
  source?: string;
  item?: unknown;
  sourcePath?: string;
}

export type GraphReferenceResolution =
  | {
      kind: "resolved_graph";
      locator: string;
      reference: RunbookReferenceAttrs | null;
      graphNodeId: string;
      graphObject: GraphObjectCardViewModel;
      projectionState: GraphReferenceProjectionState | null;
      message?: string | null;
    }
  | {
      kind: "resolved_corpus_fallback";
      locator: string;
      reference: RunbookReferenceAttrs | null;
      fallback: GraphReferenceCorpusFallback;
      projectionState: GraphReferenceProjectionState | null;
      message?: string | null;
    }
  | {
      kind: "ambiguous";
      locator: string;
      reference: RunbookReferenceAttrs | null;
      matchingGraphNodeIds: string[];
      projectionState: GraphReferenceProjectionState | null;
      message: string;
    }
  | {
      kind: "unresolved";
      locator: string;
      reference: RunbookReferenceAttrs | null;
      projectionState: GraphReferenceProjectionState | null;
      message: string;
    }
  | {
      kind: "error";
      locator: string;
      reference: RunbookReferenceAttrs | null;
      projectionState: GraphReferenceProjectionState | null;
      message: string;
    };

export interface GraphReferenceProjectionBinding {
  resolverState: GraphReferenceProjectionState | null;
  resolveRelationship(
    relationship: import("../graphObjectCard").GraphObjectRelationshipViewModel,
  ): Promise<GraphReferenceResolution>;
  openResolvedReference(
    resolution: GraphReferenceResolution,
    projectionState?: GraphReferenceProjectionState | null,
  ): void;
  openTool(toolId: string): void;
}

export interface GraphReferenceSearchItem {
  nodeId: string;
  label: string;
  kind: string;
  role: string | null;
  summary: string | null;
  aliases: string[];
  scopeLabel: string;
  reference: RunbookReferenceAttrs;
  nodeView: GraphProjectionNodeView;
}

export interface OpenGraphReferenceArgs {
  reference?: RunbookReferenceAttrs | null;
  resolution: GraphReferenceResolution;
  projectionState?: GraphReferenceProjectionState | null;
  glanceOnly?: boolean;
}
