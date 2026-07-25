import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";

import {
  acceptThreatDraftMechanics,
  generateThreatDraftCandidate,
  getStatblockCandidate,
  reconcileAcceptanceOperation,
  validateStatblockDefinition,
} from "../../api/liveApi";
import type {
  AcceptThreatDraftMechanicsResponseV1,
  GenerateThreatDraftCandidateResponseV1,
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
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [acceptPending, setAcceptPending] = useState(false);
  const [acceptError, setAcceptError] = useState<string | null>(null);
  const [acceptResult, setAcceptResult] = useState<AcceptThreatDraftMechanicsResponseV1 | null>(
    null,
  );
  const acceptOperationIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (!eligible) {
      setConfirmOpen(false);
      setAcceptPending(false);
      setAcceptError(null);
      setAcceptResult(null);
      acceptOperationIdRef.current = null;
    }
  }, [eligible, preview?.definitionDigest, editorState.stateRevision, editorEpoch]);

  const ensureOperationId = (): string => {
    if (!acceptOperationIdRef.current) {
      acceptOperationIdRef.current = crypto.randomUUID();
    }
    return acceptOperationIdRef.current;
  };

  const resetAcceptSession = () => {
    setConfirmOpen(false);
    setAcceptPending(false);
    setAcceptError(null);
    acceptOperationIdRef.current = null;
  };

  const runAccept = async () => {
    if (!preview || !eligible) return;

    const draftId = draftIdInput.trim();
    const expectedVersion = Number(draftVersionInput);
    if (!draftId || !Number.isInteger(expectedVersion) || expectedVersion < 1) {
      setAcceptError("Provide a draft ID and expected draft version ≥ 1 before accepting.");
      return;
    }

    const operationId = ensureOperationId();
    setAcceptPending(true);
    setAcceptError(null);

    try {
      const response = await acceptThreatDraftMechanics(draftId, {
        operation_id: operationId,
        expected_draft_version: expectedVersion,
        definition: workingCopy,
        validation_receipt: preview.receipt,
        validation_definition_digest: preview.definitionDigest,
        source_candidate_id: sourceCandidateId,
        change_summary: "Accepted via Statblock Workbench",
      });
      setAcceptResult(response);
      setConfirmOpen(false);
    } catch (error) {
      setAcceptError(error instanceof Error ? error.message : String(error));
    } finally {
      setAcceptPending(false);
    }
  };

  const onReconcile = async () => {
    const draftId = draftIdInput.trim();
    const operationId = acceptOperationIdRef.current;
    if (!draftId || !operationId) return;

    setAcceptPending(true);
    setAcceptError(null);
    try {
      const response = await reconcileAcceptanceOperation(draftId, operationId);
      setAcceptResult(response);
    } catch (error) {
      setAcceptError(error instanceof Error ? error.message : String(error));
    } finally {
      setAcceptPending(false);
    }
  };

  if (!previewCurrent && !acceptResult) {
    return (
      <p className="module-muted">
        {preview
          ? "Preview validation is stale — revalidate before accept/save."
          : "Validate the working copy to preview acceptance eligibility. Mechanics accept/save does not publish to the World Graph."}
      </p>
    );
  }

  if (previewCurrent && preview?.receipt.status === "invalid") {
    return (
      <p className="module-muted" role="status">
        Fix validation errors before accept/save. Invalid preview receipts cannot be accepted.
      </p>
    );
  }

  const resultLabel = acceptResult?.result_label;

  return (
    <div data-testid="accept-mechanics-flow">
      {eligible && !acceptResult ? (
        <div className="statblock-command-row">
          {!confirmOpen ? (
            <button
              type="button"
              onClick={() => {
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

      {confirmOpen && eligible && preview ? (
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

      {acceptResult ? (
        <section className="statblock-section" role="status" data-accept-result={resultLabel ?? ""}>
          {resultLabel === "mechanics_saved" ? (
            <>
              <p>
                <strong>Mechanics saved; not published</strong> to the World Graph.
              </p>
              {acceptResult.locator ? (
                <p className="module-muted">
                  Locator: statblock <code>{acceptResult.locator.statblock_id}</code>, revision{" "}
                  <code>{acceptResult.locator.revision_id}</code>, digest{" "}
                  <code>{acceptResult.locator.definition_digest}</code>
                </p>
              ) : null}
            </>
          ) : null}

          {resultLabel === "server_committed_reference_pending" ||
          acceptResult.authority_state === "server_committed" ? (
            <>
              <p className="module-muted">
                Server committed mechanics; draft reference reconciliation is pending. Mechanics
                saved; not published to the World Graph until reconciliation completes.
              </p>
              <button type="button" disabled={acceptPending} onClick={() => void onReconcile()}>
                {acceptPending ? "Reconciling…" : "Reconcile acceptance"}
              </button>
            </>
          ) : null}

          {resultLabel === "dispatched_unknown" ? (
            <>
              <p className="module-muted">
                Accept outcome unknown — the server may still be processing. Retry accept with the
                same operation id, or reconcile later if mechanics appear saved.
              </p>
              <button type="button" disabled={acceptPending} onClick={() => void runAccept()}>
                {acceptPending ? "Retrying…" : "Retry accept"}
              </button>
            </>
          ) : null}

          {resultLabel === "acceptance_blocked" ||
          resultLabel === "acceptance_busy" ||
          resultLabel === "acceptance_history_full" ||
          resultLabel === "acceptance_input_conflict" ||
          resultLabel === "acceptance_draft_unavailable" ||
          resultLabel === "accepted_ref_conflict" ||
          resultLabel === "terminal_failure" ? (
            <p className="statblock-command-error" role="alert">
              Accept blocked: {acceptResult.message ?? resultLabel}
              {acceptResult.failure_category ? ` (${acceptResult.failure_category})` : ""}
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

  const onGenerateFromDraft = async (event: FormEvent) => {
    event.preventDefault();
    const draftId = draftIdInput.trim();
    const expectedVersion = Number(draftVersionInput);
    if (!draftId || !Number.isInteger(expectedVersion) || expectedVersion < 1) {
      setGenerateError("Provide a draft ID and expected draft version ≥ 1.");
      return;
    }
    const opId = beginCandidateOp();
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
      }
    }
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
