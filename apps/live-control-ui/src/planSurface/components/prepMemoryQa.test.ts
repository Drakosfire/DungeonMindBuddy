import { describe, expect, it } from "vitest";

import type { HermesGraphGrounding, LiveQueryResponse, WorldGraphAnchorCitation } from "../../api/types";
import type { PlanSessionDescriptor } from "../types";
import {
  answerHeading,
  hasGrounding,
  isConversationContext,
  isWorldGraphAnchorCitation,
  parseHermesGraphGrounding,
  parseWorldGraphAnchorCitation,
  prepMemoryLabel,
  s1SupportFromTurn,
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

  it("formats prep memory label for world-union focus", () => {
    expect(prepMemoryLabel({ ...sessionDescriptor, memorySession: null })).toBe(
      "World graph (all sessions) · preparing Session 23",
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

  it("accepts S1 named-gap partials with zero claims or citations", () => {
    const s1Partial = hermesResponse("partial", [], {
      source_anchor_count: 0,
      acceptance_state: "partial_coverage",
      accepted_claim_ids: [],
      graph_reference_count: 0,
      reason_codes: ["named_gap", "latest_recap_memory_lag_disclosed"],
      warnings: ["graph_context_empty"],
    });

    expect(answerHeading(s1Partial)).toBe("No Hermes answer");
    expect(hasGrounding(s1Partial)).toBe(true);
    expect(validateHermesGraphCitations(s1Partial.citations, s1Partial.grounding).contractWarning).toBeNull();
  });

  it("labels S1 agent answers and admitted-recap reads", () => {
    const s1WithRead = hermesResponse("partial", [], {
      source_anchor_count: 0,
      acceptance_state: "partial_coverage",
      accepted_claim_ids: [],
      graph_reference_count: 0,
      reason_codes: [
        "named_gap",
        "latest_recap_memory_lag_disclosed",
        "admitted_recap_source_read",
      ],
    });
    expect(answerHeading(s1WithRead)).toBe("No Hermes answer");
    expect(hasGrounding(s1WithRead)).toBe(true);

    const s1Agent = hermesResponse("partial", [], {
      source_anchor_count: 0,
      acceptance_state: "partial_coverage",
      accepted_claim_ids: [],
      graph_reference_count: 0,
      reason_codes: [
        "named_gap",
        "latest_recap_memory_lag_disclosed",
        "hermes_agent_answer",
      ],
    });
    expect(answerHeading(s1Agent)).toBe("Hermes answer");
  });

  it("still rejects empty partials without named-gap reason codes", () => {
    const emptyPartial = hermesResponse("partial", [], {
      source_anchor_count: 0,
      accepted_claim_ids: [],
      graph_reference_count: 0,
      reason_codes: [],
    });
    expect(answerHeading(emptyPartial)).toBe("Hermes grounding contract error");
    expect(hasGrounding(emptyPartial)).toBe(false);
  });

  it("maps Hermes abstained and error states without treating them as grounded", () => {
    expect(answerHeading(hermesResponse("abstained", []))).toBe("Graph evidence gap");
    expect(answerHeading(hermesResponse("error", []))).toBe("Hermes graph error");
    expect(hasGrounding(hermesResponse("abstained", []))).toBe(false);
    expect(hasGrounding(hermesResponse("error", []))).toBe(false);
    expect(hasGrounding(hermesResponse("abstained", [graphCitation]))).toBe(false);
  });

  it("treats conversation_context as a non-graph answer, not an evidence gap", () => {
    const conversational = hermesResponse("conversation_context", [], {
      source_anchor_count: 0,
      accepted_claim_ids: [],
      graph_reference_count: 0,
      reason_codes: ["conversation_context_no_tool_calls"],
      diagnostic_codes: [],
    });

    expect(answerHeading(conversational)).toBe("Answered from conversation");
    expect(hasGrounding(conversational)).toBe(false);
    expect(isConversationContext(parseHermesGraphGrounding(conversational.grounding))).toBe(true);
    expect(validateHermesGraphCitations(conversational.citations, conversational.grounding)).toEqual({
      grounding: expect.objectContaining({ state: "conversation_context" }),
      citations: [],
      contractWarning: null,
    });

    const withStrayCitations = hermesResponse("conversation_context", [graphCitation]);
    expect(
      validateHermesGraphCitations(withStrayCitations.citations, withStrayCitations.grounding)
        .contractWarning,
    ).toBe("Graph citations ignored for conversation-context turns.");
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

  it("rejects grounded or partial envelopes with null revision as a contract error", () => {
    const nullRevision = hermesResponse("grounded", [graphCitation], { revision_id: null });
    expect(answerHeading(nullRevision)).toBe("Hermes grounding contract error");
    expect(hasGrounding(nullRevision)).toBe(false);
    expect(validateHermesGraphCitations(nullRevision.citations, nullRevision.grounding).citations).toHaveLength(0);

    const partialNull = hermesResponse("partial", [graphCitation], { revision_id: null });
    expect(answerHeading(partialNull)).toBe("Hermes grounding contract error");
  });

  it("rejects impossible focus scopes for grounding and citations", () => {
    expect(parseHermesGraphGrounding({
      ...baseGrounding,
      focus: { kind: "session", session_id: null },
    })).toBeNull();
    expect(parseHermesGraphGrounding({
      ...baseGrounding,
      focus: { kind: "none", session_id: "session-21" },
    })).toBeNull();
    expect(parseWorldGraphAnchorCitation({
      ...graphCitation,
      focus: { kind: "session", session_id: null },
    })).toBeNull();
    expect(parseWorldGraphAnchorCitation({
      ...graphCitation,
      focus: { kind: "none", session_id: "session-21" },
    })).toBeNull();

    const matchingMalformed = hermesResponse("grounded", [{
      ...graphCitation,
      focus: { kind: "session", session_id: null } as never,
    }], {
      focus: { kind: "session", session_id: null } as never,
    });
    expect(answerHeading(matchingMalformed)).toBe("Hermes grounding contract error");
    expect(hasGrounding(matchingMalformed)).toBe(false);
  });

  it("parses grounding and citations from unknown JSON without throwing", () => {
    expect(parseHermesGraphGrounding(null)).toBeNull();
    expect(parseHermesGraphGrounding("grounded")).toBeNull();
    expect(parseHermesGraphGrounding({
      schema: "dmb_hermes_graph_grounding_v1",
      state: "grounded",
    })).toBeNull();
    expect(parseHermesGraphGrounding({
      ...baseGrounding,
      diagnostic_codes: "not-an-array",
    })).toBeNull();
    expect(parseHermesGraphGrounding({
      ...baseGrounding,
      warnings: null,
    })).toEqual(expect.objectContaining({ warnings: [] }));
    expect(parseHermesGraphGrounding({
      ...baseGrounding,
      focus: null,
    })).toBeNull();
    expect(parseHermesGraphGrounding({
      ...baseGrounding,
      diagnostic_codes: undefined,
      warnings: undefined,
    })).toEqual(expect.objectContaining({
      diagnostic_codes: [],
      warnings: [],
    }));

    expect(parseWorldGraphAnchorCitation(null)).toBeNull();
    expect(parseWorldGraphAnchorCitation(42)).toBeNull();
    expect(parseWorldGraphAnchorCitation({ kind: "world_graph_anchor" })).toBeNull();
    expect(parseWorldGraphAnchorCitation({
      ...graphCitation,
      focus: undefined,
    })).toBeNull();
    expect(isWorldGraphAnchorCitation(null)).toBe(false);
    expect(isWorldGraphAnchorCitation(graphCitation)).toBe(true);

    const malformed = validateHermesGraphCitations(
      [null, "x", graphCitation, { kind: "world_graph_anchor" }],
      {
        schema: "dmb_hermes_graph_grounding_v1",
        state: "grounded",
        world_id: "eldyrwild",
        campaign_id: "longmont-c2",
        focus: { kind: "session", session_id: "session-21" },
        admissibility: "gm",
        revision_id: "rev-1",
        successful_tool_count: 1,
        source_anchor_count: 1,
      },
    );
    expect(malformed.citations).toHaveLength(1);
    expect(malformed.citations[0].anchor_id).toBe(graphCitation.anchor_id);
    expect(answerHeading({
      ...hermesResponse("grounded"),
      grounding: {
        schema: "dmb_hermes_graph_grounding_v1",
        state: "grounded",
      } as never,
      citations: [null as never],
    })).toBe("Hermes grounding contract error");
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

  it("s1SupportFromTurn prefers persisted turn support over wire fallback", () => {
    expect(s1SupportFromTurn(
      { s1Support: { lagDisclosure: "Persisted lag", admittedRecapExcerpt: null } },
      {
        s1_support: { lag_disclosure: "Wire lag", admitted_recap_excerpt: "Wire excerpt" },
      } as never,
    )).toEqual({ lagDisclosure: "Persisted lag", admittedRecapExcerpt: null });

    expect(s1SupportFromTurn(
      { s1Support: null },
      {
        latest_recap_change: {
          lag_disclosure: "From latest recap change",
          admitted_recap_excerpt: "Recap body",
        },
      } as never,
    )).toEqual({
      lagDisclosure: "From latest recap change",
      admittedRecapExcerpt: "Recap body",
    });
  });
});
