import {
  REVIEW_CAMPAIGN_IDS,
  formatReviewCampaignLabel,
} from "./sessionCampaignContext";

interface ReviewCampaignPickerProps {
  selectedCampaignId: string;
  onSelect: (campaignId: string) => void;
  label?: string;
  className?: string;
}

export function ReviewCampaignPicker({
  selectedCampaignId,
  onSelect,
  label = "Campaign",
  className = "graph-preview-run-picker plan-review-campaign-picker",
}: ReviewCampaignPickerProps) {
  return (
    <label className={className}>
      <span>{label}</span>
      <select
        value={selectedCampaignId}
        onChange={(event) => onSelect(event.target.value)}
        aria-label={label}
      >
        {REVIEW_CAMPAIGN_IDS.map((campaignId) => (
          <option key={campaignId} value={campaignId}>
            {formatReviewCampaignLabel(campaignId)}
          </option>
        ))}
      </select>
    </label>
  );
}
