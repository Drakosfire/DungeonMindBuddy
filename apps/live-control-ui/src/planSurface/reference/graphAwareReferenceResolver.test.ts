import { describe, expect, it } from "vitest";

import type { WorldGraphProjection, WorldGraphProjectionNodeView } from "../../api/types";
import {
  buildWorldGraphNodeIndex,
  findGraphNodeInProjection,
  parseGraphNodeLocator,
  resolvePlanReferenceFromGraphProjection,
} from "./graphAwareReferenceResolver";

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

const projection: WorldGraphProjection = {
  schema: "dmb_world_graph_projection_v1",
  snapshot: {
    worldId: "eldyrwild", campaignId: "longmont-c2", revisionId: "rev-1", headRevisionId: "rev-1",
    isHead: true, focus: { kind: "session", sessionId: "session-21" }, admissibility: "gm",
  },
  summary: { nodeCount: 1, relationshipCount: 0, attributeCount: 0, evidenceCount: 0, sourceArtifactCount: 0, projectionTruncated: false },
  nodes: [glowkindleNode],
  relationships: [], attributes: [], evidence: [], sourceArtifacts: [], diagnostics: [],
};

describe("graphAwareReferenceResolver", () => {
  it("parses graph-node locator prefixes", () => {
    expect(parseGraphNodeLocator("dmb-node:npc-glowkindle")).toBe("npc-glowkindle");
    expect(parseGraphNodeLocator("graph_node:npc-glowkindle")).toBe("npc-glowkindle");
    expect(parseGraphNodeLocator("node:npc-glowkindle")).toBe("npc-glowkindle");
    expect(parseGraphNodeLocator("dmb-node:node:tripod-null-calf")).toBe("node:tripod-null-calf");
    expect(parseGraphNodeLocator("npc-index:lysandro")).toBeNull();
  });

  it("returns graph-node result for exact node id", () => {
    const result = resolvePlanReferenceFromGraphProjection({
      locator: "dmb-node:npc-glowkindle",
      projection,
    });

    expect(result.kind).toBe("graph-node");
    expect(result.source).toBe("world-graph");
    expect(result.graphNodeId).toBe("npc-glowkindle");
    expect(result.graphObject?.label).toBe("Glowkindle");
    expect(result.fallback).toBeNull();
  });

  it("returns graph-node result for exact alias match when alias is unique", () => {
    const index = buildWorldGraphNodeIndex(projection);
    const lookup = findGraphNodeInProjection(index, { label: "Glow" });

    expect(lookup.status).toBe("found");
    if (lookup.status === "found") {
      expect(lookup.node.nodeId).toBe("npc-glowkindle");
    }

    const result = resolvePlanReferenceFromGraphProjection({
      refType: "npc",
      refId: "missing-slug",
      label: "Glow",
      projection,
    });

    expect(result.kind).toBe("graph-node");
    expect(result.graphNodeId).toBe("npc-glowkindle");
  });

  it("returns unresolved when duplicate label or alias keys are ambiguous", () => {
    const lysandraA: WorldGraphProjectionNodeView = {
      ...glowkindleNode,
      nodeId: "npc-lysandra-a",
      label: "Lysandra Ironveil",
      aliases: ["Lysandra"],
    };
    const lysandraB: WorldGraphProjectionNodeView = {
      ...glowkindleNode,
      nodeId: "npc-lysandra-b",
      label: "Lysandra of the Gate",
      aliases: ["Lysandra"],
    };
    const ambiguousProjection: WorldGraphProjection = {
      ...projection,
      nodes: [lysandraA, lysandraB],
    };

    const index = buildWorldGraphNodeIndex(ambiguousProjection);
    const lookup = findGraphNodeInProjection(index, { label: "Lysandra" });
    expect(lookup.status).toBe("ambiguous");

    const result = resolvePlanReferenceFromGraphProjection({
      refType: "npc",
      refId: "lysandra",
      label: "Lysandra",
      projection: ambiguousProjection,
    });

    expect(result.kind).toBe("unresolved");
    expect(result.source).toBe("unresolved");
    expect(result.graphObject).toBeNull();
    expect(result.ambiguousNodeIds).toEqual(["npc-lysandra-a", "npc-lysandra-b"]);
    expect(result.message).toMatch(/Could not uniquely resolve this object from graph memory/i);
    expect(result.message).toMatch(/ingest/i);
  });

  it("adapts a precomputed corpus-index fallback result when graph misses", () => {
    const fallback = {
      status: "resolved" as const,
      ref: {
        kind: "ref" as const,
        refType: "npc",
        refId: "lysandro-ironveil",
        label: "Lysandro Ironveil",
      },
      source: "npc-index",
      item: { title: "Lysandro Ironveil" },
      message: "Resolved from live npc index.",
    };

    const result = resolvePlanReferenceFromGraphProjection({
      refType: "npc",
      refId: "lysandro-ironveil",
      label: "Lysandro Ironveil",
      projection,
      fallbackResolution: fallback,
    });

    expect(result.kind).toBe("corpus-index");
    expect(result.source).toBe("corpus-index");
    expect(result.fallback).toEqual(fallback);
    expect(result.graphObject).toBeNull();
  });

  it("returns unresolved when both graph and corpus fallback miss", () => {
    const fallback = {
      status: "unresolved" as const,
      ref: {
        kind: "ref" as const,
        refType: "npc",
        refId: "missing-person",
        label: "Missing Person",
      },
      message: "Could not resolve this reference.",
    };

    const result = resolvePlanReferenceFromGraphProjection({
      refType: "npc",
      refId: "missing-person",
      label: "Missing Person",
      projection,
      fallbackResolution: fallback,
    });

    expect(result.kind).toBe("unresolved");
    expect(result.source).toBe("unresolved");
    expect(result.graphObject).toBeNull();
    expect(result.message).toMatch(/ingest/i);
  });

  it("does not mutate graph projection payload", () => {
    const snapshot = JSON.stringify(projection);

    resolvePlanReferenceFromGraphProjection({
      locator: "dmb-node:npc-glowkindle",
      projection,
    });

    expect(JSON.stringify(projection)).toBe(snapshot);
  });

  it("does not rebind a missing graph-node id through a matching label", () => {
    const labelTwin: WorldGraphProjectionNodeView = {
      ...glowkindleNode,
      nodeId: "threat:other-beast",
      label: "Tripod Null-Calf",
      aliases: ["Tripod Null-Calf"],
      kind: "threat",
    };
    const twinProjection: WorldGraphProjection = {
      ...projection,
      nodes: [labelTwin],
    };

    const result = resolvePlanReferenceFromGraphProjection({
      ref: {
        kind: "ref",
        refType: "graph-node",
        refId: "threat:tripod-null-calf",
        label: "Tripod Null-Calf",
      },
      projection: twinProjection,
      fallbackResolution: {
        status: "error",
        ref: {
          kind: "ref",
          refType: "graph-node",
          refId: "threat:tripod-null-calf",
          label: "Tripod Null-Calf",
        },
        message: "Invalid reference locator.",
      },
    });

    expect(result.kind).toBe("unresolved");
    expect(result.graphNodeId).toBeNull();
    expect(result.graphObject).toBeNull();
    expect(result.fallback).toBeNull();
    expect(result.message).toMatch(/threat:tripod-null-calf/i);
    expect(result.message).not.toMatch(/invalid reference locator/i);
  });
});
