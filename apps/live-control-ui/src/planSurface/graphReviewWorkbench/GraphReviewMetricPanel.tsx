import type { GoldReviewCompareResponse } from "../../api/types";
import { GraphGoldReviewMissTables } from "../graphGoldReview/GraphGoldReviewMissTables";
import { GraphGoldReviewScorecard } from "../graphGoldReview/GraphGoldReviewScorecard";
import type { GoldReviewSelection } from "../graphGoldReview/graphGoldReviewUtils";

interface GraphReviewMetricPanelProps {
  compare: GoldReviewCompareResponse | null;
  compareStatus: "idle" | "loading" | "ready" | "error";
  compareError: string | null;
  selection: GoldReviewSelection | null;
  onSelect: (selection: GoldReviewSelection) => void;
}

export function GraphReviewMetricPanel({
  compare,
  compareStatus,
  compareError,
  selection,
  onSelect,
}: GraphReviewMetricPanelProps) {
  const readyCompare = compareStatus === "ready" ? compare : null;
  return (
    <section className="graph-review-metric-panel" aria-label="Gold-vs-live smoke alarms">
      <header>
        <p className="plan-surface-kicker">Secondary metrics</p>
        <h3>Gold-vs-live smoke alarms</h3>
        <p className="graph-review-note">Metrics are diagnostic navigation aids, not the primary source review surface.</p>
      </header>
      {compareStatus === "idle" ? <p className="graph-review-note">Select a live run to load gold-vs-live metrics.</p> : null}
      {compareStatus === "loading" ? <p className="graph-review-note">Loading gold-vs-live metrics…</p> : null}
      {compareError ? <p className="graph-review-error">{compareError}</p> : null}
      <GraphGoldReviewScorecard compare={readyCompare} />
      <GraphGoldReviewMissTables compare={readyCompare} selection={selection} onSelect={onSelect} />
    </section>
  );
}
