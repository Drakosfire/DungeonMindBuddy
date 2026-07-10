import { describe, expect, it } from "vitest";

import type { GraphProjectionNodeView } from "../api/types";
import { buildGraphObjectCardFromNodeView } from "./buildGraphObjectCardFromNodeView";

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
      related_summary: "The party's meeting place.",
      source_excerpt: "They negotiated at the Inn after dusk.",
      source_excerpt_is_full_paragraph: true,
      source_excerpt_highlight_spans: [{ start: 24, end: 27 }],
    },
  ],
  anchored_to_focus_session: true,
  summary: "A friendly merchant who trades in rare herbs.",
  visibility: "table_known",
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
});
