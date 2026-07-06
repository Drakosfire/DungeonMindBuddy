import type { GraphIngestRunSummary } from "../../api/types";
import { ReviewCampaignPicker } from "../ReviewCampaignPicker";
import { GraphGoldReviewRunPicker } from "../graphGoldReview/GraphGoldReviewRunPicker";
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
  selectedManifestPath: string | null;
  onCampaignSelect: (campaignId: string) => void;
  onSessionSelect: (sessionId: string) => void;
  onManifestSelect: (manifestPath: string | null) => void;
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
  selectedManifestPath,
  onCampaignSelect,
  onSessionSelect,
  onManifestSelect,
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
        aria-label="Ingested sessions"
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
                  : "This session has no reviewable projection."
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
          This session has no reviewable projection. This source does not have a
          loaded recap/projection yet.
          {reviewableLabel
            ? ` Choose ${reviewableLabel} to review available graph projections.`
            : " No available graph projections were found for this campaign."}
        </p>
      ) : null}
      <GraphGoldReviewRunPicker
        runs={(selectedSession?.availableRuns ?? []).filter(
          (run: GraphIngestRunSummary) => run.preview_union_available,
        )}
        selectedManifestPath={selectedManifestPath}
        onSelect={onManifestSelect}
      />
    </section>
  );
}
