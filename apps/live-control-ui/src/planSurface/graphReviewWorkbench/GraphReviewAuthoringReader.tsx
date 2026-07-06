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
  onInspectNode: (nodeId: string) => void;
  onGraphAuthoringSelection?: (selection: GraphAuthoringSelection | null) => void;
  onGraphAuthoringAction?: (
    selection: GraphAuthoringSelection,
    action: GraphAuthoringAction,
  ) => void;
  confirmedSelection?: GraphAuthoringSelection | null;
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
  onInspectNode,
  onGraphAuthoringSelection,
  onGraphAuthoringAction,
  confirmedSelection,
}: GraphReviewAuthoringReaderProps) {
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
        authoringEnabled
        authoringContext={{
          campaignId,
          sessionId,
          graphId,
          laneRole,
          sourceArtifactPath,
          sourceArtifactSha256,
        }}
        onGraphAuthoringSelection={onGraphAuthoringSelection}
        onGraphAuthoringAction={onGraphAuthoringAction}
      />
      {confirmedSelection ? (
        <aside
          className="graph-authoring-selection-preview"
          aria-label="Selected source preview"
          data-testid="graph-authoring-selection-preview"
        >
          <p className="graph-authoring-selection-preview-lede">
            Selected source ready for graph authoring. No graph write has happened.
          </p>
          <dl className="graph-authoring-selection-preview-fields">
            <div>
              <dt>Selected text</dt>
              <dd>{confirmedSelection.selectedText}</dd>
            </div>
            <div>
              <dt>Selection kind</dt>
              <dd>{confirmedSelection.selectionKind}</dd>
            </div>
            <div>
              <dt>Campaign</dt>
              <dd>{confirmedSelection.campaignId}</dd>
            </div>
            <div>
              <dt>Session</dt>
              <dd>{confirmedSelection.sessionId}</dd>
            </div>
            <div>
              <dt>Lane role</dt>
              <dd>{confirmedSelection.laneRole ?? "—"}</dd>
            </div>
            <div>
              <dt>Graph id</dt>
              <dd>{confirmedSelection.graphId ?? "—"}</dd>
            </div>
          </dl>
        </aside>
      ) : null}
    </section>
  );
}
