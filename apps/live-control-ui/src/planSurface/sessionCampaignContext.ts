/** Campaign selection for graph review surfaces. */

import type { RecapArtifactRecord } from "../api/types";

export const REVIEW_CAMPAIGN_IDS = ["longmont-c1", "longmont-c2"] as const;

export type ReviewCampaignId = (typeof REVIEW_CAMPAIGN_IDS)[number];

export function formatReviewCampaignLabel(campaignId: string): string {
  const match = campaignId.match(/^longmont-c(\d+)$/i);
  if (match) {
    return `Longmont C${match[1]}`;
  }
  return campaignId;
}

export function isReviewCampaignId(value: string | null | undefined): value is ReviewCampaignId {
  return value != null && (REVIEW_CAMPAIGN_IDS as readonly string[]).includes(value);
}

export function requestedCampaignFromLocation(
  search: string | null | undefined = typeof window !== "undefined" ? window.location.search : null,
): string | null {
  if (search == null) return null;
  const campaign = new URLSearchParams(search).get("campaign")?.trim();
  return campaign || null;
}

/** Accepts `session-24` or bare `24`. */
export function requestedSessionNumberFromLocation(
  search: string | null | undefined = typeof window !== "undefined" ? window.location.search : null,
): number | null {
  if (search == null) return null;
  const raw = new URLSearchParams(search).get("session")?.trim();
  if (!raw) return null;
  const match = raw.match(/^(?:session-)?(\d+)$/i);
  if (!match) return null;
  const session = Number.parseInt(match[1], 10);
  return Number.isFinite(session) && session > 0 ? session : null;
}

/** Optional `?documentId=<uuid>` selects a workspace document. */
export function requestedDocumentIdFromLocation(
  search: string | null | undefined = typeof window !== "undefined" ? window.location.search : null,
): string | null {
  if (search == null) return null;
  const raw = new URLSearchParams(search).get("documentId")?.trim();
  return raw || null;
}

export type PlanGraphScopeMode = "campaign" | "world";

export interface PlanGraphLensFocus {
  campaignId: ReviewCampaignId;
  sessionNumber: number;
}

/** Multi-select campaign union + optional qualified session focus for Plan Hermes / graph search. */
export interface PlanGraphLens {
  selectedCampaignIds: ReviewCampaignId[];
  focus: PlanGraphLensFocus | null;
}

export interface DerivedPlanGraphApiLens {
  campaignId: ReviewCampaignId;
  scopeMode: PlanGraphScopeMode;
  focus: PlanGraphLensFocus | null;
}

/** Optional `?scopeMode=world|campaign` for Plan / graph-anchor lens (defaults to world). */
export function requestedScopeModeFromLocation(
  search: string | null | undefined = typeof window !== "undefined" ? window.location.search : null,
): PlanGraphScopeMode | null {
  if (search == null) return null;
  const raw = new URLSearchParams(search).get("scopeMode")?.trim().toLowerCase();
  if (raw === "world" || raw === "campaign") {
    return raw;
  }
  return null;
}

export function resolvePlanGraphScopeMode(
  requestedScopeMode: PlanGraphScopeMode | null = requestedScopeModeFromLocation(),
): PlanGraphScopeMode {
  return requestedScopeMode ?? "world";
}

function uniqueReviewCampaignIds(ids: readonly string[]): ReviewCampaignId[] {
  const seen = new Set<ReviewCampaignId>();
  const out: ReviewCampaignId[] = [];
  for (const id of ids) {
    if (!isReviewCampaignId(id) || seen.has(id)) continue;
    seen.add(id);
    out.push(id);
  }
  return out;
}

/** `?campaigns=longmont-c1,longmont-c2` multi-select. */
export function requestedCampaignsFromLocation(
  search: string | null | undefined = typeof window !== "undefined" ? window.location.search : null,
): ReviewCampaignId[] | null {
  if (search == null) return null;
  const raw = new URLSearchParams(search).get("campaigns")?.trim();
  if (!raw) return null;
  const parsed = uniqueReviewCampaignIds(raw.split(",").map((part) => part.trim()).filter(Boolean));
  return parsed.length > 0 ? parsed : null;
}

/**
 * Focus session from URL.
 * Accepts `session-24`, bare `24`, or qualified `longmont-c2:24` / `c2:24`.
 */
export function requestedLensFocusFromLocation(
  search: string | null | undefined = typeof window !== "undefined" ? window.location.search : null,
  fallbackCampaignId: string | null = null,
): PlanGraphLensFocus | null {
  if (search == null) return null;
  const raw = new URLSearchParams(search).get("session")?.trim();
  if (!raw) return null;

  const qualified = raw.match(/^(?:(longmont-c\d+)|c(\d+)):?(?:session-)?(\d+)$/i);
  if (qualified) {
    const campaignId = qualified[1]
      ? qualified[1].toLowerCase()
      : `longmont-c${qualified[2]}`;
    const sessionNumber = Number.parseInt(qualified[3], 10);
    if (isReviewCampaignId(campaignId) && Number.isFinite(sessionNumber) && sessionNumber > 0) {
      return { campaignId, sessionNumber };
    }
  }

  const bare = raw.match(/^(?:session-)?(\d+)$/i);
  if (!bare) return null;
  const sessionNumber = Number.parseInt(bare[1], 10);
  if (!Number.isFinite(sessionNumber) || sessionNumber <= 0) return null;
  if (!isReviewCampaignId(fallbackCampaignId)) return null;
  return { campaignId: fallbackCampaignId, sessionNumber };
}

/**
 * Resolve Plan graph lens from URL + plan campaign.
 * Default with no URL: active plan campaign only (safer than whole-world union).
 * Back-compat: single `?campaign=` + `?scopeMode=` map into a selected set.
 */
export function resolvePlanGraphLens(
  planCampaignId: string,
  search: string | null | undefined = typeof window !== "undefined" ? window.location.search : null,
): PlanGraphLens {
  const fromCampaigns = requestedCampaignsFromLocation(search);
  const singleCampaign = requestedCampaignFromLocation(search);
  const scopeMode = requestedScopeModeFromLocation(search);

  let selectedCampaignIds: ReviewCampaignId[];
  if (fromCampaigns) {
    selectedCampaignIds = fromCampaigns;
  } else if (isReviewCampaignId(singleCampaign) && scopeMode === "campaign") {
    selectedCampaignIds = [singleCampaign];
  } else if (isReviewCampaignId(singleCampaign) && scopeMode === "world") {
    selectedCampaignIds = [...REVIEW_CAMPAIGN_IDS];
  } else if (isReviewCampaignId(singleCampaign)) {
    selectedCampaignIds = [...REVIEW_CAMPAIGN_IDS];
  } else {
    selectedCampaignIds = isReviewCampaignId(planCampaignId)
      ? [planCampaignId]
      : [...REVIEW_CAMPAIGN_IDS];
  }

  const focusFallback =
    (selectedCampaignIds.length === 1 ? selectedCampaignIds[0] : null)
    ?? (isReviewCampaignId(planCampaignId) ? planCampaignId : null)
    ?? (selectedCampaignIds[0] ?? null);
  const focus = requestedLensFocusFromLocation(search, focusFallback);
  const normalizedFocus =
    focus && selectedCampaignIds.includes(focus.campaignId) ? focus : null;

  return {
    selectedCampaignIds,
    focus: normalizedFocus,
  };
}

/**
 * Map multi-select lens onto existing scope_mode / campaign_id API.
 * Empty selection returns null (Ask should be disabled).
 */
export function deriveApiLens(
  lens: PlanGraphLens,
  planCampaignId: string,
): DerivedPlanGraphApiLens | null {
  const selected = uniqueReviewCampaignIds(lens.selectedCampaignIds);
  if (selected.length === 0) return null;

  const scopeMode: PlanGraphScopeMode = selected.length === 1 ? "campaign" : "world";
  const campaignId: ReviewCampaignId =
    selected.length === 1
      ? selected[0]
      : isReviewCampaignId(planCampaignId) && selected.includes(planCampaignId)
        ? planCampaignId
        : selected[0];

  const focus =
    lens.focus && selected.includes(lens.focus.campaignId) ? lens.focus : null;

  return { campaignId, scopeMode, focus };
}

export function formatPlanGraphLensSummary(
  lens: PlanGraphLens,
  planCampaignId: string,
): string {
  const derived = deriveApiLens(lens, planCampaignId);
  if (!derived) return "Select at least one campaign";

  const labels = lens.selectedCampaignIds.map((id) =>
    formatReviewCampaignLabel(id).replace(/^Longmont /, ""),
  );
  const unionLabel =
    lens.selectedCampaignIds.length > 1
      ? `Union · ${labels.join("+")}`
      : `${labels[0] ?? derived.campaignId} only`;
  const focusLabel =
    derived.focus == null
      ? "no session focus"
      : `${formatReviewCampaignLabel(derived.focus.campaignId).replace(/^Longmont /, "")} · Session ${derived.focus.sessionNumber}`;
  return `${unionLabel} · ${focusLabel}`;
}

/** Write `campaigns` + qualified `session`; preserve other params (e.g. documentId). */
export function syncPlanGraphLensUrl(lens: PlanGraphLens): void {
  if (typeof window === "undefined") return;
  const params = new URLSearchParams(window.location.search);
  if (lens.selectedCampaignIds.length > 0) {
    params.set("campaigns", lens.selectedCampaignIds.join(","));
  } else {
    params.delete("campaigns");
  }
  // Prefer multi-select param; drop legacy single campaign / scopeMode when syncing lens.
  params.delete("campaign");
  params.delete("scopeMode");
  if (lens.focus) {
    params.set("session", `${lens.focus.campaignId}:${lens.focus.sessionNumber}`);
  } else {
    params.delete("session");
  }
  const path = window.location.pathname.replace(/\/+$/, "") || "/plan";
  const surfacePath = path === "/ingest" ? "/ingest" : "/plan";
  const query = params.toString();
  window.history.replaceState({}, "", query ? `${surfacePath}?${query}` : surfacePath);
}

export function resolveInitialReviewCampaignId(
  planCampaignId: string,
  requestedCampaignId: string | null = requestedCampaignFromLocation(),
): string {
  if (isReviewCampaignId(requestedCampaignId)) {
    return requestedCampaignId;
  }
  return planCampaignId;
}

export function syncReviewCampaignUrl(campaignId: string): void {
  if (typeof window === "undefined") return;
  const params = new URLSearchParams(window.location.search);
  params.set("campaign", campaignId);
  const path = window.location.pathname.replace(/\/+$/, "") || "/plan";
  const surfacePath = path === "/ingest" ? "/ingest" : "/plan";
  window.history.replaceState({}, "", `${surfacePath}?${params.toString()}`);
}

export function resolveSessionRecapContext(
  sessionId: string,
  selectedCampaignId: string,
  records: RecapArtifactRecord[],
): { campaignId: string; record: RecapArtifactRecord | undefined } {
  const record = records.find(
    (entry) => entry.session_id === sessionId && entry.campaign_id === selectedCampaignId,
  );
  return {
    campaignId: selectedCampaignId,
    record,
  };
}

export function goldReviewSessionLabel(session: {
  session_id: string;
  session_number: number | null;
}): string {
  if (session.session_number != null) {
    return `Session ${session.session_number}`;
  }
  return session.session_id;
}

export function sessionsForReviewCampaign<
  T extends { session_id: string; campaign_id: string | null | undefined },
>(sessions: T[], selectedCampaignId: string): T[] {
  return sessions.filter(
    (session) => session.campaign_id === selectedCampaignId || session.campaign_id == null,
  );
}
