import type { UnionSupergraphProjectionResponse, GraphProjectionNodeView } from "../../api/types";
import { buildGraphObjectCardFromNodeView } from "../../graphObjectCard";
import type { GraphObjectCardViewModel } from "../../graphObjectCard";
import type { RunbookReferenceAttrs } from "../../tiptap/references/runbookReferences";
import { normalizeReferenceKey } from "./referenceResolver";
import type { ReferenceResolution } from "./referenceResolver";

export type PlanReferenceResolutionKind =
  | "graph-node"
  | "corpus-index"
  | "unresolved"
  | "error";

export interface PlanReferenceResolution {
  kind: PlanReferenceResolutionKind;
  locator: string;
  refType?: string | null;
  refId?: string | null;
  graphObject?: GraphObjectCardViewModel | null;
  graphNodeId?: string | null;
  fallback?: ReferenceResolution | null;
  source: "union-supergraph" | "corpus-index" | "unresolved" | "error";
  message?: string | null;
}

export interface UnionSupergraphNodeIndex {
  byNodeId: Map<string, GraphProjectionNodeView>;
  byLabelKey: Map<string, GraphProjectionNodeView>;
}

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

export function buildUnionSupergraphNodeIndex(
  projection: UnionSupergraphProjectionResponse,
): UnionSupergraphNodeIndex {
  const byNodeId = new Map<string, GraphProjectionNodeView>();
  const byLabelKey = new Map<string, GraphProjectionNodeView>();

  const registerLabelKey = (value: string, node: GraphProjectionNodeView) => {
    const key = normalizeReferenceKey(value);
    if (!key || byLabelKey.has(key)) return;
    byLabelKey.set(key, node);
  };

  for (const node of Object.values(projection.node_views)) {
    byNodeId.set(node.node_id, node);
    registerLabelKey(node.node_id, node);
    registerLabelKey(node.label, node);
    for (const alias of node.aliases ?? []) {
      registerLabelKey(alias, node);
    }
  }

  return { byNodeId, byLabelKey };
}

function lookupNodeById(index: UnionSupergraphNodeIndex, nodeId: string): GraphProjectionNodeView | null {
  const trimmed = String(nodeId || "").trim();
  if (!trimmed) return null;

  const direct = index.byNodeId.get(trimmed);
  if (direct) return direct;

  const normalized = normalizeReferenceKey(trimmed);
  if (!normalized) return null;

  return index.byLabelKey.get(normalized) ?? null;
}

function lookupNodeByLabel(index: UnionSupergraphNodeIndex, label: string): GraphProjectionNodeView | null {
  const normalized = normalizeReferenceKey(label);
  if (!normalized) return null;
  return index.byLabelKey.get(normalized) ?? null;
}

export function findGraphNodeInProjection(
  index: UnionSupergraphNodeIndex,
  options: {
    locator?: string | null;
    refType?: string | null;
    refId?: string | null;
    label?: string | null;
  },
): GraphProjectionNodeView | null {
  const candidates: string[] = [];

  const parsedLocator = options.locator ? parseGraphNodeLocator(options.locator) : null;
  if (parsedLocator) candidates.push(parsedLocator);
  if (options.locator && !parsedLocator) candidates.push(options.locator);

  if (options.refId) {
    candidates.push(options.refId);
  }

  for (const candidate of candidates) {
    const node = lookupNodeById(index, candidate);
    if (node) return node;
  }

  if (options.label) {
    const byLabel = lookupNodeByLabel(index, options.label);
    if (byLabel) return byLabel;
  }

  return null;
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
  node: GraphProjectionNodeView,
  locator: string,
  refType?: string | null,
  refId?: string | null,
): PlanReferenceResolution {
  return {
    kind: "graph-node",
    locator,
    refType: refType ?? null,
    refId: refId ?? null,
    graphObject: buildGraphObjectCardFromNodeView(node),
    graphNodeId: node.node_id,
    fallback: null,
    source: "union-supergraph",
    message: `Resolved graph node ${node.label}.`,
  };
}

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
  projection?: UnionSupergraphProjectionResponse | null;
  fallbackResolution?: ReferenceResolution | null;
}

export function resolvePlanReferenceFromGraphProjection(
  input: ResolvePlanReferenceFromGraphProjectionInput,
): PlanReferenceResolution {
  const locator = resolutionLocator(input);
  const refType = input.refType ?? input.ref?.refType ?? null;
  const refId = input.refId ?? input.ref?.refId ?? null;
  const label = input.label ?? input.ref?.label ?? null;

  if (input.projection) {
    const index = buildUnionSupergraphNodeIndex(input.projection);
    const node = findGraphNodeInProjection(index, {
      locator: input.locator ?? locator,
      refType,
      refId,
      label,
    });

    if (node) {
      return graphNodeResolution(node, locator, refType, refId);
    }
  }

  return fallbackPlanResolution(locator, refType, refId, input.fallbackResolution);
}
