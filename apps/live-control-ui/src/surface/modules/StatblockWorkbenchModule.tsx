import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";

import {
  acceptThreatDraftMechanics,
  createThreatDraft,
  generateThreatDraftCandidate,
  getAcceptanceOperation,
  getStatblockCandidate,
  LiveApiError,
  reconcileAcceptanceOperation,
  validateStatblockDefinition,
} from "../../api/liveApi";
import type {
  AcceptanceResultLabel,
  AcceptThreatDraftMechanicsRequestV1,
  AcceptThreatDraftMechanicsResponseV1,
  CreateThreatDraftRequestV1,
  GenerateThreatDraftCandidateResponseV1,
  ReadAcceptanceOperationResponseV1,
  ReadStatblockCandidateResponseV1,
  ValidateDefinitionBuddyResponseV1,
} from "../../api/types";
import type {
  GeneratedStatblockCandidateV1,
  StatblockDefinitionV1_Input,
  ValidationReceiptV1,
} from "../../contracts/dungeonbuddy-statblocks-v1/client";
import { StatblockDefinitionEditor } from "../../statblocks/editor/StatblockDefinitionEditor";
import {
  beginValidationAttempt,
  createEditorStateFromOutput,
  getUiStatus,
  markValidationAssociated,
  markValidationUnavailable,
  type StatblockEditorState,
} from "../../statblocks/editor/statblockEditorState";
import {
  mapServerValidationStatus,
  partitionValidationIssuesByPath,
  splitIssuesBySeverity,
} from "../../statblocks/editor/statblockValidationIssues";
import { StatblockRenderer } from "../../statblocks/render/StatblockRenderer";

type LoadState =
  | { kind: "idle" }
  | { kind: "loading"; candidateId: string }
  | { kind: "success"; response: ReadStatblockCandidateResponseV1 }
  | {
      kind: "status";
      candidateId: string;
      status: Exclude<ReadStatblockCandidateResponseV1["status"], "active">;
      failureCategory: string | null;
      failureMessage: string | null;
    }
  | { kind: "error"; candidateId: string; message: string };

type ViewMode = "review" | "edit";

type PreviewValidation = {
  associatedRevision: number;
  editorEpoch: number;
  receipt: ValidationReceiptV1;
  definitionDigest: string;
};

type PendingValidation = {
  requestId: number;
  editorEpoch: number;
  stateRevision: number;
};

type ValidationFailure = {
  editorEpoch: number;
  stateRevision: number;
  message: string;
};

function previewIsCurrent(
  preview: PreviewValidation | null,
  editorState: StatblockEditorState | null,
  editorEpoch: number,
): boolean {
  if (preview == null || editorState == null) return false;
  const uiStatus = getUiStatus(editorState);
  return (
    preview.editorEpoch === editorEpoch &&
    editorState.validatedRevision === preview.associatedRevision &&
    editorState.stateRevision === preview.associatedRevision &&
    (uiStatus === "validated" ||
      uiStatus === "validated_with_warnings" ||
      uiStatus === "validated_with_errors")
  );
}

function acceptPreviewEligible(
  preview: PreviewValidation | null,
  editorState: StatblockEditorState | null,
  editorEpoch: number,
): boolean {
  if (!previewIsCurrent(preview, editorState, editorEpoch) || preview == null) return false;
  return preview.receipt.status === "valid" || preview.receipt.status === "warnings";
}

function readCandidateIdFromLocation(): string {
  if (typeof window === "undefined") return "";
  const params = new URLSearchParams(window.location.search);
  return params.get("candidateId")?.trim() ?? "";
}

/** Split comma/newline operator lists into bounded non-empty trimmed strings. */
function parseBoundedStringList(raw: string): string[] {
  return raw
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
}

function parseOptionalPositiveInt(raw: string): number | null | "invalid" {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  const value = Number(trimmed);
  if (!Number.isInteger(value) || value < 1) return "invalid";
  return value;
}

type CreatedDraftIdentity = {
  draft_id: string;
  version: number;
  name: string;
};

type CreateFormFields = {
  name: string;
  description: string;
  threatKind: string;
  createdBy: string;
  worldId: string;
  campaignId: string;
  graphRevisionId: string;
  rulesetSystem: string;
  rulesetEdition: string;
  houseRulesetId: string;
  focusSession: string;
  prepLabel: string;
  slugHint: string;
  targetCr: string;
  complexity: string;
  mustInclude: string;
  mustAvoid: string;
  intendedRoles: string;
  tags: string;
  partyLevel: string;
  partySize: string;
  terrainNotes: string;
  selectedNodeIds: string;
  admittedSourceAnchorIds: string;
};

const DEFAULT_CREATE_FORM: CreateFormFields = {
  name: "",
  description: "",
  threatKind: "creature",
  createdBy: "",
  worldId: "",
  campaignId: "",
  graphRevisionId: "",
  // Visible established repository default; operator may change.
  rulesetSystem: "dnd5e",
  rulesetEdition: "2024",
  houseRulesetId: "",
  focusSession: "",
  prepLabel: "",
  slugHint: "",
  targetCr: "",
  complexity: "",
  mustInclude: "",
  mustAvoid: "",
  intendedRoles: "",
  tags: "",
  partyLevel: "",
  partySize: "",
  terrainNotes: "",
  selectedNodeIds: "",
  admittedSourceAnchorIds: "",
};

function buildCreateThreatDraftRequest(
  fields: CreateFormFields,
): { ok: true; request: CreateThreatDraftRequestV1 } | { ok: false; message: string } {
  const name = fields.name.trim();
  const description = fields.description.trim();
  const threatKind = fields.threatKind.trim();
  const createdBy = fields.createdBy.trim();
  const worldId = fields.worldId.trim();
  const campaignId = fields.campaignId.trim();
  const graphRevisionId = fields.graphRevisionId.trim();
  const rulesetSystem = fields.rulesetSystem.trim();
  const rulesetEdition = fields.rulesetEdition.trim();

  if (!name) return { ok: false, message: "Provide a threat name." };
  if (!description) return { ok: false, message: "Provide a threat description." };
  if (!threatKind) return { ok: false, message: "Provide a threat kind." };
  if (!createdBy) return { ok: false, message: "Provide created_by (actor)." };
  if (!worldId) return { ok: false, message: "Provide an exact world_id." };
  if (!campaignId) return { ok: false, message: "Provide an exact campaign_id." };
  if (!graphRevisionId) {
    return { ok: false, message: "Provide an exact graph_revision_id (no latest fallback)." };
  }
  if (!rulesetSystem || !rulesetEdition) {
    return { ok: false, message: "Provide ruleset system and edition." };
  }

  let focusSessionValue: number | null = null;
  const focusSessionRaw = fields.focusSession.trim();
  if (focusSessionRaw) {
    const parsed = Number(focusSessionRaw);
    if (!Number.isInteger(parsed) || parsed < 0) {
      return { ok: false, message: "Focus session must be an integer ≥ 0, or empty." };
    }
    focusSessionValue = parsed;
  }

  const partyLevel = parseOptionalPositiveInt(fields.partyLevel);
  if (partyLevel === "invalid") {
    return { ok: false, message: "Party level must be an integer ≥ 1, or empty." };
  }
  const partySize = parseOptionalPositiveInt(fields.partySize);
  if (partySize === "invalid") {
    return { ok: false, message: "Party size must be an integer ≥ 1, or empty." };
  }

  const prepLabel = fields.prepLabel.trim() || null;
  const slugHint = fields.slugHint.trim() || null;
  const houseRulesetId = fields.houseRulesetId.trim() || null;
  const targetCr = fields.targetCr.trim() || null;
  const complexity = fields.complexity.trim() || null;
  const focus =
    focusSessionValue != null || prepLabel != null
      ? { session: focusSessionValue, prep_label: prepLabel }
      : null;

  return {
    ok: true,
    request: {
      world_id: worldId,
      campaign_id: campaignId,
      focus,
      name,
      slug_hint: slugHint,
      description,
      threat_kind: threatKind,
      intended_roles: parseBoundedStringList(fields.intendedRoles),
      tags: parseBoundedStringList(fields.tags),
      generation_intent: {
        ruleset: {
          system: rulesetSystem,
          edition: rulesetEdition,
          house_ruleset_id: houseRulesetId,
        },
        target_cr: targetCr,
        complexity,
        must_include: parseBoundedStringList(fields.mustInclude),
        must_avoid: parseBoundedStringList(fields.mustAvoid),
      },
      encounter_context: {
        party_level: partyLevel,
        party_size: partySize,
        terrain_notes: parseBoundedStringList(fields.terrainNotes),
      },
      graph_context_snapshot: {
        graph_revision_id: graphRevisionId,
        selected_node_ids: parseBoundedStringList(fields.selectedNodeIds),
        admitted_source_anchor_ids: parseBoundedStringList(fields.admittedSourceAnchorIds),
      },
      created_by: createdBy,
    },
  };
}

function isCreateTransportUncertainty(error: unknown): boolean {
  if (error instanceof LiveApiError) {
    // HTTP status was observed — definite request outcome from the API layer.
    return false;
  }
  return true;
}

function createdDraftFromResponse(draft: {
  draft_id?: unknown;
  version?: unknown;
  name?: unknown;
}): CreatedDraftIdentity | null {
  if (typeof draft.draft_id !== "string" || !draft.draft_id.trim()) return null;
  if (typeof draft.version !== "number" || !Number.isInteger(draft.version) || draft.version < 1) {
    return null;
  }
  const name = typeof draft.name === "string" && draft.name.trim() ? draft.name.trim() : draft.draft_id;
  return { draft_id: draft.draft_id.trim(), version: draft.version, name };
}

function isIntegrityFailureCategory(category: string | null | undefined): boolean {
  if (!category) return false;
  return (
    category === "integrity_failure" ||
    category === "contract_failure" ||
    category.endsWith("_integrity_failure")
  );
}

/** GM-visible global issue line: code, severity, original path, message, suggested_resolution. */
function GlobalIssueLine({
  issue,
}: {
  issue: {
    code: string;
    severity: string;
    field_path: string;
    message: string;
    suggested_resolution?: string | null;
  };
}) {
  const path = typeof issue.field_path === "string" ? issue.field_path : "";
  return (
    <>
      <span data-issue-code={issue.code}>code={issue.code}</span>
      {" · "}
      <span data-issue-severity-label={issue.severity}>severity={issue.severity}</span>
      {path ? (
        <>
          {" · "}
          <span data-issue-path={path}>path={path}</span>
        </>
      ) : null}
      {" · "}
      <span data-issue-message={issue.message}>{issue.message}</span>
      {issue.suggested_resolution != null ? (
        <>
          {" · "}
          <span data-issue-suggested-resolution={issue.suggested_resolution}>
            suggested={issue.suggested_resolution}
          </span>
        </>
      ) : null}
    </>
  );
}

export type CandidateStatusPresentation = {
  title: string;
  body: string;
  stateKind: "expired" | "missing" | "integrity_failure" | "dependency_unavailable";
};

export function presentCandidateStatus(
  status: Exclude<ReadStatblockCandidateResponseV1["status"], "active">,
  failureCategory: string | null | undefined,
): CandidateStatusPresentation {
  if (status === "expired") {
    return {
      title: "Candidate expired",
      stateKind: "expired",
      body: "This candidate has expired. The exact candidate ID is retained; generate a new candidate rather than falling back to mock or corpus output.",
    };
  }
  if (status === "missing") {
    return {
      title: "Candidate missing",
      stateKind: "missing",
      body: "No candidate exists for this exact ID. There is no fallback to another candidate, mock draft, or corpus file.",
    };
  }
  if (isIntegrityFailureCategory(failureCategory)) {
    return {
      title: "Candidate integrity failure",
      stateKind: "integrity_failure",
      body: "This candidate cannot be trusted because of a local contract or cache integrity failure. The exact candidate ID is retained; this is not a DungeonMindServer outage. Do not fall back to mock or corpus output.",
    };
  }
  return {
    title: "Candidate service unavailable",
    stateKind: "dependency_unavailable",
    body: "The candidate service is unavailable. Retry the exact ID; mock mechanics are not used as a fallback.",
  };
}

function CandidateStatusPanel({
  candidateId,
  status,
  failureCategory,
  failureMessage,
  onRetry,
}: {
  candidateId: string;
  status: Exclude<ReadStatblockCandidateResponseV1["status"], "active">;
  failureCategory: string | null;
  failureMessage: string | null;
  onRetry: () => void;
}) {
  const presentation = presentCandidateStatus(status, failureCategory);
  return (
    <section className="statblock-section" role="status" data-candidate-status={presentation.stateKind}>
      <h3>{presentation.title}</h3>
      <p>
        Exact ID retained: <code>{candidateId}</code>
      </p>
      <p className="module-muted">{presentation.body}</p>
      {failureCategory ? (
        <p className="module-muted">
          Category: <code>{failureCategory}</code>
          {failureMessage ? ` — ${failureMessage}` : ""}
        </p>
      ) : null}
      <button type="button" onClick={onRetry}>
        Retry exact candidate
      </button>
    </section>
  );
}

function PreviewValidationPanel({
  preview,
  editorState,
  editorEpoch,
  validationFailure,
  workingCopy,
}: {
  preview: PreviewValidation | null;
  editorState: StatblockEditorState | null;
  editorEpoch: number;
  validationFailure: ValidationFailure | null;
  workingCopy: StatblockDefinitionV1_Input | null;
}) {
  const failureCurrent =
    validationFailure != null &&
    editorState != null &&
    validationFailure.editorEpoch === editorEpoch &&
    validationFailure.stateRevision === editorState.stateRevision;

  const previewCurrent = previewIsCurrent(preview, editorState, editorEpoch);

  if (failureCurrent) {
    return (
      <section
        className="statblock-section"
        role="status"
        data-testid="preview-validation-panel"
        data-preview-state="unavailable"
      >
        <h3>Preview validation</h3>
        <p className="module-muted">
          Validation unavailable. Working copy retained (unsaved). {validationFailure.message}
        </p>
      </section>
    );
  }

  if (!preview) {
    return (
      <section
        className="statblock-section"
        role="status"
        data-testid="preview-validation-panel"
        data-preview-state="none"
      >
        <h3>Preview validation</h3>
        <p className="module-muted">
          No preview receipt yet. Validate submits the exact session working copy; nothing is saved or
          accepted.
        </p>
      </section>
    );
  }

  if (!previewCurrent) {
    return (
      <section
        className="statblock-section"
        role="status"
        data-testid="preview-validation-panel"
        data-preview-state="stale"
      >
        <h3>Preview validation</h3>
        <p className="module-muted">
          Prior preview receipt is stale / not current for this working-copy revision.
        </p>
        <p className="module-muted">
          Last digest: <code>{preview.definitionDigest}</code>
        </p>
      </section>
    );
  }

  const { fieldIssues, globalIssues } = partitionValidationIssuesByPath(
    preview.receipt.issues,
    workingCopy,
  );
  const fieldSplit = splitIssuesBySeverity(fieldIssues);
  const globalSplit = splitIssuesBySeverity(globalIssues);

  return (
    <section
      className="statblock-section"
      role="status"
      data-testid="preview-validation-panel"
      data-preview-state="current"
      data-preview-receipt-status={preview.receipt.status}
    >
      <h3>Preview validation</h3>
      <p>
        Server status: <code>{preview.receipt.status}</code> → UI{" "}
        <code>{mapServerValidationStatus(preview.receipt.status)}</code>
      </p>
      <p className="module-muted">
        Associated digest: <code>{preview.definitionDigest}</code>
      </p>

      <div data-testid="preview-field-issues">
        <h4>Field issues</h4>
        {fieldIssues.length === 0 ? <p className="module-muted">None</p> : null}
        {fieldSplit.errors.map((issue) => (
          <p key={`fe-${issue.code}-${issue.field_path}`} data-issue-severity="error">
            [error] <code>{issue.field_path}</code>: {issue.message}
          </p>
        ))}
        {fieldSplit.warnings.map((issue) => (
          <p key={`fw-${issue.code}-${issue.field_path}`} data-issue-severity="warning">
            [warning] <code>{issue.field_path}</code>: {issue.message}
          </p>
        ))}
        {fieldSplit.infos.map((issue) => (
          <p key={`fi-${issue.code}-${issue.field_path}`} data-issue-severity="info">
            [info] <code>{issue.field_path}</code>: {issue.message}
          </p>
        ))}
      </div>

      <div data-testid="preview-global-issues">
        <h4>Global issues</h4>
        {globalIssues.length === 0 ? <p className="module-muted">None</p> : null}
        {globalSplit.errors.map((issue) => (
          <p key={`ge-${issue.code}-${issue.field_path}-${issue.message}`} data-issue-severity="error">
            <GlobalIssueLine issue={issue} />
          </p>
        ))}
        {globalSplit.warnings.map((issue) => (
          <p
            key={`gw-${issue.code}-${issue.field_path}-${issue.message}`}
            data-issue-severity="warning"
          >
            <GlobalIssueLine issue={issue} />
          </p>
        ))}
        {globalSplit.infos.map((issue) => (
          <p key={`gi-${issue.code}-${issue.field_path}-${issue.message}`} data-issue-severity="info">
            <GlobalIssueLine issue={issue} />
          </p>
        ))}
      </div>
    </section>
  );
}

const ACCEPT_OP_STORAGE_PREFIX = "dmb.sbw07.acceptOperationId:";
const ACCEPT_ATTEMPT_STORAGE_PREFIX = "dmb.sbw07.acceptAttempt:";

interface StoredAcceptAttempt {
  operation_id: string;
  /** Exact mechanics:accept body for same-key replay when no journal claim exists yet. */
  request?: AcceptThreatDraftMechanicsRequestV1 | null;
}

function acceptOpStorageKey(draftId: string): string {
  return `${ACCEPT_OP_STORAGE_PREFIX}${draftId}`;
}

function acceptAttemptStorageKey(draftId: string): string {
  return `${ACCEPT_ATTEMPT_STORAGE_PREFIX}${draftId}`;
}

function readStoredAcceptAttempt(draftId: string): StoredAcceptAttempt | null {
  try {
    const rawAttempt = sessionStorage.getItem(acceptAttemptStorageKey(draftId));
    if (rawAttempt) {
      const parsed = JSON.parse(rawAttempt) as StoredAcceptAttempt;
      if (parsed && typeof parsed.operation_id === "string" && parsed.operation_id.trim()) {
        return {
          operation_id: parsed.operation_id.trim(),
          request: parsed.request ?? null,
        };
      }
    }
    const legacyOp = sessionStorage.getItem(acceptOpStorageKey(draftId));
    if (legacyOp && legacyOp.trim()) {
      return { operation_id: legacyOp.trim(), request: null };
    }
    return null;
  } catch {
    return null;
  }
}

function readStoredAcceptOperationId(draftId: string): string | null {
  return readStoredAcceptAttempt(draftId)?.operation_id ?? null;
}

function writeStoredAcceptAttempt(draftId: string, attempt: StoredAcceptAttempt): void {
  try {
    sessionStorage.setItem(acceptAttemptStorageKey(draftId), JSON.stringify(attempt));
    sessionStorage.setItem(acceptOpStorageKey(draftId), attempt.operation_id);
  } catch {
    /* private mode / quota — in-memory state still covers the session */
  }
}

function writeStoredAcceptOperationId(draftId: string, operationId: string): void {
  const existing = readStoredAcceptAttempt(draftId);
  writeStoredAcceptAttempt(draftId, {
    operation_id: operationId,
    request: existing?.request ?? null,
  });
}

function clearStoredAcceptOperationId(draftId: string): void {
  try {
    sessionStorage.removeItem(acceptAttemptStorageKey(draftId));
    sessionStorage.removeItem(acceptOpStorageKey(draftId));
  } catch {
    /* ignore */
  }
}

function acceptResultFromRead(
  read: ReadAcceptanceOperationResponseV1,
): AcceptThreatDraftMechanicsResponseV1 | null {
  const op = read.operation;
  const resultLabel = read.result_label;
  if (!op || !resultLabel) return null;
  return {
    schema: "dmb_accept_threat_draft_mechanics_response_v1",
    draft_id: read.draft_id,
    operation_id: op.operation_id,
    result_label: resultLabel,
    authority_state: op.authority_state,
    draft_ref: op.materialization.draft_ref,
    locator: op.locator ?? null,
    terminal_code: op.terminal_code ?? null,
    failure_category: op.failure_category ?? null,
    http_status: op.http_status ?? null,
    message: null,
  };
}

/**
 * Result-label action classes (response existence ≠ durable journal ownership).
 *
 * - ephemeralAttempt: no journal claim retained — discard attempted ID; allow Accept/Save again
 * - sameOperationRecovery: durable op exists or may exist — resume with same ID
 * - boundDisplay: durable outcome bound to exact identity — no new Accept while shown
 * - terminalFinished: journal slot free — must mint a new UUID via explicit start-new
 *
 * Blocked replay after a transport failure cannot treat a null journal read as proof that the
 * original POST will never claim. Bounded misses stay unresolved; only journal_present may
 * promote to recovery retain. A replacement UUID is allowed only after backend-proven
 * terminal_failure (SBW07a non-begin), never after local storage deletion.
 */
type AcceptActionClass =
  | "ephemeralAttempt"
  | "sameOperationRecovery"
  | "boundDisplay"
  | "terminalFinished";

type AcceptResultOrigin = "fresh" | "recovery";

/**
 * Claim-state evidence after an acceptance_blocked replay response.
 * `claim_unproven` = bounded successful GETs returned null — NOT authoritative non-claim.
 */
type BlockedClaimEvidence =
  | "journal_present"
  | "claim_unproven"
  | "lookup_uncertain";

/** Tunable for tests: bounded restore / claim-evidence lookup while a POST may still execute. */
export const ACCEPT_RESTORE_LOOKUP = {
  maxAttempts: 3,
  delayMs: 40,
};

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

async function resolveBlockedClaimEvidence(
  draftId: string,
  operationId: string,
): Promise<BlockedClaimEvidence> {
  let sawSuccessfulNull = false;
  for (let attempt = 1; attempt <= ACCEPT_RESTORE_LOOKUP.maxAttempts; attempt++) {
    try {
      const read = await getAcceptanceOperation(draftId, operationId);
      if (read.operation != null) {
        return "journal_present";
      }
      sawSuccessfulNull = true;
    } catch {
      // Keep polling — a later attempt may succeed. If all fail, existence is uncertain.
      if (attempt === ACCEPT_RESTORE_LOOKUP.maxAttempts) {
        return sawSuccessfulNull ? "claim_unproven" : "lookup_uncertain";
      }
    }
    if (attempt < ACCEPT_RESTORE_LOOKUP.maxAttempts) {
      await delay(ACCEPT_RESTORE_LOOKUP.delayMs);
    }
  }
  // Bounded null reads are not proof an in-flight original POST cannot still claim.
  return "claim_unproven";
}

function acceptActionClass(
  label: AcceptanceResultLabel | null | undefined,
  origin: AcceptResultOrigin = "fresh",
): AcceptActionClass | null {
  if (!label) return null;
  switch (label) {
    case "acceptance_blocked":
      return origin === "recovery" ? "sameOperationRecovery" : "ephemeralAttempt";
    case "acceptance_busy":
    case "acceptance_history_full":
      return "ephemeralAttempt";
    case "dispatched_unknown":
    case "server_committed_reference_pending":
    case "acceptance_input_conflict":
    case "acceptance_draft_unavailable":
      return "sameOperationRecovery";
    case "mechanics_saved":
    case "accepted_ref_conflict":
      return "boundDisplay";
    case "terminal_failure":
      return "terminalFinished";
    default:
      return null;
  }
}

/** Suppress Accept/Save while this durable outcome occupies the draft's accept UI. */
function suppressesNewAccept(
  label: AcceptanceResultLabel | null | undefined,
  origin: AcceptResultOrigin = "fresh",
): boolean {
  const klass = acceptActionClass(label, origin);
  return (
    klass === "sameOperationRecovery" ||
    klass === "boundDisplay" ||
    klass === "terminalFinished"
  );
}

/** Persist operation ID when a journaled (or unresolved optimistic) operation must be retained. */
function shouldPersistAcceptOperationId(
  label: AcceptanceResultLabel | null | undefined,
  origin: AcceptResultOrigin = "fresh",
): boolean {
  const klass = acceptActionClass(label, origin);
  return (
    klass === "sameOperationRecovery" ||
    klass === "boundDisplay" ||
    klass === "terminalFinished"
  );
}

async function readAcceptanceOperationWithRetries(
  draftId: string,
  operationId: string,
  isCurrent: () => boolean,
): Promise<ReadAcceptanceOperationResponseV1 | "cancelled"> {
  let last: ReadAcceptanceOperationResponseV1 | null = null;
  for (let attempt = 1; attempt <= ACCEPT_RESTORE_LOOKUP.maxAttempts; attempt++) {
    if (!isCurrent()) return "cancelled";
    last = await getAcceptanceOperation(draftId, operationId);
    if (!isCurrent()) return "cancelled";
    if (last.operation != null && last.result_label != null) {
      return last;
    }
    if (attempt < ACCEPT_RESTORE_LOOKUP.maxAttempts) {
      await delay(ACCEPT_RESTORE_LOOKUP.delayMs);
    }
  }
  return (
    last ?? {
      schema: "dmb_read_acceptance_operation_response_v1",
      draft_id: draftId,
      operation: null,
      result_label: null,
    }
  );
}

function AcceptMechanicsFlow({
  preview,
  editorState,
  editorEpoch,
  draftIdInput,
  draftVersionInput,
  sourceCandidateId,
  workingCopy,
}: {
  preview: PreviewValidation | null;
  editorState: StatblockEditorState;
  editorEpoch: number;
  draftIdInput: string;
  draftVersionInput: string;
  sourceCandidateId: string;
  workingCopy: StatblockDefinitionV1_Input;
}) {
  const eligible = acceptPreviewEligible(preview, editorState, editorEpoch);
  const previewCurrent = previewIsCurrent(preview, editorState, editorEpoch);
  const normalizedDraftId = draftIdInput.trim();
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [acceptPending, setAcceptPending] = useState(false);
  const [restorePending, setRestorePending] = useState(false);
  const [existenceUnresolved, setExistenceUnresolved] = useState(false);
  const [acceptError, setAcceptError] = useState<string | null>(null);
  const [acceptResult, setAcceptResult] = useState<AcceptThreatDraftMechanicsResponseV1 | null>(
    null,
  );
  const [acceptResultOrigin, setAcceptResultOrigin] = useState<AcceptResultOrigin>("fresh");
  /** Exact Accept body for same-key replay when the journal claim may not exist yet. */
  const [replayRequest, setReplayRequest] = useState<AcceptThreatDraftMechanicsRequestV1 | null>(
    null,
  );
  const acceptOperationIdRef = useRef<string | null>(null);
  /** Synchronous guard — Confirm can fire twice before React re-renders acceptPending. */
  const acceptInFlightRef = useRef(false);
  /** Draft ID that currently owns acceptResult / operation ref / restore UI. */
  const ownedDraftIdRef = useRef<string>("");
  const restoreGenerationRef = useRef(0);
  const acceptRequestGenerationRef = useRef(0);

  const clearOwnedAcceptState = () => {
    setConfirmOpen(false);
    setAcceptPending(false);
    setRestorePending(false);
    setExistenceUnresolved(false);
    setAcceptError(null);
    setAcceptResult(null);
    setAcceptResultOrigin("fresh");
    setReplayRequest(null);
    acceptOperationIdRef.current = null;
    acceptInFlightRef.current = false;
  };

  const persistAcceptAttempt = (
    draftId: string,
    operationId: string,
    request?: AcceptThreatDraftMechanicsRequestV1 | null,
  ) => {
    const existing = readStoredAcceptAttempt(draftId);
    writeStoredAcceptAttempt(draftId, {
      operation_id: operationId,
      request: request !== undefined ? request : (existing?.request ?? null),
    });
    if (request) {
      setReplayRequest(request);
    } else if (request === null) {
      setReplayRequest(null);
    } else if (existing?.request) {
      setReplayRequest(existing.request);
    }
  };

  const isRestoreGenerationCurrent = (draftId: string, restoreGeneration: number) => {
    return (
      restoreGeneration === restoreGenerationRef.current && ownedDraftIdRef.current === draftId
    );
  };

  const applyRestoredOperation = (
    draftId: string,
    restoreGeneration: number,
    read: ReadAcceptanceOperationResponseV1,
  ): boolean => {
    if (!isRestoreGenerationCurrent(draftId, restoreGeneration)) {
      return false;
    }
    const restored = acceptResultFromRead(read);
    if (!restored) {
      return false;
    }
    acceptOperationIdRef.current = restored.operation_id;
    persistAcceptAttempt(draftId, restored.operation_id);
    setAcceptResultOrigin("recovery");
    setAcceptResult(restored);
    setExistenceUnresolved(false);
    setAcceptError(null);
    return true;
  };

  const markExistenceUnresolved = (draftId: string, operationId: string) => {
    acceptOperationIdRef.current = operationId;
    persistAcceptAttempt(draftId, operationId);
    const stored = readStoredAcceptAttempt(draftId);
    if (stored?.request) {
      setReplayRequest(stored.request);
    }
    setExistenceUnresolved(true);
    setAcceptResult(null);
    setAcceptError(null);
  };

  const runRestoreLookup = async (draftId: string, storedId: string, restoreGeneration: number) => {
    acceptOperationIdRef.current = storedId;
    setRestorePending(true);
    setExistenceUnresolved(false);
    setAcceptError(null);

    try {
      const read = await readAcceptanceOperationWithRetries(draftId, storedId, () =>
        isRestoreGenerationCurrent(draftId, restoreGeneration),
      );
      if (read === "cancelled" || !isRestoreGenerationCurrent(draftId, restoreGeneration)) {
        return;
      }
      if (applyRestoredOperation(draftId, restoreGeneration, read)) {
        return;
      }
      // Miss after bounded retries is not proof the claim will never appear — retain ID.
      markExistenceUnresolved(draftId, storedId);
    } catch (error) {
      if (!isRestoreGenerationCurrent(draftId, restoreGeneration)) {
        return;
      }
      // Transient journal/read failure: keep the optimistic ID and allow retry.
      markExistenceUnresolved(draftId, storedId);
      setAcceptError(error instanceof Error ? error.message : String(error));
    } finally {
      if (isRestoreGenerationCurrent(draftId, restoreGeneration)) {
        setRestorePending(false);
      }
    }
  };

  // Pending identity is independent of validation eligibility — only close the confirm sheet.
  useEffect(() => {
    if (!eligible) {
      setConfirmOpen(false);
    }
  }, [eligible]);

  // Draft-scoped ownership: reset when the normalized draft ID changes, then restore only B.
  useEffect(() => {
    const draftId = normalizedDraftId;
    restoreGenerationRef.current += 1;
    acceptRequestGenerationRef.current += 1;
    const restoreGeneration = restoreGenerationRef.current;

    ownedDraftIdRef.current = draftId;
    clearOwnedAcceptState();

    if (!draftId) {
      return;
    }

    const storedId = readStoredAcceptOperationId(draftId);
    if (!storedId) {
      return;
    }

    const storedAttempt = readStoredAcceptAttempt(draftId);
    if (storedAttempt?.request) {
      setReplayRequest(storedAttempt.request);
    }

    void runRestoreLookup(draftId, storedId, restoreGeneration);

    return () => {
      // Cancellation always releases restorePending (draft change / unmount / Strict Mode).
      setRestorePending(false);
    };
  }, [normalizedDraftId]);

  const ensureOperationId = (): string => {
    if (!acceptOperationIdRef.current) {
      acceptOperationIdRef.current = crypto.randomUUID();
    }
    return acceptOperationIdRef.current;
  };

  const resetAcceptSession = () => {
    // Cancel only the pre-submit confirm sheet. Keep durable/restored/unresolved identity.
    setConfirmOpen(false);
    setAcceptPending(false);
    setAcceptError(null);
    if (
      !existenceUnresolved &&
      (!acceptResult ||
        acceptActionClass(acceptResult.result_label, acceptResultOrigin) === "ephemeralAttempt")
    ) {
      acceptOperationIdRef.current = null;
    }
  };

  const startNewAcceptOperation = () => {
    // Only safe after backend-proven terminal_failure (SBW07a non-begin). Local storage
    // deletion alone must never be treated as closing a possibly still-claiming operation.
    const draftId = ownedDraftIdRef.current;
    if (draftId) {
      clearStoredAcceptOperationId(draftId);
    }
    acceptOperationIdRef.current = null;
    acceptInFlightRef.current = false;
    setAcceptResult(null);
    setAcceptResultOrigin("fresh");
    setReplayRequest(null);
    setExistenceUnresolved(false);
    setAcceptError(null);
    setConfirmOpen(false);
    setAcceptPending(false);
  };

  const applyAcceptResponseForDraft = (
    draftId: string,
    requestGeneration: number,
    response: AcceptThreatDraftMechanicsResponseV1,
    fallbackOperationId: string,
    origin: AcceptResultOrigin,
  ) => {
    if (
      requestGeneration !== acceptRequestGenerationRef.current ||
      ownedDraftIdRef.current !== draftId
    ) {
      return;
    }
    const operationId = response.operation_id || fallbackOperationId;
    const label = response.result_label;
    setAcceptResultOrigin(origin);
    if (shouldPersistAcceptOperationId(label, origin)) {
      acceptOperationIdRef.current = operationId;
      persistAcceptAttempt(draftId, operationId);
      setExistenceUnresolved(false);
    } else {
      // Fresh ephemeral attempt: do not retain a nonexistent / non-active journal ID.
      clearStoredAcceptOperationId(draftId);
      acceptOperationIdRef.current = null;
      setReplayRequest(null);
      setExistenceUnresolved(false);
    }
    setAcceptResult(response);
    setConfirmOpen(false);
  };

  const runAccept = async () => {
    if (!preview || !eligible) return;
    // Never mint/replace while an optimistic or restored operation is unresolved.
    if (existenceUnresolved || suppressesNewAccept(acceptResult?.result_label, acceptResultOrigin)) {
      return;
    }
    // Prevent concurrent confirmations before React disables the button.
    if (acceptInFlightRef.current || acceptPending) return;

    const draftId = normalizedDraftId;
    const expectedVersion = Number(draftVersionInput);
    if (!draftId || !Number.isInteger(expectedVersion) || expectedVersion < 1) {
      setAcceptError("Provide a draft ID and expected draft version ≥ 1 before accepting.");
      return;
    }

    const operationId = ensureOperationId();
    const request: AcceptThreatDraftMechanicsRequestV1 = {
      operation_id: operationId,
      expected_draft_version: expectedVersion,
      definition: workingCopy,
      validation_receipt: preview.receipt,
      validation_definition_digest: preview.definitionDigest,
      source_candidate_id: sourceCandidateId,
      change_summary: "Accepted via Statblock Workbench",
    };
    const requestGeneration = ++acceptRequestGenerationRef.current;
    acceptInFlightRef.current = true;
    // Persist optimistically so reload / transport failure can same-body replay.
    persistAcceptAttempt(draftId, operationId, request);
    setAcceptPending(true);
    setAcceptError(null);

    try {
      const response = await acceptThreatDraftMechanics(draftId, request);
      applyAcceptResponseForDraft(draftId, requestGeneration, response, operationId, "fresh");
    } catch (error) {
      if (
        requestGeneration === acceptRequestGenerationRef.current &&
        ownedDraftIdRef.current === draftId
      ) {
        // Transport failure: keep ID + exact body for same-key Accept replay.
        markExistenceUnresolved(draftId, operationId);
        setReplayRequest(request);
        setAcceptError(error instanceof Error ? error.message : String(error));
      }
    } finally {
      acceptInFlightRef.current = false;
      if (
        requestGeneration === acceptRequestGenerationRef.current &&
        ownedDraftIdRef.current === draftId
      ) {
        setAcceptPending(false);
      }
    }
  };

  /** Same-key, same-body mechanics:accept replay — used when no journal claim exists yet. */
  const onReplayAccept = async () => {
    const draftId = normalizedDraftId;
    const operationId = acceptOperationIdRef.current;
    const request = replayRequest ?? readStoredAcceptAttempt(draftId)?.request ?? null;
    if (!draftId || !operationId || !request || ownedDraftIdRef.current !== draftId) return;
    if (acceptInFlightRef.current || acceptPending) return;

    const replayBody: AcceptThreatDraftMechanicsRequestV1 = {
      ...request,
      operation_id: operationId,
    };
    const requestGeneration = ++acceptRequestGenerationRef.current;
    acceptInFlightRef.current = true;
    persistAcceptAttempt(draftId, operationId, replayBody);
    setAcceptPending(true);
    setAcceptError(null);

    try {
      const response = await acceptThreatDraftMechanics(draftId, replayBody);
      if (
        requestGeneration !== acceptRequestGenerationRef.current ||
        ownedDraftIdRef.current !== draftId
      ) {
        return;
      }

      if (response.result_label === "acceptance_blocked") {
        // Call origin is not enough: blocked may be pre-claim rejection or journal-read failure.
        // A null journal read is never authoritative non-claim after a timed-out POST.
        const evidence = await resolveBlockedClaimEvidence(draftId, operationId);
        if (
          requestGeneration !== acceptRequestGenerationRef.current ||
          ownedDraftIdRef.current !== draftId
        ) {
          return;
        }
        if (evidence === "journal_present") {
          applyAcceptResponseForDraft(
            draftId,
            requestGeneration,
            response,
            operationId,
            "recovery",
          );
        } else {
          // claim_unproven (bounded nulls) or lookup_uncertain — retain id; no replacement UUID.
          markExistenceUnresolved(draftId, operationId);
          setReplayRequest(replayBody);
          setAcceptError(
            response.message ??
              (evidence === "claim_unproven"
                ? "acceptance blocked; journal miss is not proof the original request cannot claim — retaining operation id"
                : "acceptance blocked; journal lookup uncertain — retaining operation id"),
          );
        }
        return;
      }

      applyAcceptResponseForDraft(draftId, requestGeneration, response, operationId, "recovery");
    } catch (error) {
      if (
        requestGeneration === acceptRequestGenerationRef.current &&
        ownedDraftIdRef.current === draftId
      ) {
        markExistenceUnresolved(draftId, operationId);
        setReplayRequest(replayBody);
        setAcceptError(error instanceof Error ? error.message : String(error));
      }
    } finally {
      acceptInFlightRef.current = false;
      if (
        requestGeneration === acceptRequestGenerationRef.current &&
        ownedDraftIdRef.current === draftId
      ) {
        setAcceptPending(false);
      }
    }
  };

  const onResumeAcceptance = async () => {
    const draftId = normalizedDraftId;
    const operationId = acceptOperationIdRef.current;
    if (!draftId || !operationId || ownedDraftIdRef.current !== draftId) return;
    if (acceptInFlightRef.current || acceptPending) return;

    const requestGeneration = ++acceptRequestGenerationRef.current;
    acceptInFlightRef.current = true;
    setAcceptPending(true);
    setAcceptError(null);
    try {
      // recover_acceptance_operation — only after a journal operation exists.
      const response = await reconcileAcceptanceOperation(draftId, operationId);
      applyAcceptResponseForDraft(draftId, requestGeneration, response, operationId, "recovery");
    } catch (error) {
      if (
        requestGeneration === acceptRequestGenerationRef.current &&
        ownedDraftIdRef.current === draftId
      ) {
        // Transient reconcile failure: preserve operation ID + body for retry/replay.
        persistAcceptAttempt(draftId, operationId);
        setExistenceUnresolved(true);
        setAcceptError(error instanceof Error ? error.message : String(error));
      }
    } finally {
      acceptInFlightRef.current = false;
      if (
        requestGeneration === acceptRequestGenerationRef.current &&
        ownedDraftIdRef.current === draftId
      ) {
        setAcceptPending(false);
      }
    }
  };

  const onRetryLookup = async () => {
    const draftId = normalizedDraftId;
    const operationId = acceptOperationIdRef.current ?? readStoredAcceptOperationId(draftId);
    if (!draftId || !operationId || ownedDraftIdRef.current !== draftId) return;
    const restoreGeneration = ++restoreGenerationRef.current;
    await runRestoreLookup(draftId, operationId, restoreGeneration);
  };

  const resultLabel = acceptResult?.result_label ?? null;
  const actionClass = acceptActionClass(resultLabel, acceptResultOrigin);
  const blocksNewAccept =
    existenceUnresolved || suppressesNewAccept(resultLabel, acceptResultOrigin);
  const showAcceptEntry = eligible && !blocksNewAccept && !restorePending;

  if (restorePending && !acceptResult && !existenceUnresolved) {
    return (
      <p className="module-muted" role="status" data-testid="accept-mechanics-restoring">
        Restoring acceptance operation…
      </p>
    );
  }

  if (!previewCurrent && !blocksNewAccept) {
    return (
      <p className="module-muted">
        {preview
          ? "Preview validation is stale — revalidate before accept/save."
          : "Validate the working copy to preview acceptance eligibility. Mechanics accept/save does not publish to the World Graph."}
      </p>
    );
  }

  if (previewCurrent && preview?.receipt.status === "invalid" && !blocksNewAccept) {
    return (
      <p className="module-muted" role="status">
        Fix validation errors before accept/save. Invalid preview receipts cannot be accepted.
      </p>
    );
  }

  return (
    <div data-testid="accept-mechanics-flow" data-owned-draft={normalizedDraftId}>
      {showAcceptEntry ? (
        <div className="statblock-command-row">
          {!confirmOpen ? (
            <button
              type="button"
              onClick={() => {
                // Drop ephemeral attempt copy when starting a fresh confirm sheet.
                if (
                  acceptActionClass(acceptResult?.result_label, acceptResultOrigin) ===
                  "ephemeralAttempt"
                ) {
                  setAcceptResult(null);
                  acceptOperationIdRef.current = null;
                }
                ensureOperationId();
                setConfirmOpen(true);
                setAcceptError(null);
              }}
            >
              Accept/Save mechanics
            </button>
          ) : null}
        </div>
      ) : null}

      {confirmOpen && eligible && preview && !blocksNewAccept ? (
        <section
          className="statblock-section"
          data-testid="accept-mechanics-panel"
          aria-label="Accept mechanics confirmation"
        >
          <h4>Accept / save mechanics</h4>
          <p className="module-muted">
            Mechanics only — not published to the World Graph. Accepting saves immutable mechanics
            to the ThreatDraft; it does not create or update World Graph entities.
          </p>
          <p>
            Definition digest: <code>{preview.definitionDigest}</code>
          </p>
          <p>
            Validation status: <code>{preview.receipt.status}</code>
          </p>
          <div className="statblock-command-row">
            <button
              type="button"
              disabled={acceptPending}
              onClick={() => void runAccept()}
              data-testid="accept-mechanics-confirm"
            >
              {acceptPending ? "Accepting…" : "Confirm accept/save"}
            </button>
            <button
              type="button"
              disabled={acceptPending}
              onClick={() => resetAcceptSession()}
            >
              Cancel
            </button>
          </div>
        </section>
      ) : null}

      {acceptError ? (
        <p className="statblock-command-error" role="alert">
          {acceptError}
        </p>
      ) : null}

      {existenceUnresolved ? (
        <section
          className="statblock-section"
          role="status"
          data-testid="accept-existence-unresolved"
        >
          <p className="module-muted">
            Stored acceptance operation is not yet visible in the journal (claim may still be in
            flight, the Accept request may never have reached the backend, or the journal read
            failed transiently). The operation id is retained — do not start a new acceptance
            attempt.
          </p>
          <p className="module-muted">
            Operation: <code>{acceptOperationIdRef.current}</code>
          </p>
          <div className="statblock-command-row">
            <button
              type="button"
              disabled={acceptPending || restorePending}
              onClick={() => void onRetryLookup()}
              data-testid="accept-mechanics-retry-lookup"
            >
              {restorePending ? "Looking up…" : "Retry lookup"}
            </button>
            {replayRequest ? (
              <button
                type="button"
                disabled={acceptPending || restorePending}
                onClick={() => void onReplayAccept()}
                data-testid="accept-mechanics-replay"
              >
                {acceptPending ? "Replaying…" : "Replay accept"}
              </button>
            ) : null}
            <button
              type="button"
              disabled={acceptPending || restorePending}
              onClick={() => void onResumeAcceptance()}
              data-testid="accept-mechanics-resume-unresolved"
            >
              {acceptPending ? "Resuming…" : "Resume acceptance"}
            </button>
          </div>
          {!replayRequest ? (
            <p className="module-muted">
              Exact Accept body is unavailable for replay — use Resume only after a journal claim
              exists, or Retry lookup. A new Accept/Save attempt is not offered while this
              operation id may still claim server-side.
            </p>
          ) : (
            <p className="module-muted">
              Replay accept re-sends the exact same-key Accept body. Resume acceptance reconciles
              only after a journal operation exists. Bounded journal misses are not proof the
              original POST cannot still claim — local storage is not abandoned, and no
              replacement operation id is offered until the backend proves terminal non-begin.
            </p>
          )}
        </section>
      ) : null}

      {acceptResult ? (
        <section className="statblock-section" role="status" data-accept-result={resultLabel ?? ""}>
          {resultLabel === "mechanics_saved" ? (
            <>
              <p>
                <strong>Mechanics saved; not published</strong> to the World Graph.
              </p>
              {acceptResult.locator ? (
                <p className="module-muted" data-testid="accept-mechanics-locator">
                  Locator: statblock <code>{acceptResult.locator.statblock_id}</code>, revision{" "}
                  <code>{acceptResult.locator.revision_id}</code>, digest{" "}
                  <code>{acceptResult.locator.definition_digest}</code>
                </p>
              ) : null}
            </>
          ) : null}

          {resultLabel === "server_committed_reference_pending" ? (
            <>
              <p className="module-muted">
                Server mechanics exist (immutable revision on DungeonMindServer), but ThreatDraft
                attachment is still pending — workflow is not yet mechanics_saved. Not published to
                the World Graph.
              </p>
              <button
                type="button"
                disabled={acceptPending}
                onClick={() => void onResumeAcceptance()}
                data-testid="accept-mechanics-reconcile"
              >
                {acceptPending ? "Reconciling…" : "Reconcile acceptance"}
              </button>
            </>
          ) : null}

          {resultLabel === "dispatched_unknown" ? (
            <>
              <p className="module-muted">
                Acceptance is in an uncertain state — the Server may still be processing. Resume the
                same durable operation (do not start a new acceptance attempt).
              </p>
              <button
                type="button"
                disabled={acceptPending}
                onClick={() => void onResumeAcceptance()}
                data-testid="accept-mechanics-retry"
              >
                {acceptPending ? "Retrying…" : "Retry accept"}
              </button>
            </>
          ) : null}

          {resultLabel === "acceptance_input_conflict" ||
          resultLabel === "acceptance_draft_unavailable" ||
          (resultLabel === "acceptance_blocked" && acceptResultOrigin === "recovery") ? (
            <>
              <p
                className="statblock-command-error"
                role="alert"
                data-testid={
                  resultLabel === "acceptance_blocked"
                    ? "accept-blocked-recovery"
                    : "accept-same-op-block"
                }
              >
                Accept blocked: {acceptResult.message ?? resultLabel}
                {acceptResult.failure_category ? ` (${acceptResult.failure_category})` : ""}
                {resultLabel === "acceptance_blocked"
                  ? " The original operation id is retained — retry the same operation."
                  : ""}
              </p>
              <div className="statblock-command-row">
                {replayRequest ? (
                  <button
                    type="button"
                    disabled={acceptPending}
                    onClick={() => void onReplayAccept()}
                    data-testid="accept-mechanics-replay"
                  >
                    {acceptPending ? "Replaying…" : "Replay accept"}
                  </button>
                ) : null}
                <button
                  type="button"
                  disabled={acceptPending}
                  onClick={() => void onResumeAcceptance()}
                  data-testid="accept-mechanics-same-op-recover"
                >
                  {acceptPending ? "Recovering…" : "Resume same operation"}
                </button>
              </div>
            </>
          ) : null}

          {resultLabel === "accepted_ref_conflict" ? (
            <p className="statblock-command-error" role="alert" data-testid="accept-ref-conflict">
              Accepted-ref conflict: this draft already has different saved mechanics. First-save
              semantics cannot overwrite or reconcile onto a second locator.
              {acceptResult.message ? ` ${acceptResult.message}` : ""}
              {acceptResult.failure_category ? ` (${acceptResult.failure_category})` : ""}
            </p>
          ) : null}

          {(resultLabel === "acceptance_busy" ||
            resultLabel === "acceptance_history_full" ||
            (resultLabel === "acceptance_blocked" && acceptResultOrigin === "fresh")) ? (
            <p className="statblock-command-error" role="alert" data-testid="accept-ephemeral-block">
              Accept blocked: {acceptResult.message ?? resultLabel}
              {acceptResult.failure_category ? ` (${acceptResult.failure_category})` : ""}
              {eligible
                ? " Correct inputs if needed, then use Accept/Save again (this attempt did not claim a durable journal slot)."
                : ""}
            </p>
          ) : null}

          {resultLabel === "terminal_failure" ? (
            <>
              <p className="statblock-command-error" role="alert" data-testid="accept-terminal-failure">
                Accept terminated: {acceptResult.message ?? resultLabel}
                {acceptResult.failure_category ? ` (${acceptResult.failure_category})` : ""}
                {" "}This operation cannot be retried with the same operation id.
              </p>
              <button
                type="button"
                disabled={acceptPending}
                onClick={() => startNewAcceptOperation()}
                data-testid="accept-mechanics-start-new"
              >
                Start new acceptance attempt
              </button>
            </>
          ) : null}

          {actionClass === null && resultLabel ? (
            <p className="statblock-command-error" role="alert">
              Accept blocked: {acceptResult.message ?? resultLabel}
            </p>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}

export function StatblockWorkbenchModule() {
  const [candidateIdInput, setCandidateIdInput] = useState(readCandidateIdFromLocation);
  const [draftIdInput, setDraftIdInput] = useState("");
  const [draftVersionInput, setDraftVersionInput] = useState("1");
  const [createForm, setCreateForm] = useState<CreateFormFields>(DEFAULT_CREATE_FORM);
  const [createdDraft, setCreatedDraft] = useState<CreatedDraftIdentity | null>(null);
  const [createPhase, setCreatePhase] = useState<
    "idle" | "creating" | "create_failed" | "create_uncertain" | "draft_created" | "generating"
  >("idle");
  const [createMessage, setCreateMessage] = useState<string | null>(null);
  const [createError, setCreateError] = useState<string | null>(null);
  const [loadState, setLoadState] = useState<LoadState>({ kind: "idle" });
  const [generateMessage, setGenerateMessage] = useState<string | null>(null);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [pendingGenerate, setPendingGenerate] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>("edit");
  const [editorState, setEditorState] = useState<StatblockEditorState | null>(null);
  const [previewValidation, setPreviewValidation] = useState<PreviewValidation | null>(null);
  const [pendingValidation, setPendingValidation] = useState<PendingValidation | null>(null);
  const [validationFailure, setValidationFailure] = useState<ValidationFailure | null>(null);
  const [editorEpoch, setEditorEpoch] = useState(0);

  const validateRequestIdRef = useRef(0);
  const editorEpochRef = useRef(0);
  /** Shared monotonic identity for manual load, retry, and draft generation. */
  const candidateOpIdRef = useRef(0);
  /** Synchronous duplicate-submit guard for create-and-generate. */
  const createAndGenerateInFlightRef = useRef(false);
  const editorStateRef = useRef<StatblockEditorState | null>(null);
  editorStateRef.current = editorState;
  editorEpochRef.current = editorEpoch;

  const bumpEditorEpoch = useCallback(() => {
    const next = editorEpochRef.current + 1;
    editorEpochRef.current = next;
    setEditorEpoch(next);
    return next;
  }, []);

  const isCurrentCandidateOp = useCallback((opId: number): boolean => {
    return opId === candidateOpIdRef.current;
  }, []);

  /** Claim the next candidate operation; orphans every prior load/generate outcome. */
  const beginCandidateOp = useCallback(() => {
    return ++candidateOpIdRef.current;
  }, []);

  /** Orphan in-flight validate and clear revision-owned pending/failure records. */
  const invalidateValidationOwnership = useCallback(() => {
    validateRequestIdRef.current += 1;
    setPendingValidation(null);
    setValidationFailure(null);
    setPreviewValidation(null);
  }, []);

  const isCurrentValidateOwnership = useCallback(
    (requestId: number, epoch: number, requestedRevision: number): boolean => {
      if (requestId !== validateRequestIdRef.current) return false;
      if (epoch !== editorEpochRef.current) return false;
      const latest = editorStateRef.current;
      return latest != null && latest.stateRevision === requestedRevision;
    },
    [],
  );

  const onEditorStateChange = useCallback(
    (next: StatblockEditorState) => {
      const prev = editorStateRef.current;
      editorStateRef.current = next;
      setEditorState(next);
      if (prev && next.stateRevision !== prev.stateRevision) {
        // Immediate stale-request invalidation for the prior revision.
        validateRequestIdRef.current += 1;
        setPendingValidation(null);
        setValidationFailure(null);
      }
    },
    [],
  );

  const loadCandidate = useCallback(
    async (candidateId: string, options?: { opId?: number }) => {
      const trimmed = candidateId.trim();
      const opId = options?.opId ?? beginCandidateOp();
      // A fresh manual/retry load orphans in-flight generation UI.
      if (options?.opId == null) {
        setPendingGenerate(false);
        setGenerateMessage(null);
        setGenerateError(null);
      }
      bumpEditorEpoch();
      invalidateValidationOwnership();
      setEditorState(null);
      editorStateRef.current = null;

      if (!trimmed) {
        if (!isCurrentCandidateOp(opId)) return;
        setLoadState({ kind: "error", candidateId: "", message: "Enter an exact candidate ID." });
        return;
      }

      if (!isCurrentCandidateOp(opId)) return;
      setLoadState({ kind: "loading", candidateId: trimmed });

      try {
        const response = await getStatblockCandidate(trimmed);
        if (!isCurrentCandidateOp(opId)) return;

        if (response.status === "active" && response.candidate) {
          const nextEditor = createEditorStateFromOutput(response.candidate.definition);
          editorStateRef.current = nextEditor;
          setLoadState({ kind: "success", response });
          setEditorState(nextEditor);
          setViewMode("edit");
          return;
        }
        setLoadState({
          kind: "status",
          candidateId: response.candidate_id || trimmed,
          status: response.status === "active" ? "missing" : response.status,
          failureCategory: response.failure_category ?? null,
          failureMessage: response.failure_message ?? null,
        });
      } catch (error) {
        if (!isCurrentCandidateOp(opId)) return;
        setLoadState({
          kind: "error",
          candidateId: trimmed,
          message: error instanceof Error ? error.message : String(error),
        });
      }
    },
    [beginCandidateOp, bumpEditorEpoch, invalidateValidationOwnership, isCurrentCandidateOp],
  );

  useEffect(() => {
    const initial = readCandidateIdFromLocation();
    if (initial) {
      void loadCandidate(initial);
    }
  }, [loadCandidate]);

  const onSubmitCandidate = (event: FormEvent) => {
    event.preventDefault();
    void loadCandidate(candidateIdInput);
  };

  const runGenerateFromDraft = async (
    draftId: string,
    expectedVersion: number,
    options?: { opId?: number },
  ) => {
    const opId = options?.opId ?? beginCandidateOp();
    // Newer generation orphans prior load outcomes and prior generate UI.
    setPendingGenerate(true);
    setGenerateError(null);
    setGenerateMessage(null);
    setLoadState((prev) => (prev.kind === "loading" ? { kind: "idle" } : prev));
    try {
      const response: GenerateThreatDraftCandidateResponseV1 = await generateThreatDraftCandidate(
        draftId,
        { expected_draft_version: expectedVersion },
      );
      if (!isCurrentCandidateOp(opId)) return;

      if (response.outcome === "success" && response.candidate?.candidate_id) {
        const candidateId = response.candidate.candidate_id;
        setCandidateIdInput(candidateId);
        setGenerateMessage(
          `Generated ${candidateId}${
            response.cache_status ? ` (${response.cache_status})` : ""
          }. Loading structured review…`,
        );
        await loadCandidate(candidateId, { opId });
        return;
      }
      setGenerateError(
        response.failure_message ??
          response.failure_category ??
          "Generation failed without a typed candidate.",
      );
    } catch (error) {
      if (!isCurrentCandidateOp(opId)) return;
      setGenerateError(error instanceof Error ? error.message : String(error));
    } finally {
      if (isCurrentCandidateOp(opId)) {
        setPendingGenerate(false);
        setCreatePhase((prev) => (prev === "generating" ? "draft_created" : prev));
      }
    }
  };

  const onGenerateFromDraft = async (event: FormEvent) => {
    event.preventDefault();
    const draftId = draftIdInput.trim();
    const expectedVersion = Number(draftVersionInput);
    if (!draftId || !Number.isInteger(expectedVersion) || expectedVersion < 1) {
      setGenerateError("Provide a draft ID and expected draft version ≥ 1.");
      return;
    }
    await runGenerateFromDraft(draftId, expectedVersion);
  };

  const onRetryGenerateCreatedDraft = async () => {
    if (!createdDraft) return;
    setCreatePhase("generating");
    setCreateError(null);
    setCreateMessage(
      `Retrying generation for ThreatDraft ${createdDraft.draft_id} v${createdDraft.version}…`,
    );
    await runGenerateFromDraft(createdDraft.draft_id, createdDraft.version);
  };

  const onCreateAndGenerate = async (event: FormEvent) => {
    event.preventDefault();
    if (createAndGenerateInFlightRef.current || pendingGenerate || createPhase === "creating") {
      return;
    }

    const built = buildCreateThreatDraftRequest(createForm);
    if (!built.ok) {
      setCreateError(built.message);
      setCreatePhase("create_failed");
      return;
    }

    createAndGenerateInFlightRef.current = true;
    const opId = beginCandidateOp();
    setCreatePhase("creating");
    setCreateError(null);
    setCreateMessage("Creating ThreatDraft…");
    setGenerateError(null);
    setGenerateMessage(null);
    setPendingGenerate(false);
    setLoadState((prev) => (prev.kind === "loading" ? { kind: "idle" } : prev));

    try {
      let created: CreatedDraftIdentity | null = null;
      try {
        const response = await createThreatDraft(built.request);
        if (!isCurrentCandidateOp(opId)) return;
        created = createdDraftFromResponse(response);
        if (!created) {
          setCreatePhase("create_failed");
          setCreateError(
            "Create response lacked an exact draft_id/version; generation was not started.",
          );
          setCreateMessage(null);
          return;
        }
        setCreatedDraft(created);
        setDraftIdInput(created.draft_id);
        setDraftVersionInput(String(created.version));
        setCreatePhase("generating");
        setCreateMessage(
          `Created ThreatDraft ${created.draft_id} v${created.version} (${created.name}). Generating…`,
        );
      } catch (error) {
        if (!isCurrentCandidateOp(opId)) return;
        if (isCreateTransportUncertainty(error)) {
          setCreatePhase("create_uncertain");
          setCreateError(error instanceof Error ? error.message : String(error));
          setCreateMessage(
            "Creation outcome is unknown. The form was preserved; do not assume no draft exists. Correct only if you confirm no draft was created, then submit again.",
          );
        } else {
          setCreatePhase("create_failed");
          setCreateError(error instanceof Error ? error.message : String(error));
          setCreateMessage(null);
        }
        return;
      }

      if (!isCurrentCandidateOp(opId)) return;
      await runGenerateFromDraft(created.draft_id, created.version, { opId });
    } finally {
      createAndGenerateInFlightRef.current = false;
    }
  };

  const onStartAnotherThreat = () => {
    beginCandidateOp();
    createAndGenerateInFlightRef.current = false;
    setCreateForm(DEFAULT_CREATE_FORM);
    setCreatedDraft(null);
    setCreatePhase("idle");
    setCreateMessage(null);
    setCreateError(null);
    setGenerateMessage(null);
    setGenerateError(null);
    setPendingGenerate(false);
  };

  const updateCreateField = <K extends keyof CreateFormFields>(key: K, value: CreateFormFields[K]) => {
    setCreateForm((prev) => ({ ...prev, [key]: value }));
  };

  const onValidateWorkingCopy = async () => {
    const current = editorStateRef.current;
    if (!current) return;

    const epoch = editorEpochRef.current;
    const requestId = ++validateRequestIdRef.current;
    const requestedRevision = current.stateRevision;
    const workingCopy = current.workingCopy;
    setValidationFailure(null);
    setPendingValidation({ requestId, editorEpoch: epoch, stateRevision: requestedRevision });
    const validating = beginValidationAttempt(current);
    editorStateRef.current = validating;
    setEditorState(validating);

    let response: ValidateDefinitionBuddyResponseV1;
    try {
      response = await validateStatblockDefinition({ definition: workingCopy });
    } catch (error) {
      if (!isCurrentValidateOwnership(requestId, epoch, requestedRevision)) {
        return;
      }
      setPendingValidation(null);
      setValidationFailure({
        editorEpoch: epoch,
        stateRevision: requestedRevision,
        message: error instanceof Error ? error.message : String(error),
      });
      setEditorState((prev) => {
        if (!prev || prev.stateRevision !== requestedRevision) return prev;
        const next = markValidationUnavailable(prev);
        editorStateRef.current = next;
        return next;
      });
      return;
    }

    if (!isCurrentValidateOwnership(requestId, epoch, requestedRevision)) {
      return;
    }

    if (
      response.outcome !== "success" ||
      !response.validation_receipt ||
      response.definition_digest == null ||
      response.definition_digest !== response.validation_receipt.definition_digest
    ) {
      if (!isCurrentValidateOwnership(requestId, epoch, requestedRevision)) {
        return;
      }
      setPendingValidation(null);
      setValidationFailure({
        editorEpoch: epoch,
        stateRevision: requestedRevision,
        message:
          response.failure_message ??
          response.failure_category ??
          "Validation dependency unavailable",
      });
      setEditorState((prev) => {
        if (!prev || prev.stateRevision !== requestedRevision) return prev;
        const next = markValidationUnavailable(prev);
        editorStateRef.current = next;
        return next;
      });
      return;
    }

    if (!isCurrentValidateOwnership(requestId, epoch, requestedRevision)) {
      return;
    }

    const uiStatus = mapServerValidationStatus(response.validation_receipt.status);
    setPendingValidation(null);
    setValidationFailure(null);
    setPreviewValidation({
      associatedRevision: requestedRevision,
      editorEpoch: epoch,
      receipt: response.validation_receipt,
      definitionDigest: response.definition_digest,
    });
    setEditorState((prev) => {
      if (!prev || prev.stateRevision !== requestedRevision) return prev;
      const next = markValidationAssociated(prev, uiStatus);
      editorStateRef.current = next;
      return next;
    });
  };

  const activeCandidate: GeneratedStatblockCandidateV1 | null =
    loadState.kind === "success" ? loadState.response.candidate ?? null : null;

  const validatePendingForCurrent =
    pendingValidation != null &&
    editorState != null &&
    pendingValidation.editorEpoch === editorEpoch &&
    pendingValidation.stateRevision === editorState.stateRevision;

  return (
    <div className="module-panel statblock-workbench" data-module-id="statblock_workbench">
      <header className="statblock-workbench-header">
        <div>
          <p className="eyebrow">Typed candidate review, preview validation, and mechanics accept</p>
          <h2 className="module-title">Statblock Workbench</h2>
          <p className="module-muted">
            Displays mechanics from a structured DungeonMind candidate. Edit mode holds a session-only
            working copy; preview validation checks the copy; accept/save persists mechanics to the
            ThreatDraft without publishing to the World Graph.
          </p>
        </div>
        <span className="badge">sbw07c-accept</span>
      </header>

      <section className="statblock-section">
        <h3>New threat — create and generate</h3>
        <p className="module-muted">
          Creates one durable ThreatDraft from exact context, then generates a candidate from the
          returned draft ID and version. Browser refresh does not restore this form; keep the
          displayed draft identity for the manual path below.
        </p>
        <form className="statblock-storage-section" onSubmit={onCreateAndGenerate}>
          <div className="statblock-command-row">
            <label>
              Name
              <input
                value={createForm.name}
                onChange={(event) => updateCreateField("name", event.target.value)}
                placeholder="Mireward Latchling"
                autoComplete="off"
                data-testid="create-threat-name"
              />
            </label>
            <label>
              Threat kind
              <input
                value={createForm.threatKind}
                onChange={(event) => updateCreateField("threatKind", event.target.value)}
                autoComplete="off"
              />
            </label>
            <label>
              Created by
              <input
                value={createForm.createdBy}
                onChange={(event) => updateCreateField("createdBy", event.target.value)}
                placeholder="gm"
                autoComplete="off"
                data-testid="create-threat-created-by"
              />
            </label>
          </div>
          <label>
            Description
            <textarea
              value={createForm.description}
              onChange={(event) => updateCreateField("description", event.target.value)}
              rows={4}
              data-testid="create-threat-description"
            />
          </label>
          <div className="statblock-command-row">
            <label>
              World ID
              <input
                value={createForm.worldId}
                onChange={(event) => updateCreateField("worldId", event.target.value)}
                placeholder="exact world_id"
                autoComplete="off"
                spellCheck={false}
                data-testid="create-threat-world-id"
              />
            </label>
            <label>
              Campaign ID
              <input
                value={createForm.campaignId}
                onChange={(event) => updateCreateField("campaignId", event.target.value)}
                placeholder="exact campaign_id"
                autoComplete="off"
                spellCheck={false}
                data-testid="create-threat-campaign-id"
              />
            </label>
            <label>
              Graph revision ID
              <input
                value={createForm.graphRevisionId}
                onChange={(event) => updateCreateField("graphRevisionId", event.target.value)}
                placeholder="exact graph_revision_id"
                autoComplete="off"
                spellCheck={false}
                data-testid="create-threat-graph-revision-id"
              />
            </label>
          </div>
          <div className="statblock-command-row">
            <label>
              Ruleset system
              <input
                value={createForm.rulesetSystem}
                onChange={(event) => updateCreateField("rulesetSystem", event.target.value)}
                autoComplete="off"
                data-testid="create-threat-ruleset-system"
              />
            </label>
            <label>
              Ruleset edition
              <input
                value={createForm.rulesetEdition}
                onChange={(event) => updateCreateField("rulesetEdition", event.target.value)}
                autoComplete="off"
                data-testid="create-threat-ruleset-edition"
              />
            </label>
            <label>
              House ruleset ID
              <input
                value={createForm.houseRulesetId}
                onChange={(event) => updateCreateField("houseRulesetId", event.target.value)}
                autoComplete="off"
              />
            </label>
          </div>
          <details>
            <summary>Optional generation and focus controls</summary>
            <div className="statblock-storage-section">
              <div className="statblock-command-row">
                <label>
                  Focus session
                  <input
                    value={createForm.focusSession}
                    onChange={(event) => updateCreateField("focusSession", event.target.value)}
                    inputMode="numeric"
                  />
                </label>
                <label>
                  Prep label
                  <input
                    value={createForm.prepLabel}
                    onChange={(event) => updateCreateField("prepLabel", event.target.value)}
                    autoComplete="off"
                  />
                </label>
                <label>
                  Slug hint
                  <input
                    value={createForm.slugHint}
                    onChange={(event) => updateCreateField("slugHint", event.target.value)}
                    autoComplete="off"
                  />
                </label>
              </div>
              <div className="statblock-command-row">
                <label>
                  Target CR
                  <input
                    value={createForm.targetCr}
                    onChange={(event) => updateCreateField("targetCr", event.target.value)}
                    autoComplete="off"
                  />
                </label>
                <label>
                  Complexity
                  <input
                    value={createForm.complexity}
                    onChange={(event) => updateCreateField("complexity", event.target.value)}
                    autoComplete="off"
                  />
                </label>
                <label>
                  Party level
                  <input
                    value={createForm.partyLevel}
                    onChange={(event) => updateCreateField("partyLevel", event.target.value)}
                    inputMode="numeric"
                  />
                </label>
                <label>
                  Party size
                  <input
                    value={createForm.partySize}
                    onChange={(event) => updateCreateField("partySize", event.target.value)}
                    inputMode="numeric"
                  />
                </label>
              </div>
              <label>
                Must include (comma or newline)
                <textarea
                  value={createForm.mustInclude}
                  onChange={(event) => updateCreateField("mustInclude", event.target.value)}
                  rows={2}
                />
              </label>
              <label>
                Must avoid (comma or newline)
                <textarea
                  value={createForm.mustAvoid}
                  onChange={(event) => updateCreateField("mustAvoid", event.target.value)}
                  rows={2}
                />
              </label>
              <label>
                Intended roles (comma or newline)
                <textarea
                  value={createForm.intendedRoles}
                  onChange={(event) => updateCreateField("intendedRoles", event.target.value)}
                  rows={2}
                />
              </label>
              <label>
                Tags (comma or newline)
                <textarea
                  value={createForm.tags}
                  onChange={(event) => updateCreateField("tags", event.target.value)}
                  rows={2}
                />
              </label>
              <label>
                Terrain notes (comma or newline)
                <textarea
                  value={createForm.terrainNotes}
                  onChange={(event) => updateCreateField("terrainNotes", event.target.value)}
                  rows={2}
                />
              </label>
              <label>
                Selected node IDs (comma or newline)
                <textarea
                  value={createForm.selectedNodeIds}
                  onChange={(event) => updateCreateField("selectedNodeIds", event.target.value)}
                  rows={2}
                />
              </label>
              <label>
                Admitted source anchor IDs (comma or newline)
                <textarea
                  value={createForm.admittedSourceAnchorIds}
                  onChange={(event) =>
                    updateCreateField("admittedSourceAnchorIds", event.target.value)
                  }
                  rows={2}
                />
              </label>
            </div>
          </details>
          <div className="statblock-command-row">
            <button
              type="submit"
              disabled={
                pendingGenerate ||
                createPhase === "creating" ||
                createPhase === "generating"
              }
              data-testid="create-and-generate-submit"
            >
              {createPhase === "creating"
                ? "Creating…"
                : createPhase === "generating" || pendingGenerate
                  ? "Generating…"
                  : "Create & generate"}
            </button>
            <button type="button" onClick={onStartAnotherThreat} data-testid="start-another-threat">
              Start another threat
            </button>
            {createdDraft && generateError ? (
              <button
                type="button"
                onClick={() => void onRetryGenerateCreatedDraft()}
                disabled={pendingGenerate}
                data-testid="retry-generate-created-draft"
              >
                Retry generation (same draft)
              </button>
            ) : null}
          </div>
        </form>
        {createdDraft ? (
          <p className="statblock-command-status" data-testid="created-draft-identity" role="status">
            Created draft identity: <code>{createdDraft.draft_id}</code> v{createdDraft.version} (
            {createdDraft.name})
          </p>
        ) : null}
        {createMessage ? (
          <p className="statblock-command-status" role="status">
            {createMessage}
          </p>
        ) : null}
        {createError ? (
          <p className="statblock-command-error" role="alert" data-testid="create-threat-error">
            {createPhase === "create_uncertain"
              ? `Create outcome unknown: ${createError}`
              : `Unable to create ThreatDraft: ${createError}`}
          </p>
        ) : null}
      </section>

      <section className="statblock-section">
        <h3>Load exact candidate</h3>
        <form className="statblock-command-row" onSubmit={onSubmitCandidate}>
          <label>
            Candidate ID
            <input
              value={candidateIdInput}
              onChange={(event) => setCandidateIdInput(event.target.value)}
              placeholder="cand_…"
              autoComplete="off"
              spellCheck={false}
            />
          </label>
          <button type="submit">Load candidate</button>
        </form>
        <p className="module-muted">
          Optional deep link: <code>?candidateId=cand_…</code>
        </p>
      </section>

      <section className="statblock-section">
        <h3>Generate from ThreatDraft</h3>
        <form className="statblock-command-row" onSubmit={onGenerateFromDraft}>
          <label>
            Draft ID
            <input
              value={draftIdInput}
              onChange={(event) => setDraftIdInput(event.target.value)}
              placeholder="td_…"
              autoComplete="off"
              spellCheck={false}
            />
          </label>
          <label>
            Expected version
            <input
              value={draftVersionInput}
              onChange={(event) => setDraftVersionInput(event.target.value)}
              inputMode="numeric"
            />
          </label>
          <button type="submit" disabled={pendingGenerate}>
            {pendingGenerate ? "Generating…" : "Generate candidate"}
          </button>
        </form>
        {generateMessage ? (
          <p className="statblock-command-status" role="status">
            {generateMessage}
          </p>
        ) : null}
        {generateError ? (
          <p className="statblock-command-error" role="alert">
            Unable to generate candidate: {generateError}
          </p>
        ) : null}
      </section>

      {loadState.kind === "idle" ? (
        <p className="module-muted">Load an exact candidate ID to review structured mechanics.</p>
      ) : null}

      {loadState.kind === "loading" ? (
        <p className="module-muted" role="status">
          Loading candidate <code>{loadState.candidateId}</code>…
        </p>
      ) : null}

      {loadState.kind === "error" ? (
        <p className="module-error" role="alert">
          Unable to load candidate{loadState.candidateId ? ` ${loadState.candidateId}` : ""}:{" "}
          {loadState.message}
        </p>
      ) : null}

      {loadState.kind === "status" ? (
        <CandidateStatusPanel
          candidateId={loadState.candidateId}
          status={loadState.status}
          failureCategory={loadState.failureCategory}
          failureMessage={loadState.failureMessage}
          onRetry={() => void loadCandidate(loadState.candidateId)}
        />
      ) : null}

      {activeCandidate ? (
        <section className="statblock-section" data-testid="candidate-view-modes">
          <h3>Candidate {activeCandidate.candidate_id}</h3>
          <div className="statblock-command-row" role="group" aria-label="Candidate view mode">
            <button
              type="button"
              aria-pressed={viewMode === "review"}
              onClick={() => setViewMode("review")}
            >
              Review source
            </button>
            <button
              type="button"
              aria-pressed={viewMode === "edit"}
              onClick={() => setViewMode("edit")}
            >
              Edit working copy
            </button>
          </div>

          {viewMode === "review" ? (
            <StatblockRenderer candidate={activeCandidate} mode="review" />
          ) : null}

          {viewMode === "edit" && editorState ? (
            <>
              <div className="statblock-command-row">
                <button
                  type="button"
                  onClick={() => void onValidateWorkingCopy()}
                  disabled={validatePendingForCurrent || getUiStatus(editorState) === "validating"}
                >
                  {validatePendingForCurrent || getUiStatus(editorState) === "validating"
                    ? "Validating…"
                    : "Validate working copy"}
                </button>
              </div>
              <AcceptMechanicsFlow
                preview={previewValidation}
                editorState={editorState}
                editorEpoch={editorEpoch}
                draftIdInput={draftIdInput}
                draftVersionInput={draftVersionInput}
                sourceCandidateId={activeCandidate.candidate_id}
                workingCopy={editorState.workingCopy}
              />
              <PreviewValidationPanel
                preview={previewValidation}
                editorState={editorState}
                editorEpoch={editorEpoch}
                validationFailure={validationFailure}
                workingCopy={editorState.workingCopy}
              />
              <StatblockDefinitionEditor
                output={activeCandidate.definition}
                editorState={editorState}
                onEditorStateChange={onEditorStateChange}
              />
            </>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
