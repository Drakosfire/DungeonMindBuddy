import { describe, expect, it } from "vitest";

import type { GraphProjectionNodeView, UnionSupergraphProjectionResponse } from "../../api/types";
import {
  buildUnionSupergraphNodeIndex,
  findGraphNodeInProjection,
  parseGraphNodeLocator,
  resolvePlanReferenceFromGraphProjection,
} from "./graphAwareReferenceResolver";

const glowkindleNode: GraphProjectionNodeView = {
  node_id: "npc-glowkindle",
  label: "Glowkindle",
  kind: "npc",
  role: "merchant",
  aliases: ["Glow"],
  source_domains: ["recap"],
  evidence_badges: [],
  adjacency: [],
  anchored_to_focus_session: true,
  summary: "A friendly merchant.",
};

const projection: UnionSupergraphProjectionResponse = {
  campaign_id: "eldyrwild",
  session_id: "session-23",
  node_views: {
    "npc-glowkindle": glowkindleNode,
  },
  focus: {
    focused_evidence_ref_ids: [],
    focused_edge_ids: [],
    focused_node_ids: [],
  },
  mentions: [],
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
    expect(result.source).toBe("union-supergraph");
    expect(result.graphNodeId).toBe("npc-glowkindle");
    expect(result.graphObject?.label).toBe("Glowkindle");
    expect(result.fallback).toBeNull();
  });

  it("returns graph-node result for exact alias match", () => {
    const index = buildUnionSupergraphNodeIndex(projection);
    const node = findGraphNodeInProjection(index, { label: "Glow" });

    expect(node?.node_id).toBe("npc-glowkindle");

    const result = resolvePlanReferenceFromGraphProjection({
      refType: "npc",
      refId: "missing-slug",
      label: "Glow",
      projection,
    });

    expect(result.kind).toBe("graph-node");
    expect(result.graphNodeId).toBe("npc-glowkindle");
  });

  it("falls back to corpus-index result when graph misses", () => {
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
});
