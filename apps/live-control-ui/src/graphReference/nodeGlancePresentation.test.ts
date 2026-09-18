import { describe, expect, it } from "vitest";

import type { GraphProjectionNodeView } from "../api/types";
import { buildGraphNodeGlancePresentation } from "./nodeGlancePresentation";

function nodeFixture(overrides: Partial<GraphProjectionNodeView> = {}): GraphProjectionNodeView {
  return {
    node_id: "pc:karsemine",
    label: "Karsemine",
    kind: "player_character",
    role: "player_character",
    aliases: [],
    source_domains: ["session_recap"],
    evidence_badges: [],
    adjacency: [],
    suggested_expansions: [],
    anchored_to_focus_session: true,
    summary: null,
    ...overrides,
  };
}

describe("buildGraphNodeGlancePresentation", () => {
  it("uses one resident focus-session relationship when the evidence badge has no label", () => {
    const presentation = buildGraphNodeGlancePresentation(
      nodeFixture({
        evidence_badges: [
          {
            evidence_ref_id: "evidence:unlabeled-session-25",
            source_artifact_id: "artifact:session-25",
            source_domain: "session_recap",
            evidence_role: "support",
            is_focus_session_evidence: true,
            can_open_source: true,
            can_highlight_span: false,
            label: null,
            session_id: "session-25",
            source_span_ref_id: null,
          },
        ],
        suggested_expansions: [
          {
            edge_id: "edge:lysandra:commands:karsemine",
            node_id: "npc:lysandra",
            label: "Lysandra",
            kind: "npc",
            predicate: "commands",
            direction: "incoming",
            anchored_to_focus_session: true,
            source_domains: ["session_recap"],
            evidence_ref_ids: ["evidence:session-25"],
            edge_label: "commands",
            session_ids: ["session-25"],
            rank: 1,
            rank_reason: "current session",
          },
        ],
      }),
    );

    expect(presentation.whyNow).toBe("Lysandra commands Karsemine.");
  });

  it("prefers labeled focus evidence and does not synthesize context without a focus relationship", () => {
    expect(
      buildGraphNodeGlancePresentation(
        nodeFixture({
          evidence_badges: [
            {
              evidence_ref_id: "evidence:session-25",
              source_artifact_id: "artifact:session-25",
              source_domain: "session_recap",
              evidence_role: "support",
              is_focus_session_evidence: true,
              can_open_source: true,
              can_highlight_span: false,
              label: "Held the south gate during the attack.",
              session_id: "session-25",
              source_span_ref_id: null,
            },
          ],
        }),
      ).whyNow,
    ).toBe("Held the south gate during the attack.");

    expect(buildGraphNodeGlancePresentation(nodeFixture()).whyNow).toBeNull();
  });

  it("states a compact location fact without this-session suffix", () => {
    const presentation = buildGraphNodeGlancePresentation(
      nodeFixture({
        node_id: "loc:the-hole",
        label: "the hole",
        kind: "location",
        role: "location",
        evidence_badges: [],
        suggested_expansions: [
          {
            edge_id: "edge:swarms:located_in:the-hole",
            node_id: "threat:swarms",
            label: "Swarms",
            kind: "item",
            predicate: "located_in",
            direction: "incoming",
            anchored_to_focus_session: true,
            source_domains: ["session_recap"],
            evidence_ref_ids: [],
            edge_label: "located in",
            session_ids: ["session-27"],
            rank: 1,
            rank_reason: "current session",
          },
        ],
      }),
    );

    expect(presentation.label).toBe("the hole");
    expect(presentation.kind).toBe("location");
    expect(presentation.whyNow).toBe("Swarms located in the hole.");
    expect(presentation.whyNow).not.toMatch(/this session/i);
  });
});
