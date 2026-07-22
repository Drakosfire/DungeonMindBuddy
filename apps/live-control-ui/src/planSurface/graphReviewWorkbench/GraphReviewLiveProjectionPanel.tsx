import { useCallback, useEffect, useRef } from "react";

import { UnionSupergraphRecapProjection } from "../graphPreview/UnionSupergraphRecapProjection";
import { useProjection } from "../projection/projectionContext";
import { openGraphNodeFromChip } from "../reference/openGraphNodeFromChip";
import { planReferenceResolutionFromNodeView } from "../reference/planReferenceResolutionFromNodeView";
import { usePlanGraphReferenceResolver } from "../reference/usePlanGraphReferenceResolver";
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
    projectionAuthority,
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
    sessionId,
    campaignId,
  } = useGraphReviewLiveState();
  const { active, activePlanReference, openContentFromChip } = useProjection();
  const { resolvePlanReference, projectionState } = usePlanGraphReferenceResolver();
  const lastRefreshedProjectionKey = useRef<string | null>(null);

  const isWorldAuthority = projectionAuthority === "world_graph";

  // After merge/reload, keep an open Reference card on the fresh node_view
  // (chip opens freeze the prior snapshot).
  useEffect(() => {
    if (projectionStatus !== "ready" || !projection?.node_views) return;
    if (activePlanReference?.kind !== "graph-node" || !activePlanReference.graphNodeId) {
      return;
    }
    const nodeId = activePlanReference.graphNodeId;
    const fresh = projection.node_views[nodeId];
    if (!fresh) return;
    const refreshKey = `${projection.graph_id ?? ""}:${nodeId}:${projection.markdown?.length ?? 0}`;
    if (lastRefreshedProjectionKey.current === refreshKey) return;
    lastRefreshedProjectionKey.current = refreshKey;
    const label = fresh.label ?? nodeId;
    const { ref, resolution } = planReferenceResolutionFromNodeView(fresh, label);
    const glanceOnly =
      active?.kind === "content" ? Boolean(active.glanceOnly) : true;
    openContentFromChip(ref, resolution, glanceOnly, "ready");
  }, [
    active,
    activePlanReference,
    openContentFromChip,
    projection,
    projectionStatus,
  ]);

  const openInspectFromChip = useCallback(
    (selection: { laneRole: "gold" | "live"; nodeId: string }) => {
      const laneViews =
        (selection.laneRole === "gold" ? goldProjection : projection)?.node_views ?? {};
      const nodeView = laneViews[selection.nodeId];
      const label = nodeView?.label ?? selection.nodeId;
      setSelectedNode(selection);
      setSelectedRelationship(null);
      setSelectedDeltaNodeId(selection.nodeId);

      // Preview candidates: prefer local lane node_views (may not be on world head).
      // World authority: local views are already world-backed; still prefer them, then resolve.
      if (nodeView) {
        const { ref, resolution } = planReferenceResolutionFromNodeView(nodeView, label);
        openContentFromChip(ref, resolution, true, "ready");
        return;
      }

      void openGraphNodeFromChip(
        selection.nodeId,
        {
          resolvePlanReference,
          openContentFromChip,
          projectionState,
        },
        label,
      );
    },
    [
      goldProjection,
      openContentFromChip,
      projection,
      projectionState,
      resolvePlanReference,
      setSelectedDeltaNodeId,
      setSelectedNode,
      setSelectedRelationship,
    ],
  );

  return (
    <section
      className={`graph-review-live-projection-panel${
        hasGold && !isWorldAuthority ? "" : " graph-review-live-only-projection-panel"
      }`}
      aria-label={
        isWorldAuthority
          ? "World Graph recap projection"
          : hasGold
            ? "Gold and live source projections"
            : "Ingested recap projection"
      }
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
          {isWorldAuthority
            ? "Loading World Graph recap…"
            : "Loading preview projection…"}
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

      {projectionStatus === "ready" && projection && liveRun && isWorldAuthority ? (
        <div
          className="graph-review-live-only-projections"
          data-testid="graph-review-projection-layout"
          data-projection-authority="world_graph"
        >
          <UnionSupergraphRecapProjection
            payload={projection}
            selectedSessionId={sessionId}
            onSelectSession={() => undefined}
            sessionOptions={[sessionId]}
            selectedCampaignId={campaignId}
            projectionSource="world-graph"
            chrome="embedded"
          />
        </div>
      ) : null}

      {projectionStatus === "ready" && projection && liveRun && !isWorldAuthority ? (
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
            data-projection-authority="preview_union"
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
                onSelectObject={openInspectFromChip}
                readerMode
              />
            ) : null}
            <GraphReviewProjectionLane
              laneRole="live"
              title={hasGold ? "Live Run · read-only" : "Ingested recap · preview candidate"}
              subtitle={runIdentity}
              markdown={projection.markdown ?? FALLBACK_MARKDOWN}
              nodeViews={projection.node_views}
              sourceSpans={paragraphSourceSpans}
              mentionsCount={projection.mentions.length}
              deltaIndex={deltaIndex}
              activeObject={activeLaneObject}
              onActiveObjectChange={setActiveLaneObject}
              onSelectObject={openInspectFromChip}
              readerMode
            />
          </div>
          {/* Authoring rail / promote still open this review-only modal; chips use Plan drawer. */}
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
