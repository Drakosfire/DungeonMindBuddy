import { useCampaignRegistry } from "../worldGraph/useCampaignRegistry";
import { formatReviewCampaignLabel } from "./sessionCampaignContext";

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
  const campaignRegistry = useCampaignRegistry();
  const known = campaignRegistry.some((entry) => entry.campaignId === selectedCampaignId);
  return (
    <label className={className}>
      <span>{label}</span>
      <select
        value={selectedCampaignId}
        onChange={(event) => onSelect(event.target.value)}
        aria-label={label}
      >
        {!known && selectedCampaignId ? (
          <option value={selectedCampaignId}>
            {formatReviewCampaignLabel(selectedCampaignId)}
          </option>
        ) : null}
        {campaignRegistry.map((entry) => (
          <option key={entry.campaignId} value={entry.campaignId}>
            {formatReviewCampaignLabel(entry.campaignId)}
          </option>
        ))}
      </select>
    </label>
  );
}
