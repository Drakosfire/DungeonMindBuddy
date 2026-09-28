import type { ReadStatblockCandidateResponseV1, ThreatDraft } from "../../api/types";

/** A launch scope is taken from existing admitted context, never from asset names or IDs. */
export type StatblockDraftScope =
  | { mode: "world"; worldId: string; campaignId: null }
  | { mode: "campaign"; worldId: string; campaignId: string };

export function statblockScopeKey(scope: StatblockDraftScope): string {
  return JSON.stringify([scope.mode, scope.worldId, scope.campaignId]);
}

export function scopedWorkbenchJoinKey(scope: StatblockDraftScope): string {
  return `dmb.sbw.scopeJoin:${statblockScopeKey(scope)}`;
}

export function assertDraftScope(draft: ThreatDraft, scope: StatblockDraftScope): void {
  const exactScope = draft.world_id === scope.worldId && (
    scope.mode === "world"
      ? draft.schema === "dmb_threat_draft_v2" && draft.scope_mode === "world" && draft.campaign_id === null
      : draft.schema === "dmb_threat_draft_v1" && draft.campaign_id === scope.campaignId
  );
  if (!exactScope) throw new Error("This ThreatDraft does not belong to the selected scope.");
}

export function assertCandidateDraft(
  response: ReadStatblockCandidateResponseV1,
  draft: ThreatDraft,
  requestedCandidateId: string,
): void {
  if (
    response.status !== "active" || !response.candidate
    || response.candidate_id !== requestedCandidateId
    || response.candidate.candidate_id !== requestedCandidateId
    || response.source_draft_id !== draft.draft_id
    || !draft.candidate_refs.some((ref) => ref.candidate_id === requestedCandidateId
      && ref.generated_from_draft_version === response.source_draft_version)
  ) throw new Error("Candidate membership in the verified ThreatDraft could not be proved.");
}

export interface StoredGenerationAttempt {
  schema: "dmb_sbw_generation_attempt_v1";
  draft_id: string;
  expected_draft_version: number;
  client_request_id: string;
  /** Null means unresolved, including transport loss. Clear cannot discard it. */
  candidate_id: string | null;
}

function generationAttemptKey(scope: StatblockDraftScope): string {
  // One unresolved attempt per scope: Clear cannot permit a replacement draft to bypass it.
  return `dmb.sbw.generationAttempt:${statblockScopeKey(scope)}`;
}

export function readGenerationAttempt(scope: StatblockDraftScope): StoredGenerationAttempt | null {
  const raw = localStorage.getItem(generationAttemptKey(scope));
  if (raw === null) return null;
  const attempt = JSON.parse(raw) as StoredGenerationAttempt;
  if (
    attempt?.schema !== "dmb_sbw_generation_attempt_v1"
    || typeof attempt.draft_id !== "string" || !attempt.draft_id.trim()
    || !Number.isInteger(attempt.expected_draft_version) || attempt.expected_draft_version < 1
    || typeof attempt.client_request_id !== "string" || !attempt.client_request_id.trim()
    || (attempt.candidate_id !== null && (typeof attempt.candidate_id !== "string" || !attempt.candidate_id.trim()))
  ) throw new Error("Stored generation attempt is invalid; generation is blocked rather than replaced.");
  return attempt;
}

export function persistGenerationAttempt(
  scope: StatblockDraftScope,
  attempt: StoredGenerationAttempt,
): void {
  const existing = readGenerationAttempt(scope);
  if (existing?.candidate_id === null && (
    existing.draft_id !== attempt.draft_id
    || existing.client_request_id !== attempt.client_request_id
    || existing.expected_draft_version !== attempt.expected_draft_version
  )) throw new Error("Unresolved generation must resume the same draft, request and source version.");
  const serialized = JSON.stringify(attempt);
  const key = generationAttemptKey(scope);
  localStorage.setItem(key, serialized);
  if (localStorage.getItem(key) !== serialized) {
    throw new Error("Cannot preserve generation identity; no request may be dispatched.");
  }
}

export function settleGenerationAttempt(
  scope: StatblockDraftScope,
  attempt: StoredGenerationAttempt,
  draft: ThreatDraft,
  candidateId: string,
): boolean {
  assertDraftScope(draft, scope);
  if (draft.draft_id !== attempt.draft_id || !draft.candidate_refs.some((ref) => (
    ref.candidate_id === candidateId && ref.request_id === attempt.client_request_id
    && ref.generated_from_draft_version === attempt.expected_draft_version
  ))) throw new Error("Completed candidate does not prove the original generation attempt.");
  const current = readGenerationAttempt(scope);
  // Completion can outlive its mounted instance. It may reconcile its exact
  // stored attempt, but cannot recreate or replace a newer recovery pointer,
  // including when that newer attempt has already settled.
  if (!current || current.draft_id !== attempt.draft_id
    || current.client_request_id !== attempt.client_request_id
    || current.expected_draft_version !== attempt.expected_draft_version) return false;
  persistGenerationAttempt(scope, { ...attempt, candidate_id: candidateId });
  return true;
}
