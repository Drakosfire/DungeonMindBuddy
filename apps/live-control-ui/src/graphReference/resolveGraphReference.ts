import type { WorldGraphProjection, WorldGraphProjectionNodeView } from "../api/types";
import { buildGraphObjectCardFromNodeView } from "../graphObjectCard";
import {
  GRAPH_NODE_REF_TYPE,
  type RunbookReferenceAttrs,
} from "../tiptap/references/runbookReferences";
import { adaptWorldGraphNodeView } from "../worldGraph/worldGraphNodeViewAdapter";
import type {
  ExactGraphReferenceScope,
  GraphReferenceCorpusFallback,
  GraphReferenceProjectionState,
  GraphReferenceResolution,
} from "./types";

export function isGraphNativeReference(
  refType: string | null | undefined,
): boolean {
  return refType === GRAPH_NODE_REF_TYPE;
}

/**
 * Recognized exact graph locators (`dmb-node:`, `graph_node:`, `node:`) bind by
 * durable node ID even when `refType` is absent — never label/alias rebind.
 */
export function isExactGraphNodeLocator(
  locator: string | null | undefined,
): boolean {
  return parseGraphNodeLocator(locator ?? "") !== null;
}

export function isGraphNativeInput(options: {
  refType?: string | null;
  locator?: string | null;
}): boolean {
  return (
    isGraphNativeReference(options.refType)
    || isExactGraphNodeLocator(options.locator)
  );
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
  | { status: "conflict"; locatorNodeId: string; refId: string }
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

/** Extract exact graph snapshot scope from a World Graph projection. Never synthesize. */
export function extractExactGraphReferenceScope(
  projection: WorldGraphProjection | null | undefined,
): ExactGraphReferenceScope | null {
  const snapshot = projection?.snapshot;
  if (!snapshot) return null;

  const worldId = String(snapshot.worldId ?? "").trim();
  const campaignId = String(snapshot.campaignId ?? "").trim();
  const scopeMode = snapshot.scopeMode;
  const revisionId = String(snapshot.revisionId ?? "").trim();
  if (
    !worldId
    || !campaignId
    || !revisionId
    || (scopeMode !== "campaign" && scopeMode !== "world")
  ) {
    return null;
  }

  return { worldId, campaignId, scopeMode, revisionId };
}

export function validateExactGraphReferenceScope(
  scope: ExactGraphReferenceScope | null | undefined,
): scope is ExactGraphReferenceScope {
  return Boolean(
    scope?.worldId?.trim()
    && scope?.campaignId?.trim()
    && (scope?.scopeMode === "campaign" || scope?.scopeMode === "world")
    && scope?.revisionId?.trim(),
  );
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

/**
 * Resolve the durable node ID for an exact-native reference.
 *
 * Rules:
 * - exact locator present + refId absent → locator ID
 * - exact locator present + matching refId → that ID
 * - exact locator present + conflicting refId → conflict (fail closed)
 * - graph-node refType without exact locator → refId (else trimmed locator)
 */
export function resolveExactGraphNativeIdentity(options: {
  locator?: string | null;
  refId?: string | null;
  refType?: string | null;
}):
  | { status: "ok"; nodeId: string }
  | { status: "conflict"; locatorNodeId: string; refId: string }
  | { status: "absent" } {
  const fromRefId = String(options.refId || "").trim() || null;
  const parsed = options.locator ? parseGraphNodeLocator(options.locator) : null;

  if (parsed) {
    if (fromRefId && fromRefId !== parsed) {
      return { status: "conflict", locatorNodeId: parsed, refId: fromRefId };
    }
    return { status: "ok", nodeId: parsed };
  }

  if (isGraphNativeReference(options.refType)) {
    if (fromRefId) return { status: "ok", nodeId: fromRefId };
    const trimmed = String(options.locator || "").trim();
    if (trimmed) return { status: "ok", nodeId: trimmed };
  }

  return { status: "absent" };
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
  // Graph-native chips and recognized exact locators bind only to durable node
  // IDs — never label/alias rebind.
  if (isGraphNativeInput({ refType: options.refType, locator: options.locator })) {
    const identity = resolveExactGraphNativeIdentity(options);
    if (identity.status === "conflict") {
      return {
        status: "conflict",
        locatorNodeId: identity.locatorNodeId,
        refId: identity.refId,
      };
    }
    if (identity.status !== "ok") return { status: "miss" };
    return lookupExactNodeId(index, identity.nodeId);
  }

  const candidates: string[] = [];

  if (options.locator) candidates.push(options.locator);
  if (options.refId) candidates.push(options.refId);

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
  graphScope: ExactGraphReferenceScope,
): GraphReferenceResolution {
  return {
    kind: "resolved_graph",
    locator,
    reference,
    graphNodeId: node.nodeId,
    graphObject: buildGraphObjectCardFromNodeView(adaptWorldGraphNodeView(node)),
    graphScope,
    projectionState,
    message: `Resolved graph node ${node.label}.`,
  };
}

function missingGraphScopeResolution(
  locator: string,
  reference: RunbookReferenceAttrs | null,
  projectionState: GraphReferenceProjectionState | null,
): GraphReferenceResolution {
  return {
    kind: "error",
    locator,
    reference,
    projectionState,
    message:
      "World Graph projection snapshot lacks exact world, campaign, or revision scope; graph resolution blocked.",
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

function conflictingGraphIdentity(
  locator: string,
  reference: RunbookReferenceAttrs | null,
  locatorNodeId: string,
  conflictingRefId: string,
  projectionState: GraphReferenceProjectionState | null,
): GraphReferenceResolution {
  return {
    kind: "error",
    locator,
    reference,
    projectionState,
    message:
      `Conflicting graph identity: locator resolves to "${locatorNodeId}" but refId is "${conflictingRefId}".`,
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
  // Prefer the caller's locator when present; synthesized locators from legacy
  // refType:refId must not accidentally become exact graph locators.
  const lookupLocator = input.locator ?? null;
  const graphNative = isGraphNativeInput({ refType, locator: lookupLocator });
  const exactIdentity = graphNative
    ? resolveExactGraphNativeIdentity({ locator: lookupLocator, refId, refType })
    : { status: "absent" as const };
  const exactNodeId = exactIdentity.status === "ok" ? exactIdentity.nodeId : null;

  // Conflicting exact identities fail closed before any projection/fallback path.
  if (exactIdentity.status === "conflict") {
    return conflictingGraphIdentity(
      locator,
      reference,
      exactIdentity.locatorNodeId,
      exactIdentity.refId,
      projectionState,
    );
  }

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

  // ready without a projection is an inconsistent dependency state — fail closed.
  // Omitted/null projectionState remains caller-unspecified: when a projection is
  // supplied, perform graph lookup; when absent, legacy may use corpus fallback
  // and graph-native stays unresolved without fallback.
  if (projectionState === "ready" && !input.projection) {
    return {
      kind: "error",
      locator,
      reference,
      projectionState,
      message:
        "World Graph projection marked ready but no projection was supplied; corpus fallback disabled.",
    };
  }

  // ready (or unspecified with a projection): graph lookup, then corpus fallback
  // after ordinary miss for legacy compatibility refs only.
  if (input.projection) {
    const index = buildWorldGraphNodeIndex(input.projection);
    const lookup = findGraphNodeInProjection(index, {
      locator: lookupLocator ?? (graphNative ? locator : null),
      refType,
      refId,
      // Graph-native refs must not rebind through display labels.
      label: graphNative ? null : label,
    });

    if (lookup.status === "found") {
      const graphScope = extractExactGraphReferenceScope(input.projection);
      if (!graphScope) {
        return missingGraphScopeResolution(locator, reference, projectionState);
      }
      return graphNodeResolution(
        lookup.node,
        locator,
        reference,
        projectionState,
        graphScope,
      );
    }

    if (lookup.status === "ambiguous") {
      return ambiguousGraphResolution(locator, reference, lookup.matchingNodeIds, projectionState);
    }

    if (lookup.status === "conflict") {
      return conflictingGraphIdentity(
        locator,
        reference,
        lookup.locatorNodeId,
        lookup.refId,
        projectionState,
      );
    }

    if (graphNative) {
      return exactGraphNativeMiss(
        locator,
        reference,
        exactNodeId ?? refId,
        projectionState,
        input.lensSummary,
      );
    }
  }

  if (graphNative) {
    // Never adapt corpus fallback for graph-native chips — even when projection is absent.
    return graphNativeUnavailable(locator, reference, projectionState);
  }

  return fallbackGraphResolution(locator, reference, input.corpusFallback, projectionState);
}
