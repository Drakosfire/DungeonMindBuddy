import { describe, expect, it } from "vitest";

import type { WorldGraphProjection, WorldGraphProjectionNodeView } from "../../api/types";
import { resolvePlanRelationshipTarget } from "./resolvePlanRelationshipTarget";

const glowkindleNode: WorldGraphProjectionNodeView = {
  nodeId: "npc-glowkindle",
  label: "Glowkindle",
  kind: "npc",
  role: "merchant",
  aliases: ["Glow"],
  sourceDomains: ["recap"],
  evidenceBadges: [],
  adjacency: [],
  suggestedExpansions: [],
  evidenceRefIds: [],
  sourceArtifactIds: [],
  anchoredToFocusSession: true,
  summary: "A friendly merchant.",
};

const innNode: WorldGraphProjectionNodeView = {
  nodeId: "location-inn",
  label: "Inn",
  kind: "location",
  role: "location",
  aliases: ["The Inn"],
  sourceDomains: ["recap"],
  evidenceBadges: [],
  adjacency: [],
  suggestedExpansions: [],
  evidenceRefIds: [],
  sourceArtifactIds: [],
  anchoredToFocusSession: true,
  summary: "Meeting place.",
};

const lysandraA: WorldGraphProjectionNodeView = {
  nodeId: "npc-lysandra-a",
  label: "Lysandra",
  kind: "npc",
  role: "npc",
  aliases: ["Lysandra"],
  sourceDomains: ["recap"],
  evidenceBadges: [],
  adjacency: [],
  suggestedExpansions: [],
  evidenceRefIds: [],
  sourceArtifactIds: [],
  anchoredToFocusSession: true,
};

const lysandraB: WorldGraphProjectionNodeView = {
  nodeId: "npc-lysandra-b",
  label: "Lysandra of the Gate",
  kind: "npc",
  role: "npc",
  aliases: ["Lysandra"],
  sourceDomains: ["recap"],
  evidenceBadges: [],
  adjacency: [],
  suggestedExpansions: [],
  evidenceRefIds: [],
  sourceArtifactIds: [],
  anchoredToFocusSession: true,
};

const projection: WorldGraphProjection = {
  schema: "dmb_world_graph_projection_v1",
  snapshot: {
    worldId: "eldyrwild", campaignId: "longmont-c2", revisionId: "rev-1", headRevisionId: "rev-1",
    isHead: true, focus: { kind: "session", sessionId: "session-21" }, admissibility: "gm",
  },
  summary: { nodeCount: 4, relationshipCount: 0, attributeCount: 0, evidenceCount: 0, sourceArtifactCount: 0, projectionTruncated: false },
  nodes: [glowkindleNode, innNode, lysandraA, lysandraB],
  relationships: [], attributes: [], evidence: [], sourceArtifacts: [], diagnostics: [],
};

describe("resolvePlanRelationshipTarget", () => {
  it("resolves relationship targetId as an exact dmb-node locator", async () => {
    const resolution = await resolvePlanRelationshipTarget({
      relationship: {
        id: "edge-1",
        label: "Inn",
        predicate: "met at",
        targetId: "location-inn",
        targetKind: "location",
      },
      projection,
      projectionState: "ready",
    });

    expect(resolution.kind).toBe("graph-node");
    expect(resolution.locator).toBe("dmb-node:location-inn");
    expect(resolution.graphNodeId).toBe("location-inn");
    expect(resolution.graphObject?.label).toBe("Inn");
  });

  it("resolves unique label-only relationships without first-win", async () => {
    const resolution = await resolvePlanRelationshipTarget({
      relationship: {
        id: "edge-2",
        label: "Glow",
        predicate: "knows",
      },
      projection,
      projectionState: "ready",
    });

    expect(resolution.kind).toBe("graph-node");
    expect(resolution.graphNodeId).toBe("npc-glowkindle");
  });

  it("does not first-win ambiguous label-only relationships", async () => {
    const resolution = await resolvePlanRelationshipTarget({
      relationship: {
        id: "edge-3",
        label: "Lysandra",
        predicate: "related",
      },
      projection,
      projectionState: "ready",
    });

    expect(resolution.kind).toBe("unresolved");
    expect(resolution.ambiguousNodeIds).toEqual(["npc-lysandra-a", "npc-lysandra-b"]);
    expect(resolution.message).toMatch(/uniquely resolve/i);
  });

  it("returns unresolved miss for unknown targetId without inventing a match", async () => {
    const resolution = await resolvePlanRelationshipTarget({
      relationship: {
        id: "edge-4",
        label: "Missing Gate",
        targetId: "location-missing",
        targetKind: "location",
      },
      projection,
      projectionState: "ready",
      fetchImpl: async () =>
        ({
          ok: true,
          json: async () => ({ locations: [] }),
        }) as Response,
    });

    expect(resolution.kind).toBe("unresolved");
    expect(resolution.graphObject).toBeNull();
    expect(resolution.message).toMatch(/ingest/i);
  });

  it("does not label-fallback when targetId misses but label matches another node", async () => {
    const resolution = await resolvePlanRelationshipTarget({
      relationship: {
        id: "edge-stale",
        label: "Inn",
        targetId: "location-missing",
        targetKind: "location",
      },
      projection,
      projectionState: "ready",
      fetchImpl: async () =>
        ({
          ok: true,
          json: async () => ({ locations: [] }),
        }) as Response,
    });

    expect(resolution.kind).toBe("unresolved");
    expect(resolution.graphNodeId).toBeNull();
    expect(resolution.graphObject).toBeNull();
    expect(resolution.locator).toBe("dmb-node:location-missing");
  });
});
