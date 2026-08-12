import { useEffect, useRef, useState } from "react";

import { LiveApiError } from "../api/liveApi";
import type { DocumentCommandResult } from "../markdownCanvas/markdownCanvasTypes";
import type { WorkspaceDocumentRecord } from "../api/types";
import {
  SurfaceContextAction,
  SurfaceContextPopover,
} from "../surfaceInteraction/contextHost";

export interface BuildDocumentRenameControlProps {
  currentTitle: string;
  renaming?: boolean;
  disabled?: boolean;
  onRename: (title: string) => Promise<DocumentCommandResult<WorkspaceDocumentRecord>>;
}

function renameErrorMessage(result: DocumentCommandResult<WorkspaceDocumentRecord>): string {
  if (result.ok) return "";
  if (result.code === "conflict" || result.code === "duplicate_command") {
    return "Could not rename this source.";
  }
  const reason = result.reason ?? "";
  if (/409|revision|stale|conflict|changed elsewhere/i.test(reason)) {
    return "Source changed elsewhere. Reload before retrying.";
  }
  return "Could not rename this source.";
}

export function BuildDocumentRenameControl({
  currentTitle,
  renaming = false,
  disabled = false,
  onRename,
}: BuildDocumentRenameControlProps) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState(currentTitle);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const wasSubmittingRef = useRef(false);

  useEffect(() => {
    if (!open) {
      setTitle(currentTitle);
      setError(null);
    }
  }, [currentTitle, open]);

  useEffect(() => {
    const finished = wasSubmittingRef.current && !submitting && !renaming;
    wasSubmittingRef.current = submitting || renaming;
    if (finished && !error) {
      setOpen(false);
    }
  }, [error, renaming, submitting]);

  const trimmed = title.trim();
  const unchanged = trimmed === currentTitle.trim();
  const canSubmit = !disabled && !renaming && !submitting && Boolean(trimmed) && !unchanged;

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await onRename(trimmed);
      if (!result.ok) {
        if (result.code === "execute_failed") {
          // Prefer 409-shaped copy when LiveApiError bubbled as reason.
          setError(
            /409|revision|Source changed|expected_revision/i.test(result.reason)
              ? "Source changed elsewhere. Reload before retrying."
              : renameErrorMessage(result),
          );
        } else {
          setError(renameErrorMessage(result));
        }
        return;
      }
      setTitle(result.value.title);
      setOpen(false);
    } catch (err) {
      if (err instanceof LiveApiError && err.status === 409) {
        setError("Source changed elsewhere. Reload before retrying.");
      } else {
        setError("Could not rename this source.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const busy = renaming || submitting;
  const form = (
    <form
      className="build-document-rename__form"
      data-testid="build-document-rename-form"
      onSubmit={(event) => {
        void handleSubmit(event);
      }}
    >
      <label className="build-document-rename__field">
        <span>Title</span>
        <input
          type="text"
          data-testid="build-document-rename-title"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          disabled={disabled || busy}
          autoFocus
        />
      </label>
      <div className="build-document-rename__actions">
        <button
          type="button"
          data-testid="build-document-rename-cancel"
          onClick={() => setOpen(false)}
          disabled={busy}
        >
          Cancel
        </button>
        <button type="submit" data-testid="build-document-rename-submit" disabled={!canSubmit}>
          {busy ? "Renaming…" : "Rename source"}
        </button>
      </div>
      <div className="build-document-rename__status" aria-live="polite">
        {error ? (
          <p className="build-document-rename__error" role="alert" data-testid="build-document-rename-error">
            {error}
          </p>
        ) : null}
      </div>
    </form>
  );

  return (
    <div className="build-document-rename build-document-rename--context" data-testid="build-document-rename">
      <SurfaceContextPopover
        open={open}
        onOpenChange={(next) => {
          if (busy && !next) return;
          setOpen(next);
        }}
        title="Rename source"
        align="end"
        placement="beside"
        className="surface-context-popover--wide"
        trigger={
          <SurfaceContextAction
            data-testid="build-document-rename-open"
            onClick={() => setOpen(true)}
            disabled={disabled || busy}
          >
            Rename
          </SurfaceContextAction>
        }
      >
        {form}
      </SurfaceContextPopover>
    </div>
  );
}
