import { describe, expect, it } from "vitest";

import {
  buildPacketReview,
  buildSourceReviewWorklist,
  classifyEvidence,
  filterAdmittedToTargetSession,
  summarizeEvidenceQuality,
} from "./contextSufficiencyLadder";
import type { LiveContextEvidenceRef, LiveQueryResponse } from "../../api/types";

function evidence(overrides: Partial<LiveContextEvidenceRef>): LiveContextEvidenceRef {
  return {
    path: "corpus/example.md",
    source_role: "play_recap",
    authority: "canon_play",
    ...overrides,
  };
}

describe("contextSufficiencyLadder", () => {
  it("classifies strong campaign-text excerpts", () => {
    const result = classifyEvidence(
      evidence({
        path: "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/Session 22 - Mireward Road and Lysandro.md",
        text_excerpt:
          "The party reaches the north gate at dusk while Lysandro argues with the watch captain about curfew.",
        line_start: 24,
        line_end: 24,
      }),
    );
    expect(result.tier).toBe("strong");
  });

  it("classifies broad normalized recap routes as weak", () => {
    const result = classifyEvidence(
      evidence({
        path: "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 21 - Drake Nest Mirathorn Call.md",
        source_role: "session_memory",
        authority: "derived_memory",
      }),
    );
    expect(result.tier).toBe("weak");
  });

  it("classifies session memory jsonl prose as strong, not debug", () => {
    const result = classifyEvidence(
      evidence({
        path: "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_session_memory/Session 23 - session-23-mireward.records_meta.jsonl",
        source_role: "session_memory",
        authority: "derived_memory",
        text_excerpt:
          "Caelynn, furious after the barrage of attacks, lines herself up and unleashes a devastating lightning bolt along the line of attackers.",
        unit_id: "u-L0027-02",
      }),
    );
    expect(result.tier).toBe("strong");
  });

  it("classifies records_meta.json sidecar as debug", () => {
    const result = classifyEvidence(
      evidence({
        path: "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_session_memory/Session 23 - session-23-mireward.records_meta.json",
        source_role: "session_memory",
        authority: "derived_memory",
        text_excerpt: '{"source_recap_path": "Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 23 - session-23-mireward.md"}',
      }),
    );
    expect(result.tier).toBe("debug");
  });

  it("classifies bootstrap metadata as debug", () => {
    const result = classifyEvidence(
      evidence({
        path: "evals/c2_live_prep/live/session_23/live_packet.json",
        source_role: "live_packet",
        authority: "planning_scaffold",
        text_excerpt: '{"schema_version":"0.1.0","campaign_id":"longmont-c2"}',
      }),
    );
    expect(result.tier).toBe("debug");
  });

  it("filters cross-session excerpts when a single session is targeted", () => {
    const answer: LiveQueryResponse = {
      answer: "ignored",
      classification: {},
      events_written: [],
      jobs_queued: [],
      next_suggestions: [],
      diagnostics: [],
      provenance: {},
      context_packet: {
        schema: "dmb_enriched_planning_context_packet_v1",
        question_id: "q-s22-end",
        intent_class: "play_fact_retrieval",
        query_signals: { asks_for_last_or_final: true, session_numbers: [22] },
        admitted_evidence: [
          evidence({
            path: "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_session_memory/Session 23 - session-23-mireward.records_meta.jsonl",
            source_role: "session_memory",
            authority: "derived_memory",
            line_start: 38,
            line_end: 38,
            text_excerpt:
              "Caelynn unleashes a devastating lightning bolt along the line of attackers, dealing massive damage.",
            unit_id: "u-L0038-02",
          }),
          evidence({
            path: "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/Session 22 - Mireward Road and Lysandro.md",
            source_role: "play_recap",
            authority: "canon_play",
            line_start: 38,
            line_end: 38,
            text_excerpt:
              "And that is how they all met her father Lysandro.",
          }),
        ],
        rejected_evidence: [],
      },
    };

    const review = buildPacketReview(answer);
    expect(review?.campaignTextExcerpts).toEqual(["And that is how they all met her father Lysandro."]);
    expect(review?.campaignTextExcerpts.some((text) => text.includes("lightning bolt"))).toBe(false);
    expect(filterAdmittedToTargetSession(answer.context_packet!.admitted_evidence, [22])).toHaveLength(1);
  });

  it("builds a weak verdict for end-of-session asks without closing beats", () => {
    const answer: LiveQueryResponse = {
      answer: "ignored",
      classification: {},
      events_written: [],
      jobs_queued: [],
      next_suggestions: [],
      diagnostics: [],
      provenance: {},
      context_packet: {
        schema: "dmb_enriched_planning_context_packet_v1",
        question_id: "q3",
        intent_class: "play_fact_retrieval",
        query_signals: { asks_for_last_or_final: true, session_numbers: [23] },
        admitted_evidence: [
          evidence({
            path: "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_session_memory/Session 23 - session-23-mireward.records_meta.jsonl",
            source_role: "session_memory",
            authority: "derived_memory",
            line_start: 20,
            line_end: 20,
            text_excerpt:
              "Suddenly everyone can hear yelling and a loud bell ringing coming from outside.",
            unit_id: "u-L0020-01",
          }),
        ],
        rejected_evidence: [],
      },
    };

    const review = buildPacketReview(answer);
    expect(review?.verdict.status).toBe("weak_context");
    expect(review?.verdict.answerableNow).toBe(false);
  });

  it("builds a strong verdict when campaign excerpts are admitted", () => {
    const answer: LiveQueryResponse = {
      answer: "ignored",
      classification: {},
      events_written: [],
      jobs_queued: [],
      next_suggestions: [],
      diagnostics: [],
      provenance: {},
      context_packet: {
        schema: "dmb_enriched_planning_context_packet_v1",
        question_id: "q1",
        intent_class: "play_fact_retrieval",
        admitted_evidence: [
          evidence({
            text_excerpt:
              "The party reaches the north gate at dusk while Lysandro argues with the watch captain about curfew.",
            line_start: 24,
            line_end: 24,
          }),
        ],
        rejected_evidence: [],
      },
    };

    const review = buildPacketReview(answer);
    expect(review?.verdict.status).toBe("enough_context");
    expect(review?.verdict.answerableNow).toBe(true);
    expect(review?.campaignTextExcerpts).toHaveLength(1);
  });

  it("builds a weak verdict for metadata-only admission", () => {
    const answer: LiveQueryResponse = {
      answer: "ignored",
      classification: {},
      events_written: [],
      jobs_queued: [],
      next_suggestions: [],
      diagnostics: [],
      provenance: {},
      context_packet: {
        schema: "dmb_enriched_planning_context_packet_v1",
        question_id: "q2",
        intent_class: "play_fact_retrieval",
        admitted_evidence: [
          evidence({
            path: "evals/c2_live_prep/live/session_23/live_packet.json",
            source_role: "live_packet",
            authority: "planning_scaffold",
            text_excerpt: '{"schema_version":"0.1.0","summary":"Fresh recap ingested"}',
          }),
        ],
        rejected_evidence: [{ reason_code: "authority_mismatch", evidence: evidence({ path: "y" }) }],
      },
    };

    const review = buildPacketReview(answer);
    expect(review?.verdict.status).toBe("weak_context");
    expect(review?.verdict.answerableNow).toBe(false);
    expect(review?.rejectedSummary).toEqual(["authority_mismatch: 1"]);
    expect(review?.campaignTextExcerpts).toHaveLength(0);
  });

  it("prefers canon recap routes in the source review worklist", () => {
    const quality = summarizeEvidenceQuality([
      evidence({
        path: "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 22 - Mireward Road and Lysandro.md",
      }),
      evidence({
        path: "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/Session 22 - Mireward Road and Lysandro.md",
      }),
    ]);
    const worklist = buildSourceReviewWorklist([
      ...quality.weak,
      ...quality.strong,
      ...quality.okay,
      ...quality.debug,
    ]);
    expect(worklist.some((item) => item.path.includes("Session 22 - Mireward Road and Lysandro.md"))).toBe(true);
    expect(worklist[0]?.path).not.toContain("_normalized");
  });
});
