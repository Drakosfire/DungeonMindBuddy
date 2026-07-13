import { buildGraphObjectCardFromNodeView } from "../../graphObjectCard";
import type { GraphObjectRelationshipViewModel } from "../../graphObjectCard";
import type { WorldGraphProjection } from "../../api/types";
import {
  isCorpusFallbackAllowed,
  resolvePlanReferenceFromGraphProjection,
  type PlanGraphProjectionState,
  type PlanReferenceResolution,
} from "./graphAwareReferenceResolver";
import { REFERENCE_INDEX_ENDPOINTS, resolveReference } from "./referenceResolver";
import { adaptWorldGraphNodeForPlanCard } from "./worldGraphProjectionAdapter";

function appendIngestEscalationHint(message: string): string {
  if (/ingest/i.test(message)) return message;
  return `${message} Open /ingest to fix memory.`;
}

function withProjectionState(
  resolution: PlanReferenceResolution,
  projectionState: PlanGraphProjectionState | null,
): PlanReferenceResolution {
  return {
    ...resolution,
    graphProjectionState: projectionState,
  };
}

function unresolvedRelationshipMiss(
  locator: string,
  refType: string | null,
  label: string,
  projectionState: PlanGraphProjectionState | null,
): PlanReferenceResolution {
  return {
    kind: "unresolved",
    locator,
    refType,
    refId: null,
    graphObject: null,
    graphNodeId: null,
    fallback: null,
    source: "unresolved",
    message: appendIngestEscalationHint(
      `Could not resolve related object "${label}" from graph memory.`,
    ),
    graphProjectionState: projectionState,
  };
}

function deferredRelationshipResolution(
  locator: string,
  refType: string | null,
  projectionState: PlanGraphProjectionState | null,
): PlanReferenceResolution {
  return {
    kind: "unresolved",
    locator,
    refType,
    refId: null,
    graphObject: null,
    graphNodeId: null,
    fallback: null,
    source: "unresolved",
    message: "World Graph projection is loading; relationship resolution deferred.",
    graphProjectionState: projectionState,
  };
}

function worldGraphErrorRelationshipResolution(
  locator: string,
  refType: string | null,
  projectionState: PlanGraphProjectionState | null,
): PlanReferenceResolution {
  return {
    kind: "error",
    locator,
    refType,
    refId: null,
    graphObject: null,
    graphNodeId: null,
    fallback: null,
    source: "error",
    message: "World Graph projection failed; corpus fallback disabled.",
    graphProjectionState: projectionState,
  };
}

/**
 * Resolve a GraphObjectCard relationship target through the Plan graph-aware ladder.
 *
 * Rules:
 * - loading / error fail closed (no corpus fallback), matching chip resolution
 * - targetId → exact `projection.nodes[].nodeId` only (no label fallback)
 * - label-only → unique label/alias match only; ambiguous stays unresolved
 * - never first-win on duplicate aliases
 * - corpus fallback only when graph is unavailable or an ordinary miss in a ready projection
 */
export async function resolvePlanRelationshipTarget({
  relationship,
  projection,
  projectionState = null,
  fetchImpl,
}: {
  relationship: GraphObjectRelationshipViewModel;
  projection?: WorldGraphProjection | null;
  projectionState?: PlanGraphProjectionState | null;
  fetchImpl?: typeof fetch;
}): Promise<PlanReferenceResolution> {
  const label = String(relationship.label || "").trim() || "Related object";
  const targetId = String(relationship.targetId || "").trim() || null;
  const targetKind = String(relationship.targetKind || "").trim() || null;
  const locator = targetId ? `dmb-node:${targetId}` : label;

  if (projectionState === "loading") {
    return deferredRelationshipResolution(locator, targetKind, projectionState);
  }

  if (projectionState === "error") {
    return worldGraphErrorRelationshipResolution(locator, targetKind, projectionState);
  }

  if (targetId) {
    // Exact node-id lookup only — do not pass label into the general resolver,
    // which would otherwise unique-match a different node by label on miss.
    const exactNode = projection?.nodes.find((node) => node.nodeId === targetId) ?? null;
    if (exactNode) {
      return withProjectionState(
        {
          kind: "graph-node",
          locator,
          refType: targetKind,
          refId: targetId,
          graphObject: buildGraphObjectCardFromNodeView(adaptWorldGraphNodeForPlanCard(exactNode)),
          graphNodeId: exactNode.nodeId,
          fallback: null,
          source: "world-graph",
          message: `Resolved graph node ${exactNode.label}.`,
        },
        projectionState,
      );
    }

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
      // Omit label so an exact graph miss cannot label-fallback before corpus adapt.
      return withProjectionState(
        resolvePlanReferenceFromGraphProjection({
          locator,
          refType: targetKind,
          refId: targetId,
          projection: projection ?? null,
          fallbackResolution,
        }),
        projectionState,
      );
    }

    return unresolvedRelationshipMiss(locator, targetKind, label, projectionState);
  }

  // Label-only: graph unique match only — never invent a corpus refId from the label.
  if (projection) {
    const graphResolution = resolvePlanReferenceFromGraphProjection({
      locator: label,
      label,
      refType: targetKind,
      projection,
    });

    if (graphResolution.kind === "graph-node" || graphResolution.ambiguousNodeIds?.length) {
      return withProjectionState(graphResolution, projectionState);
    }
  }

  return unresolvedRelationshipMiss(label, targetKind, label, projectionState);
}
