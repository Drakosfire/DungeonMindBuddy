import { useSyncExternalStore } from "react";

import {
  getCampaignRegistry,
  subscribeCampaignRegistry,
  type WorldGraphCampaignRegistryEntry,
} from "./worldGraphSurfaceContext";

/**
 * Reactive campaign→world registry. Re-renders subscribers when the authority
 * read (`GET /api/live/world-graph/campaigns`) replaces the seeded fallback.
 */
export function useCampaignRegistry(): readonly WorldGraphCampaignRegistryEntry[] {
  return useSyncExternalStore(subscribeCampaignRegistry, getCampaignRegistry);
}
