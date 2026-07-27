import type {
  CandidateLineageV1,
  ReviseCandidateFromEditedDefinitionRequestV1,
  ReviseResultLabel,
  ThreatDraftCandidateRefV1,
  ThreatDraftV1,
} from "../../api/types";
import type {
  RulesetRef,
  StatblockDefinitionV1_Input,
} from "../../contracts/dungeonbuddy-statblocks-v1/client";
import type { StatblockEditorState } from "../editor/statblockEditorState";

export const REVISE_ATTEMPT_STORAGE_PREFIX = "dmb.sbw06.reviseAttempt:";
export const CANDIDATE_WORKING_COPY_PREFIX = "dmb.sbw.workingCopy:";
export const LEGACY_WORKBENCH_JOIN_KEY = "dmb.sbw.workbenchJoin";

export const MAX_REVISION_INSTRUCTIONS = 16;
export const MAX_INSTRUCTION_CODEPOINTS = 500;
export const MAX_INSTRUCTIONS_TOTAL_CODEPOINTS = 4000;

export interface StoredReviseAttemptV1 {
  schema: "dmb_sbw06_revise_attempt_v1";
  draft_id: string;
  source_candidate_id: string;
  request_id: string;
  raw_instructions: string;
  request: ReviseCandidateFromEditedDefinitionRequestV1;
  last_result: ReviseResultLabel | null;
  candidate_id: string | null;
  created_at: string;
  awaiting_local_refresh?: boolean;
  ui_preclaim?: "stale_version" | "http_422" | null;
}

export interface RevisePanelActions {
  showResume: boolean;
  showStartNew: boolean;
  allowCreateNew: boolean;
  freezeReplaySource: boolean;
  awaitingLocalRefresh: boolean;
}

export type ReviseResultClass =
  | "in_flight"
  | "resume_same"
  | "refresh_incomplete"
  | "terminal_new_allowed"
  | "blocked_diagnostics"
  | "stale_version_retry"
  | "preclaim_correctable"
  | "completed";

export type BuildReviseRequestResult =
  | { ok: true; request: ReviseCandidateFromEditedDefinitionRequestV1 }
  | { ok: false; message: string };

export type NormalizeInstructionsResult =
  | { ok: true; instructions: string[] }
  | { ok: false; message: string };

function rulesetKey(ruleset: RulesetRef): string {
  return `${ruleset.system}|${ruleset.edition}|${ruleset.house_ruleset_id ?? ""}`;
}

export function reviseAttemptStorageKey(draftId: string): string {
  return `${REVISE_ATTEMPT_STORAGE_PREFIX}${draftId.trim()}`;
}

export function candidateWorkingCopyStorageKey(draftId: string, candidateId: string): string {
  return `${CANDIDATE_WORKING_COPY_PREFIX}${draftId.trim()}:${candidateId.trim()}`;
}

export function unicodeCodePointLength(value: string): number {
  return [...value].length;
}

export function normalizeRevisionInstructions(rawLines: string[]): NormalizeInstructionsResult {
  const normalized: string[] = [];
  let totalCodepoints = 0;
  for (const item of rawLines) {
    const trimmed = item.trim();
    if (!trimmed) continue;
    if (unicodeCodePointLength(trimmed) > MAX_INSTRUCTION_CODEPOINTS) {
      return { ok: false, message: "Each instruction must be at most 500 characters." };
    }
    totalCodepoints += unicodeCodePointLength(trimmed);
    if (totalCodepoints > MAX_INSTRUCTIONS_TOTAL_CODEPOINTS) {
      return { ok: false, message: "Revision instructions exceed the total size limit." };
    }
    normalized.push(trimmed);
  }
  if (normalized.length === 0) {
    return { ok: false, message: "Enter at least one revision instruction (one per line)." };
  }
  if (normalized.length > MAX_REVISION_INSTRUCTIONS) {
    return { ok: false, message: "At most 16 revision instructions are allowed." };
  }
  return { ok: true, instructions: normalized };
}

export function normalizeRevisionInstructionsFromTextarea(raw: string): NormalizeInstructionsResult {
  return normalizeRevisionInstructions(raw.split(/\r?\n/));
}

export function buildReviseRequestFromWorkingCopy(args: {
  requestId: string;
  draft: ThreatDraftV1;
  editorState: StatblockEditorState;
  revisionInstructions: string[];
  preserveElementKeys: boolean;
}): BuildReviseRequestResult {
  const { draft, editorState, revisionInstructions, preserveElementKeys, requestId } = args;
  const workingCopy = editorState.workingCopy;
  const draftRuleset = draft.generation_intent.ruleset;
  const workingRuleset = workingCopy.ruleset;
  if (
    !workingRuleset ||
    rulesetKey(workingRuleset) !== rulesetKey(draftRuleset as RulesetRef)
  ) {
    return {
      ok: false,
      message:
        "Working-copy ruleset does not match the ThreatDraft generation ruleset — resolve before revising.",
    };
  }

  const normalized = normalizeRevisionInstructions(revisionInstructions);
  if (!normalized.ok) {
    return { ok: false, message: normalized.message };
  }

  const request: ReviseCandidateFromEditedDefinitionRequestV1 = {
    request_id: requestId,
    expected_draft_version: draft.version,
    editor_state_revision: String(editorState.stateRevision),
    source_definition: structuredClone(workingCopy) as StatblockDefinitionV1_Input,
    revision_instructions: normalized.instructions,
    preserve_element_keys: preserveElementKeys,
    ruleset: {
      system: draftRuleset.system,
      edition: draftRuleset.edition,
      house_ruleset_id: draftRuleset.house_ruleset_id ?? null,
    },
    intent: {
      target_cr: draft.generation_intent.target_cr ?? null,
      roles: [...draft.intended_roles],
      complexity: draft.generation_intent.complexity ?? null,
      must_include: [...draft.generation_intent.must_include],
      must_avoid: [...draft.generation_intent.must_avoid],
    },
    context: {
      party_level: draft.encounter_context.party_level ?? null,
      party_size: draft.encounter_context.party_size ?? null,
      terrain_notes: [...draft.encounter_context.terrain_notes],
    },
    source: {
      name_hint: draft.name,
      description: draft.description,
    },
  };

  return { ok: true, request };
}

export function validateStoredReviseAttempt(
  value: unknown,
  draftId: string,
): StoredReviseAttemptV1 | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const record = value as StoredReviseAttemptV1;
  if (record.schema !== "dmb_sbw06_revise_attempt_v1") return null;
  if (typeof record.draft_id !== "string" || record.draft_id.trim() !== draftId.trim()) {
    return null;
  }
  if (typeof record.source_candidate_id !== "string" || !record.source_candidate_id.trim()) {
    return null;
  }
  if (typeof record.request_id !== "string" || !record.request_id.trim()) return null;
  if (typeof record.raw_instructions !== "string") return null;
  if (typeof record.created_at !== "string" || !record.created_at.trim()) return null;
  const req = record.request;
  if (!req || typeof req !== "object") return null;
  if (req.request_id !== record.request_id) return null;
  if (typeof req.expected_draft_version !== "number" || req.expected_draft_version < 1) {
    return null;
  }
  if (typeof req.editor_state_revision !== "string" || !req.editor_state_revision) return null;
  if (!req.source_definition || typeof req.source_definition !== "object") return null;
  if (!Array.isArray(req.revision_instructions) || req.revision_instructions.length === 0) {
    return null;
  }
  if (typeof req.preserve_element_keys !== "boolean") return null;
  if (!req.ruleset || typeof req.ruleset !== "object") return null;
  if (record.last_result != null && typeof record.last_result !== "string") return null;
  if (record.candidate_id != null && typeof record.candidate_id !== "string") return null;
  if (
    record.awaiting_local_refresh != null &&
    typeof record.awaiting_local_refresh !== "boolean"
  ) {
    return null;
  }
  if (
    record.ui_preclaim != null &&
    record.ui_preclaim !== "stale_version" &&
    record.ui_preclaim !== "http_422"
  ) {
    return null;
  }
  return record;
}

export function readStoredReviseAttempt(draftId: string): StoredReviseAttemptV1 | null {
  try {
    const raw = sessionStorage.getItem(reviseAttemptStorageKey(draftId));
    if (!raw) return null;
    return validateStoredReviseAttempt(JSON.parse(raw) as unknown, draftId);
  } catch {
    return null;
  }
}

export function writeStoredReviseAttempt(attempt: StoredReviseAttemptV1): void {
  try {
    sessionStorage.setItem(reviseAttemptStorageKey(attempt.draft_id), JSON.stringify(attempt));
  } catch {
    /* quota / private mode */
  }
}

function readWorkingCopyJson(raw: string | null): StatblockDefinitionV1_Input | null {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return null;
    return parsed as StatblockDefinitionV1_Input;
  } catch {
    return null;
  }
}

export function readCandidateWorkingCopy(
  draftId: string,
  candidateId: string,
): StatblockDefinitionV1_Input | null {
  try {
    return readWorkingCopyJson(
      sessionStorage.getItem(candidateWorkingCopyStorageKey(draftId, candidateId)),
    );
  } catch {
    return null;
  }
}

export function writeCandidateWorkingCopy(
  draftId: string,
  candidateId: string,
  workingCopy: StatblockDefinitionV1_Input,
): void {
  try {
    sessionStorage.setItem(
      candidateWorkingCopyStorageKey(draftId, candidateId),
      JSON.stringify(workingCopy),
    );
  } catch {
    /* ignore */
  }
}

interface LegacyJoinShape {
  draft_id?: string | null;
  candidate_id?: string | null;
  working_copy?: StatblockDefinitionV1_Input | null;
}

export function readLegacyJoinWorkingCopyForCandidate(
  draftId: string,
  candidateId: string,
): StatblockDefinitionV1_Input | null {
  try {
    const raw = sessionStorage.getItem(LEGACY_WORKBENCH_JOIN_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as LegacyJoinShape;
    if (!parsed || typeof parsed !== "object") return null;
    if (parsed.draft_id?.trim() !== draftId.trim()) return null;
    if (parsed.candidate_id?.trim() !== candidateId.trim()) return null;
    const wc = parsed.working_copy;
    if (!wc || typeof wc !== "object" || Array.isArray(wc)) return null;
    return wc;
  } catch {
    return null;
  }
}

const ALL_REVISE_RESULTS: ReadonlySet<ReviseResultLabel> = new Set([
  "revise_claimed",
  "dispatched_unknown",
  "candidate_received",
  "cache_stored_ref_pending",
  "reconciled",
  "revise_busy",
  "revise_history_full",
  "revise_input_conflict",
  "revise_integrity_conflict",
  "revise_blocked",
  "revise_draft_unavailable",
  "terminal_failure",
]);

export function classifyReviseResult(result: ReviseResultLabel): ReviseResultClass {
  if (!ALL_REVISE_RESULTS.has(result)) {
    return "blocked_diagnostics";
  }
  switch (result) {
    case "revise_claimed":
    case "dispatched_unknown":
    case "candidate_received":
    case "cache_stored_ref_pending":
    case "revise_draft_unavailable":
      return "resume_same";
    case "reconciled":
      return "refresh_incomplete";
    case "terminal_failure":
      return "terminal_new_allowed";
    case "revise_busy":
    case "revise_history_full":
    case "revise_input_conflict":
    case "revise_integrity_conflict":
      return "blocked_diagnostics";
    case "revise_blocked":
      return "preclaim_correctable";
    default:
      return "blocked_diagnostics";
  }
}

export function lineageSummary(lineage: CandidateLineageV1 | null | undefined): string {
  if (!lineage) {
    return "Generated proposal — legacy ref without revise lineage";
  }
  switch (lineage.source_origin_kind) {
    case "edited_working_copy":
      return lineage.edited_working_copy
        ? `Revised from working copy at draft v${lineage.edited_working_copy.source_draft_version}`
        : "Revised from working copy";
    case "candidate":
      return lineage.candidate
        ? `Revised from candidate ${lineage.candidate.source_candidate_id}`
        : "Revised from candidate";
    case "accepted_revision":
      return lineage.accepted_revision
        ? `Revised from saved revision ${lineage.accepted_revision.statblock_id}/${lineage.accepted_revision.revision_id}`
        : "Revised from saved revision";
    default:
      return "Generated proposal";
  }
}

export function proveReconciledRefOnDraft(
  draft: ThreatDraftV1,
  candidateId: string,
  requestId: string,
): ThreatDraftCandidateRefV1 | null {
  const ref = draft.candidate_refs.find((item) => item.candidate_id === candidateId);
  if (!ref) return null;
  if (ref.request_id !== requestId) return null;
  const lineage = ref.lineage;
  if (!lineage) return null;
  if (lineage.revise_request_id !== requestId) return null;
  if (lineage.source_origin_kind !== "edited_working_copy") return null;
  return ref;
}

export function isReviseAttemptCompleted(attempt: StoredReviseAttemptV1): boolean {
  return (
    attempt.last_result === "reconciled" &&
    attempt.candidate_id != null &&
    attempt.awaiting_local_refresh !== true
  );
}

export function markReviseAwaitingLocalRefresh(
  attempt: StoredReviseAttemptV1,
  candidateId: string,
): StoredReviseAttemptV1 {
  return {
    ...attempt,
    last_result: "reconciled",
    candidate_id: candidateId,
    awaiting_local_refresh: true,
    ui_preclaim: null,
  };
}

export function markReviseAttemptCompleted(
  attempt: StoredReviseAttemptV1,
  candidateId: string,
): StoredReviseAttemptV1 {
  return {
    ...attempt,
    last_result: "reconciled",
    candidate_id: candidateId,
    awaiting_local_refresh: false,
    ui_preclaim: null,
  };
}

export function markRevisePreclaimRebuild(
  attempt: StoredReviseAttemptV1,
  preclaim: "stale_version" | "http_422",
): StoredReviseAttemptV1 {
  return {
    ...attempt,
    ui_preclaim: preclaim,
    awaiting_local_refresh: false,
  };
}

export function revisePanelActions(attempt: StoredReviseAttemptV1 | null): RevisePanelActions {
  const completedDefault: RevisePanelActions = {
    showResume: false,
    showStartNew: false,
    allowCreateNew: true,
    freezeReplaySource: false,
    awaitingLocalRefresh: false,
  };
  if (!attempt) {
    return completedDefault;
  }
  if (isReviseAttemptCompleted(attempt)) {
    return completedDefault;
  }
  if (attempt.awaiting_local_refresh === true) {
    return {
      showResume: false,
      showStartNew: false,
      allowCreateNew: false,
      freezeReplaySource: true,
      awaitingLocalRefresh: true,
    };
  }
  if (attempt.ui_preclaim === "stale_version" || attempt.ui_preclaim === "http_422") {
    return {
      showResume: false,
      showStartNew: false,
      allowCreateNew: true,
      freezeReplaySource: false,
      awaitingLocalRefresh: false,
    };
  }
  if (attempt.last_result == null) {
    return {
      showResume: true,
      showStartNew: false,
      allowCreateNew: false,
      freezeReplaySource: true,
      awaitingLocalRefresh: false,
    };
  }
  const klass = classifyReviseResult(attempt.last_result);
  if (klass === "resume_same") {
    return {
      showResume: true,
      showStartNew: false,
      allowCreateNew: false,
      freezeReplaySource: true,
      awaitingLocalRefresh: false,
    };
  }
  if (klass === "terminal_new_allowed") {
    return {
      showResume: false,
      showStartNew: true,
      allowCreateNew: false,
      freezeReplaySource: true,
      awaitingLocalRefresh: false,
    };
  }
  if (attempt.last_result === "revise_blocked") {
    return {
      showResume: false,
      showStartNew: false,
      allowCreateNew: true,
      freezeReplaySource: false,
      awaitingLocalRefresh: false,
    };
  }
  if (
    attempt.last_result === "revise_input_conflict" ||
    attempt.last_result === "revise_integrity_conflict"
  ) {
    return {
      showResume: false,
      showStartNew: false,
      allowCreateNew: false,
      freezeReplaySource: true,
      awaitingLocalRefresh: false,
    };
  }
  return {
    showResume: false,
    showStartNew: false,
    allowCreateNew: false,
    freezeReplaySource: true,
    awaitingLocalRefresh: false,
  };
}

export function updateReviseAttemptResult(
  attempt: StoredReviseAttemptV1,
  result: ReviseResultLabel,
  candidateId?: string | null,
): StoredReviseAttemptV1 {
  return {
    ...attempt,
    last_result: result,
    candidate_id: candidateId ?? attempt.candidate_id,
  };
}
