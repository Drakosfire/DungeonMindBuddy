import { describe, expect, it } from "vitest";

import type { WorldGraphProjection, WorldGraphProjectionRequest } from "../../api/types";
import {
  mapWorldGraphLensObservation,
  worldGraphLensInformationDescriptor,
} from "../../graphLens/worldGraphLensSurfaceInformation";
import {
  BUILD_WORLD_GRAPH_INFORMATION_KIND,
  BUILD_WORLD_GRAPH_PROVIDER_ID,
  adaptWorldGraphProjectionSearchItems,
  buildWorldGraphInformationDescriptor,
  formatProjectionSearchScopeLabel,
  observedRevisionId,
  searchItemsFromWorldGraphState,
} from "./buildWorldGraphSurfaceInformation";

function request(
  overrides: Partial<WorldGraphProjectionRequest> = {},
): WorldGraphProjectionRequest {
  return {
    schema: "dmb_world_graph_projection_request_v1",
    worldId: "eldyrwild",
    campaignId: "longmont-c2",
    scopeMode: "campaign",
    focus: { kind: "none", sessionId: null },
    admissibility: "gm",
    ...overrides,
  };
}

function projection(
  overrides: Partial<WorldGraphProjection> = {},
  snapshotOverrides: Partial<WorldGraphProjection["snapshot"]> = {},
): WorldGraphProjection {
  return {
    schema: "dmb_world_graph_projection_v1",
    snapshot: {
      worldId: "eldyrwild",
      campaignId: "longmont-c2",
      revisionId: "rev:abc",
      headRevisionId: "rev:abc",
      isHead: true,
      focus: { kind: "none", sessionId: null },
      admissibility: "gm",
      scopeMode: "campaign",
      ...snapshotOverrides,
    },
    summary: {
      nodeCount: 0,
      relationshipCount: 0,
      attributeCount: 0,
      evidenceCount: 0,
      sourceArtifactCount: 0,
      projectionTruncated: false,
    },
    nodes: [],
    relationships: [],
    attributes: [],
    evidence: [],
    sourceArtifacts: [],
    diagnostics: [],
    ...overrides,
  };
}

describe("buildWorldGraphInformationDescriptor", () => {
  it("reuses graph-lens scope semantics and only overrides channel/provider identity", () => {
    const lens = worldGraphLensInformationDescriptor(request());
    const descriptor = buildWorldGraphInformationDescriptor(request());
    expect(descriptor.informationKind).toBe(BUILD_WORLD_GRAPH_INFORMATION_KIND);
    expect(descriptor.providerId).toBe(BUILD_WORLD_GRAPH_PROVIDER_ID);
    expect(descriptor.authority).toBe("dungeonmind");
    expect(descriptor.subject).toEqual({ kind: "world", id: "eldyrwild" });
    expect(descriptor.scope).toEqual(lens.scope);
    expect(descriptor.channelId).toBe(
      `build-world-graph:${lens.channelId.slice("world-graph-lens:".length)}`,
    );
    expect(descriptor.channelId).not.toBe(lens.channelId);
    expect(descriptor.providerId).not.toBe(lens.providerId);
  });
});

describe("Build World Graph snapshot adaptation", () => {
  it("labels world-universal nodes as World, never the projection anchor", () => {
    expect(formatProjectionSearchScopeLabel(null)).toBe("World");
    expect(formatProjectionSearchScopeLabel("longmont-c2")).toBe("longmont-c2");
  });

  it("adapts READY items from the current projection value", () => {
    const ready = mapWorldGraphLensObservation({
      request: request(),
      response: projection({
        nodes: [
          {
            nodeId: "npc:glowkindle",
            label: "Glowkindle",
            kind: "npc",
            role: "merchant",
            aliases: ["Glow"],
            sourceDomains: ["recap"],
            evidenceBadges: [],
            adjacency: [],
            suggestedExpansions: [],
            anchoredToFocusSession: true,
            summary: "A friendly merchant.",
            campaignScope: "longmont-c2",
            evidenceRefIds: [],
            sourceArtifactIds: [],
          },
        ],
        summary: {
          nodeCount: 1,
          relationshipCount: 0,
          attributeCount: 0,
          evidenceCount: 0,
          sourceArtifactCount: 0,
          projectionTruncated: false,
        },
      }),
    });
    expect(ready.status).toBe("ready");
    const items = searchItemsFromWorldGraphState(ready);
    expect(items).toHaveLength(1);
    expect(items[0]?.nodeId).toBe("npc:glowkindle");
    expect(items[0]?.scopeLabel).toBe("longmont-c2");
    expect(observedRevisionId(ready)).toBe("rev:abc");
  });

  it("maps verified zero-node responses to EMPTY with no search items", () => {
    const empty = mapWorldGraphLensObservation({
      request: request(),
      response: projection(),
    });
    expect(empty.status).toBe("empty");
    expect(searchItemsFromWorldGraphState(empty)).toEqual([]);
    expect(observedRevisionId(empty)).toBe("rev:abc");
    expect(adaptWorldGraphProjectionSearchItems(projection())).toEqual([]);
  });
});
