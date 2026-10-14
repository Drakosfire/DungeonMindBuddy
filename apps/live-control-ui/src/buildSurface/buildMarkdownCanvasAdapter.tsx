import { useEffect, useId, useRef, useState } from "react";

import { BUILD_SURFACE_LABEL } from "./buildSurfaceConfig";
import type { MarkdownCanvasSlots } from "../markdownCanvas/MarkdownCanvas";
import { useMarkdownCanvasSession } from "../markdownCanvas/MarkdownCanvasSession";

/** Build-owned slot copy and Save action for the shared MarkdownCanvas. */
export function useBuildMarkdownCanvasSlots(args?: {
  /** When shared Edit Host publishes Save, omit the duplicate footer button. */
  hideFooterSave?: boolean;
}): MarkdownCanvasSlots {
  const session = useMarkdownCanvasSession();
  const hideFooterSave = args?.hideFooterSave === true;
  const dialogRef = useRef<HTMLDialogElement>(null);
  const dialogId = useId();
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
    tools: session.dirty ? (
      <>
        <button type="button" disabled={!canDiscard} onClick={() => {
          if (canDiscard) setPendingDiscard({ documentId: session.documentId, documentKey: session.documentKey });
        }}>
          Discard local draft
        </button>
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
        {session.exportedMarkdownAuthoritative ? (
          <button
            type="button"
            data-testid="build-reimport-authoritative-button"
            onClick={() => session.reimportFromAuthoritativeMarkdown()}
          >
            Re-import from source
          </button>
        ) : null}
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
