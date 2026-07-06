import type { GraphIngestRunSummary } from "../../api/types";
import {
  catalogSessionLabel,
  graphIngestRunToLane,
  type GraphReviewCatalogSession,
} from "./graphReviewWorkbenchUtils";

interface GraphReviewLoadLaneSummaryProps {
  session: GraphReviewCatalogSession | null;
  liveRun: GraphIngestRunSummary | null;
}

export function GraphReviewLoadLaneSummary({
  session,
  liveRun,
}: GraphReviewLoadLaneSummaryProps) {
  const liveLane = liveRun ? graphIngestRunToLane(liveRun) : null;

  return (
    <section
      className="graph-review-load-lane-summary"
      aria-label="Selected lane summary"
    >
      <p>
        <strong>Gold (expected):</strong>{" "}
        {session?.hasGold
          ? `${catalogSessionLabel(session)} · ${session.goldFixtureId ?? "gold fixture"}`
          : session
            ? "No gold fixture — live review only"
            : "Choose a session."}
      </p>
      <p>
        <strong>Live (ingested):</strong>{" "}
        {liveRun
          ? liveLane?.label ?? liveRun.run_label ?? "Selected live run"
          : session
            ? "Choose a preview-ready live run."
            : "Choose a session first."}
      </p>
    </section>
  );
}
