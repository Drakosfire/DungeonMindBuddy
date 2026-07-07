import { GraphAuthoredOverlaySummary } from "./GraphAuthoredOverlaySummary";
import { useGraphReviewLiveState } from "./GraphReviewLiveStateContext";

export function GraphReviewSessionToolbar() {
  const { projection, projectionStatus } = useGraphReviewLiveState();

  if (projectionStatus !== "ready" || !projection) {
    return null;
  }

  return (
    <div className="graph-review-session-toolbar" aria-label="Loaded session status">
      <GraphAuthoredOverlaySummary summary={projection.authored_overlay} variant="compact" />
    </div>
  );
}
