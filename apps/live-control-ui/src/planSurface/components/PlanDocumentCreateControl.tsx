import { useEffect, useRef, useState } from "react";

import {
  defaultSessionPrepTitle,
  durablePlanTargetRelpath,
} from "../config/planSessionDescriptor";

export interface PlanDocumentCreateSubmitPayload {
  title: string;
  targetSession: number;
}

interface PlanDocumentCreateControlProps {
  campaignId: string;
  campaignLabel: string;
  suggestedSession: number;
  suggestedTitle: string;
  creating?: boolean;
  createError?: string | null;
  activationError?: string | null;
  onSubmit: (payload: PlanDocumentCreateSubmitPayload) => void;
  onRetryOpen?: () => void;
  disabled?: boolean;
}

/**
 * Quiet intentional-create control for Plan prep documents. Opens an inline
 * form; management (rename/archive) stays out of scope.
 */
export function PlanDocumentCreateControl({
  campaignId,
  campaignLabel,
  suggestedSession,
  suggestedTitle,
  creating = false,
  createError = null,
  activationError = null,
  onSubmit,
  onRetryOpen,
  disabled = false,
}: PlanDocumentCreateControlProps) {
  const [open, setOpen] = useState(false);
  const [targetSession, setTargetSession] = useState(suggestedSession);
  const [title, setTitle] = useState(suggestedTitle);
  const titleManuallyEditedRef = useRef(false);

  useEffect(() => {
    setTargetSession(suggestedSession);
  }, [suggestedSession]);

  useEffect(() => {
    if (!titleManuallyEditedRef.current) {
      setTitle(suggestedTitle);
    }
  }, [suggestedTitle]);

  useEffect(() => {
    if (createError || activationError) {
      setOpen(true);
    }
  }, [createError, activationError]);

  const durablePathAvailable =
    durablePlanTargetRelpath(campaignId, targetSession) != null;

  const handleOpen = () => {
    titleManuallyEditedRef.current = false;
    setTargetSession(suggestedSession);
    setTitle(suggestedTitle);
    setOpen(true);
  };

  const handleSessionChange = (raw: string) => {
    const parsed = Number.parseInt(raw, 10);
    if (!Number.isFinite(parsed) || parsed < 1) return;
    setTargetSession(parsed);
    if (!titleManuallyEditedRef.current) {
      setTitle(defaultSessionPrepTitle(campaignLabel, parsed));
    }
  };

  const handleTitleChange = (value: string) => {
    titleManuallyEditedRef.current = true;
    setTitle(value);
  };

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (disabled || creating || !durablePathAvailable) return;
    const trimmed = title.trim();
    if (!trimmed) return;
    onSubmit({ title: trimmed, targetSession });
  };

  return (
    <div className="plan-document-create" data-testid="plan-document-create">
      {!open ? (
        <button
          type="button"
          className="plan-document-create__open"
          data-testid="plan-document-create-open"
          onClick={handleOpen}
          disabled={disabled || creating}
        >
          Create New Prep
        </button>
      ) : (
        <form className="plan-document-create__form" onSubmit={handleSubmit}>
          <label className="plan-document-create__field">
            <span>Target session</span>
            <input
              type="number"
              min={1}
              data-testid="plan-document-create-session"
              value={targetSession}
              onChange={(event) => handleSessionChange(event.target.value)}
              disabled={disabled || creating}
            />
          </label>
          <label className="plan-document-create__field">
            <span>Title</span>
            <input
              type="text"
              data-testid="plan-document-create-title"
              value={title}
              onChange={(event) => handleTitleChange(event.target.value)}
              disabled={disabled || creating}
            />
          </label>
          {!durablePathAvailable ? (
            <p
              className="plan-document-create__path-warning"
              role="alert"
              data-testid="plan-document-create-path-error"
            >
              A durable Plan path cannot be derived for this campaign and session.
              Choose a supported campaign or adjust the target session.
            </p>
          ) : null}
          {createError ? (
            <p
              className="plan-document-create__error"
              role="alert"
              data-testid="plan-document-create-error"
            >
              {createError}
            </p>
          ) : null}
          {activationError ? (
            <p
              className="plan-document-create__error"
              role="alert"
              data-testid="plan-document-create-activation-error"
            >
              Created but could not open: {activationError}
            </p>
          ) : null}
          <div className="plan-document-create__actions">
            <button
              type="submit"
              data-testid="plan-document-create-submit"
              disabled={disabled || creating || !durablePathAvailable || !title.trim()}
            >
              {creating ? "Creating…" : "Create prep"}
            </button>
            {activationError && onRetryOpen ? (
              <button
                type="button"
                data-testid="plan-document-create-retry-open"
                onClick={onRetryOpen}
                disabled={disabled || creating}
              >
                Retry Open
              </button>
            ) : null}
          </div>
        </form>
      )}
    </div>
  );
}
