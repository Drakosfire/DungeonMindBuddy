import type { GoldReviewSessionSummary, GraphIngestRunSummary } from "../../api/types";
import { goldReviewSessionLabel } from "../sessionCampaignContext";
import { goldSessionToLane, graphIngestRunToLane } from "./graphReviewWorkbenchUtils";

interface GraphReviewLoadLaneSummaryProps {
  session: GoldReviewSessionSummary | null;
  liveRun: GraphIngestRunSummary | null;
}

export function GraphReviewLoadLaneSummary({
  session,
  liveRun,
}: GraphReviewLoadLaneSummaryProps) {
  const goldLane = session ? goldSessionToLane(session) : null;
  const liveLane = liveRun ? graphIngestRunToLane(liveRun) : null;

  return (
    <section
      className="graph-review-load-lane-summary"
      aria-label="Selected lane summary"
    >
      <p>
        <strong>Gold (expected):</strong>{" "}
        {session
          ? `${goldReviewSessionLabel(session)} · ${goldLane?.label ?? session.gold_fixture_id}`
          : "Choose a gold-backed session."}
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
