import { afterEach, describe, expect, it, vi } from "vitest";
import type { ReadStatblockCandidateResponseV1, ThreatDraftV1, ThreatDraftV2 } from "../../api/types";
import {
  assertCandidateDraft, assertDraftScope, persistGenerationAttempt, readGenerationAttempt,
  settleGenerationAttempt, statblockScopeKey, type StatblockDraftScope, type StoredGenerationAttempt,
} from "./statblockDraftScope";

const a: StatblockDraftScope = { mode: "world", worldId: "of-conks-a", campaignId: null };
const b: StatblockDraftScope = { mode: "world", worldId: "of-conks-b", campaignId: null };
const attempt: StoredGenerationAttempt = {
  schema: "dmb_sbw_generation_attempt_v1", draft_id: "draft-a",
  expected_draft_version: 1, client_request_id: "one-exact-request", candidate_id: null,
};

afterEach(() => { vi.restoreAllMocks(); localStorage.clear(); });

describe("World draft scope and generation replay identity", () => {
  it("distinguishes managed World, legacy campaign and other Worlds", () => {
    const world = {
      schema: "dmb_threat_draft_v2", scope_mode: "world", world_id: a.worldId, campaign_id: null,
    } as ThreatDraftV2;
    expect(() => assertDraftScope(world, a)).not.toThrow();
    expect(() => assertDraftScope(world, b)).toThrow(/selected scope/);
    const legacy = { schema: "dmb_threat_draft_v1", world_id: "eldyrwild", campaign_id: "longmont-c1" } as ThreatDraftV1;
    expect(() => assertDraftScope(legacy, { mode: "campaign", worldId: "eldyrwild", campaignId: "longmont-c1" })).not.toThrow();
    expect(() => assertDraftScope(legacy, { mode: "campaign", worldId: "eldyrwild", campaignId: "longmont-c2" })).toThrow();
    expect(statblockScopeKey(a)).not.toBe(statblockScopeKey(b));
  });

  it("persists before dispatch, scopes restoration and refuses unresolved replacement", () => {
    persistGenerationAttempt(a, attempt);
    expect(readGenerationAttempt(a)).toEqual(attempt);
    expect(readGenerationAttempt(b)).toBeNull();
    expect(() => persistGenerationAttempt(a, { ...attempt, client_request_id: "new" })).toThrow(/Unresolved/);
    expect(() => persistGenerationAttempt(a, { ...attempt, draft_id: "another" })).toThrow(/Unresolved/);
    expect(() => persistGenerationAttempt(a, { ...attempt, expected_draft_version: 2 })).toThrow(/Unresolved/);
    expect(readGenerationAttempt(a)).toEqual(attempt);
  });

  it("requires exact candidate ID, source draft and generated-version membership before editing", () => {
    const draft = {
      draft_id: "draft-a", candidate_refs: [{ candidate_id: "cand-a", generated_from_draft_version: 1 }],
    } as ThreatDraftV2;
    const response = {
      status: "active", candidate_id: "cand-a", candidate: { candidate_id: "cand-a" },
      source_draft_id: "draft-a", source_draft_version: 1,
    } as ReadStatblockCandidateResponseV1;
    expect(() => assertCandidateDraft(response, draft, "cand-a")).not.toThrow();
    expect(() => assertCandidateDraft(response, draft, "another-id")).toThrow(/membership/);
    expect(() => assertCandidateDraft({ ...response, source_draft_id: "foreign" }, draft, "cand-a")).toThrow();
    expect(() => assertCandidateDraft({ ...response, source_draft_version: 2 }, draft, "cand-a")).toThrow();
    expect(() => assertCandidateDraft(response, { ...draft, candidate_refs: [] }, "cand-a")).toThrow();
  });

  it("settles only exact request/source lineage, including after the draft version advances", () => {
    persistGenerationAttempt(a, attempt);
    const draft = {
      schema: "dmb_threat_draft_v2", scope_mode: "world", world_id: a.worldId,
      campaign_id: null, draft_id: attempt.draft_id, version: 4,
      candidate_refs: [{ candidate_id: "cand-a", request_id: attempt.client_request_id, generated_from_draft_version: 1 }],
    } as ThreatDraftV2;
    expect(() => settleGenerationAttempt(a, attempt, { ...draft, candidate_refs: [] }, "cand-a")).toThrow(/original/);
    expect(settleGenerationAttempt(a, attempt, draft, "cand-a")).toBe(true);
    expect(settleGenerationAttempt(a, attempt, draft, "cand-a")).toBe(true);
    expect(readGenerationAttempt(a)?.candidate_id).toBe("cand-a");
    persistGenerationAttempt(a, { ...attempt, expected_draft_version: 4, client_request_id: "deliberate-next" });
    expect(readGenerationAttempt(a)?.client_request_id).toBe("deliberate-next");
  });

  it.each([
    { draft_id: "next-draft" },
    { client_request_id: "next-request" },
    { expected_draft_version: 4 },
  ])("does not let old completion replace a newer unresolved or settled attempt: %j", (identity) => {
    const oldDraft = {
      schema: "dmb_threat_draft_v2", scope_mode: "world", world_id: a.worldId,
      campaign_id: null, draft_id: attempt.draft_id, version: 4,
      candidate_refs: [{ candidate_id: "cand-a", request_id: attempt.client_request_id, generated_from_draft_version: 1 }],
    } as ThreatDraftV2;
    persistGenerationAttempt(a, attempt);
    expect(settleGenerationAttempt(a, attempt, oldDraft, "cand-a")).toBe(true);
    const next = { ...attempt, ...identity };
    persistGenerationAttempt(a, next);
    expect(settleGenerationAttempt(a, attempt, oldDraft, "cand-a")).toBe(false);
    expect(readGenerationAttempt(a)).toEqual(next);
    const nextDraft = {
      ...oldDraft, draft_id: next.draft_id,
      candidate_refs: [{ candidate_id: "cand-next", request_id: next.client_request_id,
        generated_from_draft_version: next.expected_draft_version }],
    };
    expect(settleGenerationAttempt(a, next, nextDraft, "cand-next")).toBe(true);
    expect(settleGenerationAttempt(a, attempt, oldDraft, "cand-a")).toBe(false);
    expect(readGenerationAttempt(a)).toEqual({ ...next, candidate_id: "cand-next" });
  });

  it("does not recreate a missing recovery pointer from an old completed response", () => {
    const draft = {
      schema: "dmb_threat_draft_v2", scope_mode: "world", world_id: a.worldId,
      campaign_id: null, draft_id: attempt.draft_id,
      candidate_refs: [{ candidate_id: "cand-a", request_id: attempt.client_request_id, generated_from_draft_version: 1 }],
    } as ThreatDraftV2;
    expect(settleGenerationAttempt(a, attempt, draft, "cand-a")).toBe(false);
    expect(readGenerationAttempt(a)).toBeNull();
  });

  it("fails closed if browser persistence is unavailable or does not retain the write", () => {
    const set = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("quota"); });
    expect(() => persistGenerationAttempt(a, attempt)).toThrow(/quota/);
    set.mockImplementation(() => undefined);
    expect(() => persistGenerationAttempt(a, attempt)).toThrow(/Cannot preserve/);
  });

  it("does not reinterpret corrupt stored attempts as permission for a new request", () => {
    localStorage.setItem(`dmb.sbw.generationAttempt:${statblockScopeKey(a)}`, "{}");
    expect(() => readGenerationAttempt(a)).toThrow(/invalid/);
    expect(() => persistGenerationAttempt(a, attempt)).toThrow(/invalid/);
  });
});
