import { describe, expect, it } from "vitest";

import type { GraphProjectionNodeView } from "../../api/types";
import { runbookReferenceFromGraphNode } from "./runbookReferenceFromGraphNode";

function node(
  overrides: Partial<GraphProjectionNodeView> & Pick<GraphProjectionNodeView, "node_id" | "label" | "kind">,
): GraphProjectionNodeView {
  return {
    role: "npc",
    aliases: [],
    source_domains: [],
    evidence_badges: [],
    adjacency: [],
    anchored_to_focus_session: true,
    ...overrides,
  };
}

describe("runbookReferenceFromGraphNode", () => {
  it("maps known kinds to corpus ref types and keeps node id", () => {
    expect(
      runbookReferenceFromGraphNode(
        node({ node_id: "npc-glowkindle", label: "Glowkindle", kind: "actor" }),
      ),
    ).toEqual({
      kind: "ref",
      refType: "npc",
      refId: "npc-glowkindle",
      label: "Glowkindle",
    });
  });

  it("uses refType node for unmapped graph kinds", () => {
    expect(
      runbookReferenceFromGraphNode(
        node({ node_id: "quest-rats", label: "Glowkindle Rats", kind: "quest" }),
      ),
    ).toEqual({
      kind: "ref",
      refType: "node",
      refId: "quest-rats",
      label: "Glowkindle Rats",
    });
  });
});
