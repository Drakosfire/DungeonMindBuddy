import { describe, expect, it } from "vitest";

import {
  filterObjectRefPickerCandidates,
  type GraphObjectAuthoringInspectedNode,
} from "./GraphObjectAuthoringObjectRefPicker";

/**
 * Manual dogfood (Session 11 Author Node):
 * 1. Load Session 11 projection → open Author Node → New object
 * 2. Highlight BBQ → Use this text → Kind: event → Create object
 * 3. Stay on New object; banner confirms save; Source is BBQ
 * 4. Search Target for Festival… → Stage relationship (repeat for more edges)
 * 5. Prepare & commit on the same tab — no Existing / Relationships wizard hop
 */
describe("filterObjectRefPickerCandidates", () => {
  const nodes: GraphObjectAuthoringInspectedNode[] = [
    { node_id: "bbq", label: "BBQ", kind: "event", authored: false },
    {
      node_id: "festival",
      label: "Festival of Embers",
      kind: "event",
      aliases: ["Emberfest"],
      authored: true,
    },
    { node_id: "alden", label: "Alden", kind: "npc", authored: false },
  ];

  it("returns Festival when searching festival among many nodes", () => {
    const results = filterObjectRefPickerCandidates({
      query: "Festival",
      objectProposals: [],
      existingNodes: nodes,
      scopeCandidates: [],
    });

    expect(results.map((item) => item.label)).toEqual(["Festival of Embers"]);
  });

  it("matches aliases", () => {
    const results = filterObjectRefPickerCandidates({
      query: "Emberfest",
      objectProposals: [],
      existingNodes: nodes,
      scopeCandidates: [],
    });

    expect(results.map((item) => item.label)).toEqual(["Festival of Embers"]);
  });

  it("returns all nodes for an empty query", () => {
    const results = filterObjectRefPickerCandidates({
      query: "",
      objectProposals: [],
      existingNodes: nodes,
      scopeCandidates: [],
    });

    expect(results).toHaveLength(3);
  });
});
