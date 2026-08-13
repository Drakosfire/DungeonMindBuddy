/** Runtime overlay of admitted campaign→world mappings from the server. */

export type AdmittedCampaignWorldMapping = {
  campaign_id: string;
  world_id: string;
  label?: string | null;
  source?: "seed" | "operator";
};

let overlayByCampaign: Record<string, string> = {};
const listeners = new Set<() => void>();

export function getAdmittedCampaignWorldOverlay(): Readonly<Record<string, string>> {
  return overlayByCampaign;
}

export function setAdmittedCampaignWorldOverlay(
  mappings: ReadonlyArray<AdmittedCampaignWorldMapping>,
): void {
  const next: Record<string, string> = {};
  for (const row of mappings) {
    const campaignId = row.campaign_id?.trim() ?? "";
    const worldId = row.world_id?.trim() ?? "";
    if (!campaignId || !worldId) continue;
    next[campaignId] = worldId;
  }
  overlayByCampaign = next;
  for (const listener of listeners) listener();
}

export function subscribeAdmittedCampaignWorldOverlay(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function getAdmittedWorldIdForCampaign(campaignId: string): string | null {
  return overlayByCampaign[campaignId.trim()] ?? null;
}

export function getAdmittedCampaignIds(): string[] {
  return Object.keys(overlayByCampaign).sort();
}

export function getAdmittedCampaignIdsForWorld(worldId: string): string[] {
  return Object.entries(overlayByCampaign)
    .filter(([, mapped]) => mapped === worldId)
    .map(([campaignId]) => campaignId)
    .sort();
}
