import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RetrievalFreshnessPanel } from "./RetrievalFreshnessPanel";
import type { RetrievalFreshnessDecision } from "../../api/types";

function decision(overrides: Partial<RetrievalFreshnessDecision>): RetrievalFreshnessDecision {
  return {
    schema: "dmb_retrieval_freshness_decision_v1",
    decision: "thread_context",
    used_fresh_retrieval: false,
    used_thread_context: true,
    admitted_evidence_count: 0,
    rejected_evidence_count: 0,
    prior_turn_count: 0,
    reason: "The active Hermes session/thread handle was reused, but no fresh corpus evidence was admitted for this turn.",
    warnings: ["No fresh corpus evidence was admitted for this turn."],
    ...overrides,
  };
}

describe("RetrievalFreshnessPanel", () => {
  it("shows thread-context copy and no-fresh-evidence warning", () => {
    render(<RetrievalFreshnessPanel decision={decision({})} />);

    expect(screen.getByRole("region", { name: "Retrieval freshness" })).toBeInTheDocument();
    expect(screen.getAllByText("Thread context").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/No fresh corpus evidence was admitted for this turn\./).length).toBeGreaterThan(0);
    expect(screen.getByText("0 / 0")).toBeInTheDocument();
  });

  it("shows insufficient-grounding copy and warning", () => {
    render(<RetrievalFreshnessPanel decision={decision({
      decision: "insufficient_grounding",
      used_thread_context: false,
      reason: "No admitted corpus evidence and no reliable thread/session basis were available for this turn.",
      warnings: ["No admitted corpus evidence or reliable thread basis was available; answer may be under-grounded."],
    })} />);

    expect(screen.getByText("Insufficient grounding")).toBeInTheDocument();
    expect(screen.getByText(/No admitted corpus evidence and no reliable thread basis/)).toBeInTheDocument();
    expect(screen.getByText(/answer may be under-grounded/)).toBeInTheDocument();
  });
});
