import { WorkspaceTrashControl } from "../workspaceLifecycle/WorkspaceTrashControl";
import { useSelectedWorld } from "../selectedWorld/SelectedWorldContext";
import { BuildDraftRecovery } from "./buildMarkdownCanvasAdapter";
import { BUILD_STUDIO_ACTION, type BuildStudioAction } from "./buildStudioActions";
import { useEffect, useMemo, type Ref } from "react";

import { buildBuildSurfaceIdentity } from "../agentInteraction/projectionSurfacePublication";
import { formatReviewCampaignLabel } from "../graphLens/sessionCampaignContext";
import {
  DOCUMENT_METADATA_UPDATE_COMMAND_ID,
  DOCUMENT_SAVE_COMMAND_ID,
} from "../markdownCanvas/markdownCanvasTypes";
import { useOptionalMarkdownCanvasSession } from "../markdownCanvas/MarkdownCanvasSession";
import { DurableSaveStatus } from "../components/DurableSaveStatus";
import { buildSurfaceInteractionIdentity } from "../surfaceInteraction/surfaceIdentity";
import {
  SurfaceContextBadge,
  SurfaceContextModule,
  SurfaceContextStatus,
  SurfaceContextValue,
  useSurfaceContextContribution,
} from "../surfaceInteraction/contextHost";
import { BuildDocumentCreateControl } from "./BuildDocumentCreateControl";
import { BuildDocumentRenameControl } from "./BuildDocumentRenameControl";
import { BuildDocumentSelector } from "./BuildDocumentSelector";
import { buildSavedAt, buildSaveStateFor } from "./useBuildAutosave";
import type { BuildWorkspaceDocumentController } from "./useBuildWorkspaceDocumentController";

export type BuildSurfaceContextProps = Pick<
  BuildWorkspaceDocumentController,
  | "activeRecord"
  | "activeDocumentId"
  | "documents"
  | "listStatus"
  | "switching"
  | "switchError"
  | "creating"
  | "createError"
  | "activationError"
  | "importError"
  | "pendingImportDocumentId"
  | "selectDocument"
  | "createDocument"
  | "importSourceDocument"
  | "retryImportSource"
  | "retryCreatedDocument"
  | "refreshDocuments"
  | "destinationOptions"
  | "suggestedDestinationValue"
  | "suggestedCreateCampaignId"
> & { extractionTargetRef?: Ref<HTMLDivElement> };

export function BuildSurfaceContext({
  activeRecord,
  activeDocumentId,
  documents,
  listStatus,
  switching,
  switchError,
  creating,
  createError,
  activationError,
  importError,
  pendingImportDocumentId,
  selectDocument,
  createDocument,
  importSourceDocument,
  retryImportSource,
  retryCreatedDocument,
  refreshDocuments,
  destinationOptions,
  suggestedDestinationValue,
  suggestedCreateCampaignId,
  extractionTargetRef,
}: BuildSurfaceContextProps) {
  const session = useOptionalMarkdownCanvasSession();
  const selectedWorld = useSelectedWorld();
  const trashWorldId = selectedWorld.kind === "managed" ? selectedWorld.worldId : null;
  useEffect(() => {
    const open = (event: Event) => {
      if ((event as CustomEvent<BuildStudioAction>).detail === "open") {
        document.querySelector<HTMLSelectElement>(".build-document-selector--context select")?.focus();
      }
    };
    window.addEventListener(BUILD_STUDIO_ACTION, open);
    return () => window.removeEventListener(BUILD_STUDIO_ACTION, open);
  }, []);

  const surfaceIdentity = useMemo(() => {
    if (activeDocumentId) {
      return buildBuildSurfaceIdentity({ documentId: activeDocumentId });
    }
    return buildSurfaceInteractionIdentity({
      surfaceId: "build",
      instanceParts: ["build", "empty"],
    });
  }, [activeDocumentId]);

  // Live Canvas record wins for title/status when admitted; controller is preflight only.
  const liveRecord = session?.record ?? activeRecord;
  const displayTitle = liveRecord?.title ?? activeRecord?.title ?? null;
  const authoringStatusLabel = session?.statusLabel ?? null;
  const campaignId = liveRecord?.campaign_id ?? activeRecord?.campaign_id ?? null;
  const documentClass = liveRecord?.document_class ?? activeRecord?.document_class ?? null;
  const campaignBadge = campaignId
    ? formatReviewCampaignLabel(campaignId).replace(/^Longmont /, "")
    : null;

  const metadataBusy =
    session?.activeCommand?.id === DOCUMENT_METADATA_UPDATE_COMMAND_ID;
  const saveBusy = session?.activeCommand?.id === DOCUMENT_SAVE_COMMAND_ID;
  const documentMutationBusy = metadataBusy || saveBusy || switching || creating;
  const renameAdmitted = Boolean(session?.lookupAdmission("editable").ok);

  const content = useMemo(
    () => (
      <SurfaceContextModule label="" className="build-surface-context">
        <div className="build-surface-context__row">
          {activeDocumentId && liveRecord ? (
            <>
              <span data-testid="build-canvas-title" hidden>
                {displayTitle}
              </span>
              <BuildDocumentSelector
                documents={documents}
                listStatus={listStatus}
                activeDocumentId={activeDocumentId}
                activeRecord={liveRecord}
                preferredCampaignId={campaignId}
                switching={documentMutationBusy}
                onSelect={selectDocument}
              />
              {authoringStatusLabel ? (
                <>
                  <SurfaceContextStatus
                    data-testid="build-document-status"
                    className="build-surface-context__save-status"
                    tone={/unsaved|error|fail/i.test(authoringStatusLabel) ? "warning" : "neutral"}
                  >
                    {session ? <DurableSaveStatus state={buildSaveStateFor(session)} savedAt={buildSavedAt(session)} /> : authoringStatusLabel}
                  </SurfaceContextStatus>
                  <span data-testid="build-authoring-status" hidden>
                    {authoringStatusLabel}
                  </span>
                </>
              ) : null}
              {session ? <button type="button" className="build-navbar-save" data-testid="build-navbar-save"
                disabled={session.saveDisabled || documentMutationBusy}
                title={documentMutationBusy ? "Wait for the current document action to finish." : session.saveDisabledReason ?? undefined}
                aria-describedby={session.saveDisabled && session.dirty ? "build-save-reason" : undefined}
                onClick={() => void session.saveMarkdown()}>{saveBusy ? "Saving…" : "Save"}</button> : null}
              {session?.saveDisabled && session.dirty && session.saveDisabledReason ? <span id="build-save-reason" role="status">{session.saveDisabledReason}</span> : null}
              {session?.dirty || session?.draftRecoveryAvailable ? <BuildDraftRecovery session={session!} /> : null}
            </>
          ) : (
            <>
              <SurfaceContextValue>No source loaded</SurfaceContextValue>
              <BuildDocumentSelector
                documents={documents}
                listStatus={listStatus}
                activeDocumentId={null}
                activeRecord={null}
                preferredCampaignId={suggestedCreateCampaignId}
                switching={switching || creating}
                onSelect={selectDocument}
              />
            </>
          )}
          <details className="build-source-actions">
            <summary>Source actions</summary>
            <div className="build-source-actions__menu">
              {campaignBadge ? <SurfaceContextBadge>{campaignBadge}</SurfaceContextBadge> : null}
              {documentClass ? <SurfaceContextBadge>{documentClass}</SurfaceContextBadge> : null}
              {session ? (
                <BuildDocumentRenameControl
                  currentTitle={displayTitle ?? ""}
                  renaming={metadataBusy}
                  disabled={!renameAdmitted || (documentMutationBusy && !metadataBusy)}
                  onRename={async (title) => {
                    const result = await session.updateDocumentMetadata({ title });
                    if (result.ok) {
                      refreshDocuments();
                    }
                    return result;
                  }}
                />
              ) : null}
            </div>
          </details>
          {trashWorldId ? <WorkspaceTrashControl worldId={trashWorldId}
            current={liveRecord && activeDocumentId ? {kind:"document", id:activeDocumentId, title:displayTitle ?? "Build document", surface:"build", revision:liveRecord.revision} : null}
            blocked={documentMutationBusy || !session || session.dirty || buildSaveStateFor(session) !== "saved"}
            onTrashed={() => window.location.assign(`/build?world=${encodeURIComponent(trashWorldId)}`)} onRestored={refreshDocuments} /> : null}
          {activeDocumentId && extractionTargetRef ? (
            <div className="build-extraction-slot" ref={extractionTargetRef} data-testid="build-extraction-slot" />
          ) : null}
          <BuildDocumentCreateControl
            destinationOptions={destinationOptions}
            suggestedDestinationValue={suggestedDestinationValue}
            creating={creating}
            createError={createError}
            activationError={activationError}
            importError={importError}
            pendingImportDocumentId={pendingImportDocumentId}
            onSubmit={createDocument}
            onImportSubmit={importSourceDocument}
            onRetryOpen={activationError ? retryCreatedDocument : undefined}
            onRetryImport={importError ? retryImportSource : undefined}
            disabled={documentMutationBusy}
          />
        </div>
        {listStatus === "error" ? (
          <SurfaceContextStatus tone="error">
            Document list unavailable.{" "}
            <button type="button" className="build-surface-context__retry" onClick={refreshDocuments}>
              Retry
            </button>
          </SurfaceContextStatus>
        ) : null}
        {switching ? <SurfaceContextStatus>Switching…</SurfaceContextStatus> : null}
        {switchError ? (
          <SurfaceContextStatus tone="error">{switchError}</SurfaceContextStatus>
        ) : null}
      </SurfaceContextModule>
    ),
    [
      activationError,
      activeDocumentId,
      authoringStatusLabel,
      campaignBadge,
      campaignId,
      createDocument,
      createError,
      creating,
      destinationOptions,
      displayTitle,
      extractionTargetRef,
      documentClass,
      documentMutationBusy,
      documents,
      importError,
      importSourceDocument,
      listStatus,
      liveRecord,
      metadataBusy,
      pendingImportDocumentId,
      refreshDocuments,
      renameAdmitted,
      retryCreatedDocument,
      retryImportSource,
      selectDocument,
      saveBusy,
      session,
      suggestedCreateCampaignId,
      suggestedDestinationValue,
      switchError,
      switching,
      trashWorldId,
    ],
  );

  useSurfaceContextContribution({
    id: "build-document",
    order: 10,
    surfaceIdentity,
    content,
  });

  return null;
}
