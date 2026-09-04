import {
  catalogSessionLabel,
  catalogRunToLane,
  type GraphReviewCatalogRun,
  type GraphReviewCatalogSession,
} from "./graphReviewWorkbenchUtils";

interface GraphReviewLoadLaneSummaryProps {
  session: GraphReviewCatalogSession | null;
  liveRun: GraphReviewCatalogRun | null;
}

export function GraphReviewLoadLaneSummary({
  session,
  liveRun,
}: GraphReviewLoadLaneSummaryProps) {
  const liveLane = liveRun ? catalogRunToLane(liveRun) : null;
  const compatibility = liveRun?.compatibilityManifestPath;

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
        <strong>Live (canonical):</strong>{" "}
        {liveRun
          ? liveLane?.label ?? liveRun.run.run_id
          : session
            ? "Choose an ExtractionRun."
            : "Choose a session first."}
      </p>
      {compatibility ? (
        <p>
          <strong>Compatibility locator:</strong> {compatibility}
        </p>
      ) : liveRun ? (
        <p>Gold compare locator unavailable for this exact run.</p>
      ) : null}
    </section>
  );
}
