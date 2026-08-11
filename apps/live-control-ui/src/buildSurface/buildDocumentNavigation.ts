import { workspaceDocumentSelectionSearch } from "../workspaceDocument/workspaceDocumentNavigation";

/**
 * Build document selection URL: exact `documentId` plus canonical `campaign`.
 * Preserves unrelated query params (campaigns, session, tool, dogfood, graphNodeId, …).
 */
export function buildDocumentSelectionSearch(
  currentSearch: string | null | undefined,
  documentId: string,
  campaignId: string,
): string {
  const base = workspaceDocumentSelectionSearch(currentSearch, documentId);
  const params = new URLSearchParams(base.startsWith("?") ? base.slice(1) : base);
  const trimmedCampaign = campaignId.trim();
  if (trimmedCampaign) {
    params.set("campaign", trimmedCampaign);
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}
