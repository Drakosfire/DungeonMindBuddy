import { describe, expect, it } from "vitest";

import type { WorldGraphProjection, WorldGraphProjectionNodeView } from "../api/types";
import {
  buildWorldGraphNodeIndex,
  findGraphNodeInProjection,
  parseGraphNodeLocator,
  resolveGraphReference,
} from "./resolveGraphReference";

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

describe("resolveGraphReference", () => {
  it("parses graph-node locator prefixes", () => {
    expect(parseGraphNodeLocator("dmb-node:npc-glowkindle")).toBe("npc-glowkindle");
    expect(parseGraphNodeLocator("graph_node:npc-glowkindle")).toBe("npc-glowkindle");
    expect(parseGraphNodeLocator("node:npc-glowkindle")).toBe("npc-glowkindle");
    expect(parseGraphNodeLocator("dmb-node:node:tripod-null-calf")).toBe("node:tripod-null-calf");
    expect(parseGraphNodeLocator("npc-index:lysandro")).toBeNull();
  });

  it("returns resolved_graph for exact node id", () => {
    const result = resolveGraphReference({
      locator: "dmb-node:npc-glowkindle",
      projection,
    });

    expect(result.kind).toBe("resolved_graph");
    expect(result.graphNodeId).toBe("npc-glowkindle");
    if (result.kind === "resolved_graph") {
      expect(result.graphObject.label).toBe("Glowkindle");
    }
  });

  it("graph-native exact ID wins over a wrong label on another node", () => {
    const labelTwin: WorldGraphProjectionNodeView = {
      ...glowkindleNode,
      nodeId: "threat:other-beast",
      label: "Tripod Null-Calf",
      aliases: ["Tripod Null-Calf"],
      kind: "threat",
    };
    const twinProjection: WorldGraphProjection = {
      ...projection,
      nodes: [glowkindleNode, labelTwin],
    };

    const result = resolveGraphReference({
      ref: {
        kind: "ref",
        refType: "graph-node",
        refId: "npc-glowkindle",
        label: "Tripod Null-Calf",
      },
      projection: twinProjection,
    });

    expect(result.kind).toBe("resolved_graph");
    if (result.kind === "resolved_graph") {
      expect(result.graphNodeId).toBe("npc-glowkindle");
    }
  });

  it("graph-native missing ID with uniquely matching display label stays unresolved", () => {
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

    const result = resolveGraphReference({
      ref: {
        kind: "ref",
        refType: "graph-node",
        refId: "threat:tripod-null-calf",
        label: "Tripod Null-Calf",
      },
      projection: twinProjection,
      corpusFallback: {
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
    expect(result.message).toMatch(/threat:tripod-null-calf/i);
    expect(result.message).not.toMatch(/invalid reference locator/i);
  });

  it("returns resolved_graph for exact alias match when alias is unique", () => {
    const index = buildWorldGraphNodeIndex(projection);
    const lookup = findGraphNodeInProjection(index, { label: "Glow" });

    expect(lookup.status).toBe("found");
    if (lookup.status === "found") {
      expect(lookup.node.nodeId).toBe("npc-glowkindle");
    }

    const result = resolveGraphReference({
      refType: "npc",
      refId: "missing-slug",
      label: "Glow",
      projection,
    });

    expect(result.kind).toBe("resolved_graph");
    if (result.kind === "resolved_graph") {
      expect(result.graphNodeId).toBe("npc-glowkindle");
    }
  });

  it("two legacy alias matches return ambiguous with all IDs and no fallback", () => {
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

    const result = resolveGraphReference({
      refType: "npc",
      refId: "lysandra",
      label: "Lysandra",
      projection: ambiguousProjection,
      corpusFallback: {
        status: "resolved",
        ref: {
          kind: "ref",
          refType: "npc",
          refId: "lysandra",
          label: "Lysandra",
        },
        message: "Would have fallen back.",
      },
    });

    expect(result.kind).toBe("ambiguous");
    if (result.kind === "ambiguous") {
      expect(result.matchingGraphNodeIds).toEqual(["npc-lysandra-a", "npc-lysandra-b"]);
    }
    expect(result.message).toMatch(/Could not uniquely resolve this object from graph memory/i);
    expect(result.message).toMatch(/ingest/i);
  });

  it("adapts a precomputed corpus fallback when graph misses", () => {
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

    const result = resolveGraphReference({
      refType: "npc",
      refId: "lysandro-ironveil",
      label: "Lysandro Ironveil",
      projection,
      corpusFallback: fallback,
    });

    expect(result.kind).toBe("resolved_corpus_fallback");
    if (result.kind === "resolved_corpus_fallback") {
      expect(result.fallback).toEqual(fallback);
    }
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

    const result = resolveGraphReference({
      refType: "npc",
      refId: "missing-person",
      label: "Missing Person",
      projection,
      corpusFallback: fallback,
    });

    expect(result.kind).toBe("unresolved");
    expect(result.message).toMatch(/ingest/i);
  });

  it("graph unavailable with graph-native stays unresolved without fallback", () => {
    const result = resolveGraphReference({
      ref: {
        kind: "ref",
        refType: "graph-node",
        refId: "node:bubbles",
        label: "Bubbles the Float Goat",
      },
      projection: null,
      projectionState: "unavailable",
    });

    expect(result.kind).toBe("unresolved");
    expect(result.message).toMatch(/unavailable/i);
  });

  it("unavailable ignores a supplied projection for graph-native refs", () => {
    const result = resolveGraphReference({
      ref: {
        kind: "ref",
        refType: "graph-node",
        refId: "npc-glowkindle",
        label: "Glowkindle",
      },
      projection,
      projectionState: "unavailable",
    });

    expect(result.kind).toBe("unresolved");
    expect(result.kind).not.toBe("resolved_graph");
    expect(result.message).toMatch(/unavailable/i);
  });

  it("unavailable legacy reference may use corpus fallback", () => {
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

    const result = resolveGraphReference({
      refType: "npc",
      refId: "lysandro-ironveil",
      label: "Lysandro Ironveil",
      projection,
      corpusFallback: fallback,
      projectionState: "unavailable",
    });

    expect(result.kind).toBe("resolved_corpus_fallback");
    if (result.kind === "resolved_corpus_fallback") {
      expect(result.fallback).toEqual(fallback);
    }
  });

  it("does not mutate graph projection payload", () => {
    const snapshot = JSON.stringify(projection);

    resolveGraphReference({
      locator: "dmb-node:npc-glowkindle",
      projection,
    });

    expect(JSON.stringify(projection)).toBe(snapshot);
  });

  it("defers resolution while projectionState is loading even when projection would match", () => {
    const result = resolveGraphReference({
      locator: "dmb-node:npc-glowkindle",
      projection,
      projectionState: "loading",
    });

    expect(result.kind).toBe("unresolved");
    expect(result.message).toMatch(/loading; resolution deferred/i);
    expect(result.projectionState).toBe("loading");
  });

  it("defers resolution while projectionState is loading even when corpus fallback would resolve", () => {
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

    const result = resolveGraphReference({
      refType: "npc",
      refId: "missing-slug",
      label: "Glow",
      projection,
      corpusFallback: fallback,
      projectionState: "loading",
    });

    expect(result.kind).toBe("unresolved");
    expect(result.message).toMatch(/loading; resolution deferred/i);
    expect(result.kind).not.toBe("resolved_graph");
    expect(result.kind).not.toBe("resolved_corpus_fallback");
  });

  it("returns error while projectionState is error even when projection would match", () => {
    const result = resolveGraphReference({
      locator: "dmb-node:npc-glowkindle",
      projection,
      projectionState: "error",
    });

    expect(result.kind).toBe("error");
    expect(result.message).toMatch(/projection failed; corpus fallback disabled/i);
    expect(result.kind).not.toBe("resolved_graph");
  });

  it("returns error while projectionState is error even when corpus fallback would resolve", () => {
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

    const result = resolveGraphReference({
      refType: "npc",
      refId: "missing-slug",
      label: "Glow",
      projection,
      corpusFallback: fallback,
      projectionState: "error",
    });

    expect(result.kind).toBe("error");
    expect(result.message).toMatch(/projection failed; corpus fallback disabled/i);
    expect(result.kind).not.toBe("resolved_corpus_fallback");
  });

  it("includes lens summary on graph-native miss diagnostics", () => {
    const result = resolveGraphReference({
      ref: {
        kind: "ref",
        refType: "graph-node",
        refId: "node:bubbles",
        label: "Bubbles the Float Goat",
      },
      projection,
      lensSummary: "C2 only · no session focus",
    });

    expect(result.kind).toBe("unresolved");
    expect(result.message).toMatch(/node:bubbles/i);
    expect(result.message).toMatch(/C2 only · no session focus/);
  });
});
