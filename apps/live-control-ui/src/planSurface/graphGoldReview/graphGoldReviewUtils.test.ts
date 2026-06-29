import { describe, expect, it } from "vitest";

import {
  buildMissGroups,
  formatRecall,
  headlineScores,
  pickDefaultSession,
} from "./graphGoldReviewUtils";

describe("graphGoldReviewUtils", () => {
  it("formats recall percentages", () => {
    expect(formatRecall(0.845)).toBe("84.5%");
    expect(formatRecall(undefined)).toBe("n/a");
  });

  it("picks requested session when present in gold sessions", () => {
    const sessions = [
      {
        session_id: "session-22",
        session_number: 22,
        campaign_id: "longmont-c2",
        gold_fixture_id: "gold-22",
        gold_manifest_path: "m22",
        gold_graph_path: "g22",
        gold_counts: {},
        available_runs: [],
      },
      {
        session_id: "session-23",
        session_number: 23,
        campaign_id: "longmont-c2",
        gold_fixture_id: "gold-23",
        gold_manifest_path: "m23",
        gold_graph_path: "g23",
        gold_counts: {},
        available_runs: [],
      },
    ];
    expect(pickDefaultSession(sessions, "session-23", "session-22")).toBe("session-23");
    expect(pickDefaultSession(sessions, null, "session-22")).toBe("session-23");
  });

  it("builds miss groups from comparison coverage", () => {
    const compare = {
      schema_version: "dmb_graph_gold_review_compare_v1" as const,
      version: "0.1",
      session_id: "session-23",
      campaign_id: "longmont-c2",
      gold_fixture_id: "gold-23",
      gold_manifest_path: "m23",
      gold_graph_path: "g23",
      live_run: null,
      comparison: {
        scores: {
          node_recall: 0.5,
          edge_recall: 0,
          beat_recall: 0,
          proposed_write_recall: 0,
        },
        coverage: {
          missing_gold_nodes: [{ id: "node:foo", label: "Foo" }],
          extra_candidate_edges: [{ id: "edge:bar", label: "Bar" }],
        },
        soft_misses: [],
      },
      object_index: { gold: {}, live: {} },
      match_pairs: {},
    };
    const groups = buildMissGroups(compare);
    expect(groups.find((group) => group.kind === "nodes")?.missing).toEqual([
      { id: "node:foo", label: "Foo" },
    ]);
    expect(headlineScores(compare)[0]).toEqual({ label: "Node recall", value: "50%" });
  });
});
