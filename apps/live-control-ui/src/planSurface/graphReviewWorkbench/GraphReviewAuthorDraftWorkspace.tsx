import { useCallback, useEffect, useRef, useState } from "react";

import type { GraphAuthoringSelection } from "./graphAuthoringSelection";
import {
  GraphReviewAuthoringRail,
  applyAuthoringPillSelection,
  type AuthoringWorkflowTab,
} from "./GraphReviewAuthoringRail";
import { GraphReviewAuthoringReader } from "./GraphReviewAuthoringReader";
import type { GraphReviewSelectedNode } from "./graphReviewSelectionUtils";
import { useGraphReviewLiveState } from "./GraphReviewLiveStateContext";
import { useGraphObjectAuthoringDraft } from "./useGraphObjectAuthoringDraft";

const FALLBACK_MARKDOWN = `# Projection unavailable\n\nThe selected live run did not return projected recap Markdown.`;

const DEFAULT_RAIL_FRACTION = 0.52;
const MIN_RAIL_FRACTION = 0.28;
const MAX_RAIL_FRACTION = 0.68;

export function GraphReviewAuthorDraftWorkspace() {
  const {
    campaignId,
    sessionId,
    liveRun,
    projection,
    goldProjection,
    paragraphSourceSpans,
    authorDraft,
  } = useGraphReviewLiveState();

  const graphObjectAuthoringDraft = useGraphObjectAuthoringDraft({
    campaignId,
    sessionId,
  });

  const [selectedAuthoringNode, setSelectedAuthoringNode] =
    useState<GraphReviewSelectedNode | null>(null);
  const [activeTab, setActiveTab] = useState<AuthoringWorkflowTab>("create_new");
  const [railFraction, setRailFraction] = useState(DEFAULT_RAIL_FRACTION);
  const layoutRef = useRef<HTMLDivElement | null>(null);
  const dragStateRef = useRef<{ startX: number; startFraction: number } | null>(null);

  const handleAuthoringNodeClick = useCallback(
    (nodeId: string) => {
      const selected = applyAuthoringPillSelection({
        nodeId,
        projection,
        goldProjection,
        relationshipFormState: graphObjectAuthoringDraft.relationshipFormState,
        updateRelationshipField: graphObjectAuthoringDraft.updateRelationshipField,
      });
      setSelectedAuthoringNode(selected);
      setActiveTab((current) =>
        current === "relationships" ? "relationships" : current,
      );
    },
    [goldProjection, graphObjectAuthoringDraft, projection],
  );

  const handleGraphAuthoringSelection = useCallback(
    (selection: GraphAuthoringSelection | null) => {
      if (!selection?.selectedText.trim()) {
        authorDraft.setSelectedText(null);
        return;
      }
      authorDraft.setSelectedText({
        laneRole:
          selection.laneRole === "gold" || selection.laneRole === "live"
            ? selection.laneRole
            : "live",
        text: selection.selectedText,
        sourceOffsets: null,
      });
    },
    [authorDraft],
  );

  useEffect(() => {
    if (graphObjectAuthoringDraft.selectedSource) {
      setActiveTab("create_new");
    }
  }, [graphObjectAuthoringDraft.selectedSource]);

  const finishResize = useCallback(() => {
    dragStateRef.current = null;
  }, []);

  const handleResizePointerDown = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      event.preventDefault();
      dragStateRef.current = {
        startX: event.clientX,
        startFraction: railFraction,
      };
      event.currentTarget.setPointerCapture(event.pointerId);
    },
    [railFraction],
  );

  const handleResizePointerMove = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    const dragState = dragStateRef.current;
    const layout = layoutRef.current;
    if (!dragState || !layout) return;

    const width = layout.getBoundingClientRect().width;
    if (width <= 0) return;

    const deltaX = dragState.startX - event.clientX;
    const nextRailPx = width * dragState.startFraction + deltaX;
    const nextFraction = Math.min(
      MAX_RAIL_FRACTION,
      Math.max(MIN_RAIL_FRACTION, nextRailPx / width),
    );
    setRailFraction(nextFraction);
  }, []);

  if (!projection || !liveRun) {
    return null;
  }

  const readerFraction = 1 - railFraction;

  return (
    <section
      className="graph-review-author-draft-workspace"
      aria-label="Author Draft workspace"
      data-testid="graph-review-author-draft-workspace"
    >
      <div
        ref={layoutRef}
        className="graph-review-author-draft-layout graph-review-author-draft-layout--resizable"
        style={{
          gridTemplateColumns: `minmax(0, ${readerFraction}fr) 8px minmax(18rem, ${railFraction}fr)`,
        }}
      >
        <div className="graph-review-author-draft-reader-pane">
          <GraphReviewAuthoringReader
            key={`${campaignId}:${sessionId}:${liveRun.manifest_path}`}
            campaignId={campaignId}
            sessionId={sessionId}
            graphId={projection.graph_id}
            laneRole="live"
            sourceArtifactPath={liveRun.manifest_path}
            markdown={projection.markdown ?? FALLBACK_MARKDOWN}
            nodeViews={projection.node_views}
            sourceSpans={paragraphSourceSpans}
            documentLabel="Authoring recap"
            authoringEnabled
            onInspectNode={handleAuthoringNodeClick}
            onGraphAuthoringSelection={handleGraphAuthoringSelection}
            onGraphAuthoringAction={(selection) => {
              graphObjectAuthoringDraft.openWithSelection(selection);
              setActiveTab("create_new");
            }}
          />
        </div>
        <div
          className="graph-review-author-draft-resize-handle"
          role="separator"
          aria-orientation="vertical"
          aria-label="Resize authoring tools pane"
          aria-valuemin={Math.round(MIN_RAIL_FRACTION * 100)}
          aria-valuemax={Math.round(MAX_RAIL_FRACTION * 100)}
          aria-valuenow={Math.round(railFraction * 100)}
          data-testid="graph-review-author-draft-resize-handle"
          onPointerDown={handleResizePointerDown}
          onPointerMove={handleResizePointerMove}
          onPointerUp={finishResize}
          onPointerCancel={finishResize}
          onLostPointerCapture={finishResize}
        />
        <GraphReviewAuthoringRail
          selectedAuthoringNode={selectedAuthoringNode}
          graphObjectAuthoringDraft={graphObjectAuthoringDraft}
          activeTab={activeTab}
          onActiveTabChange={setActiveTab}
        />
      </div>
    </section>
  );
}
