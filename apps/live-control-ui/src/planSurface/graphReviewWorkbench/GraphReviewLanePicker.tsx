import type { GoldReviewSessionSummary } from "../../api/types";
import { ReviewCampaignPicker } from "../ReviewCampaignPicker";
import { GraphGoldReviewRunPicker } from "../graphGoldReview/GraphGoldReviewRunPicker";
import { goldReviewSessionLabel } from "../sessionCampaignContext";
import { sessionsForReviewCampaign } from "../sessionCampaignContext";
import { hasReviewableProjection } from "./graphReviewWorkbenchUtils";

interface GraphReviewLanePickerProps {
  sessions: GoldReviewSessionSummary[];
  selectedCampaignId: string;
  selectedSessionId: string;
  selectedManifestPath: string | null;
  onCampaignSelect: (campaignId: string) => void;
  onSessionSelect: (sessionId: string) => void;
  onManifestSelect: (manifestPath: string | null) => void;
}

function reviewableSessionLabel(
  sessions: GoldReviewSessionSummary[],
): string | null {
  const reviewable = sessions.find(hasReviewableProjection);
  if (!reviewable) return null;
  return goldReviewSessionLabel(reviewable);
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
  const campaignSessions = sessionsForReviewCampaign(
    sessions,
    selectedCampaignId,
  );
  const selectedSession = campaignSessions.find(
    (session) => session.session_id === selectedSessionId,
  );
  const reviewableLabel = reviewableSessionLabel(campaignSessions);
  const selectedHasProjection = selectedSession
    ? hasReviewableProjection(selectedSession)
    : false;

  return (
    <section
      className="graph-review-workbench-controls"
      aria-label="Graph review lane selectors"
    >
      <ReviewCampaignPicker
        selectedCampaignId={selectedCampaignId}
        onSelect={onCampaignSelect}
      />
      <div
        className="graph-gold-review-session-picker"
        role="tablist"
        aria-label="Gold-backed sessions"
      >
        {campaignSessions.map((session) => {
          const active = session.session_id === selectedSessionId;
          const reviewable = hasReviewableProjection(session);
          return (
            <button
              key={session.session_id}
              type="button"
              role="tab"
              aria-selected={active}
              aria-disabled={!reviewable}
              className={
                active
                  ? "graph-gold-review-pill active"
                  : "graph-gold-review-pill"
              }
              onClick={() => reviewable && onSessionSelect(session.session_id)}
              title={
                reviewable
                  ? undefined
                  : "This session has no reviewable projection."
              }
            >
              {goldReviewSessionLabel(session)}
              {!reviewable ? " · unavailable" : ""}
            </button>
          );
        })}
      </div>
      {!selectedHasProjection ? (
        <p className="graph-review-unavailable-state" role="status">
          This session has no reviewable projection. This source does not have a
          loaded recap/projection yet.
          {reviewableLabel
            ? ` Choose ${reviewableLabel} to review available graph projections.`
            : " No available graph projections were found for this campaign."}
        </p>
      ) : null}
      <GraphGoldReviewRunPicker
        runs={(selectedSession?.available_runs ?? []).filter(
          (run) => run.preview_union_available,
        )}
        selectedManifestPath={selectedManifestPath}
        onSelect={onManifestSelect}
      />
    </section>
  );
}
