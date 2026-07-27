import { describe, expect, it } from "vitest";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

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
  campaignScope: "longmont-c1",
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
    campaignScope: "longmont-c1",
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
      campaign_scope: "longmont-c1",
      source_domains: ["recap"],
      evidence_badges: [{ evidence_ref_id: "ev-1", source_artifact_id: "artifact-1" }],
      adjacency: [{
        edge_id: "edge-1",
        node_id: "location-inn",
        source_domains: ["recap"],
        campaign_scope: "longmont-c1",
      }],
      anchored_to_focus_session: true,
    });
  });

  it("passes normalized outgoing direction through unchanged", () => {
    const adapted = adaptWorldGraphNodeForPlanCard(node);
    expect(adapted.adjacency[0]?.direction).toBe("outgoing");
  });

  it("passes normalized incoming direction through unchanged", () => {
    const inboundNode: WorldGraphProjectionNodeView = {
      ...node,
      adjacency: [{
        ...node.adjacency[0],
        direction: "incoming",
      }],
    };
    expect(adaptWorldGraphNodeForPlanCard(inboundNode).adjacency[0]?.direction).toBe("incoming");
  });

  it("passes related direction through unchanged", () => {
    const relatedNode: WorldGraphProjectionNodeView = {
      ...node,
      adjacency: [{
        ...node.adjacency[0],
        direction: "related",
      }],
    };
    expect(adaptWorldGraphNodeForPlanCard(relatedNode).adjacency[0]?.direction).toBe("related");
  });
});

describe("worldGraphProjectionAdapter PR380B hoist compatibility", () => {
  it("currently owns adaptWorldGraphNodeForPlanCard locally (pre-hoist)", () => {
    expect(adaptWorldGraphNodeForPlanCard).toBeTypeOf("function");
  });

  it("target: neutral worldGraphNodeViewAdapter module will replace direct Plan ownership", () => {
    expect(
      existsSync(
        path.join(
          path.dirname(fileURLToPath(import.meta.url)),
          "../../worldGraph/worldGraphNodeViewAdapter.ts",
        ),
      ),
    ).toBe(false);
  });
});
