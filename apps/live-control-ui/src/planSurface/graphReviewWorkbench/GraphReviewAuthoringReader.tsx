import { useMemo } from "react";

import type { GraphProjectionNodeView, RecapProjectionSourceSpan } from "../../api/types";
import { GraphProjectionReader } from "../graphProjectionReader/GraphProjectionReader";
import type {
  GraphAuthoringAction,
  GraphAuthoringSelection,
} from "./graphAuthoringSelection";

interface GraphReviewAuthoringReaderProps {
  campaignId: string;
  sessionId: string;
  graphId?: string | null;
  laneRole?: "gold" | "live" | "authored";
  sourceArtifactPath?: string | null;
  sourceArtifactSha256?: string | null;
  markdown: string;
  nodeViews: Record<string, GraphProjectionNodeView>;
  sourceSpans: RecapProjectionSourceSpan[];
  documentLabel?: string;
  authoringEnabled?: boolean;
  onInspectNode: (nodeId: string) => void;
  onGraphAuthoringSelection?: (selection: GraphAuthoringSelection | null) => void;
  onGraphAuthoringAction?: (
    selection: GraphAuthoringSelection,
    action: GraphAuthoringAction,
  ) => void;
}

export function GraphReviewAuthoringReader({
  campaignId,
  sessionId,
  graphId,
  laneRole = "live",
  sourceArtifactPath,
  sourceArtifactSha256,
  markdown,
  nodeViews,
  sourceSpans,
  documentLabel = "Live run prose",
  authoringEnabled = false,
  onInspectNode,
  onGraphAuthoringSelection,
  onGraphAuthoringAction,
}: GraphReviewAuthoringReaderProps) {
  const authoringContext = useMemo(
    () => ({
      campaignId,
      sessionId,
      graphId,
      laneRole,
      sourceArtifactPath,
      sourceArtifactSha256,
    }),
    [
      campaignId,
      sessionId,
      graphId,
      laneRole,
      sourceArtifactPath,
      sourceArtifactSha256,
    ],
  );

  return (
    <section
      className="graph-review-projection-lane graph-review-authoring-reader-lane"
      data-lane-role={laneRole}
      data-testid="graph-projection-reader"
    >
      <GraphProjectionReader
        markdown={markdown}
        nodeViews={nodeViews}
        sourceSpans={sourceSpans}
        graphId={graphId}
        documentLabel={documentLabel}
        className="graph-review-authoring-reader"
        onInspectNode={onInspectNode}
        authoringEnabled={authoringEnabled}
        authoringContext={authoringContext}
        onGraphAuthoringSelection={onGraphAuthoringSelection}
        onGraphAuthoringAction={onGraphAuthoringAction}
      />
    </section>
  );
}
