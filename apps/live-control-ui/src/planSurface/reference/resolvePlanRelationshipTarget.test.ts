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

    expect(resolution.kind).toBe("resolved_graph");
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

    expect(resolution.kind).toBe("resolved_graph");
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

    expect(resolution.kind).toBe("ambiguous");
    if (resolution.kind === "ambiguous") {
      expect(resolution.matchingGraphNodeIds).toEqual(["npc-lysandra-a", "npc-lysandra-b"]);
    }
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
    expect(resolution.locator).toBe("dmb-node:location-missing");
  });

  it("does not alias-rebind when missing targetId equals another node's unique alias", async () => {
    const aliasTwin: WorldGraphProjectionNodeView = {
      ...innNode,
      nodeId: "location-elsewhere",
      label: "Elsewhere",
      aliases: ["location-missing"],
    };
    const twinProjection: WorldGraphProjection = {
      ...projection,
      nodes: [glowkindleNode, aliasTwin, lysandraA, lysandraB],
    };

    const resolution = await resolvePlanRelationshipTarget({
      relationship: {
        id: "edge-alias-trap",
        label: "Missing Gate",
        targetId: "location-missing",
        targetKind: "location",
      },
      projection: twinProjection,
      projectionState: "ready",
      fetchImpl: async () =>
        ({
          ok: true,
          json: async () => ({ locations: [] }),
        }) as Response,
    });

    expect(resolution.kind).toBe("unresolved");
    expect(resolution.kind).not.toBe("resolved_graph");
    expect(resolution.graphNodeId).toBeUndefined();
    expect(resolution.locator).toBe("dmb-node:location-missing");
  });

  it("fails closed during projection error without querying corpus", async () => {
    let fetchCount = 0;
    const resolution = await resolvePlanRelationshipTarget({
      relationship: {
        id: "edge-integrity",
        label: "Inn",
        targetId: "location-inn",
        targetKind: "location",
      },
      projection: null,
      projectionState: "error",
      fetchImpl: async () => {
        fetchCount += 1;
        return {
          ok: true,
          json: async () => ({ locations: [{ slug: "location-inn", title: "Inn" }] }),
        } as Response;
      },
    });

    expect(resolution.kind).toBe("error");
    expect(resolution.message).toMatch(/corpus fallback disabled/i);
    expect(fetchCount).toBe(0);
  });

  it("defers relationship resolution while projection is loading", async () => {
    let fetchCount = 0;
    const resolution = await resolvePlanRelationshipTarget({
      relationship: {
        id: "edge-loading",
        label: "Inn",
        targetId: "location-inn",
        targetKind: "location",
      },
      projection,
      projectionState: "loading",
      fetchImpl: async () => {
        fetchCount += 1;
        return { ok: true, json: async () => ({ locations: [] }) } as Response;
      },
    });

    expect(resolution.kind).toBe("unresolved");
    expect(resolution.message).toMatch(/loading/i);
    expect(fetchCount).toBe(0);
  });
});
