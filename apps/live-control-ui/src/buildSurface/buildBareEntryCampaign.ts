import {
  requestedCampaignsFromLocation,
} from "../graphLens/sessionCampaignContext";

/** Known Build campaign ids for context-free entry (not a dogfood-specific silent default). */
export const BUILD_KNOWN_CAMPAIGN_IDS = ["longmont-c1", "longmont-c2"] as const;
export type BuildKnownCampaignId = (typeof BUILD_KNOWN_CAMPAIGN_IDS)[number];

export const BUILD_LAST_CAMPAIGN_STORAGE_KEY = "dmb.build.lastCampaignId";

export function isBuildKnownCampaignId(value: string | null | undefined): value is BuildKnownCampaignId {
  return value != null && (BUILD_KNOWN_CAMPAIGN_IDS as readonly string[]).includes(value);
}

export function readBuildLastCampaignId(): BuildKnownCampaignId | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(BUILD_LAST_CAMPAIGN_STORAGE_KEY)?.trim() ?? "";
    return isBuildKnownCampaignId(raw) ? raw : null;
  } catch {
    return null;
  }
}

export function writeBuildLastCampaignId(campaignId: string): void {
  if (typeof window === "undefined") return;
  const trimmed = campaignId.trim();
  if (!isBuildKnownCampaignId(trimmed)) return;
  try {
    window.localStorage.setItem(BUILD_LAST_CAMPAIGN_STORAGE_KEY, trimmed);
  } catch {
    // Ignore quota / private-mode failures; create still proceeds with explicit campaign.
  }
}

/**
 * Resolve the campaign hint for Build document context (create defaults, URL canonicalization).
 * Priority: known route `?campaign=` → first known shared-lens `?campaigns=` → last Build campaign.
 * Unknown or blank route `?campaign=` fail closed (null → picker / no write),
 * including when a remembered campaign exists — explicit malformed context
 * must not fall through to last.
 * Returns null when none are available (operator must pick; no silent dogfood campaign).
 * Agent scope is intentionally not read here — subscribing to AgentInteraction from
 * BuildSurfacePage re-entered lease publication and exceeded React update depth.
 */
export function resolveBareBuildCampaignId(input?: {
  search?: string | null;
}): string | null {
  const search = input?.search ?? (typeof window !== "undefined" ? window.location.search : null);
  if (search != null) {
    const params = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search);
    if (params.has("campaign")) {
      const fromRoute = params.get("campaign")?.trim() ?? "";
      if (!fromRoute || !isBuildKnownCampaignId(fromRoute)) {
        return null;
      }
      return fromRoute;
    }
    const sharedCampaigns = requestedCampaignsFromLocation(search) ?? [];
    const fromSharedLens = sharedCampaigns.find(isBuildKnownCampaignId);
    if (fromSharedLens) {
      return fromSharedLens;
    }
  }

  return readBuildLastCampaignId();
}

/**
 * Prefill for New Source only — must be a campaign the create form can actually show.
 * Never suggests a foreign active-document campaign (e.g. eldyrwild) or falls through
 * remembered C1/C2 when the URL explicitly fails closed on `?campaign=`.
 */
export function resolveSuggestedBuildCreateCampaignId(input: {
  activeCampaignId?: string | null;
  search?: string | null;
}): BuildKnownCampaignId | null {
  if (isBuildKnownCampaignId(input.activeCampaignId)) {
    return input.activeCampaignId;
  }

  const search =
    input.search ?? (typeof window !== "undefined" ? window.location.search : null);
  if (search != null) {
    const params = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search);
    // Explicit campaign= is fail-closed for create prefill: do not fall through to last.
    if (params.has("campaign")) {
      const fromRoute = params.get("campaign")?.trim() ?? "";
      return isBuildKnownCampaignId(fromRoute) ? fromRoute : null;
    }
  }

  const resolved = resolveBareBuildCampaignId({ search });
  return isBuildKnownCampaignId(resolved) ? resolved : null;
}

export function bareBuildAutoCreateKey(campaignId: string): string {
  return JSON.stringify({ campaignId: campaignId.trim() });
}
