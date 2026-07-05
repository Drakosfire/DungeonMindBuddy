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

export function requestedCampaignFromLocation(): string | null {
  if (typeof window === "undefined") return null;
  const campaign = new URLSearchParams(window.location.search).get("campaign")?.trim();
  return campaign || null;
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
