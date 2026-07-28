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
        <strong>Session:</strong>{" "}
        {session
          ? `${catalogSessionLabel(session)} · ${session.campaignId}`
          : "Choose a session."}
      </p>
      <p>
        <strong>World Graph:</strong>{" "}
        {session?.browseable
          ? session.recapAvailable
            ? `${session.contributionCount} contribution${session.contributionCount === 1 ? "" : "s"} · recap available`
            : `${session.contributionCount} contribution${session.contributionCount === 1 ? "" : "s"} · corpus recap missing`
          : liveRun
            ? liveLane?.label ?? liveRun.run_label ?? "Selected live run"
            : "No contributed session selected."}
      </p>
    </section>
  );
}
