import { useCallback, useMemo, useState } from "react";

import type { HistoricalRecapWorldProjectionResponse } from "../../api/types";
import {
  GraphObjectProjectionCard,
} from "../../graphObjectCard/GraphObjectProjectionCard";
import { adaptWorldGraphNodeViewMap } from "../../worldGraph/worldGraphNodeViewAdapter";
import { GraphProjectionReader } from "../graphProjectionReader/GraphProjectionReader";
import { useCompleteWorldObject } from "../../graphReference/fullWorldObjectProjection";

interface GraphReviewHistoricalRecapProjectionProps {
  projection: HistoricalRecapWorldProjectionResponse;
}

export function GraphReviewHistoricalRecapProjection({
  projection,
}: GraphReviewHistoricalRecapProjectionProps) {
  const adaptedNodeViews = useMemo(
    () => adaptWorldGraphNodeViewMap(projection.nodeViews),
    [projection.nodeViews],
  );
  const [activeNodeId, setActiveNodeId] = useState<string | null>(null);
  const [selectedRelationshipId, setSelectedRelationshipId] = useState<string | null>(null);
  const complete = useCompleteWorldObject({
    enabled: Boolean(activeNodeId),
    worldId: projection.worldId || projection.snapshot.worldId,
    campaignId: projection.campaignId,
    nodeId: activeNodeId,
    revisionPin: projection.snapshot.revisionId,
    originSurface: "ingest",
    focus: {
      kind: "session",
      sessionId: projection.sessionId,
      campaignId: projection.campaignId,
    },
  });

  const handleInspectNode = useCallback((nodeId: string) => {
    setSelectedRelationshipId(null);
    setActiveNodeId(nodeId);
  }, []);

  const handleSelectRelationshipTarget = useCallback((targetId: string) => {
    setSelectedRelationshipId(targetId);
    setActiveNodeId(targetId);
  }, []);

  const objectOpen = Boolean(activeNodeId);

  return (
    <div
      className="graph-review-historical-recap-projection"
      data-testid="graph-review-historical-recap-projection"
    >
      <div className={`recap-reader-layout${objectOpen ? " graph-explorer-open" : ""}`}>
        <GraphProjectionReader
          markdown={projection.markdown}
          nodeViews={adaptedNodeViews}
          sourceSpans={[]}
          graphId={projection.graphId}
          showGraphId={false}
          documentLabel="Historical recap"
          resetKey={`${projection.runId}:${projection.sourceRevisionId}:${projection.graphId}`}
          onInspectNode={handleInspectNode}
          onActiveNodeChange={setActiveNodeId}
          className="graph-review-historical-recap-reader"
        />
        {objectOpen ? (
          <aside className="recap-graph-object-panel" aria-label="Graph object">
            {complete.status === "loading" || complete.status === "idle" ? (
              <p className="module-muted">Loading complete World object…</p>
            ) : null}
            {complete.status === "error" || complete.status === "missing" ? (
              <p className="graph-preview-error" role="alert">
                {complete.error}
              </p>
            ) : null}
            {complete.status === "ready" && complete.nodeView ? (
              <GraphObjectProjectionCard
                nodeView={complete.nodeView}
                onSelectRelationshipTarget={handleSelectRelationshipTarget}
                selectedRelationshipId={selectedRelationshipId}
              />
            ) : null}
          </aside>
        ) : null}
      </div>
    </div>
  );
}
