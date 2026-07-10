import { describe, expect, it } from "vitest";

import type { LiveQueryResponse } from "../../api/types";
import type { PlanSessionDescriptor } from "../types";
import {
  answerHeading,
  hasGrounding,
  prepMemoryLabel,
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

describe("prepMemoryQa helpers", () => {
  it("formats prep memory label from session descriptor", () => {
    expect(prepMemoryLabel(sessionDescriptor)).toBe(
      "Memory through Session 21 · preparing Session 23",
    );
  });

  it("detects grounding from citations or admitted evidence", () => {
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
});
