import { useEffect } from "react";

import { MarkdownEditorCore } from "../tiptap/MarkdownEditorCore";
import { useWorkspaceDocumentAuthoring } from "../workspaceDocument/useWorkspaceDocumentAuthoring";
import { useAgentInteraction } from "../agentInteraction/useAgentInteraction";
import { BUILD_SURFACE_LABEL } from "./buildSurfaceConfig";

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
    const contentStatus = authoring.record.content_status;
    const loadedRevision = authoring.snapshot?.loaded_revision ?? authoring.record.revision;
    const contentSha = authoring.snapshot?.content_sha256 ?? null;
    publishSurfaceContext({
      surfaceId: "build",
      label: `${BUILD_SURFACE_LABEL} · ${authoring.record.title}`,
      campaignId: authoring.record.campaign_id,
      documentId: authoring.record.document_id,
      sessionNumber: null,
      ambientSummary: [
        authoring.record.document_class ?? "worldbuilding source",
        `rev ${loadedRevision}`,
        authoring.dirty ? "local dirty" : "local clean",
        contentStatus === "committed" ? "durable committed" : "durable draft",
        `phase ${authoring.phase}`,
      ].join(" · "),
      sourceEnvelope: {
        schema: "agent_interaction_source_envelope_v1",
        artifactRefs: [
          { kind: "workspace_document", value: authoring.record.document_id },
          ...(authoring.record.target_relpath
            ? [{ kind: "path" as const, value: authoring.record.target_relpath }]
            : []),
        ],
        provenanceSummary: [
          `revision=${loadedRevision}`,
          contentSha ? `content_sha256=${contentSha}` : null,
          `dirty=${authoring.dirty ? "true" : "false"}`,
          `content_status=${contentStatus}`,
          `phase=${authoring.phase}`,
        ].filter(Boolean).join("; "),
        warnings: authoring.error ? [authoring.error] : [],
      },
      updatedAt: new Date().toISOString(),
    });
  }, [
    authoring.dirty,
    authoring.error,
    authoring.phase,
    authoring.record,
    authoring.snapshot?.content_sha256,
    authoring.snapshot?.loaded_revision,
    publishSurfaceContext,
    rehydrateScope,
  ]);

  if (authoring.phase === "loading" || authoring.phase === "unloaded") {
    return (
      <main className="app-status" data-testid="build-surface-loading">
        <p>Loading worldbuilding source…</p>
      </main>
    );
  }

  if (authoring.phase === "load_error") {
    return (
      <main className="app-status app-error" data-testid="build-surface-error">
        <h1>{BUILD_SURFACE_LABEL}</h1>
        <p>{authoring.error ?? "Unable to load worldbuilding source."}</p>
      </main>
    );
  }

  if (authoring.phase === "conflict") {
    return (
      <main className="app-status app-error" data-testid="build-surface-conflict">
        <h1>{BUILD_SURFACE_LABEL}</h1>
        <p>{authoring.reconciliation?.conflictReason ?? "Local draft conflicts with server content."}</p>
        <button type="button" onClick={() => void authoring.reloadFromSnapshot()}>
          Reload from server
        </button>
        <button type="button" onClick={() => void authoring.discardLocalDraft()}>
          Discard local draft
        </button>
      </main>
    );
  }

  return (
    <main className="build-surface-shell" data-testid="build-surface-shell">
      <header className="build-surface-header">
        <h1>{authoring.record?.title ?? BUILD_SURFACE_LABEL}</h1>
        <p data-testid="build-document-status">{authoring.statusLabel}</p>
        <p data-testid="build-authoring-status">{authoring.statusLabel}</p>
        {authoring.error ? (
          <p role="alert" data-testid="build-save-error">{authoring.error}</p>
        ) : null}
        {authoring.record?.document_class ? (
          <p data-testid="build-document-class">{authoring.record.document_class}</p>
        ) : null}
      </header>

      <section className="build-surface-editor">
        <MarkdownEditorCore
          documentKey={authoring.documentKey}
          content={authoring.editorContent}
          onEditorChange={authoring.setEditor}
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
