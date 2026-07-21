import { describe, expect, it } from "vitest";

import type { GraphProjectionNodeView } from "../api/types";
import { buildGraphObjectCardFromNodeView } from "./buildGraphObjectCardFromNodeView";
import { relationshipSessionStamp } from "./graphObjectDisplay";

const baseNode: GraphProjectionNodeView = {
  node_id: "npc-glowkindle",
  label: "Glowkindle",
  kind: "npc",
  role: "merchant",
  aliases: ["Glow", "The glow"],
  source_domains: ["recap", "authored_overlay"],
  evidence_badges: [
    {
      evidence_ref_id: "ev-1",
      source_artifact_id: "artifact-1",
      source_domain: "recap",
      evidence_role: "mention",
      is_focus_session_evidence: true,
      can_open_source: true,
      can_highlight_span: false,
      label: "Session recap mention",
    },
  ],
  adjacency: [
    {
      edge_id: "edge-1",
      node_id: "location-inn",
      label: "Inn (Mireward Reach)",
      kind: "location",
      predicate: "negotiated with",
      direction: "outgoing",
      anchored_to_focus_session: true,
      source_domains: ["recap"],
      evidence_ref_ids: ["ev-1"],
      session_ids: ["session-2"],
      campaign_scope: "longmont-c1",
      related_summary: "The party's meeting place.",
      source_excerpt: "They negotiated at the Inn after dusk.",
      source_excerpt_is_full_paragraph: true,
      source_excerpt_highlight_spans: [{ start: 24, end: 27 }],
    },
  ],
  anchored_to_focus_session: true,
  summary: "A friendly merchant who trades in rare herbs.",
  visibility: "table_known",
  campaign_scope: "longmont-c1",
  source_anchor_text: "Glowkindle waved from the stall",
};

describe("buildGraphObjectCardFromNodeView", () => {
  it("maps GraphProjectionNodeView fields into the card view model", () => {
    const model = buildGraphObjectCardFromNodeView(baseNode);

    expect(model.id).toBe("npc-glowkindle");
    expect(model.label).toBe("Glowkindle");
    expect(model.typeBadgeLabel).toBe("Npc");
    expect(model.secondaryRoleLabel).toBe("Merchant");
    expect(model.aliases).toEqual(["Glow", "The glow"]);
    expect(model.summary).toBe("A friendly merchant who trades in rare herbs.");
    expect(model.gameSummary).toBe("A friendly merchant who trades in rare herbs.");
    expect(model.campaignScope).toBe("longmont-c1");
    expect(model.campaignLabel).toBe("C1");
    expect(model.relationships).toEqual([
      {
        id: "edge-1",
        label: "Inn (Mireward Reach)",
        predicate: "negotiated with",
        direction: "outgoing",
        summary: "The party's meeting place.",
        targetId: "location-inn",
        targetKind: "location",
        evidenceRefIds: ["ev-1"],
        sourceDomains: ["recap"],
        anchoredToFocusSession: true,
        sessionIds: ["session-2"],
        campaignScope: "longmont-c1",
        sourceExcerpt: "They negotiated at the Inn after dusk.",
        sourceExcerptIsFullParagraph: true,
        sourceExcerptHighlightSpans: [{ start: 24, end: 27 }],
      },
    ]);
    expect(model.evidence).toEqual([
      {
        id: "ev-1",
        label: "Session recap mention",
        sourceArtifactId: "artifact-1",
        sourceDomain: "recap",
        sourcePath: null,
        excerpt: null,
      },
    ]);
    expect(model.sourceDomains).toEqual(["recap", "authored_overlay"]);
    expect(model.visibilityLabel).toBe("Table known");
    expect(model.details).toEqual({
      visibilityLabel: "Table known",
      sourceDomains: ["recap", "authored_overlay"],
      evidenceCount: 1,
      sourceAnchorText: "Glowkindle waved from the stall",
      nodeId: "npc-glowkindle",
    });
  });

  it("filters placeholder summaries and duplicate aliases", () => {
    const model = buildGraphObjectCardFromNodeView({
      ...baseNode,
      summary: "Deterministic party context anchor",
      aliases: ["Glowkindle", "Glow"],
    });

    expect(model.summary).toBeNull();
    expect(model.gameSummary).toBeNull();
    expect(model.aliases).toEqual(["Glow"]);
  });

  it("keeps C1 and C2 session-2 relationships distinguishable on the card", () => {
    const model = buildGraphObjectCardFromNodeView({
      ...baseNode,
      campaign_scope: "longmont-c1",
      adjacency: [
        {
          ...baseNode.adjacency[0],
          edge_id: "edge-c1",
          label: "C1 Inn",
          session_ids: ["session-2"],
          campaign_scope: "longmont-c1",
        },
        {
          ...baseNode.adjacency[0],
          edge_id: "edge-c2",
          node_id: "location-harbor",
          label: "C2 Harbor",
          session_ids: ["session-2"],
          campaign_scope: "longmont-c2",
        },
      ],
    });

    expect(model.campaignLabel).toBe("C1");
    expect(model.relationships?.map((row) => row.campaignScope)).toEqual([
      "longmont-c1",
      "longmont-c2",
    ]);
    expect(
      model.relationships?.map((row) =>
        relationshipSessionStamp(row.sessionIds, row.campaignScope),
      ),
    ).toEqual(["C1 · S2", "C2 · S2"]);
  });
});
