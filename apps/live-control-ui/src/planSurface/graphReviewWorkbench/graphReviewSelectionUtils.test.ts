import { describe, expect, it } from "vitest";
import type { GraphProjectionNodeView } from "../../api/types";
import type { GraphReviewDeltaIndex } from "./graphReviewDeltaTypes";
import { formatGraphReviewRelationshipStatement, gameSummaryForNode, mergedIdentityNoteCopy, resolveGraphReviewSelectedNode, durableIdentitySummaryForNode } from "./graphReviewSelectionUtils";

const goldNode: GraphProjectionNodeView = {
  node_id: "gold-tripod",
  label: "Tripod Null-Calf",
  kind: "Threat",
  role: "Siege scout",
  aliases: [],
  source_domains: ["fixture"],
  evidence_badges: [],
  adjacency: [
    { edge_id: "edge-threatens", node_id: "north-gate", label: "North Gate", kind: "location", predicate: "threatens", direction: "outgoing", anchored_to_focus_session: true, source_domains: ["fixture"], evidence_ref_ids: ["ev1"], session_ids: ["session-1"] },
  ],
  anchored_to_focus_session: true,
  summary: "Siege scout and gate-pressure monster.",
};
const liveNode: GraphProjectionNodeView = { ...goldNode, node_id: "live-tripod", source_domains: ["run"] };
const goldOnlyNode: GraphProjectionNodeView = { ...goldNode, node_id: "gold-only", label: "Mireward defenders", adjacency: [], summary: null };

const deltaIndex: GraphReviewDeltaIndex = {
  schemaVersion: "dmb_graph_review_contextual_delta_index_v1",
  campaignId: "longmont-c1",
  sessionId: "session-1",
  goldLaneId: "gold",
  liveLaneId: "live",
  liveRunManifestPath: "manifest.json",
  countsByObjectKind: { node: 2, edge: 0, mention: 0, source_span: 0, beat: 0, write: 0, ignored_item: 0, deferred_item: 0, unknown: 0 },
  countsByStatus: { matched: 1, gold_only: 1, live_only: 0, changed_type: 0, changed_label: 0, changed_evidence: 0, changed_edges: 0, comparator_uncertain: 0 },
  warnings: [],
  deltas: [
    { deltaId: "matched", objectKind: "node", status: "matched", laneObjectRefs: [
      { laneId: "gold", laneRole: "gold", objectKind: "node", objectId: "gold-tripod", label: "Tripod Null-Calf" },
      { laneId: "live", laneRole: "live", objectKind: "node", objectId: "live-tripod", label: "Tripod Null-Calf" },
    ], label: "Tripod Null-Calf", summary: "Matched", sourceSpanRefIds: [], evidenceRefIds: [] },
    { deltaId: "gold-only", objectKind: "node", status: "gold_only", laneObjectRefs: [
      { laneId: "gold", laneRole: "gold", objectKind: "node", objectId: "gold-only", label: "Mireward defenders" },
    ], label: "Mireward defenders", summary: "Gold-only", sourceSpanRefIds: [], evidenceRefIds: [] },
  ],
};

const projections = {
  goldProjection: { node_views: { "gold-tripod": goldNode, "gold-only": goldOnlyNode } } as any,
  liveProjection: { node_views: { "live-tripod": liveNode } } as any,
};

describe("graphReviewSelectionUtils", () => {
  it("resolves selected gold and live matched counterparts", () => {
    expect(resolveGraphReviewSelectedNode({ laneRole: "gold", nodeId: "gold-tripod" }, projections, deltaIndex)?.counterpart?.nodeId).toBe("live-tripod");
    expect(resolveGraphReviewSelectedNode({ laneRole: "live", nodeId: "live-tripod" }, projections, deltaIndex)?.counterpart?.nodeId).toBe("gold-tripod");
  });

  it("resolves gold-only status without counterpart and handles missing nodes", () => {
    const selected = resolveGraphReviewSelectedNode({ laneRole: "gold", nodeId: "gold-only" }, projections, deltaIndex);
    expect(selected?.status).toBe("gold_only");
    expect(selected?.counterpart).toBeNull();
    expect(resolveGraphReviewSelectedNode({ laneRole: "live", nodeId: "missing" }, projections, deltaIndex)).toBeNull();
  });

  it("formats relationships and deterministic fallback summaries", () => {
    expect(formatGraphReviewRelationshipStatement("Tripod Null-Calf", goldNode.adjacency[0])).toBe("Tripod Null-Calf threatens North Gate");
    expect(formatGraphReviewRelationshipStatement("Tripod Null-Calf", { ...goldNode.adjacency[0], direction: "incoming", label: "Shepherd hymn", predicate: "empowers" })).toBe("Shepherd hymn empowers Tripod Null-Calf");
    expect(gameSummaryForNode(goldOnlyNode)).toBe("No campaign summary has been authored yet.");
    expect(gameSummaryForNode(goldNode)).toBe("Siege scout and gate-pressure monster.");
    expect(gameSummaryForNode({ ...goldOnlyNode, aliases: ["defenders"], summary: null })).toBe(
      "This threat is also known as defenders.",
    );
    expect(gameSummaryForNode({ ...goldNode, summary: null })).toBe(
      "This threat has 1 connected campaign relationship in this session.",
    );
  });

  it("builds durable identity summaries defensively and human-facing merge copy", () => {
    const survivor = {
      ...goldNode,
      merged_away_ids: ["node:lysandra"],
      merge_assertion_ids: ["assert-merge-lysandra"],
      identity_redirect_ids: ["redirect:lysandra"],
      identity_merge_record_ids: ["merge_record:lysandra"],
      aliases: ["Captain Lysandra Ironveil", "Lysandra"],
    };
    const summary = durableIdentitySummaryForNode(survivor);
    expect(summary?.foldedIdentityCount).toBe(1);
    expect(durableIdentitySummaryForNode(goldNode)).toBeNull();
    expect(mergedIdentityNoteCopy(summary!, survivor.aliases).foldedLine).toBe(
      "Folded in 1 prior identity: Lysandra.",
    );
  });
});
