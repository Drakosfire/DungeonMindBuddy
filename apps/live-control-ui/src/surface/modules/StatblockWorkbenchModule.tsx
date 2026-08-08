import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";

import {
  acceptThreatDraftMechanics,
  createThreatDraft,
  generateThreatDraftCandidate,
  getAcceptanceOperation,
  getStatblockCandidate,
  getThreatDraft,
  getWorldGraphBootstrapStatus,
  LiveApiError,
  reconcileAcceptanceOperation,
  reviseThreatDraftCandidate,
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
  ReviseCandidateFromEditedDefinitionResponseV1,
  ThreatDraftV1,
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
  updateWorkingCopy,
  type StatblockEditorState,
} from "../../statblocks/editor/statblockEditorState";
import {
  mapServerValidationStatus,
  partitionValidationIssuesByPath,
  splitIssuesBySeverity,
} from "../../statblocks/editor/statblockValidationIssues";
import { StatblockRenderer } from "../../statblocks/render/StatblockRenderer";
import {
  ThreatPublicationPanel,
  type ThreatPublicationDockModel,
} from "../../statblocks/publication/ThreatPublicationPanel";
import {
  MechanicsSavedAppendBoundary,
  ProposalHistoryPanel,
  ReviseWithAiPanel,
} from "../../statblocks/revision/StatblockRevisePanels";
import {
  buildReviseRequestFromWorkingCopy,
  classifyReviseResult,
  isExpectedDraftVersionMismatch409,
  markReviseAttemptCompleted,
  markReviseAwaitingLocalRefresh,
  markRevisePreclaimRebuild,
  proveReconciledRefOnDraft,
  readCandidateWorkingCopy,
  readLegacyJoinWorkingCopyForCandidate,
  readStoredReviseAttempt,
  reviseAttemptStorageKey,
  revisePanelActions,
  reviseResponseMatchesAttempt,
  updateReviseAttemptResult,
  writeCandidateWorkingCopy,
  writeStoredReviseAttempt,
  type StoredReviseAttemptV1,
} from "../../statblocks/revision/statblockRevisionAttempt";

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

type PublicationHeadResolution = {
  draftId: string | null;
  head: string | null;
  error: string | null;
  loading: boolean;
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

/**
 * Live Control scope defaults for dogfood create. Graph revision is NOT invented
 * here — it is resolved from World Graph bootstrap head (or an exact Advanced override).
 */
const LIVE_CONTROL_CREATE_CONTEXT = {
  world_id: "eldyrwild",
  campaign_id: "longmont-c2",
  threat_kind: "creature",
  created_by: "gm",
  ruleset: {
    system: "dnd5e",
    edition: "2024",
    house_ruleset_id: null as string | null,
  },
} as const;

type CreateFormFields = {
  description: string;
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
  /** Exact World Graph revision override (e.g. rev:…). Empty → resolve bootstrap head. */
  graphRevisionId: string;
  /**
   * Explicit operator opt-in when bootstrap status cannot be retrieved.
   * Confirmed missing head (successful bootstrap, null head) does not require this.
   */
  allowFreestandingWithoutBootstrap: boolean;
};

const DEFAULT_CREATE_FORM: CreateFormFields = {
  description: "",
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
  graphRevisionId: "",
  allowFreestandingWithoutBootstrap: false,
};

type ResolvedCreateScope = {
  world_id: string;
  campaign_id: string;
  /** Null when freestanding — generation does not write to or require the World Graph. */
  graph_revision_id: string | null;
};

/** Derive a short ThreatDraft name from pasted prose (not a full paragraph dump). */
function deriveThreatNameFromDescription(description: string): string {
  const firstLine =
    description
      .split(/\r?\n/)
      .map((line) => line.trim())
      .find((line) => line.length > 0) ?? "";
  const cleaned = firstLine.replace(/[.。]+$/u, "").trim();
  if (!cleaned) return "Untitled threat";

  const namedSubject = cleaned.match(/^(?:A|An|The)\s+(.+?)\s+is\b/iu);
  if (namedSubject?.[1]) {
    const subject = namedSubject[1].trim();
    if (subject.length > 0 && subject.length <= 80) return subject;
  }

  const firstSentence = cleaned.match(/^(.+?[.!?])(?:\s|$)/u)?.[1]?.trim();
  const candidate = firstSentence && firstSentence.length <= 80 ? firstSentence.replace(/[.!?]$/u, "").trim() : cleaned;

  const maxLen = 48;
  if (candidate.length <= maxLen) return candidate;
  const sliced = candidate.slice(0, maxLen);
  const lastSpace = sliced.lastIndexOf(" ");
  const truncated = (lastSpace > 16 ? sliced.slice(0, lastSpace) : sliced).trim();
  return `${truncated}…`;
}

function shortThreatDisplayName(name: string): string {
  const trimmed = name.trim();
  if (!trimmed) return "Untitled threat";
  if (trimmed.length <= 48) return trimmed;
  const sliced = trimmed.slice(0, 48);
  const lastSpace = sliced.lastIndexOf(" ");
  return `${(lastSpace > 16 ? sliced.slice(0, lastSpace) : sliced).trim()}…`;
}

function buildCreateThreatDraftRequest(
  fields: CreateFormFields,
  scope: ResolvedCreateScope,
): { ok: true; request: CreateThreatDraftRequestV1 } | { ok: false; message: string } {
  const description = fields.description.trim();
  if (!description) return { ok: false, message: "Provide a threat description." };

  // Freestanding drafts may omit graph grounding — create/generate do not write the graph.
  // Grounded drafts carry a concrete revision; freestanding must keep pointer lists empty.
  const graphRevisionId = scope.graph_revision_id?.trim() || null;

  const name = deriveThreatNameFromDescription(description);

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
  const targetCr = fields.targetCr.trim() || null;
  const complexity = fields.complexity.trim() || null;
  const focus =
    focusSessionValue != null || prepLabel != null
      ? { session: focusSessionValue, prep_label: prepLabel }
      : null;

  return {
    ok: true,
    request: {
      world_id: scope.world_id,
      campaign_id: scope.campaign_id,
      focus,
      name,
      slug_hint: slugHint,
      description,
      threat_kind: LIVE_CONTROL_CREATE_CONTEXT.threat_kind,
      intended_roles: parseBoundedStringList(fields.intendedRoles),
      tags: parseBoundedStringList(fields.tags),
      generation_intent: {
        ruleset: {
          system: LIVE_CONTROL_CREATE_CONTEXT.ruleset.system,
          edition: LIVE_CONTROL_CREATE_CONTEXT.ruleset.edition,
          house_ruleset_id: LIVE_CONTROL_CREATE_CONTEXT.ruleset.house_ruleset_id,
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
        selected_node_ids: [],
        admitted_source_anchor_ids: [],
      },
      created_by: LIVE_CONTROL_CREATE_CONTEXT.created_by,
    },
  };
}

const FREESTANDING_OPT_IN_HINT =
  "Enter an exact graph revision (rev:…) under Optional & advanced, or check " +
  '"Continue freestanding without a graph head" to create without provenance.';

function freestandingScope(worldId: string, campaignId: string): ResolvedCreateScope {
  return {
    world_id: worldId,
    campaign_id: campaignId,
    graph_revision_id: null,
  };
}

function requireFreestandingOptIn(
  fields: CreateFormFields,
  worldId: string,
  campaignId: string,
  reason: string,
): { ok: true; scope: ResolvedCreateScope } | { ok: false; message: string } {
  if (fields.allowFreestandingWithoutBootstrap) {
    return { ok: true, scope: freestandingScope(worldId, campaignId) };
  }
  return { ok: false, message: `${reason} ${FREESTANDING_OPT_IN_HINT}` };
}

async function resolveCreateScope(
  fields: CreateFormFields,
): Promise<{ ok: true; scope: ResolvedCreateScope } | { ok: false; message: string }> {
  const override = fields.graphRevisionId.trim();
  if (override) {
    return {
      ok: true,
      scope: {
        world_id: LIVE_CONTROL_CREATE_CONTEXT.world_id,
        campaign_id: LIVE_CONTROL_CREATE_CONTEXT.campaign_id,
        graph_revision_id: override,
      },
    };
  }

  try {
    const status = await getWorldGraphBootstrapStatus();
    const worldId =
      typeof status.worldId === "string" && status.worldId.trim()
        ? status.worldId.trim()
        : LIVE_CONTROL_CREATE_CONTEXT.world_id;
    const campaignId =
      typeof status.campaignId === "string" && status.campaignId.trim()
        ? status.campaignId.trim()
        : LIVE_CONTROL_CREATE_CONTEXT.campaign_id;
    const head =
      typeof status.currentHeadRevisionId === "string" && status.currentHeadRevisionId.trim()
        ? status.currentHeadRevisionId.trim()
        : null;
    const state = typeof status.state === "string" ? status.state.trim() : "";
    const bundleValid = status.bundleValid === true;

    // Active worlds must pin a concrete head — null head here is contradictory.
    if (state === "active" || state === "active_head_advanced") {
      if (head) {
        return {
          ok: true,
          scope: {
            world_id: worldId,
            campaign_id: campaignId,
            graph_revision_id: head,
          },
        };
      }
      return requireFreestandingOptIn(
        fields,
        worldId,
        campaignId,
        `World Graph bootstrap reports state=${state} but no current head — graph authority is contradictory.`,
      );
    }

    // Ready + valid bundle + null head: known uninitialized world; freestanding is legitimate.
    if (state === "ready" && bundleValid) {
      return {
        ok: true,
        scope: {
          world_id: worldId,
          campaign_id: campaignId,
          graph_revision_id: head,
        },
      };
    }

    // Live store head can remain readable when locked-bundle cert fails
    // (invalid_bundle / blocked). Pin that head — same authority as Recap/Hermes.
    if (head) {
      return {
        ok: true,
        scope: {
          world_id: worldId,
          campaign_id: campaignId,
          graph_revision_id: head,
        },
      };
    }

    // Typed failure/blocked states arrive as HTTP 200 with null head — not auto-freestanding.
    const diagnosticHint =
      Array.isArray(status.diagnostics) && status.diagnostics.length > 0
        ? ` Diagnostics: ${status.diagnostics
            .slice(0, 3)
            .map((d) => d.message || d.code)
            .filter(Boolean)
            .join("; ")}.`
        : "";
    return requireFreestandingOptIn(
      fields,
      worldId,
      campaignId,
      `World Graph bootstrap is not ready for automatic provenance ` +
        `(state=${state || "unknown"}, bundleValid=${bundleValid}).${diagnosticHint}`,
    );
  } catch (error) {
    // Lookup failure ≠ "no head". Graph authority is unknown — do not silently freestand.
    const detail = error instanceof Error ? error.message : String(error);
    return requireFreestandingOptIn(
      fields,
      LIVE_CONTROL_CREATE_CONTEXT.world_id,
      LIVE_CONTROL_CREATE_CONTEXT.campaign_id,
      `Unable to retrieve World Graph bootstrap status — graph authority is unknown (${detail}).`,
    );
  }
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
/** Session join for dogfood: draft/candidate IDs + local working-copy edits (not accepted mechanics). */
const WORKBENCH_JOIN_STORAGE_KEY = "dmb.sbw.workbenchJoin";

interface StoredAcceptAttempt {
  operation_id: string;
  /** Exact mechanics:accept body for same-key replay when no journal claim exists yet. */
  request?: AcceptThreatDraftMechanicsRequestV1 | null;
}

interface StoredWorkbenchJoin {
  draft_id?: string | null;
  version?: number | null;
  name?: string | null;
  candidate_id?: string | null;
  /** Local editor working copy for the joined candidate — restored across hard reload. */
  working_copy?: StatblockDefinitionV1_Input | null;
}

function readStoredWorkingCopy(value: unknown): StatblockDefinitionV1_Input | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as StatblockDefinitionV1_Input;
}

function readStoredWorkbenchJoin(): StoredWorkbenchJoin | null {
  try {
    const raw = sessionStorage.getItem(WORKBENCH_JOIN_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as StoredWorkbenchJoin;
    if (!parsed || typeof parsed !== "object") return null;
    const draft_id =
      typeof parsed.draft_id === "string" && parsed.draft_id.trim() ? parsed.draft_id.trim() : null;
    const candidate_id =
      typeof parsed.candidate_id === "string" && parsed.candidate_id.trim()
        ? parsed.candidate_id.trim()
        : null;
    const version =
      typeof parsed.version === "number" && Number.isInteger(parsed.version) && parsed.version >= 1
        ? parsed.version
        : null;
    const name = typeof parsed.name === "string" && parsed.name.trim() ? parsed.name.trim() : null;
    const working_copy = readStoredWorkingCopy(parsed.working_copy);
    if (!draft_id && !candidate_id) return null;
    return { draft_id, version, name, candidate_id, working_copy };
  } catch {
    return null;
  }
}

function writeStoredWorkbenchJoin(join: StoredWorkbenchJoin): void {
  try {
    sessionStorage.setItem(WORKBENCH_JOIN_STORAGE_KEY, JSON.stringify(join));
  } catch {
    /* private mode / quota — in-memory state still covers the session */
  }
}

/**
 * Candidate-bound create/restore identity and refreshed ThreatDraft take precedence.
 * Advanced draft fields are fallback input only when no candidate-bound identity exists.
 */
function resolveAcceptDraftIdentity(
  createdDraft: CreatedDraftIdentity | null,
  draftIdInput: string,
  draftVersionInput: string,
): { draft_id: string; version: number } | null {
  if (createdDraft?.draft_id && createdDraft.version >= 1) {
    return { draft_id: createdDraft.draft_id, version: createdDraft.version };
  }
  const draftId = draftIdInput.trim();
  const version = Number(draftVersionInput);
  if (draftId && Number.isInteger(version) && version >= 1) {
    return { draft_id: draftId, version };
  }
  const stored = readStoredWorkbenchJoin();
  if (stored?.draft_id) {
    const storedVersion = stored.version ?? 1;
    if (Number.isInteger(storedVersion) && storedVersion >= 1) {
      return { draft_id: stored.draft_id, version: storedVersion };
    }
  }
  return null;
}

/** Keep workflow failures readable in the fixed dock without dumping transport essays. */
function formatWorkbenchDockError(message: string, kind: "accept" | "validate"): string {
  const prefix = kind === "accept" ? "Accept failed" : "Validate failed";
  const raw = message.trim();
  if (/not valid JSON/i.test(raw) && /HTML page/i.test(raw)) {
    const http = raw.match(/HTTP\s+(\d+)/i)?.[1];
    return `${prefix}: HTTP ${http ?? "error"} returned HTML instead of JSON — Buddy/L3 likely down or /api not proxied.`;
  }
  if (raw.length <= 160) return `${prefix}: ${raw}`;
  return `${prefix}: ${raw.slice(0, 157).trimEnd()}…`;
}

function patchStoredWorkbenchJoin(patch: Partial<StoredWorkbenchJoin>): void {
  const prev = readStoredWorkbenchJoin() ?? {};
  const pick = (
    next: string | number | null | undefined,
    current: string | number | null | undefined,
  ): string | number | null => {
    if (next === undefined) {
      return current ?? null;
    }
    // Never clobber a known identity with an explicit null from a partial patch.
    if (next === null) {
      return current ?? null;
    }
    return next;
  };
  const pickWorkingCopy = (
    next: StatblockDefinitionV1_Input | null | undefined,
    current: StatblockDefinitionV1_Input | null | undefined,
  ): StatblockDefinitionV1_Input | null => {
    if (next === undefined) return current ?? null;
    return next;
  };
  writeStoredWorkbenchJoin({
    draft_id: pick(patch.draft_id, prev.draft_id) as string | null,
    version: pick(patch.version, prev.version) as number | null,
    name: pick(patch.name, prev.name) as string | null,
    candidate_id: pick(patch.candidate_id, prev.candidate_id) as string | null,
    working_copy: pickWorkingCopy(patch.working_copy, prev.working_copy),
  });
}

function restoreWorkingCopyForCandidate(
  base: StatblockEditorState,
  draftId: string | null,
  candidateId: string,
  stored: StoredWorkbenchJoin | null,
): StatblockEditorState {
  if (draftId?.trim()) {
    const scoped =
      readCandidateWorkingCopy(draftId, candidateId) ??
      readLegacyJoinWorkingCopyForCandidate(draftId, candidateId);
    if (scoped) {
      return updateWorkingCopy(base, () => scoped);
    }
  }
  return editorStateWithRestoredWorkingCopy(base, candidateId, stored);
}

/** Rehydrate local edits for the same candidate without treating them as accepted mechanics. */
function editorStateWithRestoredWorkingCopy(
  base: StatblockEditorState,
  candidateId: string,
  stored: StoredWorkbenchJoin | null,
): StatblockEditorState {
  if (
    !stored?.working_copy ||
    !stored.candidate_id ||
    stored.candidate_id !== candidateId
  ) {
    return base;
  }
  return updateWorkingCopy(base, () => stored.working_copy as StatblockDefinitionV1_Input);
}

function clearStoredWorkbenchJoin(): void {
  try {
    sessionStorage.removeItem(WORKBENCH_JOIN_STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

function createdDraftFromStoredJoin(
  stored: StoredWorkbenchJoin | null | undefined,
): CreatedDraftIdentity | null {
  if (!stored?.draft_id) return null;
  const version = stored.version ?? 1;
  if (!Number.isInteger(version) || version < 1) return null;
  return {
    draft_id: stored.draft_id,
    version,
    name: stored.name ?? stored.draft_id,
  };
}

/** Synchronous session restore so Accept never mounts before draft identity exists. */
function readInitialWorkbenchJoinState(): {
  createdDraft: CreatedDraftIdentity | null;
  draftIdInput: string;
  draftVersionInput: string;
  createPhase: "idle" | "draft_created";
} {
  const createdDraft = createdDraftFromStoredJoin(readStoredWorkbenchJoin());
  if (!createdDraft) {
    return {
      createdDraft: null,
      draftIdInput: "",
      draftVersionInput: "1",
      createPhase: "idle",
    };
  }
  return {
    createdDraft,
    draftIdInput: createdDraft.draft_id,
    draftVersionInput: String(createdDraft.version),
    createPhase: "draft_created",
  };
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
  draftId,
  draftVersion,
  sourceCandidateId,
  workingCopy,
  validationFailure,
  onValidate,
  validatePending,
  validateDisabled,
  mechanicsSavedDraft,
  draftAuthorityUnavailable = false,
  onMechanicsSaved,
  publicationDock = null,
}: {
  preview: PreviewValidation | null;
  editorState: StatblockEditorState;
  editorEpoch: number;
  draftId: string | null;
  draftVersion: number | null;
  sourceCandidateId: string;
  workingCopy: StatblockDefinitionV1_Input;
  validationFailure: ValidationFailure | null;
  onValidate: () => void;
  validatePending: boolean;
  validateDisabled: boolean;
  mechanicsSavedDraft: boolean;
  /** When true, version-dependent Accept/Save stays disabled until draft authority is restored. */
  draftAuthorityUnavailable?: boolean;
  /** Refresh ThreatDraft authority after a durable mechanics_saved accept so Publish can mount. */
  onMechanicsSaved?: (draftId: string) => void;
  /** Primary publication journey status/actions for the floating dock. */
  publicationDock?: ThreatPublicationDockModel | null;
}) {
  const eligible = acceptPreviewEligible(preview, editorState, editorEpoch);
  const previewCurrent = previewIsCurrent(preview, editorState, editorEpoch);
  const normalizedDraftId = (draftId ?? "").trim();
  const expectedDraftVersion =
    draftVersion != null && Number.isInteger(draftVersion) && draftVersion >= 1
      ? draftVersion
      : null;
  const validationFailureCurrent =
    validationFailure != null &&
    validationFailure.editorEpoch === editorEpoch &&
    validationFailure.stateRevision === editorState.stateRevision;
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
  /** Synchronous guard — Accept/Save can fire twice before React re-renders acceptPending. */
  const acceptInFlightRef = useRef(false);
  /** Draft ID that currently owns acceptResult / operation ref / restore UI. */
  const ownedDraftIdRef = useRef<string>("");
  const restoreGenerationRef = useRef(0);
  const acceptRequestGenerationRef = useRef(0);

  const clearOwnedAcceptState = () => {
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

    queueMicrotask(() => {
      if (!isRestoreGenerationCurrent(draftId, restoreGeneration)) {
        return;
      }
      void runRestoreLookup(draftId, storedId, restoreGeneration);
    });

    return () => {
      // Strict Mode / draft switch: orphan in-flight restore lookups.
      restoreGenerationRef.current += 1;
      setRestorePending(false);
    };
  }, [normalizedDraftId]);

  const ensureOperationId = (): string => {
    if (!acceptOperationIdRef.current) {
      acceptOperationIdRef.current = crypto.randomUUID();
    }
    return acceptOperationIdRef.current;
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
    if (label === "mechanics_saved") {
      onMechanicsSaved?.(draftId);
    }
  };

  const runAccept = async () => {
    if (!preview || !eligible) return;

    // Ephemeral attempt barriers must not block a fresh dock Accept/Save in the same click.
    let currentResult = acceptResult;
    let currentOrigin = acceptResultOrigin;
    if (acceptActionClass(currentResult?.result_label, currentOrigin) === "ephemeralAttempt") {
      setAcceptResult(null);
      acceptOperationIdRef.current = null;
      currentResult = null;
      currentOrigin = "fresh";
    }

    // Never mint/replace while an optimistic or restored operation is unresolved.
    if (existenceUnresolved || suppressesNewAccept(currentResult?.result_label, currentOrigin)) {
      return;
    }
    // Prevent concurrent Accept/Save clicks before React disables the button.
    if (acceptInFlightRef.current || acceptPending) return;

    const draftId = normalizedDraftId;
    const expectedVersion = expectedDraftVersion;
    if (!draftId || expectedVersion == null) {
      setAcceptError(
        "ThreatDraft identity missing — create and generate first, or recover a draft in Advanced.",
      );
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
  const hasDraftIdentity = Boolean(normalizedDraftId && expectedDraftVersion != null);
  const showAcceptEntry =
    eligible &&
    hasDraftIdentity &&
    !blocksNewAccept &&
    !restorePending &&
    !mechanicsSavedDraft &&
    !draftAuthorityUnavailable;

  const dockError = (() => {
    if (acceptError) {
      return {
        kind: "accept" as const,
        message: acceptError,
        display: formatWorkbenchDockError(acceptError, "accept"),
      };
    }
    if (validationFailureCurrent && validationFailure) {
      return {
        kind: "validate" as const,
        message: validationFailure.message,
        display: formatWorkbenchDockError(validationFailure.message, "validate"),
      };
    }
    return null;
  })();

  const dockStatus = (() => {
    if (publicationDock) {
      return publicationDock.status;
    }
    if (acceptPending) {
      return "Accepting…";
    }
    if (dockError) {
      return dockError.display;
    }
    if (restorePending && !acceptResult && !existenceUnresolved) {
      return "Restoring acceptance operation…";
    }
    if (existenceUnresolved) {
      return "Acceptance operation unresolved — use Retry / Replay / Resume above. New Accept/Save is blocked.";
    }
    if (blocksNewAccept) {
      if (resultLabel === "mechanics_saved") {
        return "Mechanics already saved for this draft — not published to the World Graph.";
      }
      if (resultLabel === "server_committed_reference_pending") {
        return "Server mechanics committed; ThreatDraft attachment still pending — reconcile above.";
      }
      if (resultLabel === "dispatched_unknown") {
        return "Acceptance uncertain — resume the same operation above.";
      }
      if (resultLabel === "accepted_ref_conflict") {
        return "Accepted-ref conflict — first-save cannot overwrite.";
      }
      if (resultLabel === "terminal_failure") {
        return "Acceptance terminated — start a new accept operation above if offered.";
      }
      return "Accept/Save blocked by a durable outcome — use recovery actions above.";
    }
    if (mechanicsSavedDraft) {
      return "Mechanics already saved for this draft — first-save Accept/Save is not offered for revised proposals.";
    }
    if (draftAuthorityUnavailable) {
      return "ThreatDraft snapshot unavailable — version-dependent Accept/Save is disabled until draft authority is restored.";
    }
    if (!previewCurrent) {
      return preview
        ? "Preview validation is stale — validate again before Accept/Save."
        : "Validate the working copy to enable Accept/Save. Mechanics save does not publish to the World Graph.";
    }
    if (preview?.receipt.status === "invalid") {
      return "Fix validation errors before Accept/Save.";
    }
    if (eligible && !hasDraftIdentity) {
      return "ThreatDraft identity missing — create and generate first, or recover a draft in Advanced.";
    }
    if (showAcceptEntry) {
      return "Ready to Accept/Save mechanics (ThreatDraft only — not World Graph publish).";
    }
    return "Accept/Save unavailable.";
  })();

  const onAcceptSave = () => {
    setAcceptError(null);
    void runAccept();
  };

  return (
    <div data-testid="accept-mechanics-flow" data-owned-draft={normalizedDraftId}>
      {mechanicsSavedDraft ? <MechanicsSavedAppendBoundary /> : null}
      {restorePending && !acceptResult && !existenceUnresolved ? (
        <p className="module-muted" role="status" data-testid="accept-mechanics-restoring">
          Restoring acceptance operation…
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

      <div
        className="statblock-workbench-dock"
        data-testid="workbench-edit-dock"
        role="toolbar"
        aria-label="Statblock workbench edit tools"
      >
        <p
          className="statblock-workbench-dock__status"
          role={
            publicationDock?.tone === "error" || dockError
              ? "alert"
              : "status"
          }
          data-dock-tone={
            publicationDock?.tone
            ?? (dockError ? "error" : "info")
          }
          data-testid={publicationDock ? "publication-dock-status" : undefined}
          title={dockError?.message}
        >
          {dockStatus}
        </p>
        <div className="statblock-workbench-dock__actions">
          {publicationDock ? (
            publicationDock.actions.map((action) => (
              <button
                key={action.testId}
                type="button"
                data-testid={action.testId}
                disabled={action.disabled}
                onClick={action.onClick}
              >
                {action.label}
              </button>
            ))
          ) : (
            <>
              <button
                type="button"
                onClick={() => {
                  setAcceptError(null);
                  onValidate();
                }}
                disabled={validateDisabled || validatePending}
              >
                {validatePending ? "Validating…" : "Validate working copy"}
              </button>
              <button
                type="button"
                onClick={onAcceptSave}
                disabled={!showAcceptEntry || acceptPending}
                title={showAcceptEntry ? undefined : dockStatus}
                data-testid="accept-mechanics-save"
              >
                {acceptPending ? "Accepting…" : "Accept/Save mechanics"}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}


export function StatblockWorkbenchModule() {
  const [initialJoin] = useState(readInitialWorkbenchJoinState);
  const [candidateIdInput, setCandidateIdInput] = useState(readCandidateIdFromLocation);
  const [draftIdInput, setDraftIdInput] = useState(initialJoin.draftIdInput);
  const [draftVersionInput, setDraftVersionInput] = useState(initialJoin.draftVersionInput);
  const [createForm, setCreateForm] = useState<CreateFormFields>(DEFAULT_CREATE_FORM);
  const [createdDraft, setCreatedDraft] = useState<CreatedDraftIdentity | null>(
    initialJoin.createdDraft,
  );
  const [createPhase, setCreatePhase] = useState<
    "idle" | "creating" | "create_failed" | "create_uncertain" | "draft_created" | "generating"
  >(initialJoin.createPhase);
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
  const [threatDraft, setThreatDraft] = useState<ThreatDraftV1 | null>(null);
  const [draftSnapshotPending, setDraftSnapshotPending] = useState(false);
  const [draftSnapshotError, setDraftSnapshotError] = useState<string | null>(null);
  const [draftSnapshotUnavailable, setDraftSnapshotUnavailable] = useState(false);
  const [reviseInstructionsRaw, setReviseInstructionsRaw] = useState("");
  const [preserveElementKeys, setPreserveElementKeys] = useState(true);
  const [reviseAttempt, setReviseAttempt] = useState<StoredReviseAttemptV1 | null>(null);
  const [reviseStatusMessage, setReviseStatusMessage] = useState<string | null>(null);
  const [reviseError, setReviseError] = useState<string | null>(null);
  const [revisePending, setRevisePending] = useState(false);
  const [publicationHeadResolution, setPublicationHeadResolution] =
    useState<PublicationHeadResolution>({
      draftId: null,
      head: null,
      error: null,
      loading: false,
    });
  const [publicationDock, setPublicationDock] =
    useState<ThreatPublicationDockModel | null>(null);

  const validateRequestIdRef = useRef(0);
  const editorEpochRef = useRef(0);
  /** Shared monotonic identity for manual load, retry, and draft generation. */
  const candidateOpIdRef = useRef(0);
  /** Monotonic guard for revise POST outcomes vs newer candidate/draft selection. */
  const reviseOpGenerationRef = useRef(0);
  const draftSnapshotGenerationRef = useRef(0);
  const reviseInFlightRef = useRef(false);
  const ownedDraftSnapshotIdRef = useRef<string>("");
  /** Mirrors threatDraft for load/clear paths that must not close over stale React state. */
  const threatDraftRef = useRef<ThreatDraftV1 | null>(null);
  /** Synchronous duplicate-submit guard for create-and-generate. */
  const createAndGenerateInFlightRef = useRef(false);
  const editorStateRef = useRef<StatblockEditorState | null>(null);
  const createdDraftRef = useRef<CreatedDraftIdentity | null>(initialJoin.createdDraft);
  /** Candidate id currently loaded into the editor — used to scope working-copy persistence. */
  const activeCandidateIdRef = useRef<string | null>(null);
  editorStateRef.current = editorState;
  editorEpochRef.current = editorEpoch;
  createdDraftRef.current = createdDraft;
  threatDraftRef.current = threatDraft;

  /**
   * Quarantine ThreatDraft/revise authority so late draft/revise responses and
   * stale proposal history cannot survive draft exit or unknown-draft loads.
   */
  const clearThreatDraftAuthority = useCallback(() => {
    draftSnapshotGenerationRef.current += 1;
    reviseOpGenerationRef.current += 1;
    ownedDraftSnapshotIdRef.current = "";
    threatDraftRef.current = null;
    setThreatDraft(null);
    setDraftSnapshotPending(false);
    setDraftSnapshotError(null);
    setDraftSnapshotUnavailable(false);
    setReviseAttempt(null);
    setReviseInstructionsRaw("");
    setReviseStatusMessage(null);
    setReviseError(null);
    setRevisePending(false);
    reviseInFlightRef.current = false;
  }, []);

  const applyCreatedDraftIdentity = useCallback((identity: CreatedDraftIdentity) => {
    const priorSnapshotId =
      threatDraftRef.current?.draft_id || ownedDraftSnapshotIdRef.current || null;
    const priorCreatedId = createdDraftRef.current?.draft_id ?? null;
    if (
      (priorSnapshotId && priorSnapshotId !== identity.draft_id) ||
      (priorCreatedId && priorCreatedId !== identity.draft_id)
    ) {
      // Cross-draft switch: drop the previous draft's snapshot/revise authority immediately.
      clearThreatDraftAuthority();
    }
    const hadSameDraft = createdDraftRef.current?.draft_id === identity.draft_id;
    createdDraftRef.current = identity;
    setCreatedDraft(identity);
    setDraftIdInput((current) => {
      // Candidate-bound draft switch overwrites stale Advanced recovery fields.
      if (!hadSameDraft) return identity.draft_id;
      // Keep Advanced draft ID empty when session create identity matches — Accept uses createdDraft.
      if (current.trim()) return current;
      return "";
    });
    setDraftVersionInput((current) => {
      if (!hadSameDraft) return String(identity.version);
      if (current.trim() && current !== String(identity.version)) {
        return current;
      }
      return String(identity.version);
    });
    setCreatePhase((prev) => (prev === "idle" ? "draft_created" : prev));
  }, [clearThreatDraftAuthority]);

  const refreshThreatDraftSnapshot = useCallback(async (draftId: string) => {
    const trimmed = draftId.trim();
    if (!trimmed) return;
    const generation = ++draftSnapshotGenerationRef.current;
    ownedDraftSnapshotIdRef.current = trimmed;
    setDraftSnapshotPending(true);
    setDraftSnapshotError(null);
    try {
      const draft = await getThreatDraft(trimmed);
      if (
        generation !== draftSnapshotGenerationRef.current ||
        ownedDraftSnapshotIdRef.current !== trimmed
      ) {
        return;
      }
      setThreatDraft(draft);
      setDraftSnapshotUnavailable(false);
      patchStoredWorkbenchJoin({
        draft_id: draft.draft_id,
        version: draft.version,
        name: draft.name,
      });
      const storedAttempt = readStoredReviseAttempt(trimmed);
      setReviseAttempt(storedAttempt);
      setReviseInstructionsRaw(storedAttempt?.raw_instructions ?? "");
    } catch (error) {
      if (
        generation !== draftSnapshotGenerationRef.current ||
        ownedDraftSnapshotIdRef.current !== trimmed
      ) {
        return;
      }
      setDraftSnapshotUnavailable(true);
      setDraftSnapshotError(error instanceof Error ? error.message : String(error));
    } finally {
      if (
        generation === draftSnapshotGenerationRef.current &&
        ownedDraftSnapshotIdRef.current === trimmed
      ) {
        setDraftSnapshotPending(false);
      }
    }
  }, []);

  const persistActiveCandidateWorkingCopy = useCallback(() => {
    const candidateId = activeCandidateIdRef.current;
    const draftId = createdDraftRef.current?.draft_id ?? draftIdInput.trim();
    const editor = editorStateRef.current;
    if (!candidateId || !draftId || !editor) return;
    writeCandidateWorkingCopy(draftId, candidateId, editor.workingCopy);
    patchStoredWorkbenchJoin({
      candidate_id: candidateId,
      draft_id: draftId,
      working_copy: editor.workingCopy,
    });
  }, [draftIdInput]);

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
      const candidateId = activeCandidateIdRef.current;
      if (candidateId) {
        const draftId = createdDraftRef.current?.draft_id ?? draftIdInput.trim();
        if (draftId) {
          writeCandidateWorkingCopy(draftId, candidateId, next.workingCopy);
        }
        patchStoredWorkbenchJoin({
          candidate_id: candidateId,
          working_copy: next.workingCopy,
        });
      }
    },
    [draftIdInput],
  );

  const loadCandidate = useCallback(
    async (candidateId: string, options?: { opId?: number }): Promise<boolean> => {
      if (options?.opId == null) {
        reviseOpGenerationRef.current += 1;
      }
      const trimmed = candidateId.trim();
      const opId = options?.opId ?? beginCandidateOp();
      if (!isCurrentCandidateOp(opId)) {
        return false;
      }
      persistActiveCandidateWorkingCopy();
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
      activeCandidateIdRef.current = null;

      if (!trimmed) {
        if (!isCurrentCandidateOp(opId)) return false;
        setLoadState({ kind: "error", candidateId: "", message: "Enter an exact candidate ID." });
        return false;
      }

      if (!isCurrentCandidateOp(opId)) return false;
      setLoadState({ kind: "loading", candidateId: trimmed });

      try {
        const response = await getStatblockCandidate(trimmed);
        if (!isCurrentCandidateOp(opId)) return false;

        if (response.status === "active" && response.candidate) {
          const loadedCandidateId = response.candidate.candidate_id || trimmed;
          const stored = readStoredWorkbenchJoin();
          let draftIdentityEarly: CreatedDraftIdentity | null = null;
          const fromResponseEarly =
            typeof response.source_draft_id === "string" &&
            response.source_draft_id.trim() &&
            typeof response.source_draft_version === "number" &&
            Number.isInteger(response.source_draft_version) &&
            response.source_draft_version >= 1
              ? {
                  draft_id: response.source_draft_id.trim(),
                  version: response.source_draft_version,
                  name:
                    typeof response.source_draft_name === "string" &&
                    response.source_draft_name.trim()
                      ? response.source_draft_name.trim()
                      : response.source_draft_id.trim(),
                }
              : null;
          if (fromResponseEarly) {
            draftIdentityEarly = fromResponseEarly;
          } else if (stored?.candidate_id === loadedCandidateId) {
            draftIdentityEarly = createdDraftFromStoredJoin(stored);
          } else if (
            createdDraftRef.current &&
            stored?.draft_id === createdDraftRef.current.draft_id &&
            (stored?.candidate_id == null || stored.candidate_id === loadedCandidateId)
          ) {
            draftIdentityEarly = createdDraftRef.current;
          }
          let nextEditor = createEditorStateFromOutput(response.candidate.definition);
          nextEditor = restoreWorkingCopyForCandidate(
            nextEditor,
            draftIdentityEarly?.draft_id ?? null,
            loadedCandidateId,
            stored,
          );
          editorStateRef.current = nextEditor;
          activeCandidateIdRef.current = loadedCandidateId;
          setLoadState({ kind: "success", response });
          setEditorState(nextEditor);
          setViewMode("edit");
          setCandidateIdInput(loadedCandidateId);

          const fromResponse =
            typeof response.source_draft_id === "string" &&
            response.source_draft_id.trim() &&
            typeof response.source_draft_version === "number" &&
            Number.isInteger(response.source_draft_version) &&
            response.source_draft_version >= 1
              ? {
                  draft_id: response.source_draft_id.trim(),
                  version: response.source_draft_version,
                  name:
                    typeof response.source_draft_name === "string" &&
                    response.source_draft_name.trim()
                      ? response.source_draft_name.trim()
                      : response.source_draft_id.trim(),
                }
              : null;
          // Candidate-scoped identity: response wins; stored join only when bound to
          // this candidate; same-session create may still have candidate_id=null.
          let draftIdentity: CreatedDraftIdentity | null = null;
          if (fromResponse) {
            draftIdentity = fromResponse;
          } else if (stored?.candidate_id === loadedCandidateId) {
            draftIdentity = createdDraftFromStoredJoin(stored);
          } else if (
            createdDraftRef.current &&
            stored?.draft_id === createdDraftRef.current.draft_id &&
            (stored?.candidate_id == null || stored.candidate_id === loadedCandidateId)
          ) {
            draftIdentity = createdDraftRef.current;
          }
          const preservedWorkingCopy =
            stored?.candidate_id === loadedCandidateId ? stored.working_copy ?? null : null;
          if (draftIdentity) {
            if (
              !createdDraftRef.current ||
              createdDraftRef.current.draft_id !== draftIdentity.draft_id
            ) {
              applyCreatedDraftIdentity(draftIdentity);
            }
            writeStoredWorkbenchJoin({
              draft_id: draftIdentity.draft_id,
              version: draftIdentity.version,
              name: draftIdentity.name,
              candidate_id: loadedCandidateId,
              working_copy: preservedWorkingCopy,
            });
            if (fromResponse && isCurrentCandidateOp(opId)) {
              void refreshThreatDraftSnapshot(draftIdentity.draft_id);
            }
          } else {
            // Unknown-draft candidate: quarantine any prior ThreatDraft/revise authority.
            clearThreatDraftAuthority();
            createdDraftRef.current = null;
            setCreatedDraft(null);
            setDraftIdInput("");
            setDraftVersionInput("1");
            writeStoredWorkbenchJoin({
              draft_id: null,
              version: null,
              name: null,
              candidate_id: loadedCandidateId,
              working_copy: preservedWorkingCopy,
            });
          }
          return true;
        }
        setLoadState({
          kind: "status",
          candidateId: response.candidate_id || trimmed,
          status: response.status === "active" ? "missing" : response.status,
          failureCategory: response.failure_category ?? null,
          failureMessage: response.failure_message ?? null,
        });
        return false;
      } catch (error) {
        if (!isCurrentCandidateOp(opId)) return false;
        setLoadState({
          kind: "error",
          candidateId: trimmed,
          message: error instanceof Error ? error.message : String(error),
        });
        return false;
      }
    },
    [applyCreatedDraftIdentity, beginCandidateOp, bumpEditorEpoch, clearThreatDraftAuthority, invalidateValidationOwnership, isCurrentCandidateOp, persistActiveCandidateWorkingCopy, refreshThreatDraftSnapshot],
  );

  // One-time session restore. Do not depend on loadCandidate identity — that callback
  // recreates when Advanced draftIdInput changes and would re-enter load with a partial ID.
  useEffect(() => {
    const fromUrl = readCandidateIdFromLocation();
    const stored = readStoredWorkbenchJoin();
    const restored = createdDraftFromStoredJoin(stored);
    if (restored) {
      applyCreatedDraftIdentity(restored);
    }
    if (fromUrl) {
      setCandidateIdInput(fromUrl);
      void loadCandidate(fromUrl);
      return;
    }
    if (stored?.candidate_id) {
      setCandidateIdInput(stored.candidate_id);
      void loadCandidate(stored.candidate_id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- mount-only session restore
  }, []);

  useEffect(() => {
    const draftId = threatDraft?.draft_id ?? null;
    const mechanicsSaved = threatDraft?.workflow_state === "mechanics_saved";
    if (!draftId || !mechanicsSaved) {
      setPublicationHeadResolution({ draftId: null, head: null, error: null, loading: false });
      return;
    }

    let cancelled = false;
    setPublicationHeadResolution({ draftId, head: null, error: null, loading: true });

    void (async () => {
      try {
        const status = await getWorldGraphBootstrapStatus();
        if (cancelled) return;
        const bootstrapHead =
          typeof status.currentHeadRevisionId === "string" && status.currentHeadRevisionId.trim()
            ? status.currentHeadRevisionId.trim()
            : null;
        // Bootstrap status now attaches the live store head even when locked-bundle
        // cert fails. Advanced override remains the manual pin if no head exists.
        const overrideHead = createForm.graphRevisionId.trim() || null;
        const head = bootstrapHead ?? overrideHead;
        if (head) {
          setPublicationHeadResolution({ draftId, head, error: null, loading: false });
          return;
        }
        setPublicationHeadResolution({
          draftId,
          head: null,
          error:
            "Publication is disabled until the current World Graph head is readable. "
            + "Set Advanced → Graph revision override to an exact rev:… if the store head is missing.",
          loading: false,
        });
      } catch (error) {
        if (cancelled) return;
        const overrideHead = createForm.graphRevisionId.trim() || null;
        if (overrideHead) {
          setPublicationHeadResolution({
            draftId,
            head: overrideHead,
            error: null,
            loading: false,
          });
          return;
        }
        setPublicationHeadResolution({
          draftId,
          head: null,
          error:
            error instanceof Error
              ? error.message
              : "World Graph bootstrap status unavailable.",
          loading: false,
        });
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [
    threatDraft?.draft_id,
    threatDraft?.workflow_state,
    threatDraft?.version,
    threatDraft?.accepted_mechanics_ref?.revision_id,
    threatDraft?.accepted_mechanics_ref?.definition_digest,
    createForm.graphRevisionId,
  ]);

  const onSubmitCandidate = (event: FormEvent) => {
    event.preventDefault();
    void loadCandidate(candidateIdInput);
  };

  const completeLocalReviseRefresh = useCallback(
    async (args: {
      generation: number;
      draftId: string;
      attempt: StoredReviseAttemptV1;
      candidateId: string;
      reviseCandidateOpId: number;
    }) => {
      const { generation, draftId, attempt, candidateId, reviseCandidateOpId } = args;
      try {
        const refreshed = await getThreatDraft(draftId);
        if (generation !== reviseOpGenerationRef.current) return false;
        const proof = proveReconciledRefOnDraft(refreshed, candidateId, attempt.request_id);
        if (!proof) {
          setReviseError(
            "Revised proposal reconciled; local refresh incomplete — use Finish loading revised proposal.",
          );
          return false;
        }
        setThreatDraft(refreshed);
        setDraftSnapshotUnavailable(false);
        applyCreatedDraftIdentity({
          draft_id: refreshed.draft_id,
          version: refreshed.version,
          name: refreshed.name,
        });
        const loaded = await loadCandidate(candidateId, { opId: reviseCandidateOpId });
        if (generation !== reviseOpGenerationRef.current) return false;
        if (!loaded) {
          setReviseError(
            "Revised proposal reconciled; local refresh incomplete — use Finish loading revised proposal.",
          );
          return false;
        }
        const completed = markReviseAttemptCompleted(attempt, candidateId);
        writeStoredReviseAttempt(completed);
        setReviseAttempt(completed);
        setReviseStatusMessage("Revised proposal ready.");
        setReviseError(null);
        return true;
      } catch (error) {
        if (generation !== reviseOpGenerationRef.current) return false;
        setReviseError(
          `Revised proposal reconciled; local refresh incomplete — ${
            error instanceof Error ? error.message : String(error)
          }`,
        );
        return false;
      }
    },
    [applyCreatedDraftIdentity, loadCandidate],
  );

  const handleReviseResponse = useCallback(
    async (
      generation: number,
      draftId: string,
      attempt: StoredReviseAttemptV1,
      response: ReviseCandidateFromEditedDefinitionResponseV1,
      reviseCandidateOpId: number,
    ) => {
      if (generation !== reviseOpGenerationRef.current) return;

      if (!reviseResponseMatchesAttempt(response.request_id, attempt.request_id)) {
        setReviseError(
          "Revise response identity mismatch — retaining the exact stored attempt; resume same revise.",
        );
        return;
      }

      if (response.result === "reconciled" && response.candidate_id) {
        const awaiting = markReviseAwaitingLocalRefresh(attempt, response.candidate_id);
        writeStoredReviseAttempt(awaiting);
        setReviseAttempt(awaiting);
        setReviseStatusMessage("Revised proposal reconciled — refreshing draft…");
        await completeLocalReviseRefresh({
          generation,
          draftId,
          attempt: awaiting,
          candidateId: response.candidate_id,
          reviseCandidateOpId,
        });
        return;
      }

      const updated = updateReviseAttemptResult(
        attempt,
        response.result,
        response.candidate_id ?? null,
      );
      writeStoredReviseAttempt(updated);
      setReviseAttempt(updated);

      const klass = classifyReviseResult(response.result);
      if (klass === "terminal_new_allowed") {
        setReviseStatusMessage("Revision terminated — start a new revise attempt if needed.");
      } else if (
        response.result === "revise_busy" ||
        response.result === "revise_history_full"
      ) {
        setReviseStatusMessage(
          response.result === "revise_busy"
            ? "Another revise owns this draft slot — resume the same revise when clear."
            : "Proposal history is full — resume the same revise after capacity clears.",
        );
      } else if (klass === "resume_same") {
        setReviseStatusMessage(
          "Revision outcome uncertain or still in progress — resume the same revise.",
        );
      } else if (response.result === "revise_blocked") {
        setReviseError("Revision blocked — correct inputs and retry.");
      } else {
        setReviseStatusMessage(`Revision result: ${response.result}`);
      }
    },
    [completeLocalReviseRefresh],
  );

  const postReviseAttempt = useCallback(
    async (attempt: StoredReviseAttemptV1, mode: "create" | "resume") => {
      if (reviseInFlightRef.current || revisePending) return;
      if (draftSnapshotUnavailable) return;
      // Prove exact replay authority is durable before any Buddy POST.
      if (!writeStoredReviseAttempt(attempt)) {
        setReviseError(
          "Unable to persist revise replay authority in session storage — revise not sent.",
        );
        setReviseAttempt(attempt);
        return;
      }
      const draftId = attempt.draft_id;
      const generation = ++reviseOpGenerationRef.current;
      const reviseCandidateOpId = beginCandidateOp();
      reviseInFlightRef.current = true;
      setRevisePending(true);
      setReviseError(null);
      setReviseStatusMessage(
        mode === "create" ? "Creating revised proposal…" : "Resuming same revise…",
      );
      try {
        const response = await reviseThreatDraftCandidate(draftId, attempt.request);
        await handleReviseResponse(generation, draftId, attempt, response, reviseCandidateOpId);
      } catch (error) {
        if (generation !== reviseOpGenerationRef.current) return;
        if (
          error instanceof LiveApiError &&
          isExpectedDraftVersionMismatch409(error.status, error.message)
        ) {
          setReviseStatusMessage("Draft version changed — refresh the draft and retry explicitly.");
          void refreshThreatDraftSnapshot(draftId);
          const preclaimed = markRevisePreclaimRebuild(attempt, "stale_version");
          writeStoredReviseAttempt(preclaimed);
          setReviseAttempt(preclaimed);
        } else if (error instanceof LiveApiError && error.status === 422) {
          setReviseError("Revision rejected — correct inputs and create a new revised proposal.");
          const preclaimed = markRevisePreclaimRebuild(attempt, "http_422");
          writeStoredReviseAttempt(preclaimed);
          setReviseAttempt(preclaimed);
        } else if (error instanceof LiveApiError && error.status === 409) {
          // Integrity / unknown 409 — fail closed; do not authorize a replacement request ID.
          setReviseError(
            `Revision conflict (${error.message}) — retaining the exact stored attempt; resume same revise.`,
          );
          writeStoredReviseAttempt(attempt);
          setReviseAttempt(attempt);
        } else {
          setReviseError(
            error instanceof Error
              ? `Revision outcome unknown — ${error.message}`
              : "Revision outcome unknown.",
          );
          writeStoredReviseAttempt(attempt);
          setReviseAttempt(attempt);
        }
      } finally {
        reviseInFlightRef.current = false;
        if (generation === reviseOpGenerationRef.current) {
          setRevisePending(false);
        }
      }
    },
    [draftSnapshotUnavailable, handleReviseResponse, refreshThreatDraftSnapshot, revisePending],
  );

  const onCreateRevisedProposal = useCallback(async () => {
    const editor = editorStateRef.current;
    const candidateId = activeCandidateIdRef.current;
    const draft = threatDraft;
    if (!editor || !candidateId || !draft) {
      setReviseError("Load a candidate with ThreatDraft snapshot before revising.");
      return;
    }
    const panelActions = revisePanelActions(reviseAttempt);
    if (!panelActions.allowCreateNew) {
      setReviseError("Unresolved revise attempt — resume the same revise.");
      return;
    }
    const requestId = crypto.randomUUID();
    const built = buildReviseRequestFromWorkingCopy({
      requestId,
      draft,
      editorState: editor,
      revisionInstructions: reviseInstructionsRaw.split(/\r?\n/),
      preserveElementKeys,
    });
    if (!built.ok) {
      setReviseError(built.message);
      return;
    }
    const sourceCandidateId = candidateId;
    const attempt: StoredReviseAttemptV1 = {
      schema: "dmb_sbw06_revise_attempt_v1",
      draft_id: draft.draft_id,
      source_candidate_id: sourceCandidateId,
      request_id: requestId,
      raw_instructions: reviseInstructionsRaw,
      request: built.request,
      last_result: null,
      candidate_id: null,
      created_at: new Date().toISOString(),
    };
    if (!writeStoredReviseAttempt(attempt)) {
      setReviseError(
        "Unable to persist revise replay authority in session storage — revise not sent.",
      );
      return;
    }
    setReviseAttempt(attempt);
    await postReviseAttempt(attempt, "create");
  }, [postReviseAttempt, preserveElementKeys, reviseAttempt, reviseInstructionsRaw, threatDraft]);

  const onResumeSameRevise = useCallback(async () => {
    const draftId = createdDraftRef.current?.draft_id ?? "";
    const attempt = reviseAttempt ?? (draftId ? readStoredReviseAttempt(draftId) : null);
    if (!attempt) return;
    const panelActions = revisePanelActions(attempt);
    if (!panelActions.showResume) return;
    await postReviseAttempt(attempt, "resume");
  }, [postReviseAttempt, reviseAttempt]);

  const onRetryLocalRefresh = useCallback(async () => {
    const attempt = reviseAttempt;
    if (!attempt || attempt.awaiting_local_refresh !== true || !attempt.candidate_id) {
      return;
    }
    if (reviseInFlightRef.current || revisePending) return;
    const generation = ++reviseOpGenerationRef.current;
    const reviseCandidateOpId = beginCandidateOp();
    reviseInFlightRef.current = true;
    setRevisePending(true);
    setReviseError(null);
    setReviseStatusMessage("Finishing local load of revised proposal…");
    try {
      await completeLocalReviseRefresh({
        generation,
        draftId: attempt.draft_id,
        attempt,
        candidateId: attempt.candidate_id,
        reviseCandidateOpId,
      });
    } finally {
      reviseInFlightRef.current = false;
      if (generation === reviseOpGenerationRef.current) {
        setRevisePending(false);
      }
    }
  }, [completeLocalReviseRefresh, reviseAttempt, revisePending]);

  const onStartNewReviseAttempt = useCallback(() => {
    const panelActions = revisePanelActions(reviseAttempt);
    if (!panelActions.showStartNew) return;
    const draftId = reviseAttempt?.draft_id ?? createdDraftRef.current?.draft_id;
    if (draftId) {
      try {
        sessionStorage.removeItem(reviseAttemptStorageKey(draftId));
      } catch {
        /* ignore */
      }
    }
    setReviseAttempt(null);
    setReviseStatusMessage(null);
    setReviseError(null);
  }, [reviseAttempt]);

  const onSelectProposalCandidate = useCallback(
    (candidateId: string) => {
      persistActiveCandidateWorkingCopy();
      void loadCandidate(candidateId);
    },
    [loadCandidate, persistActiveCandidateWorkingCopy],
  );

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
        setGenerateMessage("Loading candidate…");
        setCreateMessage(null);
        await loadCandidate(candidateId, { opId });
        if (isCurrentCandidateOp(opId)) {
          setGenerateMessage(null);
          setCreateMessage(null);
        }
        return;
      }
      setCreateMessage(null);
      setGenerateError(
        response.failure_message ??
          response.failure_category ??
          "Generation failed without a typed candidate.",
      );
    } catch (error) {
      if (!isCurrentCandidateOp(opId)) return;
      setCreateMessage(null);
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
    setCreateMessage("Generating…");
    await runGenerateFromDraft(createdDraft.draft_id, createdDraft.version);
  };

  const onCreateAndGenerate = async (event: FormEvent) => {
    event.preventDefault();
    if (createAndGenerateInFlightRef.current || pendingGenerate || createPhase === "creating") {
      return;
    }

    createAndGenerateInFlightRef.current = true;
    const opId = beginCandidateOp();
    setCreatePhase("creating");
    setCreateError(null);
    setCreateMessage("Resolving graph head…");
    setGenerateError(null);
    setGenerateMessage(null);
    setPendingGenerate(false);
    setLoadState((prev) => (prev.kind === "loading" ? { kind: "idle" } : prev));

    try {
      const resolved = await resolveCreateScope(createForm);
      if (!isCurrentCandidateOp(opId)) return;
      if (!resolved.ok) {
        setCreatePhase("create_failed");
        setCreateError(resolved.message);
        setCreateMessage(null);
        return;
      }

      const built = buildCreateThreatDraftRequest(createForm, resolved.scope);
      if (!built.ok) {
        setCreatePhase("create_failed");
        setCreateError(built.message);
        setCreateMessage(null);
        return;
      }

      setCreateMessage("Creating…");

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
        createdDraftRef.current = created;
        setDraftIdInput(created.draft_id);
        setDraftVersionInput(String(created.version));
        writeStoredWorkbenchJoin({
          draft_id: created.draft_id,
          version: created.version,
          name: created.name,
          candidate_id: null,
          working_copy: null,
        });
        setCreatePhase("generating");
        setCreateMessage("Generating…");
      } catch (error) {
        if (!isCurrentCandidateOp(opId)) return;
        if (isCreateTransportUncertainty(error)) {
          setCreatePhase("create_uncertain");
          setCreateError(error instanceof Error ? error.message : String(error));
          setCreateMessage(
            "Create may or may not have succeeded. Form kept — confirm before submitting again.",
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
    clearStoredWorkbenchJoin();
    clearThreatDraftAuthority();
    setCreateForm(DEFAULT_CREATE_FORM);
    setCreatedDraft(null);
    createdDraftRef.current = null;
    activeCandidateIdRef.current = null;
    setCreatePhase("idle");
    setCreateMessage(null);
    setCreateError(null);
    setGenerateMessage(null);
    setGenerateError(null);
    setPendingGenerate(false);
    setCandidateIdInput("");
    setDraftIdInput("");
    setDraftVersionInput("1");
    setLoadState({ kind: "idle" });
    setEditorState(null);
    editorStateRef.current = null;
    invalidateValidationOwnership();
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

  const boundAcceptIdentity = resolveAcceptDraftIdentity(
    createdDraft,
    draftIdInput,
    draftVersionInput,
  );
  // Refreshed ThreatDraft version wins only when it matches the candidate-bound draft identity.
  const acceptDraftIdentity =
    threatDraft != null &&
    boundAcceptIdentity != null &&
    threatDraft.draft_id === boundAcceptIdentity.draft_id
      ? { draft_id: threatDraft.draft_id, version: threatDraft.version }
      : boundAcceptIdentity;
  const acceptDraftVersion = acceptDraftIdentity?.version ?? null;
  const mechanicsSavedDraft = threatDraft?.workflow_state === "mechanics_saved";
  const reviseDraftId = threatDraft?.draft_id ?? acceptDraftIdentity?.draft_id ?? null;
  const revisePanel = revisePanelActions(reviseAttempt);
  const reviseReplayFrozen = revisePanel.freezeReplaySource && reviseAttempt != null;
  const reviseControlsDisabled =
    draftSnapshotUnavailable || !threatDraft || draftSnapshotPending || !editorState;

  return (
    <div
      className={
        activeCandidate && editorState
          ? "module-panel statblock-workbench statblock-workbench--edit-dock"
          : "module-panel statblock-workbench"
      }
      data-module-id="statblock_workbench"
    >
      <header className="statblock-workbench-header">
        <div>
          <h2 className="module-title">Statblock Workbench</h2>
          <p className="module-muted">
            Paste a threat description, generate a candidate, then edit and accept mechanics. First
            line becomes the name.
          </p>
        </div>
      </header>

      <section className="statblock-section statblock-create-section">
        <form className="statblock-create-form" onSubmit={onCreateAndGenerate}>
          <label className="statblock-create-field">
            <span className="statblock-create-field-label">Description</span>
            <textarea
              value={createForm.description}
              onChange={(event) => updateCreateField("description", event.target.value)}
              rows={8}
              placeholder={"Mireward Latchling\nA reed-choked latching scavenger from the Mireward verge."}
              data-testid="create-threat-description"
            />
          </label>
          <details className="statblock-create-details">
            <summary>Optional &amp; advanced</summary>
            <div className="statblock-create-optional">
              <p className="statblock-create-context" data-testid="create-threat-context-binding">
                Defaults: {LIVE_CONTROL_CREATE_CONTEXT.world_id} ·{" "}
                {LIVE_CONTROL_CREATE_CONTEXT.campaign_id} ·{" "}
                {LIVE_CONTROL_CREATE_CONTEXT.ruleset.system}{" "}
                {LIVE_CONTROL_CREATE_CONTEXT.ruleset.edition} ·{" "}
                {LIVE_CONTROL_CREATE_CONTEXT.threat_kind} · {LIVE_CONTROL_CREATE_CONTEXT.created_by} ·
                graph head resolved at create
              </p>
              <p className="module-muted" data-testid="create-threat-slice-badge">
                Slice: sbw06c-revise
              </p>
              <div className="statblock-create-optional-grid">
                <label className="statblock-create-field">
                  <span className="statblock-create-field-label">Focus session</span>
                  <input
                    value={createForm.focusSession}
                    onChange={(event) => updateCreateField("focusSession", event.target.value)}
                    inputMode="numeric"
                  />
                </label>
                <label className="statblock-create-field">
                  <span className="statblock-create-field-label">Prep label</span>
                  <input
                    value={createForm.prepLabel}
                    onChange={(event) => updateCreateField("prepLabel", event.target.value)}
                    autoComplete="off"
                  />
                </label>
                <label className="statblock-create-field">
                  <span className="statblock-create-field-label">Slug hint</span>
                  <input
                    value={createForm.slugHint}
                    onChange={(event) => updateCreateField("slugHint", event.target.value)}
                    autoComplete="off"
                  />
                </label>
                <label className="statblock-create-field">
                  <span className="statblock-create-field-label">Target CR</span>
                  <input
                    value={createForm.targetCr}
                    onChange={(event) => updateCreateField("targetCr", event.target.value)}
                    autoComplete="off"
                  />
                </label>
                <label className="statblock-create-field">
                  <span className="statblock-create-field-label">Complexity</span>
                  <input
                    value={createForm.complexity}
                    onChange={(event) => updateCreateField("complexity", event.target.value)}
                    autoComplete="off"
                  />
                </label>
                <label className="statblock-create-field">
                  <span className="statblock-create-field-label">Party level</span>
                  <input
                    value={createForm.partyLevel}
                    onChange={(event) => updateCreateField("partyLevel", event.target.value)}
                    inputMode="numeric"
                  />
                </label>
                <label className="statblock-create-field">
                  <span className="statblock-create-field-label">Party size</span>
                  <input
                    value={createForm.partySize}
                    onChange={(event) => updateCreateField("partySize", event.target.value)}
                    inputMode="numeric"
                  />
                </label>
                <label className="statblock-create-field">
                  <span className="statblock-create-field-label">
                    Graph revision override (exact rev:…; empty uses bootstrap head)
                  </span>
                  <input
                    value={createForm.graphRevisionId}
                    onChange={(event) => updateCreateField("graphRevisionId", event.target.value)}
                    placeholder="rev:…"
                    autoComplete="off"
                    data-testid="create-threat-graph-revision"
                  />
                </label>
                <label className="statblock-create-field statblock-create-checkbox">
                  <input
                    type="checkbox"
                    checked={createForm.allowFreestandingWithoutBootstrap}
                    onChange={(event) =>
                      updateCreateField("allowFreestandingWithoutBootstrap", event.target.checked)
                    }
                    data-testid="create-threat-allow-freestanding"
                  />
                  <span className="statblock-create-field-label">
                    Continue freestanding without a graph head (when bootstrap is unknown, not ready,
                    or contradictory)
                  </span>
                </label>
              </div>
              <label className="statblock-create-field">
                <span className="statblock-create-field-label">Must include (comma or newline)</span>
                <textarea
                  value={createForm.mustInclude}
                  onChange={(event) => updateCreateField("mustInclude", event.target.value)}
                  rows={2}
                />
              </label>
              <label className="statblock-create-field">
                <span className="statblock-create-field-label">Must avoid (comma or newline)</span>
                <textarea
                  value={createForm.mustAvoid}
                  onChange={(event) => updateCreateField("mustAvoid", event.target.value)}
                  rows={2}
                />
              </label>
              <label className="statblock-create-field">
                <span className="statblock-create-field-label">Intended roles (comma or newline)</span>
                <textarea
                  value={createForm.intendedRoles}
                  onChange={(event) => updateCreateField("intendedRoles", event.target.value)}
                  rows={2}
                />
              </label>
              <label className="statblock-create-field">
                <span className="statblock-create-field-label">Tags (comma or newline)</span>
                <textarea
                  value={createForm.tags}
                  onChange={(event) => updateCreateField("tags", event.target.value)}
                  rows={2}
                />
              </label>
              <label className="statblock-create-field">
                <span className="statblock-create-field-label">Terrain notes (comma or newline)</span>
                <textarea
                  value={createForm.terrainNotes}
                  onChange={(event) => updateCreateField("terrainNotes", event.target.value)}
                  rows={2}
                />
              </label>
            </div>
          </details>
          <div className="statblock-command-row statblock-create-actions">
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
        {createMessage ? (
          <p className="statblock-command-status" role="status" data-testid="create-threat-status">
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
        {!createMessage && createdDraft && generateError ? (
          <p
            className="statblock-command-error"
            role="alert"
            data-testid="created-draft-identity"
            data-draft-id={createdDraft.draft_id}
          >
            Couldn’t generate a candidate for {shortThreatDisplayName(createdDraft.name)}:{" "}
            {generateError}
          </p>
        ) : null}
      </section>

      <details className="statblock-section statblock-create-details" open data-testid="workbench-recover-controls">
        <summary>Advanced — recover by candidate or draft ID</summary>
        <p className="module-muted">
          Escape hatches for reopening a known <code>cand_…</code> or regenerating from an existing
          ThreatDraft.
        </p>
        <section className="statblock-storage-section">
          <h3>Load exact candidate</h3>
          <form className="statblock-command-row" onSubmit={onSubmitCandidate}>
            <label className="statblock-create-field">
              <span className="statblock-create-field-label">Candidate ID</span>
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
        <section className="statblock-storage-section">
          <h3>Generate from ThreatDraft</h3>
          <form className="statblock-command-row" onSubmit={onGenerateFromDraft}>
            <label className="statblock-create-field">
              <span className="statblock-create-field-label">Draft ID</span>
              <input
                value={draftIdInput}
                onChange={(event) => setDraftIdInput(event.target.value)}
                placeholder="td_…"
                autoComplete="off"
                spellCheck={false}
              />
            </label>
            <label className="statblock-create-field">
              <span className="statblock-create-field-label">Expected version</span>
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
      </details>

      {loadState.kind === "idle" ? (
        <p className="module-muted">
          Create and generate a threat above, or open Advanced to recover a known candidate.
        </p>
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

      {threatDraft ? (
        <ProposalHistoryPanel
          draft={threatDraft}
          activeCandidateId={activeCandidate?.candidate_id ?? null}
          onSelectCandidate={onSelectProposalCandidate}
          onRefresh={() => void refreshThreatDraftSnapshot(threatDraft.draft_id)}
          refreshPending={draftSnapshotPending}
        />
      ) : null}

      {activeCandidate ? (
        <section className="statblock-section" data-testid="candidate-view-modes">
          <h3>Candidate {activeCandidate.candidate_id}</h3>
          {draftSnapshotUnavailable ? (
            <p className="statblock-command-error" role="alert" data-testid="draft-snapshot-unavailable">
              ThreatDraft snapshot unavailable — revision and version-dependent save are disabled.{" "}
              {draftSnapshotError}
              {reviseDraftId ? (
                <button
                  type="button"
                  className="statblock-inline-retry"
                  onClick={() => void refreshThreatDraftSnapshot(reviseDraftId)}
                >
                  Retry draft refresh
                </button>
              ) : null}
            </p>
          ) : null}
          {editorState && reviseDraftId && threatDraft ? (
            <ReviseWithAiPanel
              candidateId={
                reviseReplayFrozen ? reviseAttempt.source_candidate_id : activeCandidate.candidate_id
              }
              draftId={reviseDraftId}
              draftVersion={threatDraft.version}
              editorStateRevision={
                reviseReplayFrozen
                  ? Number(reviseAttempt.request.editor_state_revision) || 0
                  : editorState.stateRevision
              }
              instructions={
                reviseReplayFrozen ? reviseAttempt.raw_instructions : reviseInstructionsRaw
              }
              onInstructionsChange={setReviseInstructionsRaw}
              preserveElementKeys={
                reviseReplayFrozen
                  ? reviseAttempt.request.preserve_element_keys
                  : preserveElementKeys
              }
              onPreserveElementKeysChange={setPreserveElementKeys}
              onCreate={() => void onCreateRevisedProposal()}
              onResume={() => void onResumeSameRevise()}
              onStartNew={onStartNewReviseAttempt}
              onRetryLocalRefresh={() => void onRetryLocalRefresh()}
              revisePending={revisePending}
              showResume={revisePanel.showResume}
              showStartNew={revisePanel.showStartNew}
              showRetryLocalRefresh={revisePanel.showRetryLocalRefresh}
              disabled={reviseControlsDisabled}
              createDisabled={!revisePanel.allowCreateNew}
              statusMessage={reviseStatusMessage}
              errorMessage={reviseError}
              mechanicsSaved={mechanicsSavedDraft}
              readOnlyInstructions={reviseReplayFrozen}
            />
          ) : null}
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

          {/* Dock stays mounted in review and edit — Validate/Accept operate on the working copy. */}
          {editorState ? (
            <AcceptMechanicsFlow
              preview={previewValidation}
              editorState={editorState}
              editorEpoch={editorEpoch}
              draftId={acceptDraftIdentity?.draft_id ?? null}
              draftVersion={acceptDraftVersion}
              sourceCandidateId={activeCandidate.candidate_id}
              workingCopy={editorState.workingCopy}
              validationFailure={validationFailure}
              onValidate={() => void onValidateWorkingCopy()}
              validatePending={
                validatePendingForCurrent || getUiStatus(editorState) === "validating"
              }
              validateDisabled={
                validatePendingForCurrent || getUiStatus(editorState) === "validating"
              }
              mechanicsSavedDraft={mechanicsSavedDraft}
              draftAuthorityUnavailable={draftSnapshotUnavailable}
              onMechanicsSaved={(id) => {
                void refreshThreatDraftSnapshot(id);
              }}
              publicationDock={publicationDock}
            />
          ) : null}

          {mechanicsSavedDraft && threatDraft ? (
            <section
              className="statblock-section"
              aria-label="Publish to World Graph"
              data-testid="workbench-publication-entry"
            >
              <h3>Identity & proposal review</h3>
              {publicationHeadResolution.draftId === threatDraft.draft_id &&
              publicationHeadResolution.loading ? (
                <p className="module-muted" role="status" data-testid="publication-head-loading">
                  Resolving World Graph head…
                </p>
              ) : publicationHeadResolution.draftId === threatDraft.draft_id &&
                publicationHeadResolution.head ? (
                <ThreatPublicationPanel
                  key={[
                    threatDraft.draft_id,
                    String(threatDraft.version),
                    threatDraft.accepted_mechanics_ref?.statblock_id ?? "",
                    threatDraft.accepted_mechanics_ref?.revision_id ?? "",
                    threatDraft.accepted_mechanics_ref?.definition_digest ?? "",
                  ].join(":")}
                  draft={threatDraft}
                  expectedParentRevisionId={publicationHeadResolution.head}
                  onDockModelChange={setPublicationDock}
                  resolveExpectedParentRevisionId={async () => {
                    const status = await getWorldGraphBootstrapStatus();
                    const bootstrapHead =
                      typeof status.currentHeadRevisionId === "string"
                      && status.currentHeadRevisionId.trim()
                        ? status.currentHeadRevisionId.trim()
                        : null;
                    const head = bootstrapHead || createForm.graphRevisionId.trim() || null;
                    if (!head) {
                      throw new Error(
                        "Publication retry requires a readable World Graph head "
                        + "(store head from bootstrap status, or exact Advanced graph revision override).",
                      );
                    }
                    setPublicationHeadResolution({
                      draftId: threatDraft.draft_id,
                      head,
                      error: null,
                      loading: false,
                    });
                    return head;
                  }}
                />
              ) : publicationHeadResolution.draftId === threatDraft.draft_id &&
                publicationHeadResolution.error ? (
                <p
                  className="statblock-command-error"
                  role="status"
                  data-testid="publication-head-unavailable"
                >
                  {publicationHeadResolution.error}
                </p>
              ) : null}
            </section>
          ) : null}
        </section>
      ) : null}

      {reviseAttempt?.awaiting_local_refresh && reviseDraftId && threatDraft && !editorState ? (
        <section className="statblock-section" data-testid="revise-awaiting-refresh-panel">
          <ReviseWithAiPanel
            candidateId={reviseAttempt.source_candidate_id}
            draftId={reviseDraftId}
            draftVersion={threatDraft.version}
            editorStateRevision={Number(reviseAttempt.request.editor_state_revision) || 0}
            instructions={reviseAttempt.raw_instructions}
            onInstructionsChange={setReviseInstructionsRaw}
            preserveElementKeys={reviseAttempt.request.preserve_element_keys}
            onPreserveElementKeysChange={setPreserveElementKeys}
            onCreate={() => void onCreateRevisedProposal()}
            onResume={() => void onResumeSameRevise()}
            onStartNew={onStartNewReviseAttempt}
            onRetryLocalRefresh={() => void onRetryLocalRefresh()}
            revisePending={revisePending}
            showResume={revisePanel.showResume}
            showStartNew={revisePanel.showStartNew}
            showRetryLocalRefresh={revisePanel.showRetryLocalRefresh}
            disabled
            createDisabled
            statusMessage={reviseStatusMessage}
            errorMessage={reviseError}
            mechanicsSaved={mechanicsSavedDraft}
            readOnlyInstructions
          />
        </section>
      ) : null}
    </div>
  );
}
