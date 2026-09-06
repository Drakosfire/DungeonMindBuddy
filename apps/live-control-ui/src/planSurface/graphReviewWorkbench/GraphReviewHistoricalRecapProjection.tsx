import { useCallback, useMemo, useState } from "react";

import type { HistoricalRecapWorldProjectionResponse } from "../../api/types";
import {
  GraphObjectProjectionCard,
  resolveExactProjectedNode,
} from "../../graphObjectCard/GraphObjectProjectionCard";
import { adaptWorldGraphNodeViewMap } from "../../worldGraph/worldGraphNodeViewAdapter";
import { GraphProjectionReader } from "../graphProjectionReader/GraphProjectionReader";

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
  const activeNodeView = activeNodeId
    ? resolveExactProjectedNode(adaptedNodeViews, activeNodeId)
    : null;

  const handleInspectNode = useCallback((nodeId: string) => {
    setSelectedRelationshipId(null);
    setActiveNodeId(nodeId);
  }, []);

  const handleSelectRelationshipTarget = useCallback((targetId: string) => {
    setSelectedRelationshipId(targetId);
    if (resolveExactProjectedNode(adaptedNodeViews, targetId)) {
      setActiveNodeId(targetId);
    }
  }, [adaptedNodeViews]);

  return (
    <div
      className="graph-review-historical-recap-projection"
      data-testid="graph-review-historical-recap-projection"
    >
      <p
        className="graph-review-historical-recap-meta"
        data-testid="graph-review-historical-recap-meta"
      >
        <code>{projection.sourceArtifactId}</code>
        {" · "}
        {projection.campaignId}
        {" · "}
        {projection.sessionId}
        {" · "}
        status <code>{projection.runStatus}</code>
        {" · World "}
        <code>{projection.worldId}</code>
        {" · graph "}
        <code>{projection.graphId}</code>
      </p>
      <p className="recap-reader-hint">
        Exact durable recap text projected onto the current World snapshot. Graph pills resolve
        current World identities; this view is read-only and does not promote the run.
      </p>
      <div className={`recap-reader-layout${activeNodeView ? " graph-explorer-open" : ""}`}>
        <GraphProjectionReader
          markdown={projection.markdown}
          nodeViews={adaptedNodeViews}
          sourceSpans={[]}
          graphId={projection.graphId}
          showGraphId={false}
          documentLabel="Historical recap"
          subtitle={`${projection.campaignId} · ${projection.sessionId}`}
          resetKey={`${projection.runId}:${projection.sourceRevisionId}:${projection.graphId}`}
          onInspectNode={handleInspectNode}
          onActiveNodeChange={setActiveNodeId}
          className="graph-review-historical-recap-reader"
        />
        {activeNodeView ? (
          <aside className="recap-graph-object-panel" aria-label="Graph object">
            <GraphObjectProjectionCard
              nodeView={activeNodeView}
              onSelectRelationshipTarget={handleSelectRelationshipTarget}
              selectedRelationshipId={selectedRelationshipId}
            />
          </aside>
        ) : null}
      </div>
    </div>
  );
}
