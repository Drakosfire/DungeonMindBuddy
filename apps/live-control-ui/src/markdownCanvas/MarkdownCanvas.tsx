import type { ReactNode } from "react";
import type { Content } from "@tiptap/react";

import { MarkdownEditorCore } from "../tiptap/MarkdownEditorCore";
import { useMarkdownCanvasSession } from "./MarkdownCanvasSession";

export interface MarkdownCanvasSlots {
  /** Optional title override; defaults to record title. */
  title?: ReactNode;
  /** Extra status lines under the default status label. */
  statusExtra?: ReactNode;
  /** When true, omit the default status paragraph (use statusExtra only). */
  hideDefaultStatus?: boolean;
  /** Footer / document actions (e.g. Save). */
  actions?: ReactNode;
  /** Adjacent tools rendered above or beside the editor. */
  tools?: ReactNode;
  /** Loading copy. */
  loadingMessage?: string;
  /** Load-error heading. */
  errorHeading?: string;
  /** Conflict heading. */
  conflictHeading?: string;
  className?: string;
  editorClassName?: string;
  dataTestId?: string;
  editorDataTestId?: string;
  loadingTestId?: string;
  errorTestId?: string;
  authorityErrorTestId?: string;
  conflictTestId?: string;
  statusTestId?: string;
  saveErrorTestId?: string;
}

export interface MarkdownCanvasProps {
  slots?: MarkdownCanvasSlots;
}

/**
 * Rendered document work object. Consumes MarkdownCanvasSession; imports no surface
 * plugin or extract-run product types.
 */
export function MarkdownCanvas({ slots = {} }: MarkdownCanvasProps) {
  const session = useMarkdownCanvasSession();
  const {
    title,
    statusExtra,
    hideDefaultStatus = false,
    actions,
    tools,
    loadingMessage = "Loading document…",
    errorHeading = "Document",
    conflictHeading = "Document",
    className = "markdown-canvas",
    editorClassName = "markdown-canvas-editor",
    dataTestId = "markdown-canvas",
    editorDataTestId = "markdown-canvas-editor",
    loadingTestId,
    errorTestId,
    authorityErrorTestId,
    conflictTestId,
    statusTestId,
    saveErrorTestId,
  } = slots;

  if (session.phase === "loading" || session.phase === "unloaded") {
    return (
      <main className="app-status" data-testid={loadingTestId ?? `${dataTestId}-loading`}>
        <p>{loadingMessage}</p>
      </main>
    );
  }

  if (session.phase === "load_error") {
    return (
      <main className="app-status app-error" data-testid={errorTestId ?? `${dataTestId}-error`}>
        <h1>{errorHeading}</h1>
        <p data-testid={authorityErrorTestId ?? `${dataTestId}-authority-error`}>
          {session.error ?? "Unable to load document."}
        </p>
      </main>
    );
  }

  if (session.phase === "conflict") {
    return (
      <main className="app-status app-error" data-testid={conflictTestId ?? `${dataTestId}-conflict`}>
        <h1>{conflictHeading}</h1>
        <p>{session.statusLabel}</p>
        <button type="button" onClick={() => void session.reloadFromSnapshot()}>
          Reload from server
        </button>
        <button type="button" onClick={() => void session.discardLocalDraft()}>
          Discard local draft
        </button>
      </main>
    );
  }

  return (
    <main className={className} data-testid={dataTestId}>
      {tools}
      <header className="markdown-canvas-header">
        <h1>{title ?? session.record?.title ?? errorHeading}</h1>
        {hideDefaultStatus ? null : (
          <p data-testid={statusTestId ?? `${dataTestId}-status`}>{session.statusLabel}</p>
        )}
        {session.error ? (
          <p role="alert" data-testid={saveErrorTestId ?? `${dataTestId}-save-error`}>{session.error}</p>
        ) : null}
        {statusExtra}
      </header>

      <section className={editorClassName}>
        <MarkdownEditorCore
          documentKey={session.documentKey}
          content={session.editorContent as Content}
          onEditorChange={session.setEditor}
          onUpdate={session.handleEditorUpdate}
          dataTestId={editorDataTestId}
        />
      </section>

      {actions ? <footer className="markdown-canvas-actions">{actions}</footer> : null}
    </main>
  );
}
