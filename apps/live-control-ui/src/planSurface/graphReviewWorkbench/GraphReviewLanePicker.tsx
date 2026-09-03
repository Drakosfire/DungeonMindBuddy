import { ReviewCampaignPicker } from "../ReviewCampaignPicker";
import { GraphReviewRunPicker } from "./GraphReviewRunPicker";
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
  selectedRunId: string | null;
  onCampaignSelect: (campaignId: string) => void;
  onSessionSelect: (sessionId: string) => void;
  onRunSelect: (runId: string | null) => void;
}

function exactReviewSessionLabel(
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
  selectedRunId,
  onCampaignSelect,
  onSessionSelect,
  onRunSelect,
}: GraphReviewLanePickerProps) {
  const campaignSessions = catalogSessionsForReviewCampaign(
    sessions,
    selectedCampaignId,
  );
  const selectedSession = campaignSessions.find(
    (session) => session.sessionId === selectedSessionId,
  );
  const exactReviewLabel = exactReviewSessionLabel(campaignSessions);
  const selectedHasExactReview = selectedSession
    ? hasCatalogReviewableRun(selectedSession)
    : false;
  const selectedHasRuns = Boolean(selectedSession?.availableRuns.length);

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
        aria-label="Ingested sessions"
      >
        {campaignSessions.map((session) => {
          const active = session.sessionId === selectedSessionId;
          const hasRuns = session.availableRuns.length > 0;
          const exactReviewable = hasCatalogReviewableRun(session);
          return (
            <button
              key={session.sessionId}
              type="button"
              role="tab"
              aria-selected={active}
              aria-disabled={!hasRuns}
              className={
                active
                  ? "graph-gold-review-pill active"
                  : "graph-gold-review-pill"
              }
              onClick={() => hasRuns && onSessionSelect(session.sessionId)}
              title={
                !hasRuns
                  ? "This session has no canonical ExtractionRuns."
                  : exactReviewable
                    ? undefined
                    : "Visible history only — no REVIEWABLE exact-review candidate."
              }
            >
              {catalogSessionLabel(session)}
              {!hasRuns
                ? " · unavailable"
                : !exactReviewable
                  ? " · history"
                  : ""}
            </button>
          );
        })}
      </div>
      {selectedHasRuns && !selectedHasExactReview ? (
        <p className="graph-review-unavailable-state" role="status">
          This session has catalog-visible runs but no REVIEWABLE exact-review
          candidate.
          {exactReviewLabel
            ? ` Choose ${exactReviewLabel} for exact review.`
            : " Promoted/terminal runs remain visible history only."}
        </p>
      ) : null}
      {!selectedHasRuns ? (
        <p className="graph-review-unavailable-state" role="status">
          This session has no canonical ExtractionRun yet.
          {exactReviewLabel
            ? ` Choose ${exactReviewLabel} to review available runs.`
            : " No canonical recap runs were found for this campaign."}
        </p>
      ) : null}
      <GraphReviewRunPicker
        runs={selectedSession?.availableRuns ?? []}
        selectedRunId={selectedRunId}
        onSelect={onRunSelect}
      />
    </section>
  );
}
