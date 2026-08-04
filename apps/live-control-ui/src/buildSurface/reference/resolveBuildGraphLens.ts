import {
  classifyBuildDocumentScope,
  getCampaignIdsForWorld,
} from "../../worldGraph/worldGraphSurfaceContext";

export type BuildGraphRevisionPolicy =
  | { kind: "head" }
  | { kind: "pinned"; revisionId: string };

export type BuildGraphLensResolution =
  | {
      status: "ready";
      documentId: string;
      documentCampaignId: string;
      campaignId: string;
      worldId: string;
      availableCampaignIds: readonly string[];
      revision: BuildGraphRevisionPolicy;
    }
  | {
      status: "selection_required";
      documentId: string;
      documentCampaignId: string;
      worldId: string;
      availableCampaignIds: readonly string[];
      revision: BuildGraphRevisionPolicy;
      reason: string;
    }
  | {
      status: "invalid";
      reason: string;
    };

function resolveRevisionPolicy(
  requestedRevisionId: string | null,
): BuildGraphRevisionPolicy {
  const trimmed = requestedRevisionId?.trim() ?? "";
  if (!trimmed) {
    return { kind: "head" };
  }
  return { kind: "pinned", revisionId: trimmed };
}

export function resolveBuildGraphLens(input: {
  documentId: string;
  documentCampaignId: string;
  requestedCampaignId: string | null;
  requestedRevisionId: string | null;
}): BuildGraphLensResolution {
  const documentId = input.documentId.trim();
  const documentCampaignId = input.documentCampaignId.trim();
  const requestedCampaignId = input.requestedCampaignId?.trim() || null;
  const revision = resolveRevisionPolicy(input.requestedRevisionId);

  if (!documentId || !documentCampaignId) {
    return {
      status: "invalid",
      reason: "Build graph lens requires a document id and campaign/world scope.",
    };
  }

  const scope = classifyBuildDocumentScope(documentCampaignId);
  if (scope.kind === "unknown") {
    return {
      status: "invalid",
      reason: `Unknown Build document scope: ${documentCampaignId}.`,
    };
  }

  if (scope.kind === "campaign") {
    const availableCampaignIds = [scope.campaignId] as const;

    if (requestedCampaignId && requestedCampaignId !== scope.campaignId) {
      return {
        status: "invalid",
        reason: `Campaign-scoped document (${documentCampaignId}) does not admit campaign lens ${requestedCampaignId}.`,
      };
    }

    return {
      status: "ready",
      documentId,
      documentCampaignId,
      campaignId: scope.campaignId,
      worldId: scope.worldId,
      availableCampaignIds,
      revision,
    };
  }

  const worldId = scope.worldId;
  const availableCampaignIds = getCampaignIdsForWorld(worldId);

  if (!requestedCampaignId) {
    return {
      status: "selection_required",
      documentId,
      documentCampaignId,
      worldId,
      availableCampaignIds,
      revision,
      reason: `World-scoped document (${documentCampaignId}) requires an explicit campaign selection.`,
    };
  }

  if (!availableCampaignIds.includes(requestedCampaignId)) {
    return {
      status: "invalid",
      reason: `Campaign ${requestedCampaignId} is not mapped to world ${worldId}.`,
    };
  }

  return {
    status: "ready",
    documentId,
    documentCampaignId,
    campaignId: requestedCampaignId,
    worldId,
    availableCampaignIds,
    revision,
  };
}
