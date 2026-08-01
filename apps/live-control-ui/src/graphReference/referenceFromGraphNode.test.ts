import { describe, expect, it } from "vitest";

import type { GraphProjectionNodeView } from "../api/types";
import { referenceFromGraphNode } from "./referenceFromGraphNode";

describe("referenceFromGraphNode", () => {
  it("builds a graph-native reference from a projection node", () => {
    const node: GraphProjectionNodeView = {
      node_id: "npc-glowkindle",
      label: "Glowkindle",
      kind: "npc",
      role: "merchant",
      aliases: ["Glow"],
      source_domains: ["recap"],
      evidence_badges: [],
      adjacency: [],
      anchored_to_focus_session: true,
    };

    expect(referenceFromGraphNode(node)).toEqual({
      kind: "ref",
      refType: "graph-node",
      refId: "npc-glowkindle",
      label: "Glowkindle",
    });
  });

  it("preserves colonated durable node ids", () => {
    const node: GraphProjectionNodeView = {
      node_id: "threat:tripod-null-calf",
      label: "Tripod Null-Calf",
      kind: "threat",
      role: null,
      aliases: [],
      source_domains: [],
      evidence_badges: [],
      adjacency: [],
      anchored_to_focus_session: false,
    };

    expect(referenceFromGraphNode(node).refId).toBe("threat:tripod-null-calf");
  });
});
