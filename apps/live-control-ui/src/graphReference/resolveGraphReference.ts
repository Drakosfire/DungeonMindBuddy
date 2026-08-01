import type { WorldGraphProjection, WorldGraphProjectionNodeView } from "../api/types";
import { buildGraphObjectCardFromNodeView } from "../graphObjectCard";
import {
  GRAPH_NODE_REF_TYPE,
  type RunbookReferenceAttrs,
} from "../tiptap/references/runbookReferences";
import { adaptWorldGraphNodeView } from "../worldGraph/worldGraphNodeViewAdapter";
import type {
  GraphReferenceCorpusFallback,
  GraphReferenceProjectionState,
  GraphReferenceResolution,
} from "./types";

export function isGraphNativeReference(
  refType: string | null | undefined,
): boolean {
  return refType === GRAPH_NODE_REF_TYPE;
}

/** Corpus fallback is allowed only when World Graph is unavailable, or ready with an ordinary miss. */
export function isCorpusFallbackAllowed(
  projectionState: GraphReferenceProjectionState | null,
): boolean {
  return projectionState === "unavailable" || projectionState === "ready";
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

export function normalizeReferenceKey(value: string): string {
  return String(value || "")
    .toLowerCase()
    .replace(/[_\s]+/g, "-")
    .replace(/[^a-z0-9-]+/g, "")
    .replace(/-+/g, "-")
    .replace(/^-+|-+$/g, "");
}

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

function resolutionReference(input: {
  refType?: string | null;
  refId?: string | null;
  label?: string | null;
  ref?: RunbookReferenceAttrs | null;
}): RunbookReferenceAttrs | null {
  if (input.ref) return input.ref;
  const refType = input.refType ?? null;
  const refId = input.refId ?? null;
  if (!refType || !refId) return null;
  return {
    kind: "ref",
    refType,
    refId,
    label: input.label ?? refId,
  };
}

function appendIngestEscalationHint(message: string): string {
  if (/ingest/i.test(message)) return message;
  return `${message} Open /ingest to fix memory.`;
}

function graphNodeResolution(
  node: WorldGraphProjectionNodeView,
  locator: string,
  reference: RunbookReferenceAttrs | null,
  projectionState: GraphReferenceProjectionState | null,
): GraphReferenceResolution {
  return {
    kind: "resolved_graph",
    locator,
    reference,
    graphNodeId: node.nodeId,
    graphObject: buildGraphObjectCardFromNodeView(adaptWorldGraphNodeView(node)),
    projectionState,
    message: `Resolved graph node ${node.label}.`,
  };
}

function ambiguousGraphResolution(
  locator: string,
  reference: RunbookReferenceAttrs | null,
  matchingGraphNodeIds: string[],
  projectionState: GraphReferenceProjectionState | null,
): GraphReferenceResolution {
  return {
    kind: "ambiguous",
    locator,
    reference,
    matchingGraphNodeIds,
    projectionState,
    message: appendIngestEscalationHint(
      "Could not uniquely resolve this object from graph memory. Use /ingest to review aliases or identity.",
    ),
  };
}

function fallbackGraphResolution(
  locator: string,
  reference: RunbookReferenceAttrs | null,
  corpusFallback: GraphReferenceCorpusFallback | null | undefined,
  projectionState: GraphReferenceProjectionState | null,
): GraphReferenceResolution {
  if (!corpusFallback) {
    return {
      kind: "unresolved",
      locator,
      reference,
      projectionState,
      message: "Could not resolve this reference from graph memory or corpus indexes. Open /ingest to fix memory.",
    };
  }

  if (corpusFallback.status === "resolved") {
    return {
      kind: "resolved_corpus_fallback",
      locator,
      reference: reference ?? corpusFallback.ref,
      fallback: corpusFallback,
      projectionState,
      message: corpusFallback.message,
    };
  }

  if (corpusFallback.status === "error") {
    return {
      kind: "error",
      locator,
      reference: reference ?? corpusFallback.ref,
      projectionState,
      message: corpusFallback.message,
    };
  }

  return {
    kind: "unresolved",
    locator,
    reference: reference ?? corpusFallback.ref,
    projectionState,
    message: appendIngestEscalationHint(
      corpusFallback.message
      || "Could not resolve this reference from graph memory or corpus indexes.",
    ),
  };
}

export interface ResolveGraphReferenceInput {
  locator?: string | null;
  refType?: string | null;
  refId?: string | null;
  label?: string | null;
  ref?: RunbookReferenceAttrs | null;
  projection?: WorldGraphProjection | null;
  corpusFallback?: GraphReferenceCorpusFallback | null;
  lensSummary?: string | null;
  projectionState?: GraphReferenceProjectionState | null;
}

function exactGraphNativeMiss(
  locator: string,
  reference: RunbookReferenceAttrs | null,
  refId: string | null,
  projectionState: GraphReferenceProjectionState | null,
  lensSummary?: string | null,
): GraphReferenceResolution {
  const idLabel = refId?.trim() || "unknown";
  const lensHint = lensSummary?.trim() ? ` (${lensSummary.trim()})` : "";
  return {
    kind: "unresolved",
    locator,
    reference,
    projectionState,
    message: appendIngestEscalationHint(
      `Graph node "${idLabel}" was not found in the loaded World Graph projection${lensHint}.`,
    ),
  };
}

function graphNativeUnavailable(
  locator: string,
  reference: RunbookReferenceAttrs | null,
  projectionState: GraphReferenceProjectionState | null,
): GraphReferenceResolution {
  return {
    kind: "unresolved",
    locator,
    reference,
    projectionState,
    message: "World Graph is unavailable; graph-native reference cannot be resolved.",
  };
}

export function resolveGraphReference(
  input: ResolveGraphReferenceInput,
): GraphReferenceResolution {
  const locator = resolutionLocator(input);
  const refType = input.refType ?? input.ref?.refType ?? null;
  const refId = input.refId ?? input.ref?.refId ?? null;
  const label = input.label ?? input.ref?.label ?? null;
  const reference = resolutionReference({ ref: input.ref, refType, refId, label });
  const projectionState = input.projectionState ?? null;
  const graphNative = isGraphNativeReference(refType);

  // Projection-state gates belong in the neutral resolver so Build (or any
  // future caller) cannot bypass Plan's fail-closed rules by calling directly.
  if (projectionState === "loading") {
    return {
      kind: "unresolved",
      locator,
      reference,
      projectionState,
      message: "World Graph projection is loading; resolution deferred.",
    };
  }

  if (projectionState === "error") {
    return {
      kind: "error",
      locator,
      reference,
      projectionState,
      message: "World Graph projection failed; corpus fallback disabled.",
    };
  }

  if (projectionState === "unavailable") {
    if (graphNative) {
      return graphNativeUnavailable(locator, reference, projectionState);
    }
    return fallbackGraphResolution(locator, reference, input.corpusFallback, projectionState);
  }

  // ready (or unspecified): graph lookup, then corpus fallback after ordinary miss.
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
      return graphNodeResolution(lookup.node, locator, reference, projectionState);
    }

    if (lookup.status === "ambiguous") {
      return ambiguousGraphResolution(locator, reference, lookup.matchingNodeIds, projectionState);
    }

    if (graphNative) {
      return exactGraphNativeMiss(locator, reference, refId, projectionState, input.lensSummary);
    }
  }

  if (graphNative) {
    // Never adapt corpus fallback for graph-native chips — even when projection is absent.
    return graphNativeUnavailable(locator, reference, projectionState);
  }

  return fallbackGraphResolution(locator, reference, input.corpusFallback, projectionState);
}
