import type {
  ReadStatblockCandidateResponseV1,
  TerminalGenerationDispositionV1,
  ThreatDraft,
} from "../../api/types";

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
  /** Present only after exact Buddy-local terminal journal proof is validated. */
  terminal_disposition?: TerminalGenerationDispositionV1;
}

export interface SettledGenerationHistoryEntry {
  schema: "dmb_sbw_generation_history_entry_v1";
  draft_id: string;
  expected_draft_version: number;
  client_request_id: string;
  terminal_disposition: TerminalGenerationDispositionV1;
}

function generationAttemptKey(scope: StatblockDraftScope): string {
  // One unresolved attempt per scope: Clear cannot permit a replacement draft to bypass it.
  return `dmb.sbw.generationAttempt:${statblockScopeKey(scope)}`;
}

function generationHistoryKey(scope: StatblockDraftScope): string {
  return `dmb.sbw.generationHistory:${statblockScopeKey(scope)}`;
}

export function isUnresolvedGenerationAttempt(
  attempt: StoredGenerationAttempt | null | undefined,
): attempt is StoredGenerationAttempt {
  return attempt?.candidate_id === null && attempt.terminal_disposition === undefined;
}

function assertTerminalDisposition(
  scope: StatblockDraftScope,
  attempt: StoredGenerationAttempt,
  disposition: TerminalGenerationDispositionV1,
): void {
  if (
    (disposition.status !== "terminal_failure" && disposition.status !== "terminal_expired")
    || disposition.draft_id !== attempt.draft_id
    || disposition.source_draft_version !== attempt.expected_draft_version
    || disposition.request_id !== attempt.client_request_id
    || !/^sha256:[0-9a-f]{64}$/.test(disposition.request_digest)
    || disposition.world_id !== scope.worldId
    || disposition.scope_mode !== scope.mode
    || disposition.campaign_id !== scope.campaignId
  ) throw new Error("Terminal generation proof does not match the exact request, source version and scope.");
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
  if (attempt.terminal_disposition !== undefined) {
    assertTerminalDisposition(scope, attempt, attempt.terminal_disposition);
  }
  return attempt;
}

export function persistGenerationAttempt(
  scope: StatblockDraftScope,
  attempt: StoredGenerationAttempt,
): void {
  const existing = readGenerationAttempt(scope);
  if (isUnresolvedGenerationAttempt(existing) && (
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

export function readSettledGenerationHistory(
  scope: StatblockDraftScope,
): SettledGenerationHistoryEntry[] {
  const raw = localStorage.getItem(generationHistoryKey(scope));
  if (raw === null) return [];
  const entries = JSON.parse(raw) as SettledGenerationHistoryEntry[];
  if (!Array.isArray(entries)) throw new Error("Stored generation history is invalid; generation is blocked.");
  for (const entry of entries) {
    if (
      entry?.schema !== "dmb_sbw_generation_history_entry_v1"
      || typeof entry.draft_id !== "string" || !entry.draft_id.trim()
      || !Number.isInteger(entry.expected_draft_version) || entry.expected_draft_version < 1
      || typeof entry.client_request_id !== "string" || !entry.client_request_id.trim()
    ) throw new Error("Stored generation history is invalid; generation is blocked.");
    assertTerminalDisposition(scope, {
      schema: "dmb_sbw_generation_attempt_v1",
      draft_id: entry.draft_id,
      expected_draft_version: entry.expected_draft_version,
      client_request_id: entry.client_request_id,
      candidate_id: null,
      terminal_disposition: entry.terminal_disposition,
    }, entry.terminal_disposition);
  }
  return entries;
}

export function settleTerminalGenerationAttempt(
  scope: StatblockDraftScope,
  attempt: StoredGenerationAttempt,
  disposition: TerminalGenerationDispositionV1,
): boolean {
  assertTerminalDisposition(scope, attempt, disposition);
  const entry: SettledGenerationHistoryEntry = {
    schema: "dmb_sbw_generation_history_entry_v1",
    draft_id: attempt.draft_id,
    expected_draft_version: attempt.expected_draft_version,
    client_request_id: attempt.client_request_id,
    terminal_disposition: disposition,
  };
  const history = readSettledGenerationHistory(scope);
  const matchingEntry = history.find((item) => item.draft_id === entry.draft_id
    && item.expected_draft_version === entry.expected_draft_version
    && item.client_request_id === entry.client_request_id);
  if (matchingEntry && JSON.stringify(matchingEntry.terminal_disposition) !== JSON.stringify(disposition)) {
    throw new Error("Terminal generation history conflicts with the exact durable request proof.");
  }
  if (!matchingEntry) {
    const serializedHistory = JSON.stringify([...history, entry]);
    const historyKey = generationHistoryKey(scope);
    localStorage.setItem(historyKey, serializedHistory);
    if (localStorage.getItem(historyKey) !== serializedHistory) {
      throw new Error("Cannot preserve terminal generation history; the attempt remains unresolved.");
    }
  }

  const current = readGenerationAttempt(scope);
  if (!current || current.draft_id !== attempt.draft_id
    || current.client_request_id !== attempt.client_request_id
    || current.expected_draft_version !== attempt.expected_draft_version
    || !isUnresolvedGenerationAttempt(current)) return false;
  persistGenerationAttempt(scope, { ...current, terminal_disposition: disposition });
  return true;
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
