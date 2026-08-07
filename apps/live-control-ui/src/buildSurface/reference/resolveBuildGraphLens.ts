import {
  admitBuildDocumentScope,
  admitBuildWorldGraphBrowse,
  classifyBuildDocumentScope,
  getCampaignIdsForWorld,
} from "../../worldGraph/worldGraphSurfaceContext";
import type { WorldGraphProjectionRequest } from "../../api/types";
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
      /**
       * True when the Find lens campaign is admitted for writes into this
       * document. Cross-campaign browse within the world may still be ready
       * with insertAdmitted=false.
       */
      insertAdmitted: boolean;
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
      insertAdmitted: false;
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

function focusFromProjectionRequest(
  focus: WorldGraphProjectionRequest["focus"],
  fallbackCampaignId: string,
): BuildGraphLensFocus {
  if (focus?.kind === "session" && focus.sessionId) {
    return {
      kind: "session",
      sessionId: focus.sessionId,
      focusCampaignId: focus.campaignId?.trim() || fallbackCampaignId,
    };
  }
  return DEFAULT_FOCUS;
}

function insertAdmittedForDocument(
  documentCampaignId: string,
  lensCampaignId: string,
): boolean {
  return admitBuildDocumentScope({
    documentCampaignId,
    incomingCampaignId: lensCampaignId,
  }).ok;
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
      insertAdmitted: true,
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
      insertAdmitted: false,
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
    insertAdmitted: true,
  };
}

/**
 * Build Find lens:
 * - Shared nav controls browse identity (campaign/scope/focus) when its world is
 *   admitted by the document.
 * - Document scope classification always runs first (unknown fails closed).
 * - Revision pin stays Build-URL-owned.
 * - Prefer the shared provider's exact request when present so Build cannot
 *   re-derive a divergent campaignId default in world-union mode.
 */
export function resolveBuildFindGraphLens(input: {
  documentId: string;
  documentCampaignId: string;
  requestedCampaignId: string | null;
  requestedRevisionId: string | null;
  sharedLens: PlanGraphLens | null;
  /** Canonical shared projection request — preferred over re-deriving from the lens. */
  sharedRequest?: WorldGraphProjectionRequest | null;
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

  const documentScope = classifyBuildDocumentScope(documentCampaignId);
  if (documentScope.kind === "unknown") {
    return {
      status: "invalid",
      reason: `Unknown Build document scope: ${documentCampaignId}.`,
    };
  }

  const sharedRequest = input.sharedRequest ?? null;
  if (sharedRequest) {
    const browse = admitBuildWorldGraphBrowse({
      documentCampaignId,
      projectionWorldId: sharedRequest.worldId,
    });
    if (browse.ok) {
      return {
        status: "ready",
        documentId,
        documentCampaignId,
        campaignId: sharedRequest.campaignId,
        worldId: sharedRequest.worldId,
        availableCampaignIds: getCampaignIdsForWorld(sharedRequest.worldId),
        revision,
        scopeMode: sharedRequest.scopeMode ?? "campaign",
        focus: focusFromProjectionRequest(sharedRequest.focus, sharedRequest.campaignId),
        insertAdmitted: insertAdmittedForDocument(documentCampaignId, sharedRequest.campaignId),
      };
    }
  }

  const sharedLens = input.sharedLens;
  if (sharedLens && sharedLens.selectedCampaignIds.length > 0) {
    // Prefer provider default (shared defaultCampaignId), never Build URL campaign,
    // so world-union campaignId matches the resident shared request.
    const context = getWorldGraphContextFromLens(
      sharedLens,
      input.defaultCampaignId ?? sharedLens.selectedCampaignIds[0],
    );
    if (context) {
      const browse = admitBuildWorldGraphBrowse({
        documentCampaignId,
        projectionWorldId: context.worldId,
      });
      if (browse.ok) {
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
          insertAdmitted: insertAdmittedForDocument(documentCampaignId, context.campaignId),
        };
      }
    }
  }

  return resolveBuildGraphLens({
    documentId,
    documentCampaignId,
    requestedCampaignId: input.requestedCampaignId,
    requestedRevisionId: input.requestedRevisionId,
  });
}
