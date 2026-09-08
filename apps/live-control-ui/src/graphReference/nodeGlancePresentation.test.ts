import { describe, expect, it } from "vitest";

import type { GraphProjectionNodeView } from "../api/types";
import { buildGraphNodeGlancePresentation } from "./nodeGlancePresentation";

function orikNode(overrides: Partial<GraphProjectionNodeView> = {}): GraphProjectionNodeView {
  return {
    node_id: "npc:orik",
    label: "Orik",
    kind: "npc",
    role: "npc",
    aliases: [],
    source_domains: ["recap"],
    evidence_badges: [
      {
        evidence_ref_id: "ev-1",
        source_artifact_id: "artifact-1",
        source_domain: "recap",
        evidence_role: "support",
        is_focus_session_evidence: true,
        can_open_source: false,
        can_highlight_span: false,
      },
    ],
    adjacency: [
      {
        edge_id: "edge-orik-brin",
        node_id: "npc:brin",
        label: "Brin",
        kind: "npc",
        predicate: "associated_with",
        edge_label: "associated with",
        direction: "outgoing",
        anchored_to_focus_session: true,
        source_domains: ["recap"],
        evidence_ref_ids: [],
      },
    ],
    anchored_to_focus_session: true,
    summary: null,
    ...overrides,
  };
}

describe("buildGraphNodeGlancePresentation", () => {
  it("reads Orik as associated with Brin and drops evidence-role Why now", () => {
    const presentation = buildGraphNodeGlancePresentation(orikNode());

    expect(presentation.whyNow).toBeNull();
    expect(presentation.threadHints[0]?.edgeLabel).toBe("Orik is associated with Brin");
  });

  it("keeps genuine planning prose as Why now", () => {
    const presentation = buildGraphNodeGlancePresentation(
      orikNode({
        evidence_badges: [
          {
            evidence_ref_id: "ev-1",
            source_artifact_id: "artifact-1",
            source_domain: "recap",
            evidence_role: "support",
            is_focus_session_evidence: true,
            can_open_source: false,
            can_highlight_span: false,
            label: "Held the south gate with Brin",
          },
        ],
      }),
    );

    expect(presentation.whyNow).toBe("Held the south gate with Brin");
  });
});
