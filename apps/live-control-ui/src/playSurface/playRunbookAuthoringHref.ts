import { workspaceDocumentSelectionSearch } from "../workspaceDocument/workspaceDocumentNavigation";

/**
 * Exact WorkObject navigation from Play to the ordinary TipTap authoring surface.
 * Identity is the opaque document UUID. Title, path, session, and list position
 * are never used.
 */
export function playRunbookAuthoringHref(
  documentId: string,
  currentSearch: string | null | undefined = "",
): string {
  return `/plan${workspaceDocumentSelectionSearch(currentSearch, documentId)}`;
}

/**
 * Product-side campaign guard for Edit Runbook.
 * Unknown/absent Play campaign does not block navigation; Plan admission remains
 * authoritative. A known mismatch must not open the Runbook under the current
 * Play campaign.
 */
export function playRunbookAuthoringCampaignMismatch(
  productCampaignId: string | null | undefined,
  runbookCampaignId: string | null | undefined,
): string | null {
  const product = productCampaignId?.trim() ?? "";
  if (product.length === 0) return null;
  const runbook = runbookCampaignId?.trim() ?? "";
  if (runbook === product) return null;
  const runbookLabel = runbook.length > 0 ? runbook : "an unknown campaign";
  return `This Runbook belongs to ${runbookLabel}; current Play campaign is ${product}.`;
}
