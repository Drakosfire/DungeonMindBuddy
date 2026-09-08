import { describe, expect, it } from "vitest";

import type { WorldGraphProjectionNodeView } from "../api/types";
import { buildGraphObjectCardFromNodeView } from "../graphObjectCard/buildGraphObjectCardFromNodeView";
import { session23WorldGraphRecapFixture } from "../planSurface/graphPreview/worldGraphRecapFixture";
import { adaptWorldGraphNodeForPlanCard } from "../planSurface/reference/worldGraphProjectionAdapter";
import { adaptWorldGraphNodeView } from "./worldGraphNodeViewAdapter";

const provenanceNode: WorldGraphProjectionNodeView = {
  nodeId: "node:orik",
  label: "Orik",
  kind: "npc",
  role: "npc",
  aliases: ["Orik"],
  sourceDomains: ["recap"],
  summary: "A Mireward defender.",
  anchoredToFocusSession: true,
  campaignScope: "longmont-c2",
  evidenceBadges: [],
  adjacency: [
    {
      edgeId: "edge:orik:associated_with:brin",
      nodeId: "node:brin",
      label: "Brin",
      kind: "npc",
      predicate: "associated_with",
      direction: "outgoing",
      anchoredToFocusSession: true,
      sourceDomains: ["recap"],
      evidenceRefIds: ["evidence:c2s25:orik-brin"],
      edgeLabel: "associated with",
      sessionIds: ["session-25"],
      campaignScope: "longmont-c2",
      relatedSummary: "Sheltered with Orik.",
      sourceExcerpt: "Orik and Brin sheltered in the warehouse.",
      sourceExcerptIsFullParagraph: true,
      sourceExcerptHighlightSpans: [{ start: 13, end: 17 }],
    },
  ],
  suggestedExpansions: [
    {
      edgeId: "edge:orik:associated_with:brin",
      nodeId: "node:brin",
      label: "Brin",
      kind: "npc",
      predicate: "associated_with",
      direction: "outgoing",
      anchoredToFocusSession: true,
      sourceDomains: ["recap"],
      evidenceRefIds: ["evidence:c2s25:orik-brin"],
      edgeLabel: "associated with",
      sessionIds: ["session-25"],
      campaignScope: "longmont-c2",
      relatedSummary: "Sheltered with Orik.",
      sourceExcerpt: "Orik and Brin sheltered in the warehouse.",
      sourceExcerptIsFullParagraph: true,
      sourceExcerptHighlightSpans: [{ start: 13, end: 17 }],
      rank: 1,
      rankReason: "current session",
    },
  ],
  evidenceRefIds: ["evidence:c2s25:orik-brin"],
  sourceArtifactIds: ["artifact:recap:longmont-c2:session-25:fd38b5915b32"],
};

describe("worldGraphNodeViewAdapter", () => {
  it("preserves focus-anchored and prior-context posture", () => {
    const { nodeViews } = session23WorldGraphRecapFixture;
    expect(adaptWorldGraphNodeView(nodeViews.pc_caelynn).anchored_to_focus_session).toBe(true);
    expect(adaptWorldGraphNodeView(nodeViews.loc_mirathorn).anchored_to_focus_session).toBe(false);
  });

  it("Plan compatibility alias delegates to the neutral adapter", () => {
    const adapted = adaptWorldGraphNodeForPlanCard(session23WorldGraphRecapFixture.nodeViews.pc_caelynn);
    expect(adapted.node_id).toBe("pc_caelynn");
    expect(adapted.anchored_to_focus_session).toBe(true);
  });

  it("preserves relationship provenance fields through node view and card adaptation", () => {
    const adapted = adaptWorldGraphNodeView(provenanceNode);
    const adjacency = adapted.adjacency[0];
    expect(adjacency.source_excerpt).toBe("Orik and Brin sheltered in the warehouse.");
    expect(adjacency.source_excerpt_is_full_paragraph).toBe(true);
    expect(adjacency.source_excerpt_highlight_spans).toEqual([{ start: 13, end: 17 }]);
    expect(adapted.suggested_expansions?.[0]?.source_excerpt_is_full_paragraph).toBe(true);
    expect(adapted.suggested_expansions?.[0]?.source_excerpt_highlight_spans).toEqual([
      { start: 13, end: 17 },
    ]);

    const card = buildGraphObjectCardFromNodeView(adapted);
    expect(card.relationships).toEqual([
      expect.objectContaining({
        id: "edge:orik:associated_with:brin",
        targetId: "node:brin",
        sourceExcerpt: "Orik and Brin sheltered in the warehouse.",
        sourceExcerptIsFullParagraph: true,
        sourceExcerptHighlightSpans: [{ start: 13, end: 17 }],
      }),
    ]);
  });
});
