import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";

import {
  generateThreatDraftCandidate,
  getStatblockCandidate,
  validateStatblockDefinition,
} from "../../api/liveApi";
import type {
  GenerateThreatDraftCandidateResponseV1,
  ReadStatblockCandidateResponseV1,
  ValidateDefinitionBuddyResponseV1,
} from "../../api/types";
import type {
  GeneratedStatblockCandidateV1,
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
  receipt: ValidationReceiptV1;
  definitionDigest: string;
};

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
  validateFailureMessage,
}: {
  preview: PreviewValidation | null;
  editorState: StatblockEditorState | null;
  validateFailureMessage: string | null;
}) {
  const uiStatus = editorState ? getUiStatus(editorState) : null;
  const previewCurrent =
    preview != null &&
    editorState != null &&
    editorState.validatedRevision === preview.associatedRevision &&
    editorState.stateRevision === preview.associatedRevision &&
    (uiStatus === "validated" ||
      uiStatus === "validated_with_warnings" ||
      uiStatus === "validated_with_errors");

  if (validateFailureMessage) {
    return (
      <section
        className="statblock-section"
        role="status"
        data-testid="preview-validation-panel"
        data-preview-state="unavailable"
      >
        <h3>Preview validation</h3>
        <p className="module-muted">
          Validation unavailable. Working copy retained (unsaved). {validateFailureMessage}
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

  const { fieldIssues, globalIssues } = partitionValidationIssuesByPath(preview.receipt.issues);
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
      </div>

      <div data-testid="preview-global-issues">
        <h4>Global issues</h4>
        {globalIssues.length === 0 ? <p className="module-muted">None</p> : null}
        {globalSplit.errors.map((issue) => (
          <p key={`ge-${issue.code}-${issue.message}`} data-issue-severity="error">
            [error] {issue.message}
          </p>
        ))}
        {globalSplit.warnings.map((issue) => (
          <p key={`gw-${issue.code}-${issue.message}`} data-issue-severity="warning">
            [warning] {issue.message}
          </p>
        ))}
      </div>
    </section>
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
  const [validateFailureMessage, setValidateFailureMessage] = useState<string | null>(null);
  const [pendingValidate, setPendingValidate] = useState(false);
  const validateRequestIdRef = useRef(0);
  const editorStateRef = useRef<StatblockEditorState | null>(null);
  editorStateRef.current = editorState;

  const loadCandidate = useCallback(async (candidateId: string) => {
    const trimmed = candidateId.trim();
    if (!trimmed) {
      setLoadState({ kind: "error", candidateId: "", message: "Enter an exact candidate ID." });
      return;
    }
    setLoadState({ kind: "loading", candidateId: trimmed });
    setGenerateMessage(null);
    setGenerateError(null);
    setEditorState(null);
    setPreviewValidation(null);
    setValidateFailureMessage(null);
    try {
      const response = await getStatblockCandidate(trimmed);
      if (response.status === "active" && response.candidate) {
        setLoadState({ kind: "success", response });
        setEditorState(createEditorStateFromOutput(response.candidate.definition));
        setViewMode("edit");
        setPreviewValidation(null);
        setValidateFailureMessage(null);
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
      setLoadState({
        kind: "error",
        candidateId: trimmed,
        message: error instanceof Error ? error.message : String(error),
      });
    }
  }, []);

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
    setPendingGenerate(true);
    setGenerateError(null);
    setGenerateMessage(null);
    try {
      const response: GenerateThreatDraftCandidateResponseV1 = await generateThreatDraftCandidate(
        draftId,
        { expected_draft_version: expectedVersion },
      );
      if (response.outcome === "success" && response.candidate?.candidate_id) {
        const candidateId = response.candidate.candidate_id;
        setCandidateIdInput(candidateId);
        setGenerateMessage(
          `Generated ${candidateId}${
            response.cache_status ? ` (${response.cache_status})` : ""
          }. Loading structured review…`,
        );
        await loadCandidate(candidateId);
        return;
      }
      setGenerateError(
        response.failure_message ??
          response.failure_category ??
          "Generation failed without a typed candidate.",
      );
    } catch (error) {
      setGenerateError(error instanceof Error ? error.message : String(error));
    } finally {
      setPendingGenerate(false);
    }
  };

  const onValidateWorkingCopy = async () => {
    const current = editorStateRef.current;
    if (!current) return;

    const requestId = ++validateRequestIdRef.current;
    const requestedRevision = current.stateRevision;
    const workingCopy = current.workingCopy;
    setPendingValidate(true);
    setValidateFailureMessage(null);
    setEditorState(beginValidationAttempt(current));

    let response: ValidateDefinitionBuddyResponseV1;
    try {
      response = await validateStatblockDefinition({ definition: workingCopy });
    } catch (error) {
      if (requestId !== validateRequestIdRef.current) {
        setPendingValidate(false);
        return;
      }
      setEditorState((prev) => {
        if (!prev || prev.stateRevision !== requestedRevision) return prev;
        return markValidationUnavailable(prev);
      });
      setValidateFailureMessage(error instanceof Error ? error.message : String(error));
      setPendingValidate(false);
      return;
    }

    if (requestId !== validateRequestIdRef.current) {
      setPendingValidate(false);
      return;
    }

    const latest = editorStateRef.current;
    if (!latest || latest.stateRevision !== requestedRevision) {
      setPendingValidate(false);
      return;
    }

    if (
      response.outcome !== "success" ||
      !response.validation_receipt ||
      response.definition_digest == null ||
      response.definition_digest !== response.validation_receipt.definition_digest
    ) {
      setEditorState((prev) => {
        if (!prev || prev.stateRevision !== requestedRevision) return prev;
        return markValidationUnavailable(prev);
      });
      setValidateFailureMessage(
        response.failure_message ??
          response.failure_category ??
          "Validation dependency unavailable",
      );
      setPendingValidate(false);
      return;
    }

    const uiStatus = mapServerValidationStatus(response.validation_receipt.status);
    setPreviewValidation({
      associatedRevision: requestedRevision,
      receipt: response.validation_receipt,
      definitionDigest: response.definition_digest,
    });
    setValidateFailureMessage(null);
    setEditorState((prev) => {
      if (!prev || prev.stateRevision !== requestedRevision) return prev;
      return markValidationAssociated(prev, uiStatus);
    });
    setPendingValidate(false);
  };

  const activeCandidate: GeneratedStatblockCandidateV1 | null =
    loadState.kind === "success" ? loadState.response.candidate ?? null : null;

  return (
    <div className="module-panel statblock-workbench" data-module-id="statblock_workbench">
      <header className="statblock-workbench-header">
        <div>
          <p className="eyebrow">Typed candidate review and preview validation</p>
          <h2 className="module-title">Statblock Workbench</h2>
          <p className="module-muted">
            Displays mechanics from a structured DungeonMind candidate. Edit mode holds a session-only
            working copy; preview validation does not accept or save mechanics.
          </p>
        </div>
        <span className="badge">sbw05c-preview</span>
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
          <button type="submit" disabled={loadState.kind === "loading"}>
            {loadState.kind === "loading" ? "Loading…" : "Load candidate"}
          </button>
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
                  disabled={pendingValidate || getUiStatus(editorState) === "validating"}
                >
                  {pendingValidate || getUiStatus(editorState) === "validating"
                    ? "Validating…"
                    : "Validate working copy"}
                </button>
                <p className="module-muted">
                  Preview validation only — session-only and unsaved. No accept or save path.
                </p>
              </div>
              <PreviewValidationPanel
                preview={previewValidation}
                editorState={editorState}
                validateFailureMessage={validateFailureMessage}
              />
              <StatblockDefinitionEditor
                output={activeCandidate.definition}
                editorState={editorState}
                onEditorStateChange={setEditorState}
              />
            </>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
