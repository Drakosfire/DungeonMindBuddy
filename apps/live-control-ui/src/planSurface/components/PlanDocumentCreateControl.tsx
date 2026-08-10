import { useEffect, useMemo, useRef, useState } from "react";

import { defaultSessionPrepTitle } from "../config/planSessionDescriptor";

export interface PlanDocumentCreateSubmitPayload {
  title: string;
  targetSession: number;
}

export interface PlanDocumentCreateActiveDocument {
  title: string;
  targetSession: number | null;
}

interface PlanDocumentCreateControlProps {
  campaignId: string;
  campaignLabel: string;
  suggestedSession: number;
  suggestedTitle: string;
  /** Active Plan documents used for same-session copy and distinct-title gate. */
  activeDocuments?: PlanDocumentCreateActiveDocument[];
  creating?: boolean;
  createError?: string | null;
  activationError?: string | null;
  onSubmit: (payload: PlanDocumentCreateSubmitPayload) => void;
  onRetryOpen?: () => void;
  disabled?: boolean;
}

function normalizePlanTitle(title: string): string {
  return title.trim().replace(/\s+/g, " ").toLowerCase();
}

/**
 * Quiet intentional-create control for Plan prep documents. Opens an inline
 * form; management (rename/archive) stays out of scope.
 */
export function PlanDocumentCreateControl({
  campaignLabel,
  suggestedSession,
  suggestedTitle,
  activeDocuments = [],
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

  const sameSessionActive = useMemo(
    () =>
      activeDocuments.filter(
        (document) => document.targetSession != null && document.targetSession === targetSession,
      ),
    [activeDocuments, targetSession],
  );

  const titleConflicts = useMemo(() => {
    const normalized = normalizePlanTitle(title);
    if (!normalized) return false;
    return sameSessionActive.some(
      (document) => normalizePlanTitle(document.title) === normalized,
    );
  }, [sameSessionActive, title]);

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
    if (disabled || creating || titleConflicts) return;
    const trimmed = title.trim();
    if (!trimmed) return;
    onSubmit({ title: trimmed, targetSession });
  };

  const canSubmit = !disabled && !creating && !titleConflicts && Boolean(title.trim());

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
            <span>For session</span>
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
          {sameSessionActive.length > 0 ? (
            <p
              className="plan-document-create__same-session"
              data-testid="plan-document-create-same-session"
            >
              {sameSessionActive.length === 1
                ? `1 other prep is already aimed at Session ${targetSession}.`
                : `${sameSessionActive.length} other preps are already aimed at Session ${targetSession}.`}{" "}
              This will create another alternative.
            </p>
          ) : null}
          {titleConflicts ? (
            <p
              className="plan-document-create__title-warning"
              role="alert"
              data-testid="plan-document-create-title-error"
            >
              Give this alternative a distinct title, such as &quot;If the party goes north&quot;.
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
              disabled={!canSubmit}
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
