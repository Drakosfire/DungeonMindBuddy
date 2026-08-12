import { useMemo } from "react";

import { buildBuildSurfaceIdentity } from "../agentInteraction/projectionSurfacePublication";
import { formatReviewCampaignLabel } from "../graphLens/sessionCampaignContext";
import {
  DOCUMENT_METADATA_UPDATE_COMMAND_ID,
  DOCUMENT_SAVE_COMMAND_ID,
} from "../markdownCanvas/markdownCanvasTypes";
import { useOptionalMarkdownCanvasSession } from "../markdownCanvas/MarkdownCanvasSession";
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
  | "selectDocument"
  | "createDocument"
  | "retryCreatedDocument"
  | "refreshDocuments"
  | "creatableCampaignIds"
  | "suggestedCreateCampaignId"
>;

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
  selectDocument,
  createDocument,
  retryCreatedDocument,
  refreshDocuments,
  creatableCampaignIds,
  suggestedCreateCampaignId,
}: BuildSurfaceContextProps) {
  const session = useOptionalMarkdownCanvasSession();

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
      <SurfaceContextModule label="DOCUMENT" className="build-surface-context">
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
              {campaignBadge ? (
                <SurfaceContextBadge>{campaignBadge}</SurfaceContextBadge>
              ) : null}
              {documentClass ? (
                <SurfaceContextBadge>{documentClass}</SurfaceContextBadge>
              ) : null}
              {authoringStatusLabel ? (
                <>
                  <SurfaceContextStatus
                    data-testid="build-document-status"
                    className="build-surface-context__save-status"
                    tone={/unsaved|error|fail/i.test(authoringStatusLabel) ? "warning" : "neutral"}
                  >
                    {authoringStatusLabel}
                  </SurfaceContextStatus>
                  <span data-testid="build-authoring-status" hidden>
                    {authoringStatusLabel}
                  </span>
                </>
              ) : null}
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
          <BuildDocumentCreateControl
            creatableCampaignIds={creatableCampaignIds}
            suggestedCampaignId={suggestedCreateCampaignId}
            creating={creating}
            createError={createError}
            activationError={activationError}
            onSubmit={createDocument}
            onRetryOpen={activationError ? retryCreatedDocument : undefined}
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
      creatableCampaignIds,
      createDocument,
      createError,
      creating,
      displayTitle,
      documentClass,
      documentMutationBusy,
      documents,
      listStatus,
      liveRecord,
      metadataBusy,
      refreshDocuments,
      renameAdmitted,
      retryCreatedDocument,
      selectDocument,
      session,
      suggestedCreateCampaignId,
      switchError,
      switching,
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
