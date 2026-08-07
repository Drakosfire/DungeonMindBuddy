import {
  classifyBuildDocumentScope,
  getCampaignIdsForWorld,
} from "../../worldGraph/worldGraphSurfaceContext";
import {
  getWorldGraphContextFromLens,
  type PlanWorldGraphContext,
} from "../../graphLens/worldGraphContextFromLens";
import type { PlanGraphLens } from "../../graphLens/sessionCampaignContext";

export type BuildGraphRevisionPolicy =
  | { kind: "head" }
  | { kind: "pinned"; revisionId: string };

export type BuildGraphLensFocus = PlanWorldGraphContext["focus"];

export type BuildGraphLensResolution =
  | {
      status: "ready";
      documentId: string;
      documentCampaignId: string;
      campaignId: string;
      worldId: string;
      availableCampaignIds: readonly string[];
      revision: BuildGraphRevisionPolicy;
      scopeMode: "campaign" | "world";
      focus: BuildGraphLensFocus;
    }
  | {
      status: "selection_required";
      documentId: string;
      documentCampaignId: string;
      worldId: string;
      availableCampaignIds: readonly string[];
      revision: BuildGraphRevisionPolicy;
      scopeMode: "campaign" | "world";
      focus: BuildGraphLensFocus;
      reason: string;
    }
  | {
      status: "invalid";
      reason: string;
    };

const DEFAULT_FOCUS: BuildGraphLensFocus = { kind: "none", sessionId: null };

function resolveRevisionPolicy(
  requestedRevisionId: string | null,
): BuildGraphRevisionPolicy {
  const trimmed = requestedRevisionId?.trim() ?? "";
  if (!trimmed) {
    return { kind: "head" };
  }
  return { kind: "pinned", revisionId: trimmed };
}

/**
 * Document-local Build graph lens (campaign/none defaults).
 * Prefer {@link resolveBuildFindGraphLens} when the shared nav lens is available.
 */
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
      scopeMode: "campaign",
      focus: DEFAULT_FOCUS,
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
      scopeMode: "campaign",
      focus: DEFAULT_FOCUS,
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
    scopeMode: "campaign",
    focus: DEFAULT_FOCUS,
  };
}

/**
 * Build Find lens: prefer the shared World Graph nav for campaign/scope/focus so
 * chrome and Find share one exact request identity. Revision pin stays Build-URL-owned.
 * Falls back to document-local resolution when the shared nav has no selection.
 */
export function resolveBuildFindGraphLens(input: {
  documentId: string;
  documentCampaignId: string;
  requestedCampaignId: string | null;
  requestedRevisionId: string | null;
  sharedLens: PlanGraphLens | null;
  defaultCampaignId: string | null;
}): BuildGraphLensResolution {
  const documentId = input.documentId.trim();
  const documentCampaignId = input.documentCampaignId.trim();
  const revision = resolveRevisionPolicy(input.requestedRevisionId);

  if (!documentId || !documentCampaignId) {
    return {
      status: "invalid",
      reason: "Build graph lens requires a document id and campaign/world scope.",
    };
  }

  const sharedLens = input.sharedLens;
  if (sharedLens && sharedLens.selectedCampaignIds.length > 0) {
    const context = getWorldGraphContextFromLens(
      sharedLens,
      input.defaultCampaignId ?? sharedLens.selectedCampaignIds[0],
    );
    if (context) {
      return {
        status: "ready",
        documentId,
        documentCampaignId,
        campaignId: context.campaignId,
        worldId: context.worldId,
        availableCampaignIds: getCampaignIdsForWorld(context.worldId),
        revision,
        scopeMode: context.scopeMode,
        focus: context.focus,
      };
    }
  }

  return resolveBuildGraphLens({
    documentId,
    documentCampaignId,
    requestedCampaignId: input.requestedCampaignId,
    requestedRevisionId: input.requestedRevisionId,
  });
}
