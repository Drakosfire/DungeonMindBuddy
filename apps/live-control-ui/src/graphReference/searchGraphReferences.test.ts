import { describe, expect, it } from "vitest";

import type { GraphReferenceSearchItem } from "./types";
import { searchGraphReferences, sortGraphReferenceItems } from "./searchGraphReferences";
import { referenceFromGraphNode } from "./referenceFromGraphNode";

function item(
  overrides: Partial<GraphReferenceSearchItem> & Pick<GraphReferenceSearchItem, "nodeId" | "label">,
): GraphReferenceSearchItem {
  const nodeView = overrides.nodeView ?? {
    node_id: overrides.nodeId,
    label: overrides.label,
    kind: overrides.kind ?? "npc",
    role: overrides.role ?? "npc",
    aliases: overrides.aliases ?? [],
    source_domains: [],
    evidence_badges: [],
    adjacency: [],
    anchored_to_focus_session: true,
  };
  return {
    kind: overrides.kind ?? "npc",
    role: overrides.role ?? "npc",
    summary: overrides.summary ?? null,
    aliases: overrides.aliases ?? [],
    scopeLabel: overrides.scopeLabel ?? "world",
    reference: overrides.reference ?? referenceFromGraphNode(nodeView),
    nodeView,
    ...overrides,
  };
}

const items = [
  item({
    nodeId: "npc-glowkindle",
    label: "Glowkindle",
    kind: "npc",
    role: "merchant",
    aliases: ["Glow"],
    summary: "A friendly herb trader.",
  }),
  item({
    nodeId: "location-inn",
    label: "Inn",
    kind: "location",
    role: "location",
    aliases: ["The Inn"],
  }),
  item({
    nodeId: "quest-rats",
    label: "Glowkindle Rats",
    kind: "quest",
    role: "job",
  }),
];

describe("searchGraphReferences", () => {
  it("returns all items for an empty query", () => {
    expect(searchGraphReferences(items, "").map((entry) => entry.nodeId)).toEqual([
      "npc-glowkindle",
      "location-inn",
      "quest-rats",
    ]);
  });

  it("matches label, alias, kind, and summary tokens", () => {
    expect(searchGraphReferences(items, "glow").map((entry) => entry.nodeId)).toEqual([
      "npc-glowkindle",
      "quest-rats",
    ]);
    expect(searchGraphReferences(items, "merchant").map((entry) => entry.nodeId)).toEqual([
      "npc-glowkindle",
    ]);
    expect(searchGraphReferences(items, "the inn").map((entry) => entry.nodeId)).toEqual([
      "location-inn",
    ]);
    expect(searchGraphReferences(items, "herb").map((entry) => entry.nodeId)).toEqual([
      "npc-glowkindle",
    ]);
  });

  it("requires every token to match", () => {
    expect(searchGraphReferences(items, "glow quest").map((entry) => entry.nodeId)).toEqual([
      "quest-rats",
    ]);
    expect(searchGraphReferences(items, "glow location")).toEqual([]);
  });

  it("respects limit", () => {
    expect(searchGraphReferences(items, "", { limit: 1 })).toHaveLength(1);
  });
});

describe("sortGraphReferenceItems", () => {
  it("sorts by kind then label", () => {
    expect(sortGraphReferenceItems(items).map((entry) => entry.nodeId)).toEqual([
      "location-inn",
      "npc-glowkindle",
      "quest-rats",
    ]);
  });
});
