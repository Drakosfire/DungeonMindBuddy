import { describe, expect, it } from "vitest";

import { buildGraphObjectCardFromNodeView } from "../../graphObjectCard";
import type { GraphProjectionNodeView } from "../../api/types";
import {
  computeGraphObjectCardCoverage,
  isThinCardCoverage,
} from "./graphObjectDogfoodModel";

const thinNode: GraphProjectionNodeView = {
  node_id: "npc-thin",
  label: "Thin NPC",
  kind: "npc",
  role: "npc",
  aliases: [],
  source_domains: [],
  evidence_badges: [],
  adjacency: [],
  anchored_to_focus_session: true,
  summary: null,
};

const richNode: GraphProjectionNodeView = {
  node_id: "npc-glowkindle",
  label: "Glowkindle",
  kind: "npc",
  role: "merchant",
  aliases: ["Glow"],
  source_domains: ["recap"],
  evidence_badges: [
    {
      evidence_ref_id: "ev-1",
      label: "Session recap mention",
      source_domain: "recap",
      source_artifact_id: "artifact-1",
    },
  ],
  adjacency: [
    {
      edge_id: "edge-1",
      node_id: "location-inn",
      label: "Inn",
      kind: "location",
      predicate: "met at",
      direction: "outgoing",
      related_summary: null,
      evidence_ref_ids: [],
      source_domains: ["recap"],
      anchored_to_focus_session: true,
      session_ids: [],
    },
  ],
  anchored_to_focus_session: true,
  summary: "A friendly merchant.",
  source_anchor_text: "Glowkindle waved.",
};

describe("computeGraphObjectCardCoverage", () => {
  it("marks thin cards when summary/relationships/evidence are missing", () => {
    const coverage = computeGraphObjectCardCoverage(buildGraphObjectCardFromNodeView(thinNode));
    expect(isThinCardCoverage(coverage)).toBe(true);
    expect(coverage.missing).toEqual(
      expect.arrayContaining(["summary", "aliases", "relationships", "evidence", "source-anchor"]),
    );
  });

  it("reports present coverage flags for a rich card", () => {
    const coverage = computeGraphObjectCardCoverage(buildGraphObjectCardFromNodeView(richNode));
    expect(isThinCardCoverage(coverage)).toBe(false);
    expect(coverage.flags).toEqual(
      expect.arrayContaining(["summary", "aliases", "relationships", "evidence", "source-anchor"]),
    );
  });
});
