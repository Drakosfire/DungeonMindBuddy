import { describe, expect, it } from "vitest";

import type { GraphProjectionNodeView, UnionSupergraphProjectionResponse } from "../../api/types";
import { resolvePlanRelationshipTarget } from "./resolvePlanRelationshipTarget";

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

const innNode: GraphProjectionNodeView = {
  node_id: "location-inn",
  label: "Inn",
  kind: "location",
  role: "location",
  aliases: ["The Inn"],
  source_domains: ["recap"],
  evidence_badges: [],
  adjacency: [],
  anchored_to_focus_session: true,
  summary: "Meeting place.",
};

const lysandraA: GraphProjectionNodeView = {
  node_id: "npc-lysandra-a",
  label: "Lysandra",
  kind: "npc",
  role: "npc",
  aliases: ["Lysandra"],
  source_domains: ["recap"],
  evidence_badges: [],
  adjacency: [],
  anchored_to_focus_session: true,
};

const lysandraB: GraphProjectionNodeView = {
  node_id: "npc-lysandra-b",
  label: "Lysandra of the Gate",
  kind: "npc",
  role: "npc",
  aliases: ["Lysandra"],
  source_domains: ["recap"],
  evidence_badges: [],
  adjacency: [],
  anchored_to_focus_session: true,
};

const projection: UnionSupergraphProjectionResponse = {
  campaign_id: "longmont-c2",
  session_id: "session-21",
  node_views: {
    "npc-glowkindle": glowkindleNode,
    "location-inn": innNode,
    "npc-lysandra-a": lysandraA,
    "npc-lysandra-b": lysandraB,
  },
  focus: {
    focused_evidence_ref_ids: [],
    focused_edge_ids: [],
    focused_node_ids: [],
  },
  mentions: [],
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
