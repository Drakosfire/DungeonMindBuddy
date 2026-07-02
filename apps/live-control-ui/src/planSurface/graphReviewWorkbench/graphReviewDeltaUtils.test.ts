import { describe, expect, it } from "vitest";

import type { GoldReviewCompareResponse, GraphReviewLane, UnionSupergraphProjectionResponse } from "../../api/types";
import { GRAPH_REVIEW_DELTA_OBJECT_KINDS, GRAPH_REVIEW_DELTA_STATUSES } from "./graphReviewDeltaTypes";
import { buildGraphReviewDeltaIndex } from "./graphReviewDeltaUtils";

const goldLane: GraphReviewLane = {
  laneId: "gold-lane",
  role: "gold",
  sourceKind: "gold_fixture",
  label: "Gold",
  campaignId: "c1",
  sessionId: "s1",
  status: "available",
  counts: { nodes: 1, edges: 0 },
  metadata: {},
};

const liveLane: GraphReviewLane = {
  laneId: "live-lane",
  role: "live",
  sourceKind: "graph_ingest_run",
  label: "Live",
  campaignId: "c1",
  sessionId: "s1",
  manifestPath: "runs/live/manifest.json",
  status: "available",
  counts: { nodes: 1, edges: 0 },
  metadata: {},
};

function compare(overrides: Partial<GoldReviewCompareResponse> = {}): GoldReviewCompareResponse {
  return {
    schema_version: "dmb_graph_gold_review_compare_v1",
    version: "1",
    session_id: "s1",
    campaign_id: "c1",
    gold_fixture_id: "gold",
    gold_manifest_path: "gold/manifest.json",
    gold_graph_path: "gold/graph.json",
    live_run: null,
    comparison: { scores: {}, coverage: {}, soft_misses: [] },
    object_index: { gold: {}, live: {} },
    match_pairs: {},
    ...overrides,
  };
}

const projection: UnionSupergraphProjectionResponse = {
  campaign_id: "c1",
  session_id: "s1",
  graph_id: "g1",
  focus: { focus_session_id: "s1", focused_evidence_ref_ids: [], focused_edge_ids: [], focused_node_ids: [] },
  node_views: {
    "live-node-1": {
      node_id: "live-node-1",
      label: "Lysandra Ironveil",
      kind: "actor",
      role: "candidate",
      aliases: [],
      source_domains: [],
      evidence_badges: [
        { evidence_ref_id: "ev1", source_artifact_id: "a1", source_domain: "recap", evidence_role: "source_evidence", is_focus_session_evidence: true, can_open_source: true, can_highlight_span: true, source_span_ref_id: "source-span-12" },
      ],
      adjacency: [],
      anchored_to_focus_session: true,
    },
  },
  mentions: [],
};

describe("buildGraphReviewDeltaIndex", () => {
  it("returns an empty warned index when comparison is missing", () => {
    const index = buildGraphReviewDeltaIndex({ compare: null, liveProjection: null, goldLane, liveLane });
    expect(index.deltas).toEqual([]);
    expect(index.warnings).toContain("Comparison is not loaded yet.");
  });

  it("emits matched deltas with gold and live refs", () => {
    const index = buildGraphReviewDeltaIndex({ compare: compare({ object_index: { gold: { g: { object_kind: "node", object_id: "gold-node-1", label: "Lysandra", payload: {} } }, live: { l: { object_kind: "node", object_id: "live-node-1", label: "Lysandra", payload: {} } } }, match_pairs: { node: [{ gold_id: "gold-node-1", live_id: "live-node-1", score: 0.9 }] } }), liveProjection: projection, goldLane, liveLane });
    expect(index.deltas).toHaveLength(1);
    expect(index.deltas[0].status).toBe("matched");
    expect(index.deltas[0].laneObjectRefs.map((ref) => ref.laneRole)).toEqual(["gold", "live"]);
  });

  it("emits gold_only for unmatched gold objects", () => {
    const index = buildGraphReviewDeltaIndex({ compare: compare({ object_index: { gold: { g: { object_kind: "edge", object_id: "gold-edge-1", label: "North Gate defense chain", payload: {} } }, live: {} } }), liveProjection: null, goldLane, liveLane });
    expect(index.deltas[0].status).toBe("gold_only");
  });

  it("emits live_only for unmatched live objects", () => {
    const index = buildGraphReviewDeltaIndex({ compare: compare({ object_index: { gold: {}, live: { l: { object_kind: "node", object_id: "live-node-1", label: "Tripod Null-Calf", payload: {} } } } }), liveProjection: projection, goldLane, liveLane });
    expect(index.deltas[0].status).toBe("live_only");
  });

  it("emits comparator_uncertain when a pair references a missing object", () => {
    const index = buildGraphReviewDeltaIndex({ compare: compare({ object_index: { gold: { g: { object_kind: "node", object_id: "gold-node-1", label: "Lysandra", payload: {} } }, live: {} }, match_pairs: { node: [{ gold_id: "gold-node-1", live_id: "live-node-42", score: 0.1 }] } }), liveProjection: null, goldLane, liveLane });
    expect(index.deltas.some((delta) => delta.status === "comparator_uncertain")).toBe(true);
    expect(index.deltas[0].summary).toContain("missing live object live-node-42");
  });

  it("emits comparator_uncertain for duplicate pairs", () => {
    const index = buildGraphReviewDeltaIndex({ compare: compare({ object_index: { gold: { g: { object_kind: "node", object_id: "gold-node-1", label: "Lysandra", payload: {} } }, live: { l1: { object_kind: "node", object_id: "live-node-1", label: "Lysandra", payload: {} }, l2: { object_kind: "node", object_id: "live-node-2", label: "Lysandra II", payload: {} } } }, match_pairs: { node: [{ gold_id: "gold-node-1", live_id: "live-node-1", score: 0.9 }, { gold_id: "gold-node-1", live_id: "live-node-2", score: 0.8 }] } }), liveProjection: null, goldLane, liveLane });
    expect(index.deltas.some((delta) => delta.status === "comparator_uncertain" && delta.summary.includes("duplicate gold object"))).toBe(true);
  });

  it("attaches live projection node source span refs", () => {
    const index = buildGraphReviewDeltaIndex({ compare: compare({ object_index: { gold: { g: { object_kind: "node", object_id: "gold-node-1", label: "Lysandra", payload: {} } }, live: { l: { object_kind: "node", object_id: "live-node-1", label: "Lysandra", payload: {} } } }, match_pairs: { node: [{ gold_id: "gold-node-1", live_id: "live-node-1", score: 0.9 }] } }), liveProjection: projection, goldLane, liveLane });
    expect(index.deltas[0].primarySourceSpanRefId).toBe("source-span-12");
  });

  it("initializes all count keys", () => {
    const index = buildGraphReviewDeltaIndex({ compare: null, liveProjection: null, goldLane, liveLane });
    expect(Object.keys(index.countsByStatus)).toEqual(GRAPH_REVIEW_DELTA_STATUSES);
    expect(Object.keys(index.countsByObjectKind)).toEqual(GRAPH_REVIEW_DELTA_OBJECT_KINDS);
  });

  it("sorts deltas deterministically", () => {
    const input = compare({ object_index: { gold: { b: { object_kind: "node", object_id: "b", label: "B", payload: {} }, a: { object_kind: "node", object_id: "a", label: "A", payload: {} } }, live: { c: { object_kind: "node", object_id: "c", label: "C", payload: {} } } } });
    const first = buildGraphReviewDeltaIndex({ compare: input, liveProjection: null, goldLane, liveLane }).deltas.map((delta) => delta.deltaId);
    const second = buildGraphReviewDeltaIndex({ compare: input, liveProjection: null, goldLane, liveLane }).deltas.map((delta) => delta.deltaId);
    expect(first).toEqual(second);
    expect(first).toEqual([...first].sort());
  });
});
