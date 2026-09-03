/**
 * Build secondary World Graph Surface Information (SI-5A).
 *
 * Descriptor identity is exact-request identity. Observation mapping is the
 * shared DungeonMind graph-lens mapper; Build only overrides channel/provider ids.
 */

import type { WorldGraphProjection, WorldGraphProjectionRequest } from "../../api/types";
import { referenceFromGraphNode } from "../../graphReference/referenceFromGraphNode";
import type { GraphReferenceSearchItem } from "../../graphReference/types";
import {
  worldGraphLensInformationDescriptor,
  worldGraphLensRequestKey,
} from "../../graphLens/worldGraphLensSurfaceInformation";
import type {
  SurfaceInformationDescriptor,
  SurfaceInformationSnapshot,
  SurfaceInformationState,
} from "../../surfaceInformation";
import { adaptWorldGraphNodeView } from "../../worldGraph/worldGraphNodeViewAdapter";

export const BUILD_WORLD_GRAPH_INFORMATION_KIND = "world_graph_projection";
export const BUILD_WORLD_GRAPH_PROVIDER_ID = "build_world_graph_projection";

export const BUILD_WORLD_GRAPH_FALLBACK_SNAPSHOT: SurfaceInformationSnapshot<WorldGraphProjection> =
  Object.freeze({
    generation: 0,
    state: Object.freeze({
      status: "loading",
      diagnostics: Object.freeze([]),
    }),
  });

export function buildWorldGraphInformationDescriptor(
  request: WorldGraphProjectionRequest,
): SurfaceInformationDescriptor {
  const base = worldGraphLensInformationDescriptor(request);
  const requestKey = worldGraphLensRequestKey(request);
  return {
    ...base,
    channelId: `build-world-graph:${requestKey}`,
    informationKind: BUILD_WORLD_GRAPH_INFORMATION_KIND,
    providerId: BUILD_WORLD_GRAPH_PROVIDER_ID,
  };
}

/**
 * Display label for object campaign tenancy.
 * `campaign_scope: null` means world-universal — never collapse to the projection anchor.
 */
export function formatProjectionSearchScopeLabel(
  campaignScope: string | null | undefined,
): string {
  const trimmed = campaignScope?.trim();
  return trimmed || "World";
}

export function adaptWorldGraphProjectionSearchItems(
  projection: WorldGraphProjection,
): GraphReferenceSearchItem[] {
  return projection.nodes.map((node) => {
    const nodeView = adaptWorldGraphNodeView(node);
    return {
      nodeId: nodeView.node_id,
      label: nodeView.label,
      kind: nodeView.kind,
      role: nodeView.role,
      summary: nodeView.summary ?? null,
      aliases: nodeView.aliases ?? [],
      scopeLabel: formatProjectionSearchScopeLabel(nodeView.campaign_scope),
      reference: referenceFromGraphNode(nodeView),
      nodeView,
    };
  });
}

export function searchItemsFromWorldGraphState(
  state: SurfaceInformationState<WorldGraphProjection>,
): readonly GraphReferenceSearchItem[] {
  if (state.status === "ready" || state.status === "stale") {
    return adaptWorldGraphProjectionSearchItems(state.value);
  }
  return [];
}

export function observedRevisionId(
  state: SurfaceInformationState<WorldGraphProjection>,
): string | null {
  if (
    state.status === "ready"
    || state.status === "empty"
    || state.status === "stale"
  ) {
    return state.revision.kind === "exact" ? state.revision.value : null;
  }
  return null;
}

export function observedIsHead(
  state: SurfaceInformationState<WorldGraphProjection>,
  revisionMode: "head" | "pinned",
): boolean {
  if (revisionMode !== "head") return false;
  if (state.status !== "ready" && state.status !== "stale") return false;
  return state.value.snapshot.isHead === true;
}
