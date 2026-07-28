import { ReviewCampaignPicker } from "../ReviewCampaignPicker";
import {
  catalogSessionLabel,
  catalogSessionsForReviewCampaign,
  hasCatalogReviewableRun,
  type GraphReviewCatalogSession,
} from "./graphReviewWorkbenchUtils";

interface GraphReviewLanePickerProps {
  sessions: GraphReviewCatalogSession[];
  selectedCampaignId: string;
  selectedSessionId: string;
  onCampaignSelect: (campaignId: string) => void;
  onSessionSelect: (sessionId: string) => void;
}

function reviewableSessionLabel(
  sessions: GraphReviewCatalogSession[],
): string | null {
  const reviewable = sessions.find(hasCatalogReviewableRun);
  if (!reviewable) return null;
  return catalogSessionLabel(reviewable);
}

export function GraphReviewLanePicker({
  sessions,
  selectedCampaignId,
  selectedSessionId,
  onCampaignSelect,
  onSessionSelect,
}: GraphReviewLanePickerProps) {
  const campaignSessions = catalogSessionsForReviewCampaign(
    sessions,
    selectedCampaignId,
  );
  const selectedSession = campaignSessions.find(
    (session) => session.sessionId === selectedSessionId,
  );
  const reviewableLabel = reviewableSessionLabel(campaignSessions);
  const selectedHasProjection = selectedSession
    ? hasCatalogReviewableRun(selectedSession)
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
        aria-label="World Graph sessions"
      >
        {campaignSessions.map((session) => {
          const active = session.sessionId === selectedSessionId;
          const reviewable = hasCatalogReviewableRun(session);
          return (
            <button
              key={session.sessionId}
              type="button"
              role="tab"
              aria-selected={active}
              aria-disabled={!reviewable}
              className={
                active
                  ? "graph-gold-review-pill active"
                  : "graph-gold-review-pill"
              }
              onClick={() => reviewable && onSessionSelect(session.sessionId)}
              title={
                reviewable
                  ? undefined
                  : session.browseable
                    ? "This session is in the World Graph but has no corpus recap yet."
                    : "This session is not available for Load recap."
              }
            >
              {catalogSessionLabel(session)}
              {!reviewable ? " · unavailable" : ""}
            </button>
          );
        })}
      </div>
      {!selectedHasProjection ? (
        <p className="graph-review-unavailable-state" role="status">
          This session is not browseable from the World Graph yet.
          {reviewableLabel
            ? ` Choose ${reviewableLabel} to open a contributed session.`
            : " No contributed sessions with corpus recaps were found for this campaign."}
        </p>
      ) : (
        <p className="graph-gold-review-note" role="status">
          Load opens the committed World Graph session lens (not an ingest-run
          preview).
        </p>
      )}
    </section>
  );
}
