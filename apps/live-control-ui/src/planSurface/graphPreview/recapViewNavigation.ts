/** Build / navigate to Plan Recap View for a campaign session. */

export function normalizeRecapSessionParam(sessionId: string): string {
  const trimmed = sessionId.trim();
  if (!trimmed) return trimmed;
  if (/^session-\d+$/i.test(trimmed)) {
    return `session-${trimmed.slice("session-".length)}`;
  }
  if (/^\d+$/.test(trimmed)) {
    return `session-${trimmed}`;
  }
  return trimmed.startsWith("session-") ? trimmed : `session-${trimmed}`;
}

export function buildRecapViewHref(campaignId: string, sessionId: string): string {
  const campaign = campaignId.trim();
  const session = normalizeRecapSessionParam(sessionId);
  return `/plan?tool=recap&campaign=${encodeURIComponent(campaign)}&session=${encodeURIComponent(session)}`;
}

export function navigateToRecapView(campaignId: string, sessionId: string): void {
  if (typeof window === "undefined") return;
  window.location.assign(buildRecapViewHref(campaignId, sessionId));
}
