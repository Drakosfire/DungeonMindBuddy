import { useEffect, useMemo, useRef, useState } from "react";

import { DocumentConversationDock, type PlanConversationPresentationHosts } from "../planSurface/components/PlanConversationDockAdapter";
import { usePublishWorldBuildConversation, type SavedWorldBuildConversationContext } from "../agentInteraction/WorldAgentConversation";
import type { AppChromeToolsGeneration } from "../chrome/AppChrome";
import { getBuildSourceNavigation } from "../api/liveApi";
import { MarkdownCanvas } from "../markdownCanvas/MarkdownCanvas";
import {
  useMarkdownCanvasSession,
  type MarkdownCanvasSessionValue,
} from "../markdownCanvas/MarkdownCanvasSession";
import type { MarkdownCanvasSlots } from "../markdownCanvas/MarkdownCanvas";
import { useAgentInteraction } from "../agentInteraction/useAgentInteraction";
import { parseBuildSourceNavigationQuery } from "../sourceNavigation/sourceNavigation";
import { BuildGraphObjectContext, parseBuildGraphPointerFromLocation } from "./BuildGraphObjectContext";
import { BUILD_DOCUMENT_SAVE_COMMAND_ID } from "./buildDocumentCommands";
import { useBuildMarkdownCanvasSlots } from "./buildMarkdownCanvasAdapter";
import { BUILD_SURFACE_LABEL } from "./buildSurfaceConfig";
import {
  BuildSourceReader,
  type BuildSourceNavigationTarget,
} from "./BuildSourceReader";

/** Rejected authority diagnostics stay in the page UI; Agent Interaction gets no UUID/rev/path/hash. */
export const BUILD_AUTHORITY_REJECTION_AMBIENT = "Document rejected by Build authority";

function isPresentableSourcePhase(phase: string): boolean {
  return !["unloaded", "loading", "load_error", "conflict"].includes(phase);
}

const IDLE_SOURCE_NAVIGATION_TARGET: BuildSourceNavigationTarget = { status: "none" };

function BuildPresentableSourceView({
  session,
  editSlots,
  navigationTarget,
  onEditorTools,
}: {
  session: MarkdownCanvasSessionValue;
  editSlots: MarkdownCanvasSlots;
  navigationTarget: BuildSourceNavigationTarget;
  onEditorTools?: (tools: AppChromeToolsGeneration | null) => void;
}) {
  const [outlineVersion, setOutlineVersion] = useState(0);
  useEffect(() => {
    const editor = session.editor;
    if (!editor) return;
    const update = () => setOutlineVersion(value => value + 1);
    editor.on("update", update);
    editor.on("selectionUpdate", update);
    return () => { editor.off("update", update); editor.off("selectionUpdate", update); };
  }, [session.editor]);

  useEffect(() => {
    const editor = session.editor;
    const headings: { position: number; level: number; text: string }[] = [];
    editor?.state.doc.descendants((node, position) => {
      if (node.type.name === "heading") headings.push({ position, level: node.attrs.level, text: node.textContent });
    });
    onEditorTools?.({ target: { kind: "document", id: session.record!.document_id },
      tools: { sections: [{ id: "build-document", title: "Document", defaultOpen: true, actions: [],
        panel: <><div className="build-formatting" role="group" aria-label="Text formatting">
          <button type="button" disabled={!editor} aria-pressed={editor?.isActive("bold") ?? false}
            onClick={() => editor?.chain().focus().toggleBold().run()}>Bold</button>
          <button type="button" disabled={!editor} aria-pressed={editor?.isActive("italic") ?? false}
            onClick={() => editor?.chain().focus().toggleItalic().run()}>Italic</button>
          <button type="button" disabled={!editor} onClick={() => editor?.chain().focus().toggleHeading({ level: 2 }).run()}>Heading</button>
          <button type="button" disabled={!editor?.can().undo()} onClick={() => editor?.chain().focus().undo().run()}>Undo</button>
          <button type="button" disabled={!editor?.can().redo()} onClick={() => editor?.chain().focus().redo().run()}>Redo</button>
        </div><nav className="markdown-document-outline" aria-label="On this page">
          {headings.length ? <ol>{headings.map(heading => <li key={heading.position}
            style={{ paddingInlineStart: `${Math.min(heading.level - 1, 2) * 0.75}rem` }}>
            <button type="button" onClick={() => editor?.chain().focus().setTextSelection(heading.position + 1).scrollIntoView().run()}>
              {heading.text || "Untitled section"}
            </button>
          </li>)}</ol> : <p>No headings in this document.</p>}
        </nav></> }] } });
    return () => onEditorTools?.(null);
  }, [onEditorTools, session.editor, session.record?.document_id, outlineVersion]);

  return <div className="build-surface-shell" data-testid="build-surface-shell">
    {navigationTarget.status !== "none" ? <details className="build-source-evidence" open>
      <summary>Saved evidence passage</summary>
      <BuildSourceReader showOutline={false} title={session.record!.title}
        markdown={session.snapshot!.markdown} dirty={session.dirty} navigationTarget={navigationTarget} />
    </details> : null}
    <MarkdownCanvas slots={editSlots} />
  </div>;
}

function BuildConversationBinding({ source, hosts }: { source: SavedWorldBuildConversationContext | null; hosts: PlanConversationPresentationHosts }) {
  usePublishWorldBuildConversation(source, hosts);
  return null;
}

/** Build's no-document landing is still a framed projection with the same conversation dock. */
export function BuildEmptyLanding({ loadStatus }: { loadStatus: "idle" | "loading" | "ready" | "empty" | "error" }) {
  const isLoading = loadStatus === "idle" || loadStatus === "loading";
  const hasError = loadStatus === "error";
  const reader = (
    <div className="build-surface-with-graph-context document-projection" data-document-surface="build">
      <main
        className={`build-surface-shell build-empty-landing${hasError ? " build-empty-landing--error" : ""}`}
        data-testid="build-surface-empty"
        aria-busy={isLoading}
      >
        <div className="build-empty-landing__hero">
          <span className="build-empty-landing__mark" aria-hidden="true">✧</span>
          <p className="build-empty-landing__eyebrow">BUILD · WORLDBUILDING</p>
          <h1>{hasError ? "That source could not be opened." : "Give this world a place to begin."}</h1>
          <p className="build-empty-landing__intro">
            {hasError
              ? "Choose another source above, or start a fresh page from Source actions."
              : "Open an existing source, start a blank page, or bring in lore you already have. Your work will live here as an editable document."}
          </p>
        </div>
        {isLoading ? (
          <p className="build-empty-landing__status" role="status">Finding your worldbuilding sources…</p>
        ) : hasError ? (
          <p className="build-empty-landing__status" role="alert">The requested source is unavailable. You can choose another from the Build bar.</p>
        ) : (
          <div className="build-empty-landing__paths" aria-label="Ways to begin">
            <section>
              <span>01 · OPEN</span>
              <h2>Choose a source</h2>
              <p>Return to a saved worldbuilding document from the source selector above.</p>
            </section>
            <section>
              <span>02 · CREATE</span>
              <h2>Start a blank page</h2>
              <p>Open Source actions in the Build bar and choose New source.</p>
            </section>
            <section>
              <span>03 · IMPORT</span>
              <h2>Bring in your lore</h2>
              <p>Use Import source to bring existing Markdown into this world.</p>
            </section>
          </div>
        )}
        <p className="build-empty-landing__footnote">The document, world tools, and conversation share this workspace.</p>
      </main>
    </div>
  );

  return (
    <div className="build-workspace-projection">
      <DocumentConversationDock surface="build" contextLabel="Worldbuilding source" reader={reader}>
        {hosts => <BuildConversationBinding source={null} hosts={hosts} />}
      </DocumentConversationDock>
    </div>
  );
}

/**
 * Build document workspace: shared authoring and conversation publication.
 * Document authority lives on MarkdownCanvasSession (provider is owned by BuildSurfacePage).
 * Saved evidence remains separate from the directly editable working document.
 */
export function BuildSurfaceShell({ onEditorTools }: { onEditorTools?: (tools: AppChromeToolsGeneration | null) => void }) {
  const session = useMarkdownCanvasSession();
  const { rehydrateScope, publishSurfaceContext, surfaceInteractionPublication } = useAgentInteraction();
  const hasSharedEditSave = (surfaceInteractionPublication?.editCommands ?? []).some(
    (command) => command.id === BUILD_DOCUMENT_SAVE_COMMAND_ID,
  );
  const slots = useBuildMarkdownCanvasSlots({ hideFooterSave: hasSharedEditSave });
  const conversationContext = useMemo(() => session.record?.world_id && session.record.content_status === "committed"
    && session.snapshot && isPresentableSourcePhase(session.phase) ? {
      worldId: session.record.world_id, documentId: session.record.document_id,
      revision: session.snapshot.loaded_revision, contentSha256: session.snapshot.content_sha256,
      surfaceInstanceId: `build:${session.record.document_id}`, title: session.record.title, dirty: session.dirty,
    } : null, [session.record, session.snapshot, session.phase, session.dirty]);
  const lastAcceptedCampaignRef = useRef<string>("build");
  const [navigationTarget, setNavigationTarget] = useState<BuildSourceNavigationTarget>(
    IDLE_SOURCE_NAVIGATION_TARGET,
  );

  const isPresentable =
    session.record != null
    && session.snapshot != null
    && isPresentableSourcePhase(session.phase);

  useEffect(() => {
    if (session.record?.campaign_id) {
      lastAcceptedCampaignRef.current = session.record.campaign_id;
    }
  }, [session.record?.campaign_id]);

  useEffect(() => {
    const publishNeutral = (ambientSummary: string) => {
      rehydrateScope({
        campaignId: lastAcceptedCampaignRef.current || "build",
        sessionNumber: null,
        surfaceId: "build",
        documentId: null,
      });
      publishSurfaceContext({
        surfaceId: "build",
        label: BUILD_SURFACE_LABEL,
        campaignId: null,
        documentId: null,
        sessionNumber: null,
        ambientSummary,
        sourceEnvelope: null,
        updatedAt: new Date().toISOString(),
      });
    };

    if (session.phase === "unloaded" || session.phase === "loading") {
      publishNeutral("Loading worldbuilding source…");
      return;
    }

    if (session.phase === "load_error") {
      publishNeutral(BUILD_AUTHORITY_REJECTION_AMBIENT);
      return;
    }

    // No accepted record (including conflict after quarantined snapshot) must not
    // retain a prior UUID/path/hash in Agent Interaction.
    if (!session.record) {
      publishNeutral(
        session.phase === "conflict"
          ? "Document reconciliation required"
          : "Build surface idle",
      );
      return;
    }

    rehydrateScope({
      campaignId: session.record.campaign_id,
      sessionNumber: null,
      surfaceId: "build",
      documentId: session.record.document_id,
    });
    const contentStatus = session.record.content_status;
    const loadedRevision = session.snapshot?.loaded_revision ?? session.record.revision;
    const contentSha = session.snapshot?.content_sha256 ?? null;
    publishSurfaceContext({
      surfaceId: "build",
      label: `${BUILD_SURFACE_LABEL} · ${session.record.title}`,
      campaignId: session.record.campaign_id,
      documentId: session.record.document_id,
      sessionNumber: null,
      ambientSummary: [
        session.record.document_class ?? "worldbuilding source",
        `rev ${loadedRevision}`,
        session.dirty ? "local dirty" : "local clean",
        contentStatus === "committed" ? "durable committed" : "durable draft",
        `phase ${session.phase}`,
      ].join(" · "),
      sourceEnvelope: {
        schema: "agent_interaction_source_envelope_v1",
        artifactRefs: [
          { kind: "workspace_document", value: session.record.document_id },
          ...(session.record.target_relpath
            ? [{ kind: "path" as const, value: session.record.target_relpath }]
            : []),
        ],
        provenanceSummary: [
          `revision=${loadedRevision}`,
          contentSha ? `content_sha256=${contentSha}` : null,
          `dirty=${session.dirty ? "true" : "false"}`,
          `content_status=${contentStatus}`,
          `phase=${session.phase}`,
        ].filter(Boolean).join("; "),
        warnings: session.error ? [session.error] : [],
      },
      updatedAt: new Date().toISOString(),
    });
  }, [
    session.dirty,
    session.error,
    session.phase,
    session.record,
    session.snapshot?.content_sha256,
    session.snapshot?.loaded_revision,
    publishSurfaceContext,
    rehydrateScope,
  ]);

  // Leaving Build (or remounting for a new documentId) must not leave prior accepted context.
  useEffect(() => {
    return () => {
      rehydrateScope({
        campaignId: lastAcceptedCampaignRef.current || "build",
        sessionNumber: null,
        surfaceId: "build",
        documentId: null,
      });
      publishSurfaceContext({
        surfaceId: "build",
        label: BUILD_SURFACE_LABEL,
        campaignId: null,
        documentId: null,
        sessionNumber: null,
        ambientSummary: "Build surface idle",
        sourceEnvelope: null,
        updatedAt: new Date().toISOString(),
      });
    };
  }, [publishSurfaceContext, rehydrateScope]);

  const sourceNavigationQuery = parseBuildSourceNavigationQuery(window.location.search);
  const acceptedDocumentId = session.record?.document_id ?? null;
  const savedContentSha256 = session.snapshot?.content_sha256 ?? null;

  useEffect(() => {
    if (!sourceNavigationQuery) {
      setNavigationTarget(IDLE_SOURCE_NAVIGATION_TARGET);
      return;
    }

    const targetKey = `${sourceNavigationQuery.sourceArtifactId}:${sourceNavigationQuery.sourceSpanRefId}`;
    if (!acceptedDocumentId) {
      setNavigationTarget({ status: "pending", targetKey });
      return;
    }

    let cancelled = false;
    setNavigationTarget({ status: "pending", targetKey });

    void getBuildSourceNavigation(sourceNavigationQuery)
      .then((result) => {
        if (cancelled) return;

        const resolvedTargetKey = `${result.sourceArtifactId}:${result.sourceSpanRefId}`;
        if (result.documentId !== acceptedDocumentId) {
          setNavigationTarget({
            status: "document_mismatch",
            message:
              result.message
              || "This source passage belongs to a different Build document than the one currently open.",
            targetKey: resolvedTargetKey,
          });
          return;
        }

        const digestMatchesSaved =
          savedContentSha256 != null
          && result.currentContentSha256 === result.artifactContentSha256
          && savedContentSha256 === result.currentContentSha256;

        if (result.status === "stale" || !result.canHighlight || !digestMatchesSaved) {
          setNavigationTarget({
            status: "stale",
            message:
              result.message
              || "Source has changed since this evidence was admitted. The cited line range cannot be highlighted exactly.",
            targetKey: resolvedTargetKey,
          });
          return;
        }

        setNavigationTarget({
          status: "exact",
          startLine: result.startLine,
          endLine: result.endLine,
          targetKey: resolvedTargetKey,
        });
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setNavigationTarget({
          status: "error",
          message: error instanceof Error ? error.message : "Source navigation could not be resolved.",
          targetKey,
        });
      });

    return () => {
      cancelled = true;
    };
  }, [
    acceptedDocumentId,
    savedContentSha256,
    sourceNavigationQuery?.sourceArtifactId,
    sourceNavigationQuery?.sourceSpanRefId,
  ]);

  // Document-backed graph context must wait for an accepted record. While the
  // document is loading, conflicted, or rejected, session.record is null — mounting
  // then would skip scope admission and race a later rejection.
  const graphPointer = parseBuildGraphPointerFromLocation();
  const acceptedDocumentCampaignId = session.record?.campaign_id ?? null;

  const editSlots: MarkdownCanvasSlots = {
    ...slots,
    // Outer shell owns build-surface-shell when presentable; avoid nested duplicate.
    dataTestId: "build-surface-editor-shell",
    className: "build-surface-editor-shell",
  };

  const projection = (
    <div className="build-surface-with-graph-context document-projection" data-document-surface="build">
      {graphPointer && acceptedDocumentCampaignId ? (
        <BuildGraphObjectContext
          documentCampaignId={acceptedDocumentCampaignId}
          requireDocumentScope
        />
      ) : null}
      {!isPresentable ? (
        <MarkdownCanvas slots={slots} />
      ) : (
        <BuildPresentableSourceView
          key={session.record!.document_id}
          session={session}
          editSlots={editSlots}
          navigationTarget={navigationTarget}
          onEditorTools={onEditorTools}
        />
      )}
    </div>
  );
  return <div className="build-workspace-projection">
    <DocumentConversationDock surface="build" contextLabel={session.record?.title ?? "Worldbuilding source"} reader={projection}>
      {hosts => <BuildConversationBinding source={conversationContext} hosts={hosts} />}
    </DocumentConversationDock>
  </div>;
}
