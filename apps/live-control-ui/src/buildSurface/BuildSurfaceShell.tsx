import { useEffect, useRef, useState } from "react";

import { MarkdownCanvas } from "../markdownCanvas/MarkdownCanvas";
import {
  useMarkdownCanvasSession,
  type MarkdownCanvasSessionValue,
} from "../markdownCanvas/MarkdownCanvasSession";
import type { MarkdownCanvasSlots } from "../markdownCanvas/MarkdownCanvas";
import { useAgentInteraction } from "../agentInteraction/useAgentInteraction";
import { BuildGraphObjectContext, parseBuildGraphPointerFromLocation } from "./BuildGraphObjectContext";
import { BUILD_DOCUMENT_SAVE_COMMAND_ID } from "./buildDocumentCommands";
import { useBuildMarkdownCanvasSlots } from "./buildMarkdownCanvasAdapter";
import { BUILD_SURFACE_LABEL } from "./buildSurfaceConfig";
import { BuildSourceReader } from "./BuildSourceReader";

/** Rejected authority diagnostics stay in the page UI; Agent Interaction gets no UUID/rev/path/hash. */
export const BUILD_AUTHORITY_REJECTION_AMBIENT = "Document rejected by Build authority";

export type BuildSourceViewMode = "read" | "edit";

function isPresentableSourcePhase(phase: string): boolean {
  return (
    phase !== "unloaded"
    && phase !== "loading"
    && phase !== "load_error"
    && phase !== "conflict"
  );
}

function isEffectivelyEmptyMarkdown(markdown: string): boolean {
  return markdown.trim().length === 0;
}

export function initialSourceViewMode(args: {
  dirty: boolean;
  markdown: string;
}): BuildSourceViewMode {
  if (args.dirty) return "edit";
  if (isEffectivelyEmptyMarkdown(args.markdown)) return "edit";
  return "read";
}

/**
 * Ephemeral Read/Edit chrome for one admitted document.
 * Mounted with `key={documentId}` so the initial mode decision runs once per document.
 */
function BuildPresentableSourceView({
  session,
  editSlots,
}: {
  session: MarkdownCanvasSessionValue;
  editSlots: MarkdownCanvasSlots;
}) {
  const [sourceViewMode, setSourceViewMode] = useState<BuildSourceViewMode>(() =>
    initialSourceViewMode({
      dirty: session.dirty,
      markdown: session.snapshot?.markdown ?? "",
    }),
  );

  return (
    <div className="build-surface-shell" data-testid="build-surface-shell">
      <div
        className="build-source-mode-toggle"
        role="group"
        aria-label="Source view mode"
        data-testid="build-source-mode-toggle"
      >
        <button
          type="button"
          className="build-source-mode-toggle__button"
          aria-label="Read source"
          aria-pressed={sourceViewMode === "read"}
          data-testid="build-source-mode-read"
          onClick={() => setSourceViewMode("read")}
        >
          Read
        </button>
        <button
          type="button"
          className="build-source-mode-toggle__button"
          aria-label="Edit source"
          aria-pressed={sourceViewMode === "edit"}
          data-testid="build-source-mode-edit"
          onClick={() => setSourceViewMode("edit")}
        >
          Edit
        </button>
      </div>
      {sourceViewMode === "read" ? (
        <BuildSourceReader
          title={session.record!.title}
          markdown={session.snapshot!.markdown}
          dirty={session.dirty}
        />
      ) : (
        <MarkdownCanvas slots={editSlots} />
      )}
    </div>
  );
}

/**
 * Build document chrome: Agent Interaction publication + Read/Edit composition.
 * Document authority lives on MarkdownCanvasSession (provider is owned by BuildSurfacePage).
 * Read renders exact saved snapshot Markdown; Edit preserves MarkdownCanvas authoring.
 */
export function BuildSurfaceShell() {
  const session = useMarkdownCanvasSession();
  const { rehydrateScope, publishSurfaceContext, surfaceInteractionPublication } = useAgentInteraction();
  const hasSharedEditSave = (surfaceInteractionPublication?.editCommands ?? []).some(
    (command) => command.id === BUILD_DOCUMENT_SAVE_COMMAND_ID,
  );
  const slots = useBuildMarkdownCanvasSlots({ hideFooterSave: hasSharedEditSave });
  const lastAcceptedCampaignRef = useRef<string>("build");

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

  return (
    <div className="build-surface-with-graph-context">
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
        />
      )}
    </div>
  );
}
