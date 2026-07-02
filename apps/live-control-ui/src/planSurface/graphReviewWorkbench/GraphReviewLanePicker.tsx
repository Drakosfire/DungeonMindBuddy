import type { GoldReviewSessionSummary } from "../../api/types";
import { ReviewCampaignPicker } from "../ReviewCampaignPicker";
import { GraphGoldReviewRunPicker } from "../graphGoldReview/GraphGoldReviewRunPicker";
import { GraphGoldReviewSessionPicker } from "../graphGoldReview/GraphGoldReviewSessionPicker";
import { sessionsForReviewCampaign } from "../sessionCampaignContext";

interface GraphReviewLanePickerProps {
  sessions: GoldReviewSessionSummary[];
  selectedCampaignId: string;
  selectedSessionId: string;
  selectedManifestPath: string | null;
  onCampaignSelect: (campaignId: string) => void;
  onSessionSelect: (sessionId: string) => void;
  onManifestSelect: (manifestPath: string | null) => void;
}

export function GraphReviewLanePicker({
  sessions,
  selectedCampaignId,
  selectedSessionId,
  selectedManifestPath,
  onCampaignSelect,
  onSessionSelect,
  onManifestSelect,
}: GraphReviewLanePickerProps) {
  const campaignSessions = sessionsForReviewCampaign(sessions, selectedCampaignId);
  const selectedSession = campaignSessions.find((session) => session.session_id === selectedSessionId);

  return (
    <section className="graph-review-workbench-controls" aria-label="Graph review lane selectors">
      <ReviewCampaignPicker selectedCampaignId={selectedCampaignId} onSelect={onCampaignSelect} />
      <GraphGoldReviewSessionPicker
        sessions={campaignSessions}
        selectedSessionId={selectedSessionId}
        onSelect={onSessionSelect}
      />
      <GraphGoldReviewRunPicker
        runs={selectedSession?.available_runs ?? []}
        selectedManifestPath={selectedManifestPath}
        onSelect={onManifestSelect}
      />
    </section>
  );
}
