import { describe, expect, it } from "vitest";

import type { GraphProjectionNodeView, GraphReviewExistingObjectCandidate } from "../../api/types";
import { isExactGovernedExistingTarget } from "./graphExistingObjectEligibility";

const candidate = (candidate_id: string): Pick<GraphReviewExistingObjectCandidate, "candidate_id"> => ({
  candidate_id,
});

const node = (node_id: string): GraphProjectionNodeView => ({
  node_id,
  label: node_id,
  kind: "concept",
  role: "concept",
  aliases: [],
  source_domains: ["campaign_memory"],
  evidence_badges: [],
  adjacency: [],
  suggested_expansions: [],
  anchored_to_focus_session: false,
});

describe("graphExistingObjectEligibility", () => {
  it("requires the candidate's exact durable id in the governed projection", () => {
    const governed = { "node:questionable-company": node("node:questionable-company") };

    expect(isExactGovernedExistingTarget(candidate("node:questionable-company"), governed)).toBe(true);
    expect(isExactGovernedExistingTarget(candidate("pc:ephanna"), governed)).toBe(false);
  });

  it("fails closed when the shared World projection is unavailable", () => {
    expect(isExactGovernedExistingTarget(candidate("pc:ephanna"), null)).toBe(false);
  });

  it("keeps legacy standalone authoring callers compatible when no lens is supplied", () => {
    expect(isExactGovernedExistingTarget(candidate("pc:ephanna"), undefined)).toBe(true);
  });
});
