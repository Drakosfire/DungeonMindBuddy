import { describe, expect, it } from "vitest";

import type { GraphProjectionNodeView, GraphReviewExistingObjectCandidate } from "../../api/types";
import {
  getGraphReviewBindTargetNodeId,
  isExactGovernedExistingTarget,
} from "./graphExistingObjectEligibility";

const candidate = (
  candidate_id: string,
  existing_object_ref: Record<string, string> | null = null,
): Pick<GraphReviewExistingObjectCandidate, "candidate_id" | "existing_object_ref"> => ({
  candidate_id,
  existing_object_ref,
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

  it("uses the server bind target when the search identity differs", () => {
    const governed = { "pc:ephanna": node("pc:ephanna") };
    const result = candidate("party:ephanna", {
      source: "party_pc",
      object_id: "pc:ephanna",
    });

    expect(getGraphReviewBindTargetNodeId(result)).toBe("pc:ephanna");
    expect(isExactGovernedExistingTarget(result, governed)).toBe(true);
  });

  it("does not let a governed search identity authorize a different bind target", () => {
    const governed = { "party:ephanna": node("party:ephanna") };
    const result = candidate("party:ephanna", {
      source: "party_pc",
      object_id: "pc:ephanna",
    });

    expect(getGraphReviewBindTargetNodeId(result)).toBe("pc:ephanna");
    expect(isExactGovernedExistingTarget(result, governed)).toBe(false);
  });

  it("fails closed when the shared World projection is unavailable", () => {
    expect(isExactGovernedExistingTarget(candidate("pc:ephanna"), null)).toBe(false);
  });

  it("keeps legacy standalone authoring callers compatible when no lens is supplied", () => {
    expect(isExactGovernedExistingTarget(candidate("pc:ephanna"), undefined)).toBe(true);
  });
});
