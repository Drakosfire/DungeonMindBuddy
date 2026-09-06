import type { HistoricalRecapInspectionResponse } from "../../api/types";
import { GraphProjectionReader } from "../graphProjectionReader/GraphProjectionReader";

interface GraphReviewHistoricalRecapProjectionProps {
  inspection: HistoricalRecapInspectionResponse;
}

export function GraphReviewHistoricalRecapProjection({
  inspection,
}: GraphReviewHistoricalRecapProjectionProps) {
  const campaign = inspection.campaignId?.trim() || "unknown campaign";
  const session = inspection.sessionId?.trim() || "unknown session";

  return (
    <div
      className="graph-review-historical-recap-projection"
      data-testid="graph-review-historical-recap-projection"
    >
      <p
        className="graph-review-historical-recap-meta"
        data-testid="graph-review-historical-recap-meta"
      >
        <code>{inspection.sourceArtifactId}</code>
        {" · "}
        {campaign}
        {" · "}
        {session}
        {" · "}
        status <code>{inspection.runStatus}</code>
      </p>
      <GraphProjectionReader
        markdown={inspection.sourceProse ?? ""}
        nodeViews={{}}
        sourceSpans={[]}
        documentLabel="Historical recap"
        subtitle={`${campaign} · ${session}`}
        className="graph-review-historical-recap-reader"
      />
    </div>
  );
}
