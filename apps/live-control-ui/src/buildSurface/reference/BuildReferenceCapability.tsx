import { useCallback, useMemo } from "react";

import { usePublishSurfaceInteraction } from "../../agentInteraction/usePublishSurfaceInteraction";
import type { GraphReferenceSearchItem } from "../../graphReference/types";
import { useOptionalMarkdownCanvasSession } from "../../markdownCanvas/MarkdownCanvasSession";
import type { WorkspaceDocumentAuthoringPhase } from "../../workspaceDocument/workspaceDocumentAuthoringMachine";
import {
  buildBuildSurfaceInteractionPublication,
  type BuildReferenceContextBinding,
} from "./buildBuildSurfaceInteractionPublication";
import { resolveBuildGraphLens } from "./resolveBuildGraphLens";
import { useBuildWorldGraphProjection } from "./useBuildWorldGraphProjection";

const EMPTY_PUBLICATION_PHASES: ReadonlySet<WorkspaceDocumentAuthoringPhase> = new Set([
  "unloaded",
  "loading",
  "load_error",
  "conflict",
]);

function readBuildGraphLensParams(): {
  requestedCampaignId: string | null;
  requestedRevisionId: string | null;
} {
  if (typeof window === "undefined") {
    return { requestedCampaignId: null, requestedRevisionId: null };
  }
  const params = new URLSearchParams(window.location.search);
  return {
    requestedCampaignId: params.get("campaign")?.trim() || null,
    requestedRevisionId: params.get("graphRevision")?.trim() || null,
  };
}

export interface BuildReferenceCapabilityProps {
  documentId: string | null;
}

export function BuildReferenceCapability({ documentId }: BuildReferenceCapabilityProps) {
  const session = useOptionalMarkdownCanvasSession();
  const lensParams = useMemo(() => readBuildGraphLensParams(), [documentId]);

  const acceptedDocument = useMemo(() => {
    if (!documentId || !session || session.documentId !== documentId) return null;
    if (EMPTY_PUBLICATION_PHASES.has(session.phase)) return null;
    if (!session.record) return null;
    return {
      documentId: session.record.document_id,
      campaignId: session.record.campaign_id,
    };
  }, [documentId, session]);

  const lens = useMemo(() => {
    if (!acceptedDocument) {
      return {
        status: "invalid" as const,
        reason: "Build graph lens requires an accepted document.",
      };
    }
    return resolveBuildGraphLens({
      documentId: acceptedDocument.documentId,
      documentCampaignId: acceptedDocument.campaignId,
      requestedCampaignId: lensParams.requestedCampaignId,
      requestedRevisionId: lensParams.requestedRevisionId,
    });
  }, [acceptedDocument, lensParams.requestedCampaignId, lensParams.requestedRevisionId]);

  const projection = useBuildWorldGraphProjection({
    lens,
    documentIdentity: {
      documentId: acceptedDocument?.documentId ?? "",
      campaignId: acceptedDocument?.campaignId ?? "",
    },
  });

  const selectCampaign = useCallback((_campaignId: string) => {
    // URL lens write lands with search projection (nano7).
  }, []);

  const viewExact = useCallback((_item: GraphReferenceSearchItem) => {
    // Exact View lands with object projection (nano7).
  }, []);

  const referenceContext = useMemo<BuildReferenceContextBinding | null>(() => {
    if (!acceptedDocument) return null;
    return {
      schema: "dmb_build_reference_context_v1",
      documentId: acceptedDocument.documentId,
      documentCampaignId: acceptedDocument.campaignId,
      lens,
      projectionState: projection.state,
      projectionError: projection.error,
      requestedRevisionId: projection.requestedRevisionId,
      loadedRevisionId: projection.loadedRevisionId,
      items: projection.items,
      selectCampaign,
      viewExact,
    };
  }, [
    acceptedDocument,
    lens,
    projection.error,
    projection.items,
    projection.loadedRevisionId,
    projection.requestedRevisionId,
    projection.state,
    selectCampaign,
    viewExact,
  ]);

  const publication = useMemo(
    () =>
      buildBuildSurfaceInteractionPublication({
        documentId,
        acceptedDocument,
        referenceContext,
      }),
    [acceptedDocument, documentId, referenceContext],
  );

  usePublishSurfaceInteraction(publication);

  return null;
}
