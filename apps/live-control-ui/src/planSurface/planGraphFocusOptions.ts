import type { IngestionSourceBundle } from "../api/types";
import {
  REVIEW_CAMPAIGN_IDS,
  formatReviewCampaignLabel,
  type PlanGraphLensFocus,
  type ReviewCampaignId,
} from "./sessionCampaignContext";

export interface PlanGraphLoadFocusOption {
  campaignId: ReviewCampaignId;
  sessionNumber: number;
  label: string;
}

export type PlanGraphFocusValidationStatus = "none" | "pending" | "valid" | "invalid";

function numberField(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function shortCampaignLabel(campaignId: ReviewCampaignId): string {
  return formatReviewCampaignLabel(campaignId).replace(/^Longmont /, "");
}

export function focusOptionKey(
  option: Pick<PlanGraphLoadFocusOption, "campaignId" | "sessionNumber">,
): string {
  return `${option.campaignId}:${option.sessionNumber}`;
}

export function optionsIncludeFocus(
  options: readonly PlanGraphLoadFocusOption[],
  focus: PlanGraphLensFocus | null,
): boolean {
  if (!focus) return false;
  const key = focusOptionKey(focus);
  return options.some((option) => focusOptionKey(option) === key);
}

/** Session numbers present in an ingest source bundle (newest first). */
export function sessionNumbersFromBundle(bundle: IngestionSourceBundle): number[] {
  const sessions = new Set<number>();
  for (const unit of bundle.units ?? []) {
    const session = numberField(unit.fields.sessionNumber);
    if (session !== null) sessions.add(session);
  }
  return Array.from(sessions).sort((a, b) => b - a);
}

export function buildFocusOptionsFromBundles(
  selectedCampaignIds: readonly ReviewCampaignId[],
  bundlesByCampaign: ReadonlyMap<ReviewCampaignId, IngestionSourceBundle>,
): PlanGraphLoadFocusOption[] {
  const options: PlanGraphLoadFocusOption[] = [];
  for (const campaignId of REVIEW_CAMPAIGN_IDS) {
    if (!selectedCampaignIds.includes(campaignId)) continue;
    const bundle = bundlesByCampaign.get(campaignId);
    if (!bundle) continue;
    for (const sessionNumber of sessionNumbersFromBundle(bundle)) {
      options.push({
        campaignId,
        sessionNumber,
        label: `${shortCampaignLabel(campaignId)} · Session ${sessionNumber}`,
      });
    }
  }
  return options;
}
