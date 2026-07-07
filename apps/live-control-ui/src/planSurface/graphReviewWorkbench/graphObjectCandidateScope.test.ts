import { describe, expect, it } from "vitest";

import type { GraphReviewExistingObjectCandidate } from "../../api/types";
import {
  GRAPH_OBJECT_CANDIDATE_SCOPE_LABELS,
  groupCandidatesByScope,
  inferCandidateGraphScopeFromProjectionNode,
  resolverCandidateToInspectedNode,
} from "./graphObjectCandidateScope";

describe("graphObjectCandidateScope", () => {
  it("groups candidates by scope without collapsing same labels", () => {
    const candidates: GraphReviewExistingObjectCandidate[] = [
      {
        candidate_id: "authored:1",
        label: "Questionable Company",
        kind: "party",
        confidence: "high",
        score: 0.95,
        reason: "Alias match: gang",
        source: "union_supergraph",
        suggested_action: "link_existing_later",
        matched_features: [],
        graph_scope: "authored_overlay",
        source_label: GRAPH_OBJECT_CANDIDATE_SCOPE_LABELS.authored_overlay,
      },
      {
        candidate_id: "gang-node",
        label: "gang",
        kind: "unknown",
        confidence: "high",
        score: 1,
        reason: "Exact label match",
        source: "live_projection",
        suggested_action: "link_existing_later",
        matched_features: [],
        graph_scope: "current_recap_projection",
        source_label: GRAPH_OBJECT_CANDIDATE_SCOPE_LABELS.current_recap_projection,
      },
    ];

    const grouped = groupCandidatesByScope(candidates);
    expect(grouped).toHaveLength(2);
    expect(grouped[0]?.candidates[0]?.label).toBe("Questionable Company");
    expect(grouped[1]?.candidates[0]?.label).toBe("gang");
  });

  it("maps resolver candidates into inspected nodes with source metadata", () => {
    const inspected = resolverCandidateToInspectedNode({
      candidate_id: "party:bonogo",
      label: "Bonogo",
      kind: "pc",
      confidence: "high",
      score: 1,
      reason: "Exact label match",
      source: "union_supergraph",
      suggested_action: "link_existing_later",
      matched_features: [],
      graph_scope: "party_pc",
      source_label: "Party / PCs",
    });

    expect(inspected).toMatchObject({
      node_id: "party:bonogo",
      label: "Bonogo",
      graphScope: "party_pc",
      sourceLabel: "Party / PCs",
    });
  });

  it("maps recap source_domains to current_recap_projection", () => {
    expect(
      inferCandidateGraphScopeFromProjectionNode({
        source_domains: ["recap"],
        kind: "location",
        role: "candidate",
      }),
    ).toBe("current_recap_projection");
  });

  it("maps authored overlay nodes to authored_overlay scope", () => {
    expect(
      inferCandidateGraphScopeFromProjectionNode({
        source_domains: ["authored_overlay"],
        authored: true,
        kind: "party",
        role: "authored",
      }),
    ).toBe("authored_overlay");
  });
});
