import type { WorldGraphProjection, WorldGraphProjectionNodeView } from "../../api/types";
import { buildGraphObjectCardFromNodeView } from "../../graphObjectCard";
import type { GraphObjectCardViewModel } from "../../graphObjectCard";
import {
  GRAPH_NODE_REF_TYPE,
  type RunbookReferenceAttrs,
} from "../../tiptap/references/runbookReferences";
import { normalizeReferenceKey } from "./referenceResolver";
import type { ReferenceResolution } from "./referenceResolver";
import { adaptWorldGraphNodeForPlanCard } from "./worldGraphProjectionAdapter";

export function isGraphNativeReference(
  refType: string | null | undefined,
): boolean {
  return refType === GRAPH_NODE_REF_TYPE;
}

export type PlanReferenceResolutionKind =
  | "graph-node"
  | "corpus-index"
  | "unresolved"
  | "error";

export type PlanGraphProjectionState =
  | "loading"
  | "ready"
  | "unavailable"
  | "error";

/** Corpus fallback is allowed only when World Graph is unavailable, or ready with an ordinary miss. */
export function isCorpusFallbackAllowed(
  projectionState: PlanGraphProjectionState | null,
): boolean {
  return projectionState === "unavailable" || projectionState === "ready";
}

export interface PlanReferenceResolution {
  kind: PlanReferenceResolutionKind;
  locator: string;
  refType?: string | null;
  refId?: string | null;
  graphObject?: GraphObjectCardViewModel | null;
  graphNodeId?: string | null;
  /** Populated when label/alias lookup matched more than one graph node. */
  ambiguousNodeIds?: string[];
  fallback?: ReferenceResolution | null;
  source: "world-graph" | "corpus-index" | "unresolved" | "error";
  message?: string | null;
  /** World Graph projection availability at resolve time. */
  graphProjectionState?: PlanGraphProjectionState | null;
}

export interface WorldGraphNodeIndex {
  byNodeId: Map<string, WorldGraphProjectionNodeView>;
  /** Label/alias keys map to every node that claims that key; unique-only lookups use length === 1. */
  byLabelKey: Map<string, WorldGraphProjectionNodeView[]>;
}

export type GraphNodeProjectionLookup =
  | { status: "found"; node: WorldGraphProjectionNodeView }
  | { status: "ambiguous"; matchingNodeIds: string[] }
  | { status: "miss" };

const GRAPH_NODE_LOCATOR_PATTERNS = [
  /^dmb-node:(.+)$/i,
  /^graph_node:(.+)$/i,
  /^node:(.+)$/i,
] as const;

export function parseGraphNodeLocator(locator: string): string | null {
  const trimmed = String(locator || "").trim();
  if (!trimmed) return null;

  for (const pattern of GRAPH_NODE_LOCATOR_PATTERNS) {
    const match = trimmed.match(pattern);
    if (match?.[1]) {
      return match[1].trim();
    }
  }

  return null;
}

export function buildWorldGraphNodeIndex(projection: WorldGraphProjection): WorldGraphNodeIndex {
  const byNodeId = new Map<string, WorldGraphProjectionNodeView>();
  const byLabelKey = new Map<string, WorldGraphProjectionNodeView[]>();

  const registerLabelKey = (value: string, node: WorldGraphProjectionNodeView) => {
    const key = normalizeReferenceKey(value);
    if (!key) return;

    const existing = byLabelKey.get(key) ?? [];
    if (existing.some((entry) => entry.nodeId === node.nodeId)) return;

    byLabelKey.set(key, [...existing, node]);
  };

  for (const node of projection.nodes) {
    byNodeId.set(node.nodeId, node);
    registerLabelKey(node.nodeId, node);
    registerLabelKey(node.label, node);
    for (const alias of node.aliases ?? []) {
      registerLabelKey(alias, node);
    }
  }

  return { byNodeId, byLabelKey };
}

function uniqueLabelKeyMatch(
  index: WorldGraphNodeIndex,
  key: string,
): GraphNodeProjectionLookup {
  const normalized = normalizeReferenceKey(key);
  if (!normalized) return { status: "miss" };

  const matches = index.byLabelKey.get(normalized) ?? [];
  if (matches.length === 1) {
    return { status: "found", node: matches[0] };
  }
  if (matches.length > 1) {
    return {
      status: "ambiguous",
      matchingNodeIds: matches.map((node) => node.nodeId),
    };
  }
  return { status: "miss" };
}

function lookupNodeById(index: WorldGraphNodeIndex, nodeId: string): GraphNodeProjectionLookup {
  const trimmed = String(nodeId || "").trim();
  if (!trimmed) return { status: "miss" };

  const direct = index.byNodeId.get(trimmed);
  if (direct) return { status: "found", node: direct };

  return uniqueLabelKeyMatch(index, trimmed);
}

function lookupExactNodeId(
  index: WorldGraphNodeIndex,
  nodeId: string,
): GraphNodeProjectionLookup {
  const trimmed = String(nodeId || "").trim();
  if (!trimmed) return { status: "miss" };
  const direct = index.byNodeId.get(trimmed);
  return direct ? { status: "found", node: direct } : { status: "miss" };
}

function lookupNodeByLabel(index: WorldGraphNodeIndex, label: string): GraphNodeProjectionLookup {
  return uniqueLabelKeyMatch(index, label);
}

function graphNativeNodeId(options: {
  locator?: string | null;
  refId?: string | null;
}): string | null {
  const fromRefId = String(options.refId || "").trim();
  if (fromRefId) return fromRefId;
  if (!options.locator) return null;
  const parsed = parseGraphNodeLocator(options.locator);
  if (parsed) return parsed;
  const trimmed = String(options.locator).trim();
  return trimmed || null;
}

export function findGraphNodeInProjection(
  index: WorldGraphNodeIndex,
  options: {
    locator?: string | null;
    refType?: string | null;
    refId?: string | null;
    label?: string | null;
  },
): GraphNodeProjectionLookup {
  // Graph-native chips bind only to durable node IDs — never label/alias rebind.
  if (isGraphNativeReference(options.refType)) {
    const nodeId = graphNativeNodeId(options);
    if (!nodeId) return { status: "miss" };
    return lookupExactNodeId(index, nodeId);
  }

  const candidates: string[] = [];

  const parsedLocator = options.locator ? parseGraphNodeLocator(options.locator) : null;
  if (parsedLocator) candidates.push(parsedLocator);
  if (options.locator && !parsedLocator) candidates.push(options.locator);

  if (options.refId) {
    candidates.push(options.refId);
  }

  for (const candidate of candidates) {
    const lookup = lookupNodeById(index, candidate);
    if (lookup.status === "found" || lookup.status === "ambiguous") {
      return lookup;
    }
  }

  if (options.label) {
    return lookupNodeByLabel(index, options.label);
  }

  return { status: "miss" };
}

function resolutionLocator(input: {
  locator?: string | null;
  refType?: string | null;
  refId?: string | null;
  label?: string | null;
  ref?: RunbookReferenceAttrs | null;
}): string {
  if (input.locator) return input.locator;
  if (input.ref) {
    return `#dmb-${input.ref.kind}:${input.ref.refType}:${input.ref.refId}`;
  }
  if (input.refType && input.refId) {
    return `${input.refType}:${input.refId}`;
  }
  return input.label ?? "";
}

function graphNodeResolution(
  node: WorldGraphProjectionNodeView,
  locator: string,
  refType?: string | null,
  refId?: string | null,
): PlanReferenceResolution {
  return {
    kind: "graph-node",
    locator,
    refType: refType ?? null,
    refId: refId ?? null,
    graphObject: buildGraphObjectCardFromNodeView(adaptWorldGraphNodeForPlanCard(node)),
    graphNodeId: node.nodeId,
    fallback: null,
    source: "world-graph",
    message: `Resolved graph node ${node.label}.`,
  };
}

function ambiguousGraphResolution(
  locator: string,
  refType: string | null | undefined,
  refId: string | null | undefined,
  matchingNodeIds: string[],
): PlanReferenceResolution {
  return {
    kind: "unresolved",
    locator,
    refType: refType ?? null,
    refId: refId ?? null,
    graphObject: null,
    graphNodeId: null,
    ambiguousNodeIds: matchingNodeIds,
    fallback: null,
    source: "unresolved",
    message: appendIngestEscalationHint(
      "Could not uniquely resolve this object from graph memory. Use /ingest to review aliases or identity.",
    ),
  };
}

/**
 * Adapts a precomputed corpus-index `ReferenceResolution` into the Plan ladder.
 *
 * This seam does not call `resolveReference()` itself — the caller must fetch
 * corpus indexes separately and pass `fallbackResolution` when wiring Plan chips.
 */
function fallbackPlanResolution(
  locator: string,
  refType: string | null | undefined,
  refId: string | null | undefined,
  fallbackResolution: ReferenceResolution | null | undefined,
): PlanReferenceResolution {
  if (!fallbackResolution) {
    return {
      kind: "unresolved",
      locator,
      refType: refType ?? null,
      refId: refId ?? null,
      graphObject: null,
      graphNodeId: null,
      fallback: null,
      source: "unresolved",
      message: "Could not resolve this reference from graph memory or corpus indexes. Open /ingest to fix memory.",
    };
  }

  if (fallbackResolution.status === "resolved") {
    return {
      kind: "corpus-index",
      locator,
      refType: refType ?? fallbackResolution.ref.refType ?? null,
      refId: refId ?? fallbackResolution.ref.refId ?? null,
      graphObject: null,
      graphNodeId: null,
      fallback: fallbackResolution,
      source: "corpus-index",
      message: fallbackResolution.message,
    };
  }

  if (fallbackResolution.status === "error") {
    return {
      kind: "error",
      locator,
      refType: refType ?? fallbackResolution.ref.refType ?? null,
      refId: refId ?? fallbackResolution.ref.refId ?? null,
      graphObject: null,
      graphNodeId: null,
      fallback: fallbackResolution,
      source: "error",
      message: fallbackResolution.message,
    };
  }

  return {
    kind: "unresolved",
    locator,
    refType: refType ?? fallbackResolution.ref.refType ?? null,
    refId: refId ?? fallbackResolution.ref.refId ?? null,
    graphObject: null,
    graphNodeId: null,
    fallback: fallbackResolution,
    source: "unresolved",
    message: appendIngestEscalationHint(
      fallbackResolution.message
      || "Could not resolve this reference from graph memory or corpus indexes.",
    ),
  };
}

function appendIngestEscalationHint(message: string): string {
  if (/ingest/i.test(message)) return message;
  return `${message} Open /ingest to fix memory.`;
}

export interface ResolvePlanReferenceFromGraphProjectionInput {
  locator?: string | null;
  refType?: string | null;
  refId?: string | null;
  label?: string | null;
  ref?: RunbookReferenceAttrs | null;
  projection?: WorldGraphProjection | null;
  /** Precomputed corpus-index resolution from `resolveReference()` — not fetched here. */
  fallbackResolution?: ReferenceResolution | null;
}

function exactGraphNativeMiss(
  locator: string,
  refType: string | null,
  refId: string | null,
): PlanReferenceResolution {
  const idLabel = refId?.trim() || "unknown";
  return {
    kind: "unresolved",
    locator,
    refType,
    refId,
    graphObject: null,
    graphNodeId: null,
    fallback: null,
    source: "unresolved",
    message: appendIngestEscalationHint(
      `Graph node "${idLabel}" was not found in the loaded World Graph projection.`,
    ),
  };
}

function graphNativeUnavailable(
  locator: string,
  refType: string | null,
  refId: string | null,
): PlanReferenceResolution {
  return {
    kind: "unresolved",
    locator,
    refType,
    refId,
    graphObject: null,
    graphNodeId: null,
    fallback: null,
    source: "unresolved",
    message: "World Graph is unavailable; graph-native reference cannot be resolved.",
  };
}

export function resolvePlanReferenceFromGraphProjection(
  input: ResolvePlanReferenceFromGraphProjectionInput,
): PlanReferenceResolution {
  const locator = resolutionLocator(input);
  const refType = input.refType ?? input.ref?.refType ?? null;
  const refId = input.refId ?? input.ref?.refId ?? null;
  const label = input.label ?? input.ref?.label ?? null;
  const graphNative = isGraphNativeReference(refType);

  if (input.projection) {
    const index = buildWorldGraphNodeIndex(input.projection);
    const lookup = findGraphNodeInProjection(index, {
      locator: input.locator ?? locator,
      refType,
      refId,
      // Graph-native refs must not rebind through display labels.
      label: graphNative ? null : label,
    });

    if (lookup.status === "found") {
      return graphNodeResolution(lookup.node, locator, refType, refId);
    }

    if (lookup.status === "ambiguous") {
      return ambiguousGraphResolution(locator, refType, refId, lookup.matchingNodeIds);
    }

    if (graphNative) {
      return exactGraphNativeMiss(locator, refType, refId);
    }
  }

  if (graphNative) {
    // Never adapt corpus fallback for graph-native chips — even when projection is absent.
    return graphNativeUnavailable(locator, refType, refId);
  }

  return fallbackPlanResolution(locator, refType, refId, input.fallbackResolution);
}
