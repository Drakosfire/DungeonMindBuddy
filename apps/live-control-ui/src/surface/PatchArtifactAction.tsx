import { useMemo, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";

import type {
  ArtifactReadResponse,
  PatchArtifactMetadata,
  ProjectionCapability,
  ProjectionCommand,
  ProjectionTarget,
  ProjectionWriteResult,
} from "../api/types";

interface PatchArtifactActionProps {
  target: ProjectionTarget;
  capability: ProjectionCapability;
  artifact: ArtifactReadResponse & { artifact_kind: "roll_table" };
  onSubmitCommand: (command: ProjectionCommand) => Promise<ProjectionWriteResult>;
  onAccepted?: (result: ProjectionWriteResult) => Promise<void> | void;
}

interface PreviewState {
  result: ProjectionWriteResult;
  oldText: string;
  newText: string;
  rationale: string;
  fileStateToken: string;
  confirmIdempotencyKey: string;
}

function makeConfirmIdempotencyKey(target: ProjectionTarget): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `ui-patch-artifact:${target.target_type}:${target.target_id}:${crypto.randomUUID()}`;
  }
  return `ui-patch-artifact:${target.target_type}:${target.target_id}:${Date.now()}`;
}

function getPatchMetadata(result: ProjectionWriteResult): PatchArtifactMetadata["patch"] | null {
  const metadata = result.metadata;
  if (metadata == null || typeof metadata !== "object") {
    return null;
  }
  const patchRaw = (metadata as PatchArtifactMetadata).patch;
  if (patchRaw == null || typeof patchRaw !== "object") {
    return null;
  }
  return patchRaw;
}

function isPreviewReadyResult(result: ProjectionWriteResult): boolean {
  const patch = getPatchMetadata(result);
  return result.status === "noop" && patch?.dry_run === true;
}

function hasPathLikePayloadFields(payload: Record<string, unknown>): boolean {
  return (
    "source_path" in payload ||
    "file_path" in payload ||
    "path" in payload ||
    "artifact_text" in payload
  );
}

export function PatchArtifactAction({
  target,
  capability,
  artifact,
  onSubmitCommand,
  onAccepted,
}: PatchArtifactActionProps) {
  const [expanded, setExpanded] = useState(false);
  const [oldText, setOldText] = useState("");
  const [newText, setNewText] = useState("");
  const [rationale, setRationale] = useState("");
  const [previewState, setPreviewState] = useState<PreviewState | null>(null);
  const [result, setResult] = useState<ProjectionWriteResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [confirming, setConfirming] = useState(false);

  const currentToken = artifact.file_state_token;
  const stalePreview = previewState != null && previewState.fileStateToken !== currentToken;
  const canOpen = capability.enabled;
  const canRun = !previewing && !confirming && expanded;

  const validationMessage = useMemo(() => {
    if (!currentToken) {
      return "Cannot patch this artifact because no file state token was returned. Refresh the artifact and try again.";
    }
    if (oldText.length === 0) {
      return "Text to replace is required.";
    }
    if (newText.length === 0) {
      return "Replacement text is required.";
    }
    if (oldText === newText) {
      return "Replacement text must differ from text to replace.";
    }
    if (oldText.length > 20000) {
      return "Text to replace must be 20000 characters or fewer.";
    }
    if (newText.length > 20000) {
      return "Replacement text must be 20000 characters or fewer.";
    }
    return null;
  }, [currentToken, oldText, newText]);

  const previewMatchesInputs =
    previewState != null &&
    previewState.oldText === oldText &&
    previewState.newText === newText &&
    previewState.rationale === rationale &&
    previewState.fileStateToken === currentToken;

  const canPreview = canRun && validationMessage == null;
  const canConfirm = canRun && previewMatchesInputs && !stalePreview && !confirming && !previewing;

  function clearPreviewState() {
    setPreviewState(null);
  }

  function handleEditChange(
    setter: (value: string) => void,
  ): (event: ChangeEvent<HTMLTextAreaElement | HTMLInputElement>) => void {
    return (event) => {
      setter(event.target.value);
      if (previewState != null) {
        clearPreviewState();
      }
    };
  }

  async function handlePreview(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setResult(null);
    if (validationMessage) {
      setError(validationMessage);
      return;
    }
    if (!currentToken) {
      setError("File state token is missing.");
      return;
    }

    const payload: Record<string, unknown> = {
      expected_file_state_token: currentToken,
      old_text: oldText,
      new_text: newText,
      dry_run: true,
    };
    const trimmedRationale = rationale.trim();
    if (trimmedRationale.length > 0) {
      payload.rationale = trimmedRationale;
    }
    if (hasPathLikePayloadFields(payload)) {
      setError("Patch payload included forbidden path-like fields.");
      return;
    }

    const command: ProjectionCommand = {
      command_type: "patch_artifact",
      target,
      lane: "prep_note",
      payload,
      evidence: [],
      requested_by: {
        requester_type: "human_ui",
        requester_id: "live-control-ui",
      },
      idempotency_key: null,
    };

    setPreviewing(true);
    try {
      const previewResult = await onSubmitCommand(command);
      setResult(previewResult);
      if (isPreviewReadyResult(previewResult)) {
        setPreviewState({
          result: previewResult,
          oldText,
          newText,
          rationale,
          fileStateToken: currentToken,
          confirmIdempotencyKey: makeConfirmIdempotencyKey(target),
        });
      } else {
        clearPreviewState();
      }
    } catch (previewError: unknown) {
      setError(previewError instanceof Error ? previewError.message : "Preview failed.");
      clearPreviewState();
    } finally {
      setPreviewing(false);
    }
  }

  async function handleConfirm() {
    setError(null);
    if (previewState == null) {
      setError("Run a successful preview before confirming.");
      return;
    }
    if (previewState.fileStateToken !== currentToken || !currentToken) {
      setError("Artifact changed since preview. Refresh and preview again before confirming.");
      return;
    }

    const payload: Record<string, unknown> = {
      expected_file_state_token: previewState.fileStateToken,
      old_text: previewState.oldText,
      new_text: previewState.newText,
      dry_run: false,
    };
    const trimmedRationale = previewState.rationale.trim();
    if (trimmedRationale.length > 0) {
      payload.rationale = trimmedRationale;
    }
    if (hasPathLikePayloadFields(payload)) {
      setError("Patch payload included forbidden path-like fields.");
      return;
    }

    const command: ProjectionCommand = {
      command_type: "patch_artifact",
      target,
      lane: "prep_note",
      payload,
      evidence: [],
      requested_by: {
        requester_type: "human_ui",
        requester_id: "live-control-ui",
      },
      idempotency_key: previewState.confirmIdempotencyKey,
    };

    setConfirming(true);
    try {
      const confirmResult = await onSubmitCommand(command);
      setResult(confirmResult);
      if (confirmResult.status === "accepted") {
        clearPreviewState();
        setOldText("");
        setNewText("");
        setRationale("");
        await onAccepted?.(confirmResult);
      }
    } catch (confirmError: unknown) {
      setError(confirmError instanceof Error ? confirmError.message : "Confirm failed.");
    } finally {
      setConfirming(false);
    }
  }

  const patchMetadata = result ? getPatchMetadata(result) : null;
  const previewPatchMetadata = previewState ? getPatchMetadata(previewState.result) : null;

  return (
    <section className="patch-artifact-action" aria-label="Patch roll table action">
      <button
        type="button"
        onClick={() => setExpanded((value) => !value)}
        disabled={!canOpen || previewing || confirming}
      >
        Patch artifact
      </button>
      {expanded ? (
        <form className="patch-artifact-form" onSubmit={handlePreview}>
          {!currentToken ? (
            <p className="module-error">
              Cannot patch this artifact because no file state token was returned. Refresh the
              artifact and try again.
            </p>
          ) : null}
          <label>
            Text to replace
            <textarea
              aria-label="Text to replace"
              value={oldText}
              onChange={handleEditChange(setOldText)}
              disabled={previewing || confirming || !currentToken}
              maxLength={21000}
            />
          </label>
          <label>
            Replacement text
            <textarea
              aria-label="Replacement text"
              value={newText}
              onChange={handleEditChange(setNewText)}
              disabled={previewing || confirming || !currentToken}
              maxLength={21000}
            />
          </label>
          <label>
            Rationale (optional)
            <input
              aria-label="Rationale (optional)"
              value={rationale}
              onChange={handleEditChange(setRationale)}
              disabled={previewing || confirming || !currentToken}
            />
          </label>
          <div className="patch-artifact-actions">
            <button type="submit" disabled={!canPreview}>
              {previewing ? "Previewing…" : "Preview patch"}
            </button>
            <button type="button" disabled={!canConfirm} onClick={() => void handleConfirm()}>
              {confirming ? "Confirming…" : "Confirm patch"}
            </button>
            <button
              type="button"
              onClick={() => {
                setExpanded(false);
              }}
              disabled={previewing || confirming}
            >
              Cancel
            </button>
          </div>
          {previewState ? (
            <p className="module-muted">Preview ready. Confirm uses exactly the previewed values.</p>
          ) : null}
          {stalePreview ? (
            <p className="module-error">
              Artifact token changed since preview. Refresh and preview again before confirming.
            </p>
          ) : null}
          {error ? <p className="module-error">{error}</p> : null}
          {result ? (
            <div className="write-result">
              <p className="write-result-title">Status: {result.status}</p>
              {result.status === "accepted" ? <p className="module-muted">Patch applied.</p> : null}
              {result.conflicts.map((conflict, index) => (
                <p key={`${conflict.conflict_type}:${index}`} className="module-muted">
                  {conflict.conflict_type}: {conflict.message}
                </p>
              ))}
              {result.diagnostics.map((diag, index) => (
                <p key={`${diag}:${index}`} className="module-muted">
                  {diag}
                </p>
              ))}
              {result.events_appended.map((eventId) => (
                <p key={eventId} className="module-muted">
                  Audit event: {eventId}
                </p>
              ))}
              {result.artifacts_changed.map((changed) => (
                <p key={`${changed.target_type}:${changed.target_id}`} className="module-muted">
                  Artifact changed: {changed.target_type} {changed.target_id}
                </p>
              ))}
              {result.invalidations.map((invalidation, index) => (
                <p
                  key={`${invalidation.projection_key}:${index}`}
                  className="module-muted"
                >{`Invalidation: ${invalidation.projection_key}`}</p>
              ))}
              {patchMetadata?.file_state_token_before ? (
                <p className="module-muted">Before token: {patchMetadata.file_state_token_before}</p>
              ) : null}
              {patchMetadata?.file_state_token_after ? (
                <p className="module-muted">After token: {patchMetadata.file_state_token_after}</p>
              ) : null}
              {typeof patchMetadata?.replacement_count === "number" ? (
                <p className="module-muted">Replacement count: {patchMetadata.replacement_count}</p>
              ) : null}
              {typeof patchMetadata?.old_text_length === "number" ? (
                <p className="module-muted">Old length: {patchMetadata.old_text_length}</p>
              ) : null}
              {typeof patchMetadata?.new_text_length === "number" ? (
                <p className="module-muted">New length: {patchMetadata.new_text_length}</p>
              ) : null}
              {patchMetadata?.unified_diff ? (
                <>
                  <p className="module-muted">Server preview:</p>
                  <pre className="artifact-markdown">{patchMetadata.unified_diff}</pre>
                </>
              ) : null}
            </div>
          ) : null}
          {previewPatchMetadata?.dry_run ? (
            <p className="module-muted">Preview mode: server dry-run confirmed.</p>
          ) : null}
        </form>
      ) : null}
    </section>
  );
}
