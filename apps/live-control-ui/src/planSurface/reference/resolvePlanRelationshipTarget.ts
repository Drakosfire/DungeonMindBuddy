import { buildGraphObjectCardFromNodeView } from "../../graphObjectCard";
import type { GraphObjectRelationshipViewModel } from "../../graphObjectCard";
import type { WorldGraphProjection } from "../../api/types";
import type { GraphReferenceCorpusFallback, GraphReferenceProjectionState, GraphReferenceResolution } from "../../graphReference/types";
import {
  isCorpusFallbackAllowed,
  mapReferenceResolutionToCorpusFallback,
  resolvePlanReferenceFromGraphProjection,
} from "./graphAwareReferenceResolver";
import { REFERENCE_INDEX_ENDPOINTS, resolveReference } from "./referenceResolver";
import { adaptWorldGraphNodeForPlanCard } from "./worldGraphProjectionAdapter";

function appendIngestEscalationHint(message: string): string {
  if (/ingest/i.test(message)) return message;
  return `${message} Open /ingest to fix memory.`;
}

function withProjectionState(
  resolution: GraphReferenceResolution,
  projectionState: GraphReferenceProjectionState | null,
): GraphReferenceResolution {
  return {
    ...resolution,
    projectionState,
  };
}

function unresolvedRelationshipMiss(
  locator: string,
  reference: GraphReferenceResolution["reference"],
  label: string,
  projectionState: GraphReferenceProjectionState | null,
): GraphReferenceResolution {
  return {
    kind: "unresolved",
    locator,
    reference,
    projectionState,
    message: appendIngestEscalationHint(
      `Could not resolve related object "${label}" from graph memory.`,
    ),
  };
}

function deferredRelationshipResolution(
  locator: string,
  reference: GraphReferenceResolution["reference"],
  projectionState: GraphReferenceProjectionState | null,
): GraphReferenceResolution {
  return {
    kind: "unresolved",
    locator,
    reference,
    projectionState,
    message: "World Graph projection is loading; relationship resolution deferred.",
  };
}

function worldGraphErrorRelationshipResolution(
  locator: string,
  reference: GraphReferenceResolution["reference"],
  projectionState: GraphReferenceProjectionState | null,
): GraphReferenceResolution {
  return {
    kind: "error",
    locator,
    reference,
    projectionState,
    message: "World Graph projection failed; corpus fallback disabled.",
  };
}

function readyWithoutProjectionRelationshipResolution(
  locator: string,
  reference: GraphReferenceResolution["reference"],
  projectionState: GraphReferenceProjectionState | null,
): GraphReferenceResolution {
  return {
    kind: "error",
    locator,
    reference,
    projectionState,
    message:
      "World Graph projection marked ready but no projection was supplied; corpus fallback disabled.",
  };
}

/**
 * After an exact targetId miss, adapt governed corpus fallback only.
 * Never re-enter graph label/alias resolution with the stale target ID.
 */
function corpusFallbackAfterExactTargetMiss(
  locator: string,
  reference: GraphReferenceResolution["reference"],
  corpusFallback: GraphReferenceCorpusFallback,
  projectionState: GraphReferenceProjectionState | null,
): GraphReferenceResolution {
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

/**
 * Resolve a GraphObjectCard relationship target through the Plan graph-aware ladder.
 */
export async function resolvePlanRelationshipTarget({
  relationship,
  projection,
  projectionState = null,
  fetchImpl,
}: {
  relationship: GraphObjectRelationshipViewModel;
  projection?: WorldGraphProjection | null;
  projectionState?: GraphReferenceProjectionState | null;
  fetchImpl?: typeof fetch;
}): Promise<GraphReferenceResolution> {
  const label = String(relationship.label || "").trim() || "Related object";
  const targetId = String(relationship.targetId || "").trim() || null;
  const targetKind = String(relationship.targetKind || "").trim() || null;
  const locator = targetId ? `dmb-node:${targetId}` : label;
  const reference = targetKind && targetId
    ? { kind: "ref" as const, refType: targetKind, refId: targetId, label }
    : null;

  if (projectionState === "loading") {
    return deferredRelationshipResolution(locator, reference, projectionState);
  }

  if (projectionState === "error") {
    return worldGraphErrorRelationshipResolution(locator, reference, projectionState);
  }

  if (projectionState === "ready" && !projection) {
    return readyWithoutProjectionRelationshipResolution(locator, reference, projectionState);
  }

  // Unavailable ignores any supplied projection (handoff: dependency unavailable).
  // Exact-target relationships may still use governed corpus fallback; label-only
  // relationships must not read graph data.
  const usableProjection = projectionState === "unavailable" ? null : projection;

  if (targetId) {
    const exactNode = usableProjection?.nodes.find((node) => node.nodeId === targetId) ?? null;
    if (exactNode) {
      return withProjectionState(
        {
          kind: "resolved_graph",
          locator,
          reference,
          graphNodeId: exactNode.nodeId,
          graphObject: buildGraphObjectCardFromNodeView(adaptWorldGraphNodeForPlanCard(exactNode)),
          projectionState,
          message: `Resolved graph node ${exactNode.label}.`,
        },
        projectionState,
      );
    }

    // Exact targetId miss: do not pass the ID through label/alias graph lookup
    // again (that can rebind a stale ID to another node's alias). Proceed only
    // to governed corpus fallback or unresolved.
    const canUseCorpusIndex =
      isCorpusFallbackAllowed(projectionState)
      && Boolean(targetKind && REFERENCE_INDEX_ENDPOINTS[targetKind]);
    if (canUseCorpusIndex && targetKind) {
      const fallbackResolution = await resolveReference(
        {
          kind: "ref",
          refType: targetKind,
          refId: targetId,
          label,
        },
        fetchImpl,
      );
      return withProjectionState(
        corpusFallbackAfterExactTargetMiss(
          locator,
          reference,
          mapReferenceResolutionToCorpusFallback(fallbackResolution),
          projectionState,
        ),
        projectionState,
      );
    }

    return unresolvedRelationshipMiss(locator, reference, label, projectionState);
  }

  if (usableProjection) {
    const graphResolution = resolvePlanReferenceFromGraphProjection({
      locator: label,
      label,
      refType: targetKind,
      projection: usableProjection,
      projectionState,
    });

    if (graphResolution.kind === "resolved_graph" || graphResolution.kind === "ambiguous") {
      return withProjectionState(graphResolution, projectionState);
    }
  }

  return unresolvedRelationshipMiss(label, reference, label, projectionState);
}
