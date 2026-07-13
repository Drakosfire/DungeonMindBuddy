import { describe, expect, it } from "vitest";

import type { WorldGraphProjectionNodeView } from "../../api/types";
import { adaptWorldGraphNodeForPlanCard } from "./worldGraphProjectionAdapter";

const node: WorldGraphProjectionNodeView = {
  nodeId: "npc-glowkindle",
  label: "Glowkindle",
  kind: "npc",
  role: "merchant",
  aliases: ["Glow"],
  sourceDomains: ["recap"],
  summary: "A friendly merchant.",
  anchoredToFocusSession: true,
  evidenceBadges: [{
    evidenceRefId: "ev-1",
    sourceArtifactId: "artifact-1",
    sourceDomain: "recap",
    evidenceRole: "mention",
    isFocusSessionEvidence: true,
    canOpenSource: true,
    canHighlightSpan: true,
    label: "Session recap mention",
    sessionId: "session-21",
    sourceSpanRefId: "span-1",
  }],
  adjacency: [{
    edgeId: "edge-1",
    nodeId: "location-inn",
    label: "Inn",
    kind: "location",
    predicate: "met at",
    direction: "outgoing",
    anchoredToFocusSession: true,
    sourceDomains: ["recap"],
    evidenceRefIds: ["ev-1"],
    sessionIds: ["session-21"],
    relatedSummary: "Trades herbs.",
    sourceExcerpt: "Glowkindle waved from the inn.",
  }],
  suggestedExpansions: [],
  evidenceRefIds: ["ev-1"],
  sourceArtifactIds: ["artifact-1"],
};

describe("adaptWorldGraphNodeForPlanCard", () => {
  it("adapts camelCase World Graph fields at the Plan card boundary", () => {
    expect(adaptWorldGraphNodeForPlanCard(node)).toMatchObject({
      node_id: "npc-glowkindle",
      source_domains: ["recap"],
      evidence_badges: [{ evidence_ref_id: "ev-1", source_artifact_id: "artifact-1" }],
      adjacency: [{ edge_id: "edge-1", node_id: "location-inn", source_domains: ["recap"] }],
      anchored_to_focus_session: true,
    });
  });
});
