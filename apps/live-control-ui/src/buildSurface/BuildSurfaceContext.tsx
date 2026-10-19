import { useOptionalAgentInteraction } from "../agentInteraction/AgentInteractionProvider";
import { BUILD_FIND_EXISTING_TOOL_ID } from "./reference/buildReferenceIds";
import { SurfaceNavbarIconButton } from "../surfaceInteraction/contextHost/SurfaceNavbarIconButton";
import { useWorkspaceInventoryVersion } from "../workspaceLifecycle/workspaceInventoryChange";
import { WorkspaceTrashControl } from "../workspaceLifecycle/WorkspaceTrashControl";
import { useSelectedWorld } from "../selectedWorld/SelectedWorldContext";
import { BuildDraftRecovery } from "./buildMarkdownCanvasAdapter";
import { BUILD_STUDIO_ACTION, requestBuildStudioAction, type BuildStudioAction } from "./buildStudioActions";
import { useEffect, useMemo, useRef, type Ref } from "react";

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
  SurfaceContextAction,
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
  const agentInteraction = useOptionalAgentInteraction();
  const openReferenceTool = agentInteraction?.openTool;
  const linkAvailable = agentInteraction?.surfaceInteractionPublication?.tools.some(tool => tool.id === BUILD_FIND_EXISTING_TOOL_ID && tool.availability.status === "enabled") ?? false;
  const selectedWorld = useSelectedWorld();
  const trashWorldId = selectedWorld.kind === "managed" ? selectedWorld.worldId : null;
  const trashInventoryVersion = useWorkspaceInventoryVersion(trashWorldId);
  const consumedTrashInventory = useRef<{worldId:string|null; version:number} | null>(null);
  useEffect(() => {
    if (trashInventoryVersion === 0 || (consumedTrashInventory.current?.worldId === trashWorldId
      && consumedTrashInventory.current.version === trashInventoryVersion)) return;
    // Mark consumed before refresh: the controller may return a new callback after its list update.
    consumedTrashInventory.current = {worldId:trashWorldId, version:trashInventoryVersion};
    refreshDocuments();
  }, [trashWorldId, trashInventoryVersion, refreshDocuments]);
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
  const needsRecovery = session?.phase === "conflict" || session?.exportedMarkdownAuthoritative === true;
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
              {session ? <SurfaceNavbarIconButton icon="save" label={saveBusy ? "Saving…" : "Save"} className="build-navbar-save" data-testid="build-navbar-save"
                disabled={session.saveDisabled || documentMutationBusy}
                title={documentMutationBusy ? "Wait for the current document action to finish." : (session.phase === "conflict" ? "Resolve the browser draft conflict before saving." : session.saveDisabledReason) ?? undefined}
                aria-describedby={needsRecovery && session.saveDisabled && session.dirty ? "build-save-reason" : undefined}
                onClick={() => void session.saveMarkdown()} /> : null}
              {needsRecovery && session ? <details className="surface-navbar-recovery">
                <summary>Draft recovery</summary><div className="surface-navbar-recovery__panel">
                  {session.saveDisabled && session.dirty && session.saveDisabledReason ? <p id="build-save-reason" role="status">{session.phase === "conflict" ? "The browser draft and saved document differ. Review conflicting copies to compare them and choose a working copy. Both complete copies are protected before anything is replaced." : session.saveDisabledReason}</p> : null}
                  <BuildDraftRecovery session={session} />
                </div>
              </details> : null}
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
              {!needsRecovery && session && (session.dirty || session.draftRecoveryAvailable || session.conflictRecovery?.protectedCopies) ?
                <details className="build-source-recovery"><summary>Draft and recovery copies</summary><BuildDraftRecovery session={session} /></details> : null}
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
          {activeDocumentId ? <>
            <SurfaceContextAction className="build-navbar-tool" aria-label="Link existing node" title="Link an existing graph node" disabled={!linkAvailable || !renameAdmitted || documentMutationBusy}
              onClick={() => { if (linkAvailable) openReferenceTool?.(BUILD_FIND_EXISTING_TOOL_ID); }}>Link node</SurfaceContextAction>
            <SurfaceContextAction className="build-navbar-tool" aria-label="Open Image Studio" title="Create or place an image" disabled={!renameAdmitted || documentMutationBusy}
              onClick={() => requestBuildStudioAction("image")}>Images</SurfaceContextAction>
          </> : null}
          {trashWorldId ? <WorkspaceTrashControl showTrash={false} worldId={trashWorldId}
            current={liveRecord && activeDocumentId ? {kind:"document", id:activeDocumentId, title:displayTitle ?? "Build document", surface:"build", revision:liveRecord.revision} : null}
            blocked={documentMutationBusy || !session || session.dirty || buildSaveStateFor(session) !== "saved"}
            onTrashed={() => window.location.assign(`/build?world=${encodeURIComponent(trashWorldId)}`)} /> : null}
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
      openReferenceTool,
      linkAvailable,
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
      needsRecovery,
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
