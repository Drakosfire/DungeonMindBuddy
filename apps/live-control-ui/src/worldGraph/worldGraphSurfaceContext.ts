import type { WorldGraphProjectionRequest } from "../api/types";

export const WORLD_ID_BY_CAMPAIGN: Record<string, string> = {
  "longmont-c1": "eldyrwild",
  "longmont-c2": "eldyrwild",
};

export function getWorldIdForCampaign(campaignId: string): string | null {
  return WORLD_ID_BY_CAMPAIGN[campaignId] ?? null;
}

export function getCampaignIdsForWorld(worldId: string): readonly string[] {
  return Object.entries(WORLD_ID_BY_CAMPAIGN)
    .filter(([, mappedWorldId]) => mappedWorldId === worldId)
    .map(([campaignId]) => campaignId)
    .sort();
}

export type BuildDocumentScopeClassification =
  | { kind: "campaign"; campaignId: string; worldId: string }
  | { kind: "world"; worldId: string }
  | { kind: "unknown" };

export function classifyBuildDocumentScope(
  documentCampaignId: string,
): BuildDocumentScopeClassification {
  const trimmed = documentCampaignId.trim();
  const mappedWorldId = WORLD_ID_BY_CAMPAIGN[trimmed];
  if (mappedWorldId) {
    return { kind: "campaign", campaignId: trimmed, worldId: mappedWorldId };
  }

  const campaignIdsForWorld = getCampaignIdsForWorld(trimmed);
  if (campaignIdsForWorld.length > 0) {
    return { kind: "world", worldId: trimmed };
  }

  return { kind: "unknown" };
}

export function buildWorldGraphRecapProjectionRequest(input: {
  campaignId: string;
  sessionId: string;
}): WorldGraphProjectionRequest | null {
  const worldId = getWorldIdForCampaign(input.campaignId);
  if (!worldId) return null;

  return {
    schema: "dmb_world_graph_projection_request_v1",
    worldId,
    campaignId: input.campaignId,
    scopeMode: "campaign",
    focus: {
      kind: "session",
      sessionId: input.sessionId,
      campaignId: input.campaignId,
    },
    admissibility: "gm",
  };
}

export function buildBuildWorldGraphProjectionRequest(input: {
  campaignId: string;
  revisionPin?: string | null;
}): WorldGraphProjectionRequest | null {
  const worldId = getWorldIdForCampaign(input.campaignId);
  if (!worldId) return null;

  return {
    schema: "dmb_world_graph_projection_request_v1",
    worldId,
    campaignId: input.campaignId,
    scopeMode: "campaign",
    focus: { kind: "none", sessionId: null },
    admissibility: "gm",
    revisionPin: input.revisionPin ?? null,
  };
}

/**
 * Post-confirm Graph Review exact read.
 * Uses receipt.worldId (no remapping). Fail closed when campaign map is missing
 * or disagrees with the receipt world.
 */
export function buildGraphReviewCommittedProjectionRequest(input: {
  campaignId: string;
  sessionId?: string | null;
  receipt: { worldId: string; committedRevisionId: string };
}): WorldGraphProjectionRequest | null {
  const campaignId = input.campaignId.trim();
  const receiptWorldId = input.receipt.worldId.trim();
  const committedRevisionId = input.receipt.committedRevisionId.trim();
  if (!campaignId || !receiptWorldId || !committedRevisionId) return null;

  const mappedWorldId = getWorldIdForCampaign(campaignId);
  if (!mappedWorldId || mappedWorldId !== receiptWorldId) return null;

  const sessionId = input.sessionId?.trim() || "";
  return {
    schema: "dmb_world_graph_projection_request_v1",
    worldId: receiptWorldId,
    campaignId,
    scopeMode: "campaign",
    focus: sessionId
      ? { kind: "session", sessionId, campaignId }
      : { kind: "none", sessionId: null },
    admissibility: "gm",
    revisionPin: committedRevisionId,
  };
}

export function admitBuildDocumentScope(input: {
  documentCampaignId: string | null | undefined;
  incomingCampaignId: string;
}):
  | { ok: true }
  | { ok: false; reason: string } {
  const documentCampaignId = input.documentCampaignId?.trim() ?? "";
  if (!documentCampaignId) {
    return {
      ok: false,
      reason: "Select a Build source with a known campaign or world scope before opening graph context.",
    };
  }

  const worldId = getWorldIdForCampaign(input.incomingCampaignId);
  if (!worldId) {
    return {
      ok: false,
      reason: `Unknown campaign mapping for ${input.incomingCampaignId}. Graph context cannot load.`,
    };
  }

  if (
    documentCampaignId === input.incomingCampaignId
    || documentCampaignId === worldId
  ) {
    return { ok: true };
  }

  return {
    ok: false,
    reason: `Build source scope (${documentCampaignId}) does not admit graph context for campaign ${input.incomingCampaignId} (world ${worldId}).`,
  };
}
