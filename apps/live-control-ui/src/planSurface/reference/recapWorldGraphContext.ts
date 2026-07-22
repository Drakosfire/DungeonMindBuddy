import type { PlanWorldGraphContext } from "./planGraphContextRequest";

const WORLD_ID_BY_CAMPAIGN: Record<string, string> = {
  "longmont-c1": "eldyrwild",
  "longmont-c2": "eldyrwild",
};

/**
 * Build a session-focused World Graph context for Recap / post-merge Ingest
 * projections. Shared so Recap View and Graph Review cannot diverge.
 *
 * Uses world scope so standing PCs are present and warm cache keys match the
 * server-side recap upgrade path (campaign → world for standing).
 */
export function buildRecapWorldGraphContext(
  campaignId: string,
  sessionId: string,
): PlanWorldGraphContext | null {
  const worldId = WORLD_ID_BY_CAMPAIGN[campaignId];
  if (!worldId) return null;
  const trimmedSession = sessionId.trim();
  if (!trimmedSession) return null;
  return {
    worldId,
    campaignId,
    scopeMode: "world",
    focus: {
      kind: "session",
      sessionId: trimmedSession,
      focusCampaignId: campaignId,
    },
  };
}

export function worldIdForCampaign(campaignId: string): string | null {
  return WORLD_ID_BY_CAMPAIGN[campaignId] ?? null;
}
