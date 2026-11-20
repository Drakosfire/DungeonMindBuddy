import { useEffect, useSyncExternalStore } from "react";
let campaign: string | null = null;
let owner: symbol | null = null;
const listeners = new Set<() => void>();
const subscribe = (listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener); }; };
const notify = () => { for (const listener of listeners) listener(); };
/** Only the mounted legacy Plan owner publishes this scope; navigation releases it. */
export function usePublishCampaignTrashScope(campaignId: string | null): void {
  useEffect(() => {
    if (!campaignId) return;
    const lease = Symbol(); owner = lease; campaign = campaignId; notify();
    return () => { if (owner === lease) { owner = null; campaign = null; notify(); } };
  }, [campaignId]);
}
export const useCampaignTrashScope = () => useSyncExternalStore(subscribe, () => campaign, () => null);
