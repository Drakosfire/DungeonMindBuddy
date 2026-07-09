import { describe, expect, it } from "vitest";
import type { GraphProjectionAdjacencyCandidate, GraphProjectionNodeView } from "../../api/types";
import type { GraphReviewDeltaIndex } from "./graphReviewDeltaTypes";
import {
  durableIdentitySummaryForNode,
  formatGraphReviewRelationshipStatement,
  gameSummaryForNode,
  graphObjectSecondaryRoleLabel,
  graphObjectTypeBadgeLabel,
  groupRelationshipsByEvidence,
  mergedIdentityNoteCopy,
  relationshipGroupLabel,
  relationshipGroupMetaLine,
  resolveGraphReviewSelectedNode,
} from "./graphReviewSelectionUtils";

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
    expect(formatGraphReviewRelationshipStatement("Tripod Null-Calf", goldNode.adjacency[0])).toBe(
      "North Gate · threatens",
    );
    expect(formatGraphReviewRelationshipStatement("Tripod Null-Calf", { ...goldNode.adjacency[0], direction: "incoming", label: "Shepherd hymn", predicate: "empowers" })).toBe(
      "Shepherd hymn · empowers",
    );
    expect(gameSummaryForNode(goldOnlyNode)).toBeNull();
    expect(gameSummaryForNode(goldNode)).toBe("Siege scout and gate-pressure monster.");
    expect(gameSummaryForNode({ ...goldOnlyNode, aliases: ["defenders"], summary: null })).toBe(
      "This threat is also known as defenders.",
    );
    expect(gameSummaryForNode({ ...goldNode, summary: null })).toBe(
      "This threat has 1 connected campaign relationship in this session.",
    );
    expect(
      gameSummaryForNode({
        ...goldOnlyNode,
        summary: "Deterministic party context anchor",
        aliases: ["Lysandra"],
      }),
    ).toBe("This threat is also known as Lysandra.");
  });

  it("formats object type badges for the selected object header", () => {
    expect(graphObjectTypeBadgeLabel("character", "companion")).toBe("Character");
    expect(graphObjectSecondaryRoleLabel("character", "companion")).toBe("Companion");
    expect(graphObjectTypeBadgeLabel("location", "location")).toBe("Location");
    expect(graphObjectSecondaryRoleLabel("location", "location")).toBeNull();
    expect(graphObjectTypeBadgeLabel(null, null)).toBe("Object");
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

  it("groups relationships grounded in the identical highlighted source phrase", () => {
    const sharedExcerpt =
      "Bonogo and Karsemine slipped past the guards while the others caused a distraction.";
    const bonogoRelationship: GraphProjectionAdjacencyCandidate = {
      edge_id: "edge-bonogo",
      node_id: "pc_bonogo",
      label: "Bonogo",
      kind: "pc",
      predicate: "present_at",
      direction: "outgoing",
      anchored_to_focus_session: true,
      source_domains: ["recap"],
      evidence_ref_ids: ["ev-bonogo"],
      session_ids: ["session-23"],
      source_excerpt: sharedExcerpt,
      source_excerpt_is_full_paragraph: true,
      source_excerpt_highlight_spans: [{ start: 0, end: 24 }],
    };
    const karsemineRelationship: GraphProjectionAdjacencyCandidate = {
      ...bonogoRelationship,
      edge_id: "edge-karsemine",
      node_id: "pc_karsemine",
      label: "Karsemine",
      evidence_ref_ids: ["ev-karsemine"],
    };
    const unrelatedRelationship: GraphProjectionAdjacencyCandidate = {
      edge_id: "edge-inn",
      node_id: "location_inn",
      label: "Inn",
      kind: "location",
      predicate: "located_at",
      direction: "outgoing",
      anchored_to_focus_session: true,
      source_domains: ["recap"],
      evidence_ref_ids: ["ev-inn"],
      session_ids: ["session-23"],
    };

    const groups = groupRelationshipsByEvidence([
      bonogoRelationship,
      karsemineRelationship,
      unrelatedRelationship,
    ]);

    expect(groups).toHaveLength(2);
    const sharedGroup = groups.find((group) => group.members.length === 2);
    expect(sharedGroup?.members.map((member) => member.node_id)).toEqual([
      "pc_bonogo",
      "pc_karsemine",
    ]);
    expect(relationshipGroupLabel(sharedGroup!.members)).toBe("Bonogo & Karsemine");
    expect(relationshipGroupMetaLine(sharedGroup!.members)).toBe("present at · pc");

    const soloGroup = groups.find((group) => group.members.length === 1);
    expect(soloGroup?.members[0].node_id).toBe("location_inn");
  });

  it("does not group relationships whose highlighted phrases differ", () => {
    const bonogoRelationship: GraphProjectionAdjacencyCandidate = {
      edge_id: "edge-bonogo",
      node_id: "pc_bonogo",
      label: "Bonogo",
      kind: "pc",
      predicate: "present_at",
      direction: "outgoing",
      anchored_to_focus_session: true,
      source_domains: ["recap"],
      evidence_ref_ids: ["ev-bonogo"],
      session_ids: ["session-23"],
      source_excerpt: "Bonogo climbed the wall while Karsemine watched the gate below.",
      source_excerpt_is_full_paragraph: true,
      source_excerpt_highlight_spans: [{ start: 0, end: 21 }],
    };
    const karsemineRelationship: GraphProjectionAdjacencyCandidate = {
      ...bonogoRelationship,
      edge_id: "edge-karsemine",
      node_id: "pc_karsemine",
      label: "Karsemine",
      evidence_ref_ids: ["ev-karsemine"],
      source_excerpt_highlight_spans: [{ start: 30, end: 65 }],
    };

    const groups = groupRelationshipsByEvidence([bonogoRelationship, karsemineRelationship]);
    expect(groups).toHaveLength(2);
  });
});
