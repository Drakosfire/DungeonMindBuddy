import { useCallback, useMemo, useState } from "react";

import type { WorldGraphRecapProjection } from "../../api/types";
import {
  GraphObjectProjectionCard,
} from "../../graphObjectCard/GraphObjectProjectionCard";
import { CompleteObjectPartialWarning } from "../../graphReference/CompleteObjectPartialWarning";
import { CompleteWorldObjectAdvancedDetails } from "../../graphReference/CompleteWorldObjectAdvancedDetails";
import {
  useCompleteWorldObject,
  usesCompleteWorldObjectPayload,
} from "../../graphReference/fullWorldObjectProjection";
import { PeekClaim } from "../../surfaceInteraction/peekHost";
import { adaptWorldGraphNodeViewMap } from "../../worldGraph/worldGraphNodeViewAdapter";
import { GraphProjectionReader } from "../graphProjectionReader/GraphProjectionReader";
import { ReviewCampaignPicker } from "../ReviewCampaignPicker";

function recapOriginSurface(): "ingest" | "plan" {
  if (typeof window === "undefined") return "plan";
  return window.location.pathname.replace(/\/+$/, "") === "/ingest" ? "ingest" : "plan";
}

interface WorldGraphRecapProjectionProps {
  payload: WorldGraphRecapProjection;
  selectedSessionId: string;
  onSelectSession: (sessionId: string) => void;
  sessionOptions: string[];
  selectedCampaignId: string;
  onSelectCampaign: (campaignId: string) => void;
}

export function WorldGraphRecapProjectionView({
  payload,
  selectedSessionId,
  onSelectSession,
  sessionOptions,
  selectedCampaignId,
  onSelectCampaign,
}: WorldGraphRecapProjectionProps) {
  const adaptedNodeViews = useMemo(
    () => adaptWorldGraphNodeViewMap(payload.nodeViews),
    [payload.nodeViews],
  );
  const [activeNodeId, setActiveNodeId] = useState<string | null>(null);
  const [selectedRelationshipId, setSelectedRelationshipId] = useState<string | null>(null);
  const revisionId = payload.snapshot.revisionId;
  const objectOpen = Boolean(activeNodeId);
  const complete = useCompleteWorldObject({
    enabled: objectOpen,
    worldId: payload.snapshot.worldId,
    campaignId: selectedCampaignId,
    nodeId: activeNodeId,
    revisionPin: revisionId,
    originSurface: recapOriginSurface(),
    focus: {
      kind: "session",
      sessionId: selectedSessionId,
      campaignId: selectedCampaignId,
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

  const handleCloseObject = useCallback(() => {
    setSelectedRelationshipId(null);
    setActiveNodeId(null);
  }, []);

  const peekLabel = complete.nodeView?.label?.trim() || "Campaign memory";

  const reviewToolbar = (
    <div className="recap-reader-toolbar">
      <ReviewCampaignPicker selectedCampaignId={selectedCampaignId} onSelect={onSelectCampaign} />
      <label className="graph-preview-run-picker">
        <span>Focus session</span>
        <select value={selectedSessionId} onChange={(event) => onSelectSession(event.target.value)}>
          {sessionOptions.map((sessionId) => (
            <option key={sessionId} value={sessionId}>
              {sessionId.replace("session-", "Session ")}
            </option>
          ))}
        </select>
      </label>
    </div>
  );

  return (
    <div className="recap-reader-root world-graph-recap-root">
      {reviewToolbar}
      <div className="recap-reader-layout union-supergraph-layout">
        <GraphProjectionReader
          markdown={payload.markdown}
          nodeViews={adaptedNodeViews}
          sourceSpans={[]}
          graphId={payload.graphId}
          showGraphId={false}
          documentLabel="Published recap"
          resetKey={`${payload.graphId}:${selectedSessionId}`}
          onInspectNode={handleInspectNode}
          onActiveNodeChange={setActiveNodeId}
          className="world-graph-recap-reader"
        />
      </div>
      <PeekClaim
        kind="world-object"
        active={objectOpen}
        label={peekLabel}
        onDismiss={handleCloseObject}
      >
        {objectOpen ? (
          <aside className="recap-graph-object-panel" aria-label={peekLabel}>
            <header className="recap-graph-object-panel__header">
              <button type="button" onClick={handleCloseObject} aria-label={`Close ${peekLabel}`}>
                ×
              </button>
            </header>
            {complete.status === "loading" || complete.status === "idle" ? (
              <p className="module-muted">Loading campaign memory…</p>
            ) : null}
            {complete.status === "error" || complete.status === "missing" ? (
              <p className="graph-preview-error" role="alert">
                {complete.error}
              </p>
            ) : null}
            <CompleteObjectPartialWarning result={complete.result} />
            {usesCompleteWorldObjectPayload(complete.status) && complete.nodeView ? (
              <GraphObjectProjectionCard
                mode="campaign-memory"
                nodeView={complete.nodeView}
                onSelectRelationshipTarget={handleSelectRelationshipTarget}
                selectedRelationshipId={selectedRelationshipId}
                advancedSlot={complete.result ? (
                  <CompleteWorldObjectAdvancedDetails
                    result={complete.result}
                    originSurface={recapOriginSurface()}
                    bare
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
