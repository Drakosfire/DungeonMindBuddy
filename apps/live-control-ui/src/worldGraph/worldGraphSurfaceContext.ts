import type { WorldGraphProjectionRequest } from "../api/types";

export const WORLD_ID_BY_CAMPAIGN: Record<string, string> = {
  "longmont-c1": "eldyrwild",
  "longmont-c2": "eldyrwild",
};

export function getWorldIdForCampaign(campaignId: string): string | null {
  return WORLD_ID_BY_CAMPAIGN[campaignId] ?? null;
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
