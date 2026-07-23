import { useEffect } from "react";

import { MarkdownEditorCore } from "../tiptap/MarkdownEditorCore";
import { useWorkspaceDocumentAuthoring } from "../workspaceDocument/useWorkspaceDocumentAuthoring";
import { useAgentInteraction } from "../agentInteraction/useAgentInteraction";
import {
  BUILD_DOCUMENT_STATUS_COMMITTED,
  BUILD_DOCUMENT_STATUS_DIRTY,
  BUILD_SURFACE_LABEL,
} from "./buildSurfaceConfig";

interface BuildSurfaceShellProps {
  documentId: string;
}

export function BuildSurfaceShell({ documentId }: BuildSurfaceShellProps) {
  const { rehydrateScope, publishSurfaceContext } = useAgentInteraction();
  const authoring = useWorkspaceDocumentAuthoring({
    documentId,
    surface: "build",
    kind: "worldbuilding_source",
  });

  useEffect(() => {
    if (!authoring.record) return;
    rehydrateScope({
      campaignId: authoring.record.campaign_id,
      sessionNumber: null,
      surfaceId: "build",
      documentId: authoring.record.document_id,
    });
    publishSurfaceContext({
      surfaceId: "build",
      label: `${BUILD_SURFACE_LABEL} · ${authoring.record.title}`,
      campaignId: authoring.record.campaign_id,
      documentId: authoring.record.document_id,
      sessionNumber: null,
      ambientSummary: authoring.record.document_class ?? "worldbuilding source",
      sourceEnvelope: null,
      updatedAt: new Date().toISOString(),
    });
  }, [authoring.record, publishSurfaceContext, rehydrateScope]);

  if (authoring.status === "loading") {
    return (
      <main className="app-status" data-testid="build-surface-loading">
        <p>Loading worldbuilding source…</p>
      </main>
    );
  }

  if (authoring.status === "error") {
    return (
      <main className="app-status app-error" data-testid="build-surface-error">
        <h1>{BUILD_SURFACE_LABEL}</h1>
        <p>{authoring.error ?? "Unable to load worldbuilding source."}</p>
      </main>
    );
  }

  if (authoring.status === "conflict") {
    return (
      <main className="app-status app-error" data-testid="build-surface-conflict">
        <h1>{BUILD_SURFACE_LABEL}</h1>
        <p>{authoring.reconciliation?.conflictReason ?? "Local draft conflicts with server content."}</p>
        <button type="button" onClick={() => void authoring.reloadFromSnapshot()}>
          Reload from server
        </button>
        <button type="button" onClick={authoring.discardLocalDraft}>
          Discard local draft
        </button>
      </main>
    );
  }

  const lifecycleLabel = authoring.dirty ? BUILD_DOCUMENT_STATUS_DIRTY : BUILD_DOCUMENT_STATUS_COMMITTED;

  return (
    <main className="build-surface-shell" data-testid="build-surface-shell">
      <header className="build-surface-header">
        <h1>{authoring.record?.title ?? BUILD_SURFACE_LABEL}</h1>
        <p data-testid="build-document-status">{lifecycleLabel}</p>
        <p data-testid="build-authoring-status">{authoring.statusLabel}</p>
        {authoring.record?.document_class ? (
          <p data-testid="build-document-class">{authoring.record.document_class}</p>
        ) : null}
      </header>

      <section className="build-surface-editor">
        <MarkdownEditorCore
          documentKey={authoring.documentKey}
          content={authoring.editorContent}
          onEditorChange={authoring.setEditor}
          onUpdate={() => authoring.markDirty()}
          dataTestId="build-markdown-editor"
        />
      </section>

      <footer className="build-surface-actions">
        <button
          type="button"
          data-testid="build-save-button"
          disabled={authoring.saveDisabled}
          onClick={() => void authoring.saveMarkdown()}
        >
          Save
        </button>
      </footer>
    </main>
  );
}
