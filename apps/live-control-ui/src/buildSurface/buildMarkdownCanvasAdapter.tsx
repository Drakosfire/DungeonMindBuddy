import type { WorkspaceDraftRecoveryReview } from "../workspaceDocument/workspaceDocumentRecovery";
import { useEffect, useId, useRef, useState } from "react";

import { BUILD_SURFACE_LABEL } from "./buildSurfaceConfig";
import type { MarkdownCanvasSlots } from "../markdownCanvas/MarkdownCanvas";
import { type MarkdownCanvasSessionValue, useMarkdownCanvasSession } from "../markdownCanvas/MarkdownCanvasSession";

/** Build-owned slot copy and Save action for the shared MarkdownCanvas. */
export function useBuildMarkdownCanvasSlots(args?: {
  /** When shared Edit Host publishes Save, omit the duplicate footer button. */
  hideFooterSave?: boolean;
  hideDraftTools?: boolean;
}): MarkdownCanvasSlots {
  return useBuildSlotsForSession(useMarkdownCanvasSession(), args);
}

function useBuildSlotsForSession(session: MarkdownCanvasSessionValue, args?: { hideFooterSave?: boolean; hideDraftTools?: boolean }): MarkdownCanvasSlots {
  const hideFooterSave = args?.hideFooterSave === true;
  const dialogRef = useRef<HTMLDialogElement>(null);
  const dialogId = useId();
  const recoveryDialogRef = useRef<HTMLDialogElement>(null);
  const [recoveryReview, setRecoveryReview] = useState<WorkspaceDraftRecoveryReview | null>(null);
  const [recoveryError, setRecoveryError] = useState("");
  useEffect(() => { setRecoveryReview(null); setRecoveryError(""); }, [session.documentId, session.documentKey]);
  useEffect(() => {
    if (recoveryReview && recoveryDialogRef.current && !recoveryDialogRef.current.open) recoveryDialogRef.current.showModal();
  }, [recoveryReview]);
  function reviewRecovery() {
    try { setRecoveryReview(session.prepareDraftRecovery()); setRecoveryError(""); }
    catch (error) { setRecoveryError(error instanceof Error ? error.message : "Draft recovery is unavailable."); }
  }
  function confirmRecovery(mode: "source" | "current" = "source") {
    if (!recoveryReview) return;
    try { session.confirmDraftRecovery(recoveryReview, mode); setRecoveryReview(null); setRecoveryError(""); }
    catch (error) { setRecoveryError(error instanceof Error ? error.message : "The draft was not replaced."); }
  }
  function restoreRecovery() {
    try { session.restoreDraftRecovery(); setRecoveryError(""); }
    catch (error) { setRecoveryError(error instanceof Error ? error.message : "The draft was not restored."); }
  }
  const [pendingDiscard, setPendingDiscard] = useState<{ documentId: string; documentKey: string } | null>(null);
  const pendingMatches = pendingDiscard != null && session.dirty
    && pendingDiscard.documentId === session.documentId
    && pendingDiscard.documentKey === session.documentKey;
  useEffect(() => {
    if (pendingDiscard && !pendingMatches) setPendingDiscard(null);
  }, [pendingDiscard, pendingMatches]);
  useEffect(() => {
    const dialog = dialogRef.current;
    if (pendingMatches && dialog && !dialog.open) dialog.showModal();
  }, [pendingMatches]);
  const canDiscard = ["ready_clean", "ready_dirty", "save_error", "committed"].includes(session.phase)
    && session.activeCommand == null;

  return {
    title: session.record?.title ?? BUILD_SURFACE_LABEL,
    loadingMessage: "Loading worldbuilding source…",
    errorHeading: BUILD_SURFACE_LABEL,
    conflictHeading: BUILD_SURFACE_LABEL,
    className: "build-surface-shell",
    editorClassName: "build-surface-editor tiptap-spike-editor",
    dataTestId: "build-surface-shell",
    editorDataTestId: "build-markdown-editor",
    loadingTestId: "build-surface-loading",
    errorTestId: "build-surface-error",
    authorityErrorTestId: "build-authority-error",
    conflictTestId: "build-surface-conflict",
    saveErrorTestId: "build-save-error",
    tools: (session.dirty || session.exportedMarkdownAuthoritative || session.draftRecoveryAvailable) && !args?.hideDraftTools ? (
      <>
        {session.exportedMarkdownAuthoritative ? <button type="button" disabled={!canDiscard} onClick={reviewRecovery}>Review protected draft</button> : null}
        {session.draftRecoveryAvailable ? <button type="button" disabled={!canDiscard} onClick={restoreRecovery}>Restore protected draft</button> : null}
        {recoveryError && !recoveryReview ? <span role="alert">{recoveryError}</span> : null}
        {recoveryReview ? <dialog ref={recoveryDialogRef} aria-labelledby={`${dialogId}-recovery-title`}
          onCancel={() => setRecoveryReview(null)} style={{ maxWidth: "min(46rem, calc(100vw - 2rem))", maxHeight: "80vh", overflow: "auto" }}>
          <h2 id={`${dialogId}-recovery-title`}>Review protected draft</h2>
          <p>A previous editing problem protected a copy in this browser. Choose the page you want to keep; neither choice saves over the server yet.</p>
          <p>Both versions will first be kept in a verified recovery copy. You can restore it before making newer edits.</p>
          <details><summary>Current page preview</summary><pre style={{ whiteSpace: "pre-wrap" }}>{recoveryReview.editorText}</pre></details>
          <details><summary>Preserved Markdown</summary><pre style={{ whiteSpace: "pre-wrap" }}>{recoveryReview.preservedMarkdown}</pre></details>
          {recoveryReview.currentPageIssue && <p>{recoveryReview.currentPageIssue}</p>}
          <div style={{ position: "sticky", bottom: 0, background: "var(--surface, #171d28)", padding: ".75rem 0", display: "flex", gap: ".5rem", flexWrap: "wrap" }}>
            <button type="button" disabled={!canDiscard || !recoveryReview.canKeepCurrent} onClick={() => confirmRecovery("current")}>Keep current page and resume saving</button>
            <button type="button" disabled={!canDiscard || recoveryReview.canUsePreserved === false} onClick={() => confirmRecovery("source")}>Use preserved version</button>
            <button type="button" autoFocus onClick={() => setRecoveryReview(null)}>Cancel review</button>
          </div>
          {recoveryError ? <p role="alert">{recoveryError}</p> : null}
        </dialog> : null}
        {session.dirty ? <button className="build-discard-draft" type="button" disabled={!canDiscard} onClick={() => {
          if (canDiscard) setPendingDiscard({ documentId: session.documentId, documentKey: session.documentKey });
        }}>
          Discard draft
        </button> : null}
        {pendingMatches ? (
          <dialog ref={dialogRef} role="alertdialog" aria-modal="true"
            aria-labelledby={`${dialogId}-title`} aria-describedby={`${dialogId}-description`}
            onCancel={() => setPendingDiscard(null)}
            style={{ maxWidth: "min(28rem, calc(100vw - 2rem))", padding: "1.25rem", borderRadius: 8,
              background: "var(--surface, #171d28)", color: "var(--fg, #e8eaef)", border: "1px solid var(--border, #2a3142)" }}>
            <h2 id={`${dialogId}-title`}>Discard local draft?</h2>
            <p id={`${dialogId}-description`}>Unsaved edits in this browser will be removed. The saved source will not change.</p>
            <div style={{ display: "flex", gap: "0.5rem", justifyContent: "flex-end", flexWrap: "wrap" }}>
              <button type="button" autoFocus onClick={() => setPendingDiscard(null)}>Keep editing</button>
              <button type="button" disabled={!canDiscard} onClick={() => {
                if (!canDiscard || !pendingMatches) return;
                setPendingDiscard(null);
                void session.discardLocalDraft();
              }}>Discard changes</button>
            </div>
          </dialog>
        ) : null}
      </>
    ) : undefined,
    hideDefaultStatus: true,
    hideReadyHeader: true,
    actions: hideFooterSave ? undefined : (
      <>
        <button
          type="button"
          data-testid="build-save-button"
          disabled={session.saveDisabled}
          onClick={() => void session.saveMarkdown()}
        >
          Save
        </button>
      </>
    ),
  };
}

export const BUILD_MARKDOWN_CANVAS = {
  surface: "build" as const,
  kind: "worldbuilding_source" as const,
};

/** Keep recovery in the document navigation, outside authored paper. */
export function BuildDraftRecovery({ session }: { session: MarkdownCanvasSessionValue }) {
  const slots = useBuildSlotsForSession(session, { hideFooterSave: true });
  return <div className="build-draft-recovery">{slots.tools}</div>;
}
