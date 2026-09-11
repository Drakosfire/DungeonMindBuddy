import { useCallback, useMemo, useState } from "react";

import type { HistoricalRecapWorldProjectionResponse } from "../../api/types";
import {
  GraphObjectProjectionCard,
} from "../../graphObjectCard/GraphObjectProjectionCard";
import { adaptWorldGraphNodeViewMap } from "../../worldGraph/worldGraphNodeViewAdapter";
import { GraphProjectionReader } from "../graphProjectionReader/GraphProjectionReader";
import { useCompleteWorldObject, usesCompleteWorldObjectPayload } from "../../graphReference/fullWorldObjectProjection";
import { CompleteObjectPartialWarning } from "../../graphReference/CompleteObjectPartialWarning";
import { CompleteWorldObjectAdvancedDetails } from "../../graphReference/CompleteWorldObjectAdvancedDetails";
import { PeekClaim } from "../../surfaceInteraction/peekHost";

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

  const handleCloseObject = useCallback(() => {
    setSelectedRelationshipId(null);
    setActiveNodeId(null);
  }, []);

  return (
    <div
      className="graph-review-historical-recap-projection"
      data-testid="graph-review-historical-recap-projection"
    >
      <div className="recap-reader-layout graph-review-historical-recap-layout">
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
      </div>
      <PeekClaim kind="world-object" active={objectOpen}>
        {objectOpen ? (
          <aside className="recap-graph-object-panel" aria-label="Graph object">
            <header className="recap-graph-object-panel__header">
              <span>World object</span>
              <button type="button" onClick={handleCloseObject} aria-label="Close World object">
                ×
              </button>
            </header>
            {complete.status === "loading" || complete.status === "idle" ? (
              <p className="module-muted">Loading complete World object…</p>
            ) : null}
            {complete.status === "error" || complete.status === "missing" ? (
              <p className="graph-preview-error" role="alert">
                {complete.error}
              </p>
            ) : null}
            <CompleteObjectPartialWarning result={complete.result} />
            {usesCompleteWorldObjectPayload(complete.status) && complete.nodeView ? (
              <GraphObjectProjectionCard
                nodeView={complete.nodeView}
                onSelectRelationshipTarget={handleSelectRelationshipTarget}
                selectedRelationshipId={selectedRelationshipId}
                advancedSlot={complete.result ? (
                  <CompleteWorldObjectAdvancedDetails
                    result={complete.result}
                    originSurface="ingest"
                  />
                ) : undefined}
              />
            ) : null}
          </aside>
        ) : null}
      </PeekClaim>
    </div>
  );
}
