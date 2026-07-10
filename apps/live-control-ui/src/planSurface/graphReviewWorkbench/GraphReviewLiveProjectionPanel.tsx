// PR003_LEGACY_GRAPH_PREVIEW_EXEMPTION:
// Retained until PR007/PR008 removes preview/latest-ingest selectors from surface APIs.
import { GraphReviewProjectionLane } from "./GraphReviewProjectionLane";
import { GraphReviewProjectedInteractionSurface } from "./GraphReviewProjectedInteractionSurface";
import { useGraphReviewLiveState } from "./GraphReviewLiveStateContext";

const FALLBACK_MARKDOWN = `# Projection unavailable\n\nThe selected live run did not return projected recap Markdown.`;

function metadataValue(value: string | null | undefined): string {
  return value && value.trim() ? value : "—";
}

export function GraphReviewLiveProjectionPanel() {
  const {
    liveRun,
    hasGold,
    projection,
    projectionStatus,
    projectionError,
    goldProjection,
    goldProjectionStatus,
    goldProjectionError,
    deltaIndex,
    paragraphSourceSpans,
    activeLaneObject,
    setActiveLaneObject,
    setSelectedNode,
    selectedNodeViewModel,
    selectedRelationship,
    setSelectedRelationship,
    setSelectedDeltaNodeId,
    projectedInteractionOpen,
    setProjectedInteractionOpen,
    setSelectedEvidenceDeltaId,
    runIdentity,
  } = useGraphReviewLiveState();

  const openInspectDialog = (selection: {
    laneRole: "gold" | "live";
    nodeId: string;
  }) => {
    setSelectedNode(selection);
    setSelectedRelationship(null);
    setSelectedDeltaNodeId(selection.nodeId);
    setProjectedInteractionOpen(true);
  };

  return (
    <section
      className={`graph-review-live-projection-panel${hasGold ? "" : " graph-review-live-only-projection-panel"}`}
      aria-label={hasGold ? "Gold and live source projections" : "Ingested recap projection"}
    >
      {projectionStatus === "idle" ? (
        <p className="graph-review-live-projection-status">
          Select a live graph-ingest run to render its source projection.
        </p>
      ) : null}

      {projectionStatus === "unavailable" && liveRun ? (
        <div className="graph-review-live-projection-status" role="status">
          <p>
            Selected live run does not have a preview-union projection available
            yet.
          </p>
          <dl className="graph-review-lane-meta">
            <div>
              <dt>Run label</dt>
              <dd>{metadataValue(liveRun.run_label)}</dd>
            </div>
            <div>
              <dt>Run id</dt>
              <dd>{metadataValue(liveRun.run_id)}</dd>
            </div>
            <div>
              <dt>Status</dt>
              <dd>{metadataValue(liveRun.status)}</dd>
            </div>
            <div>
              <dt>Manifest path</dt>
              <dd>{metadataValue(liveRun.manifest_path)}</dd>
            </div>
            <div>
              <dt>Preview union path</dt>
              <dd>{metadataValue(liveRun.preview_union_store_path)}</dd>
            </div>
            <div>
              <dt>Next actions</dt>
              <dd>
                {liveRun.next_actions.length
                  ? liveRun.next_actions.join("; ")
                  : "—"}
              </dd>
            </div>
          </dl>
        </div>
      ) : null}

      {projectionStatus === "loading" ? (
        <p className="graph-review-live-projection-status" role="status">
          Loading selected live lane projection…
        </p>
      ) : null}

      {projectionStatus === "error" && liveRun ? (
        <div className="graph-review-error" role="alert">
          <p>
            {projectionError ?? "Failed to load selected live lane projection."}
          </p>
          <p>Selected run: {runIdentity}</p>
        </div>
      ) : null}

      {projectionStatus === "ready" && projection && liveRun ? (
        <>
          {hasGold && goldProjectionStatus === "loading" ? (
            <p className="graph-review-live-projection-status" role="status">
              Loading gold fixture projection…
            </p>
          ) : null}
          {hasGold && goldProjectionStatus === "error" ? (
            <div className="graph-review-error" role="alert">
              <p>
                {goldProjectionError ??
                  "Failed to load gold fixture projection."}
              </p>
            </div>
          ) : null}
          <div
            className={
              hasGold
                ? "graph-review-real-two-lane-projections"
                : "graph-review-live-only-projections"
            }
            data-testid="graph-review-projection-layout"
          >
            {hasGold && goldProjectionStatus === "ready" && goldProjection ? (
              <GraphReviewProjectionLane
                laneRole="gold"
                title="Gold Fixture · read-only"
                subtitle={
                  goldProjection.fixture_version
                    ? `Fixture ${goldProjection.fixture_version}`
                    : goldProjection.gold_fixture_relpath
                }
                markdown={goldProjection.markdown ?? FALLBACK_MARKDOWN}
                nodeViews={goldProjection.node_views}
                sourceSpans={goldProjection.source_spans}
                mentionsCount={goldProjection.mentions.length}
                deltaIndex={deltaIndex}
                activeObject={activeLaneObject}
                onActiveObjectChange={setActiveLaneObject}
                onSelectObject={openInspectDialog}
                readerMode
              />
            ) : null}
            <GraphReviewProjectionLane
              laneRole="live"
              title={hasGold ? "Live Run · read-only" : "Ingested recap"}
              subtitle={runIdentity}
              markdown={projection.markdown ?? FALLBACK_MARKDOWN}
              nodeViews={projection.node_views}
              sourceSpans={paragraphSourceSpans}
              mentionsCount={projection.mentions.length}
              deltaIndex={deltaIndex}
              activeObject={activeLaneObject}
              onActiveObjectChange={setActiveLaneObject}
              onSelectObject={openInspectDialog}
              readerMode
            />
          </div>
          <GraphReviewProjectedInteractionSurface
            open={projectedInteractionOpen}
            selectedNode={selectedNodeViewModel}
            selectedRelationship={selectedRelationship}
            onClose={() => setProjectedInteractionOpen(false)}
            onSelectRelationship={(relationship) =>
              selectedNodeViewModel
                ? setSelectedRelationship({
                    laneRole: selectedNodeViewModel.laneRole,
                    sourceNodeId: selectedNodeViewModel.node.node_id,
                    adjacentNodeId: relationship.node_id,
                    edgeId: relationship.edge_id,
                  })
                : undefined
            }
            onClearRelationship={() => setSelectedRelationship(null)}
            onSelectEvidenceDelta={setSelectedEvidenceDeltaId}
          />
        </>
      ) : null}
    </section>
  );
}
