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
 * Visible New Source campaign choices.
 *
 * `BUILD_KNOWN_CAMPAIGN_IDS` remains context-free entry defaults only. Creation choices
 * also include every campaign already present on admissible Build sources (listed active
 * worldbuilding records + the currently admitted record). That keeps Create authority
 * aligned with what Build can already load, without inventing a separate non-creatable
 * loadable-scope policy.
 */
export function resolveBuildCreateCampaignChoices(input: {
  documents?: ReadonlyArray<{ campaign_id: string }> | null;
  activeCampaignId?: string | null;
}): string[] {
  const choices: string[] = [];
  const seen = new Set<string>();
  const push = (raw: string | null | undefined) => {
    const id = raw?.trim() ?? "";
    if (!id || seen.has(id)) return;
    seen.add(id);
    choices.push(id);
  };

  for (const id of BUILD_KNOWN_CAMPAIGN_IDS) {
    push(id);
  }
  for (const record of input.documents ?? []) {
    push(record.campaign_id);
  }
  push(input.activeCampaignId);
  return choices;
}

/**
 * Prefill for New Source — must be a campaign the create form can actually show.
 * Prefers the admitted document's campaign when it is creatable; otherwise route/last
 * hints only when they appear in `creatableCampaignIds`. Explicit blank/unknown
 * `?campaign=` stays fail-closed (no fallthrough to remembered last) unless the
 * active admitted campaign is itself creatable.
 */
export function resolveSuggestedBuildCreateCampaignId(input: {
  activeCampaignId?: string | null;
  search?: string | null;
  creatableCampaignIds: readonly string[];
}): string | null {
  const creatable = new Set(
    input.creatableCampaignIds.map((id) => id.trim()).filter(Boolean),
  );
  const active = input.activeCampaignId?.trim() ?? "";
  if (active && creatable.has(active)) {
    return active;
  }

  const search =
    input.search ?? (typeof window !== "undefined" ? window.location.search : null);
  if (search != null) {
    const params = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search);
    // Explicit campaign= is fail-closed for create prefill: do not fall through to last.
    if (params.has("campaign")) {
      const fromRoute = params.get("campaign")?.trim() ?? "";
      return fromRoute && creatable.has(fromRoute) ? fromRoute : null;
    }
  }

  const resolved = resolveBareBuildCampaignId({ search })?.trim() ?? "";
  return resolved && creatable.has(resolved) ? resolved : null;
}

export function bareBuildAutoCreateKey(campaignId: string): string {
  return JSON.stringify({ campaignId: campaignId.trim() });
}
