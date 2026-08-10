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

const PLAN_TITLE_EXAMPLES = [
  "If the party goes north",
  "If the siege breaks",
  "If they flee",
  "If the deal holds",
] as const;

/** Delay before mid-edit session digits retarget title/helpers (e.g. 27 → 2 → 26). */
const SESSION_COMMIT_DEBOUNCE_MS = 300;

function findConflictingSameSessionTitle(
  title: string,
  sameSessionActive: PlanDocumentCreateActiveDocument[],
): string | null {
  const normalized = normalizePlanTitle(title);
  if (!normalized) return null;
  const match = sameSessionActive.find(
    (document) => normalizePlanTitle(document.title) === normalized,
  );
  return match?.title.trim() || null;
}

function suggestUnusedPlanTitleExample(
  sameSessionActive: PlanDocumentCreateActiveDocument[],
): string | null {
  const taken = new Set(
    sameSessionActive.map((document) => normalizePlanTitle(document.title)).filter(Boolean),
  );
  return PLAN_TITLE_EXAMPLES.find((example) => !taken.has(normalizePlanTitle(example))) ?? null;
}

function parseSessionInput(raw: string): number | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  const parsed = Number.parseInt(trimmed, 10);
  if (!Number.isFinite(parsed) || parsed < 1 || String(parsed) !== trimmed) {
    return null;
  }
  return parsed;
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
  const [sessionText, setSessionText] = useState(String(suggestedSession));
  const [targetSession, setTargetSession] = useState(suggestedSession);
  const [title, setTitle] = useState(suggestedTitle);
  const titleManuallyEditedRef = useRef(false);
  const sessionCommitTimerRef = useRef<number | null>(null);
  const campaignLabelRef = useRef(campaignLabel);
  campaignLabelRef.current = campaignLabel;

  const clearSessionCommitTimer = () => {
    if (sessionCommitTimerRef.current != null) {
      window.clearTimeout(sessionCommitTimerRef.current);
      sessionCommitTimerRef.current = null;
    }
  };

  const commitSession = (parsed: number) => {
    setTargetSession((current) => {
      if (current === parsed) return current;
      if (!titleManuallyEditedRef.current) {
        setTitle(defaultSessionPrepTitle(campaignLabelRef.current, parsed));
      }
      return parsed;
    });
  };

  useEffect(() => {
    clearSessionCommitTimer();
    setSessionText(String(suggestedSession));
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

  const wasCreatingRef = useRef(false);
  useEffect(() => {
    const finishedCreating = wasCreatingRef.current && !creating;
    wasCreatingRef.current = creating;
    if (!finishedCreating || createError || activationError) return;
    // Successful create/activation cycle — collapse back to the quiet open control.
    clearSessionCommitTimer();
    titleManuallyEditedRef.current = false;
    setSessionText(String(suggestedSession));
    setTargetSession(suggestedSession);
    setTitle(suggestedTitle);
    setOpen(false);
  }, [activationError, createError, creating, suggestedSession, suggestedTitle]);

  useEffect(() => () => clearSessionCommitTimer(), []);

  const sameSessionActive = useMemo(
    () =>
      activeDocuments.filter(
        (document) => document.targetSession != null && document.targetSession === targetSession,
      ),
    [activeDocuments, targetSession],
  );

  const conflictingTitle = useMemo(
    () => findConflictingSameSessionTitle(title, sameSessionActive),
    [sameSessionActive, title],
  );
  const titleConflicts = conflictingTitle != null;
  const unusedTitleExample = useMemo(
    () => (titleConflicts ? suggestUnusedPlanTitleExample(sameSessionActive) : null),
    [sameSessionActive, titleConflicts],
  );

  const handleOpen = () => {
    clearSessionCommitTimer();
    titleManuallyEditedRef.current = false;
    setSessionText(String(suggestedSession));
    setTargetSession(suggestedSession);
    setTitle(suggestedTitle);
    setOpen(true);
  };

  const handleSessionChange = (raw: string) => {
    setSessionText(raw);
    const parsed = parseSessionInput(raw);
    clearSessionCommitTimer();
    if (parsed == null) return;
    sessionCommitTimerRef.current = window.setTimeout(() => {
      sessionCommitTimerRef.current = null;
      commitSession(parsed);
    }, SESSION_COMMIT_DEBOUNCE_MS);
  };

  const handleSessionBlur = () => {
    clearSessionCommitTimer();
    const parsed = parseSessionInput(sessionText);
    if (parsed != null) {
      setSessionText(String(parsed));
      commitSession(parsed);
      return;
    }
    setSessionText(String(targetSession));
  };

  const handleTitleChange = (value: string) => {
    titleManuallyEditedRef.current = true;
    setTitle(value);
  };

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    clearSessionCommitTimer();
    // Commit pending session digits synchronously so Enter-before-debounce
    // cannot pair a new targetSession with a stale auto title from the last render.
    const effectiveSession = parseSessionInput(sessionText) ?? targetSession;
    const effectiveTitle =
      !titleManuallyEditedRef.current && effectiveSession !== targetSession
        ? defaultSessionPrepTitle(campaignLabelRef.current, effectiveSession)
        : title;
    setSessionText(String(effectiveSession));
    setTargetSession(effectiveSession);
    if (effectiveTitle !== title) {
      setTitle(effectiveTitle);
    }
    if (disabled || creating) return;
    const trimmed = effectiveTitle.trim();
    if (!trimmed) return;
    const sameSessionForSubmit = activeDocuments.filter(
      (document) =>
        document.targetSession != null && document.targetSession === effectiveSession,
    );
    if (findConflictingSameSessionTitle(trimmed, sameSessionForSubmit) != null) return;
    onSubmit({ title: trimmed, targetSession: effectiveSession });
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
        <form
          className="plan-document-create__form"
          data-testid="plan-document-create-form"
          onSubmit={handleSubmit}
        >
          <div className="plan-document-create__controls">
            <label className="plan-document-create__field plan-document-create__field--session">
              <span>For session</span>
              <input
                type="number"
                min={1}
                data-testid="plan-document-create-session"
                value={sessionText}
                onChange={(event) => handleSessionChange(event.target.value)}
                onBlur={handleSessionBlur}
                disabled={disabled || creating}
              />
            </label>
            <label className="plan-document-create__field plan-document-create__field--title">
              <span>Title</span>
              <input
                type="text"
                data-testid="plan-document-create-title"
                value={title}
                onChange={(event) => handleTitleChange(event.target.value)}
                disabled={disabled || creating}
              />
            </label>
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
          </div>
          <div className="plan-document-create__status" aria-live="polite">
            <p
              className={
                sameSessionActive.length > 0
                  ? "plan-document-create__same-session"
                  : "plan-document-create__status-slot"
              }
              data-testid="plan-document-create-same-session"
              hidden={sameSessionActive.length === 0}
            >
              {sameSessionActive.length === 1
                ? `1 other prep is already aimed at Session ${targetSession}.`
                : `${sameSessionActive.length} other preps are already aimed at Session ${targetSession}.`}{" "}
              This will create another alternative.
            </p>
            <p
              className={
                titleConflicts && conflictingTitle
                  ? "plan-document-create__title-warning"
                  : "plan-document-create__status-slot"
              }
              role={titleConflicts && conflictingTitle ? "alert" : undefined}
              data-testid="plan-document-create-title-error"
              hidden={!(titleConflicts && conflictingTitle)}
            >
              {titleConflicts && conflictingTitle
                ? `Another active prep for Session ${targetSession} is already titled "${conflictingTitle}".${
                    unusedTitleExample
                      ? ` Choose a different name, such as "${unusedTitleExample}".`
                      : " Choose a different name."
                  }`
                : null}
            </p>
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
          </div>
        </form>
      )}
    </div>
  );
}
