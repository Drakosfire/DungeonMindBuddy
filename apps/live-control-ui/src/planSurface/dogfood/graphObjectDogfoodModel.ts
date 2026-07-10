import type { GraphObjectCardViewModel } from "../../graphObjectCard";
import { hasPlanSourceOrEvidence } from "../reference/buildPlanGraphObjectActions";

export type GraphObjectDogfoodUsefulness =
  | "useful"
  | "thin"
  | "confusing"
  | "wrong"
  | "unknown";

export interface GraphObjectDogfoodState {
  addedNodeIds: string[];
  viewedNodeIds: string[];
  removedNodeIds: string[];
  notesByNodeId: Record<string, string>;
  usefulnessByNodeId: Record<string, GraphObjectDogfoodUsefulness>;
}

export type GraphObjectCardCoverageFlag =
  | "summary"
  | "aliases"
  | "relationships"
  | "evidence"
  | "source-anchor"
  | "actions"
  | "statblock-tool"
  | "ingest-path";

export interface GraphObjectCardCoverage {
  flags: GraphObjectCardCoverageFlag[];
  missing: GraphObjectCardCoverageFlag[];
}

const ALL_COVERAGE_FLAGS: GraphObjectCardCoverageFlag[] = [
  "summary",
  "aliases",
  "relationships",
  "evidence",
  "source-anchor",
  "actions",
  "statblock-tool",
  "ingest-path",
];

export const GRAPH_OBJECT_DOGFOOD_USEFULNESS_OPTIONS: Array<{
  value: GraphObjectDogfoodUsefulness;
  label: string;
}> = [
  { value: "unknown", label: "Unknown" },
  { value: "useful", label: "Useful" },
  { value: "thin", label: "Thin" },
  { value: "confusing", label: "Confusing" },
  { value: "wrong", label: "Wrong" },
];

export const COVERAGE_FLAG_LABELS: Record<GraphObjectCardCoverageFlag, string> = {
  summary: "Has summary",
  aliases: "Has aliases",
  relationships: "Has relationships",
  evidence: "Has evidence",
  "source-anchor": "Has source anchor",
  actions: "Has actions",
  "statblock-tool": "Has statblock/tool affordance",
  "ingest-path": "Has /ingest path",
};

export function createEmptyGraphObjectDogfoodState(): GraphObjectDogfoodState {
  return {
    addedNodeIds: [],
    viewedNodeIds: [],
    removedNodeIds: [],
    notesByNodeId: {},
    usefulnessByNodeId: {},
  };
}

export function addNodeToDogfoodList(
  state: GraphObjectDogfoodState,
  nodeId: string,
): GraphObjectDogfoodState {
  const id = String(nodeId || "").trim();
  if (!id) return state;
  if (state.addedNodeIds.includes(id)) return state;

  return {
    ...state,
    addedNodeIds: [...state.addedNodeIds, id],
    removedNodeIds: state.removedNodeIds.filter((entry) => entry !== id),
  };
}

export function removeNodeFromDogfoodList(
  state: GraphObjectDogfoodState,
  nodeId: string,
): GraphObjectDogfoodState {
  const id = String(nodeId || "").trim();
  if (!id) return state;
  if (!state.addedNodeIds.includes(id)) return state;

  return {
    ...state,
    addedNodeIds: state.addedNodeIds.filter((entry) => entry !== id),
    removedNodeIds: state.removedNodeIds.includes(id)
      ? state.removedNodeIds
      : [...state.removedNodeIds, id],
  };
}

export function markNodeViewed(
  state: GraphObjectDogfoodState,
  nodeId: string,
): GraphObjectDogfoodState {
  const id = String(nodeId || "").trim();
  if (!id || state.viewedNodeIds.includes(id)) return state;
  return {
    ...state,
    viewedNodeIds: [...state.viewedNodeIds, id],
  };
}

export function setNodeUsefulness(
  state: GraphObjectDogfoodState,
  nodeId: string,
  usefulness: GraphObjectDogfoodUsefulness,
): GraphObjectDogfoodState {
  const id = String(nodeId || "").trim();
  if (!id) return state;
  return {
    ...state,
    usefulnessByNodeId: {
      ...state.usefulnessByNodeId,
      [id]: usefulness,
    },
  };
}

export function setNodeNotes(
  state: GraphObjectDogfoodState,
  nodeId: string,
  notes: string,
): GraphObjectDogfoodState {
  const id = String(nodeId || "").trim();
  if (!id) return state;
  return {
    ...state,
    notesByNodeId: {
      ...state.notesByNodeId,
      [id]: notes,
    },
  };
}

/**
 * Dogfood-only coverage indicators for a card view model.
 * Not a product quality score — surfaces thin/missing fields for operator judgment.
 */
export function computeGraphObjectCardCoverage(
  model: GraphObjectCardViewModel | null | undefined,
): GraphObjectCardCoverage {
  if (!model) {
    return { flags: [], missing: [...ALL_COVERAGE_FLAGS] };
  }

  const present = new Set<GraphObjectCardCoverageFlag>();

  if (String(model.summary || model.gameSummary || "").trim()) {
    present.add("summary");
  }
  if ((model.aliases?.length ?? 0) > 0) {
    present.add("aliases");
  }
  if ((model.relationships?.length ?? 0) > 0) {
    present.add("relationships");
  }
  if (hasPlanSourceOrEvidence(model)) {
    present.add("evidence");
  }
  if (String(model.details?.sourceAnchorText || "").trim()) {
    present.add("source-anchor");
  }

  const actions = model.actions ?? [];
  if (actions.length > 0) {
    present.add("actions");
  }
  if (actions.some((action) => action.kind === "open-statblock" || action.kind === "open-roll-table")) {
    present.add("statblock-tool");
  }
  if (actions.some((action) => action.kind === "open-ingest")) {
    present.add("ingest-path");
  }

  const flags = ALL_COVERAGE_FLAGS.filter((flag) => present.has(flag));
  const missing = ALL_COVERAGE_FLAGS.filter((flag) => !present.has(flag));
  return { flags, missing };
}

export function isThinCardCoverage(coverage: GraphObjectCardCoverage): boolean {
  return (
    coverage.missing.includes("summary") ||
    coverage.missing.includes("relationships") ||
    coverage.missing.includes("evidence")
  );
}
