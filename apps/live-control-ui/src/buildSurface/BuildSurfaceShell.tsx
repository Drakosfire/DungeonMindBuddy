import { useEffect, useMemo, useRef } from "react";

import type { AppChromeTools } from "../chrome/AppChrome";
import { MarkdownCanvas } from "../markdownCanvas/MarkdownCanvas";
import { useMarkdownCanvasSession } from "../markdownCanvas/MarkdownCanvasSession";
import { useAgentInteraction } from "../agentInteraction/useAgentInteraction";
import { buildBuildSurfaceIdentity } from "../agentInteraction/projectionSurfacePublication";
import type { ProjectionSurfacePublication } from "../agentInteraction/projectionSurfacePublication";
import { PlanGraphReferenceResolverProvider } from "../planSurface/reference/usePlanGraphReferenceResolver";
import type { SurfaceConfig } from "../planSurface/types";
import { useBuildMarkdownCanvasSlots } from "./buildMarkdownCanvasAdapter";
import { BuildGraphReferenceShell } from "./BuildGraphReferenceShell";
import { BUILD_SURFACE_LABEL } from "./buildSurfaceConfig";
import { createBuildSurfaceConfig } from "./createBuildSurfaceConfig";

/** Rejected authority diagnostics stay in the page UI; Agent Interaction gets no UUID/rev/path/hash. */
export const BUILD_AUTHORITY_REJECTION_AMBIENT = "Document rejected by Build authority";

interface BuildSurfaceShellProps {
  onEditorToolsChange?: (tools: AppChromeTools | null) => void;
  isEditDockOpen?: boolean;
  onEditDockOpenChange?: (open: boolean) => void;
}

function BuildSurfaceBoundShell({
  config,
  onEditorToolsChange,
  slots,
  isEditDockOpen,
  onEditDockOpenChange,
}: {
  config: SurfaceConfig;
  onEditorToolsChange?: (tools: AppChromeTools | null) => void;
  slots: ReturnType<typeof useBuildMarkdownCanvasSlots>;
  isEditDockOpen?: boolean;
  onEditDockOpenChange?: (open: boolean) => void;
}) {
  return (
    /*
     * Reuse PlanGraphReferenceResolverProvider with a minimal session descriptor
     * (campaign from workspace record, memorySession null) so world-graph search
     * works without Plan prep-session policy or PlanGraphLoadPanel.
     */
    <PlanGraphReferenceResolverProvider sessionDescriptor={config.sessionDescriptor}>
      <div className="build-surface-layout plan-surface-layout">
        <div className="plan-surface-main">
          <BuildGraphReferenceShell
            slots={slots}
            onEditorToolsChange={onEditorToolsChange}
            isEditDockOpen={isEditDockOpen}
            onEditDockOpenChange={onEditDockOpenChange}
          />
        </div>
      </div>
    </PlanGraphReferenceResolverProvider>
  );
}

/**
 * Build document chrome: Agent Interaction publication + shared MarkdownCanvas.
 * Document authority lives on MarkdownCanvasSession (provider is owned by BuildSurfacePage).
 */
export function BuildSurfaceShell({
  onEditorToolsChange,
  isEditDockOpen,
  onEditDockOpenChange,
}: BuildSurfaceShellProps) {
  const session = useMarkdownCanvasSession();
  const slots = useBuildMarkdownCanvasSlots();
  const {
    rehydrateScope,
    publishSurfaceContext,
    publishProjectionSurface,
    updateProjectionSurfaceConfig,
  } = useAgentInteraction();
  const lastAcceptedCampaignRef = useRef<string>("build");

  const surfaceConfig = useMemo(
    () => (session.record ? createBuildSurfaceConfig(session.record) : null),
    [
      session.record?.campaign_id,
      session.record?.content_status,
      session.record?.document_id,
      session.record?.revision,
      session.record?.target_relpath,
      session.record?.title,
      session.record,
    ],
  );

  const graphReferenceReady =
    Boolean(session.record)
    && session.phase !== "loading"
    && session.phase !== "unloaded"
    && session.phase !== "load_error"
    && session.phase !== "conflict";

  const publication = useMemo((): ProjectionSurfacePublication | null => {
    if (!graphReferenceReady || !surfaceConfig || !session.record) return null;
    return {
      identity: buildBuildSurfaceIdentity({ documentId: session.record.document_id }),
      config: surfaceConfig,
    };
  }, [graphReferenceReady, session.record, surfaceConfig]);

  const publicationInstanceKey = publication?.identity.instanceKey ?? null;
  const publicationRef = useRef(publication);
  publicationRef.current = publication;

  useEffect(() => {
    if (!publicationRef.current) return;
    return publishProjectionSurface(publicationRef.current);
  }, [publicationInstanceKey, publishProjectionSurface]);

  useEffect(() => {
    if (!publication) return;
    updateProjectionSurfaceConfig(publication);
  }, [publication, updateProjectionSurfaceConfig]);

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

  if (graphReferenceReady && surfaceConfig) {
    return (
      <BuildSurfaceBoundShell
        config={surfaceConfig}
        onEditorToolsChange={onEditorToolsChange}
        slots={slots}
        isEditDockOpen={isEditDockOpen}
        onEditDockOpenChange={onEditDockOpenChange}
      />
    );
  }

  return <MarkdownCanvas slots={slots} />;
}
