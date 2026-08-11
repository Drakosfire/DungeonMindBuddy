import { useMemo } from "react";

import { buildBuildSurfaceIdentity } from "../agentInteraction/projectionSurfacePublication";
import { formatReviewCampaignLabel } from "../graphLens/sessionCampaignContext";
import { buildSurfaceInteractionIdentity } from "../surfaceInteraction/surfaceIdentity";
import {
  SurfaceContextBadge,
  SurfaceContextModule,
  SurfaceContextStatus,
  SurfaceContextValue,
  useSurfaceContextContribution,
} from "../surfaceInteraction/contextHost";
import { BuildDocumentCreateControl } from "./BuildDocumentCreateControl";
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
  | "authoringStatusLabel"
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
  authoringStatusLabel,
}: BuildSurfaceContextProps) {
  const surfaceIdentity = useMemo(() => {
    if (activeDocumentId) {
      return buildBuildSurfaceIdentity({ documentId: activeDocumentId });
    }
    return buildSurfaceInteractionIdentity({
      surfaceId: "build",
      instanceParts: ["build", "empty"],
    });
  }, [activeDocumentId]);

  const campaignBadge = activeRecord?.campaign_id
    ? formatReviewCampaignLabel(activeRecord.campaign_id).replace(/^Longmont /, "")
    : null;

  const content = useMemo(
    () => (
      <SurfaceContextModule label="DOCUMENT" className="build-surface-context">
        <div className="build-surface-context__row">
          {activeRecord ? (
            <>
              <span data-testid="build-canvas-title" hidden>
                {activeRecord.title}
              </span>
              <BuildDocumentSelector
                documents={documents}
                listStatus={listStatus}
                activeDocumentId={activeDocumentId}
                activeRecord={activeRecord}
                preferredCampaignId={activeRecord.campaign_id}
                switching={switching}
                onSelect={selectDocument}
              />
              {campaignBadge ? (
                <SurfaceContextBadge>{campaignBadge}</SurfaceContextBadge>
              ) : null}
              {activeRecord.document_class ? (
                <SurfaceContextBadge>{activeRecord.document_class}</SurfaceContextBadge>
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
                switching={switching}
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
            disabled={switching}
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
      activeDocumentId,
      activeRecord,
      activationError,
      authoringStatusLabel,
      campaignBadge,
      creatableCampaignIds,
      createDocument,
      createError,
      creating,
      documents,
      listStatus,
      refreshDocuments,
      retryCreatedDocument,
      selectDocument,
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
