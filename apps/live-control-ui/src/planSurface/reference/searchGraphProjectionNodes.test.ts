import { describe, expect, it } from "vitest";

import type { GraphProjectionNodeView } from "../../api/types";
import {
  searchGraphProjectionNodes,
  sortGraphProjectionNodes,
} from "./searchGraphProjectionNodes";

function node(
  overrides: Partial<GraphProjectionNodeView> & Pick<GraphProjectionNodeView, "node_id" | "label">,
): GraphProjectionNodeView {
  return {
    kind: "npc",
    role: "npc",
    aliases: [],
    source_domains: [],
    evidence_badges: [],
    adjacency: [],
    anchored_to_focus_session: true,
    ...overrides,
  };
}

const nodes = [
  node({
    node_id: "npc-glowkindle",
    label: "Glowkindle",
    kind: "npc",
    role: "merchant",
    aliases: ["Glow"],
    summary: "A friendly herb trader.",
  }),
  node({
    node_id: "location-inn",
    label: "Inn",
    kind: "location",
    role: "location",
    aliases: ["The Inn"],
  }),
  node({
    node_id: "quest-rats",
    label: "Glowkindle Rats",
    kind: "quest",
    role: "job",
  }),
];

describe("searchGraphProjectionNodes", () => {
  it("returns all nodes for an empty query", () => {
    expect(searchGraphProjectionNodes(nodes, "").map((entry) => entry.node_id)).toEqual([
      "npc-glowkindle",
      "location-inn",
      "quest-rats",
    ]);
  });

  it("matches label, alias, kind, and summary tokens", () => {
    expect(searchGraphProjectionNodes(nodes, "glow").map((entry) => entry.node_id)).toEqual([
      "npc-glowkindle",
      "quest-rats",
    ]);
    expect(searchGraphProjectionNodes(nodes, "merchant").map((entry) => entry.node_id)).toEqual([
      "npc-glowkindle",
    ]);
    expect(searchGraphProjectionNodes(nodes, "the inn").map((entry) => entry.node_id)).toEqual([
      "location-inn",
    ]);
    expect(searchGraphProjectionNodes(nodes, "herb").map((entry) => entry.node_id)).toEqual([
      "npc-glowkindle",
    ]);
  });

  it("requires every token to match", () => {
    expect(searchGraphProjectionNodes(nodes, "glow quest").map((entry) => entry.node_id)).toEqual([
      "quest-rats",
    ]);
    expect(searchGraphProjectionNodes(nodes, "glow location")).toEqual([]);
  });

  it("respects limit", () => {
    expect(searchGraphProjectionNodes(nodes, "", { limit: 1 })).toHaveLength(1);
  });
});

describe("sortGraphProjectionNodes", () => {
  it("sorts by kind then label", () => {
    expect(sortGraphProjectionNodes(nodes).map((entry) => entry.node_id)).toEqual([
      "location-inn",
      "npc-glowkindle",
      "quest-rats",
    ]);
  });
});
