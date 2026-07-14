import { describe, expect, it } from "vitest";

import type { HermesGraphGrounding, LiveQueryResponse, WorldGraphAnchorCitation } from "../../api/types";
import type { PlanSessionDescriptor } from "../types";
import {
  answerHeading,
  hasGrounding,
  isWorldGraphAnchorCitation,
  prepMemoryLabel,
  validateHermesGraphCitations,
} from "./prepMemoryQa";

const sessionDescriptor: PlanSessionDescriptor = {
  surfaceId: "plan",
  campaignId: "longmont-c2",
  campaignLabel: "Longmont C2",
  prepSession: 23,
  memorySession: 21,
  liveSession: 22,
  sourceStatusLabel: "Session 21",
  sourceStatusKind: "unknown",
  planningDocument: {
    documentId: "longmont-c2-session-23-prep",
    title: "C2 Session 23 Prep",
    targetRelpath: "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/Session 23 Prep.md",
    storageKey: "dmb.planCanvas.longmont-c2.23.longmont-c2-session-23-prep",
    status: "local_draft",
  },
};

const baseGrounding: HermesGraphGrounding = {
  schema: "dmb_hermes_graph_grounding_v1",
  state: "grounded",
  world_id: "eldyrwild",
  campaign_id: "longmont-c2",
  focus: { kind: "session", session_id: "session-21" },
  admissibility: "gm",
  revision_id: "rev-1",
  successful_tool_count: 1,
  source_anchor_count: 1,
  diagnostic_codes: [],
  warnings: [],
};

const graphCitation: WorldGraphAnchorCitation = {
  schema: "dmb_world_graph_anchor_citation_v1",
  kind: "world_graph_anchor",
  anchor_id: "source-anchor:v1:abc",
  world_id: "eldyrwild",
  campaign_id: "longmont-c2",
  focus: { kind: "session", session_id: "session-21" },
  admissibility: "gm",
  revision_id: "rev-1",
};

function hermesResponse(
  state: HermesGraphGrounding["state"],
  citations: LiveQueryResponse["citations"] = [graphCitation],
  groundingOverrides: Partial<HermesGraphGrounding> = {},
): LiveQueryResponse {
  return {
    answer: "Hermes answer",
    mode: "hermes_graph_agent",
    classification: {} as never,
    events_written: [],
    jobs_queued: [],
    next_suggestions: [],
    diagnostics: {},
    provenance: {},
    grounding: { ...baseGrounding, state, ...groundingOverrides },
    citations,
  };
}

describe("prepMemoryQa helpers", () => {
  it("formats prep memory label from session descriptor", () => {
    expect(prepMemoryLabel(sessionDescriptor)).toBe(
      "Memory through Session 21 · preparing Session 23",
    );
  });

  it("detects grounding from citations or admitted evidence for legacy Live responses", () => {
    const grounded: LiveQueryResponse = {
      answer: "Grounded",
      classification: {} as never,
      events_written: [],
      jobs_queued: [],
      next_suggestions: [],
      diagnostics: {},
      provenance: {},
      citations: [{ evidence_id: "e1", path: "corpus/test.md", source_role: "play_recap", authority: "canon_play" }],
      context_packet: null,
      retrieval_freshness: null,
    };
    const ungrounded: LiveQueryResponse = {
      ...grounded,
      citations: [],
      context_packet: { admitted_evidence: [], rejected_evidence: [] },
    };

    expect(hasGrounding(grounded)).toBe(true);
    expect(hasGrounding(ungrounded)).toBe(false);
    expect(answerHeading(grounded)).toBe("Grounded answer");
    expect(answerHeading(ungrounded)).toBe("Ungrounded draft");
  });

  it("maps Hermes grounded and partial states with validated graph citations", () => {
    expect(answerHeading(hermesResponse("grounded"))).toBe("Graph-grounded answer");
    expect(answerHeading(hermesResponse("partial", [graphCitation], { warnings: ["qualified"] }))).toBe("Qualified graph answer");
    expect(hasGrounding(hermesResponse("grounded"))).toBe(true);
    expect(hasGrounding(hermesResponse("partial"))).toBe(true);
  });

  it("maps Hermes abstained and error states without treating them as grounded", () => {
    expect(answerHeading(hermesResponse("abstained", []))).toBe("Graph evidence gap");
    expect(answerHeading(hermesResponse("error", []))).toBe("Hermes graph error");
    expect(hasGrounding(hermesResponse("abstained", []))).toBe(false);
    expect(hasGrounding(hermesResponse("error", []))).toBe(false);
    expect(hasGrounding(hermesResponse("abstained", [graphCitation]))).toBe(false);
  });

  it("reports contract errors for malformed Hermes grounding or mismatched citations", () => {
    const missingGrounding = hermesResponse("grounded");
    delete missingGrounding.grounding;
    expect(answerHeading(missingGrounding)).toBe("Hermes grounding contract error");
    expect(hasGrounding(missingGrounding)).toBe(false);

    const groundedWithoutCitations = hermesResponse("grounded", []);
    expect(answerHeading(groundedWithoutCitations)).toBe("Hermes grounding contract error");
    expect(hasGrounding(groundedWithoutCitations)).toBe(false);

    const mismatchedCitation = hermesResponse("grounded", [{
      ...graphCitation,
      revision_id: "FOREIGN_REVISION_ID",
    }]);
    expect(answerHeading(mismatchedCitation)).toBe("Hermes grounding contract error");
    expect(hasGrounding(mismatchedCitation)).toBe(false);
  });

  it("validates graph citations against grounding scope and revision", () => {
    expect(isWorldGraphAnchorCitation(graphCitation)).toBe(true);
    expect(isWorldGraphAnchorCitation({
      evidence_id: "e1",
      path: "corpus/test.md",
      source_role: "play_recap",
      authority: "canon_play",
    })).toBe(false);

    const validated = validateHermesGraphCitations([graphCitation], baseGrounding);
    expect(validated.citations).toHaveLength(1);
    expect(validated.contractWarning).toBeNull();

    const dropped = validateHermesGraphCitations([{
      ...graphCitation,
      world_id: "FOREIGN_WORLD_ID",
    }], baseGrounding);
    expect(dropped.citations).toHaveLength(0);
    expect(dropped.contractWarning).toContain("scope or revision mismatch");
  });
});
