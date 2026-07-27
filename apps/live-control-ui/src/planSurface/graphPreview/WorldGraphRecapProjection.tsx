import { useCallback, useMemo, useState } from "react";

import type { WorldGraphRecapProjection } from "../../api/types";
import {
  GraphObjectProjectionCard,
  resolveExactProjectedNode,
} from "../../graphObjectCard/GraphObjectProjectionCard";
import { adaptWorldGraphNodeViewMap } from "../../worldGraph/worldGraphNodeViewAdapter";
import { GraphProjectionReader } from "../graphProjectionReader/GraphProjectionReader";
import { ReviewCampaignPicker } from "../ReviewCampaignPicker";

interface WorldGraphRecapProjectionProps {
  payload: WorldGraphRecapProjection;
  selectedSessionId: string;
  onSelectSession: (sessionId: string) => void;
  sessionOptions: string[];
  selectedCampaignId: string;
  onSelectCampaign: (campaignId: string) => void;
}

function buildContinueInBuildHref(
  campaignId: string,
  nodeId: string,
  revisionId: string,
): string {
  const params = new URLSearchParams({
    campaign: campaignId,
    graphNodeId: nodeId,
    graphRevision: revisionId,
  });
  return `/build?${params.toString()}`;
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

  const activeNodeView = activeNodeId
    ? resolveExactProjectedNode(adaptedNodeViews, activeNodeId)
    : null;

  const revisionId = payload.snapshot.revisionId;

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

  const continueInBuildHref =
    activeNodeId && revisionId
      ? buildContinueInBuildHref(selectedCampaignId, activeNodeId, revisionId)
      : null;

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
      <header className="recap-reader-header">
        <div>
          <p className="plan-surface-kicker">Published World Graph · session recap</p>
          <h2>Session focus lens</h2>
          <p>
            This view reads the selected canonical recap against the campaign&apos;s durable World Graph
            memory. Chips open exact durable node ids from the published projection — not preview-union
            candidates.
          </p>
          <p className="union-supergraph-source-note">
            Source: published World Graph revision <code>{revisionId}</code>.
            {payload.snapshot.isHead ? " Current head." : " Pinned read from this response."}
          </p>
        </div>
        <span className="union-supergraph-graph-id">{payload.graphId}</span>
      </header>

      <p className="recap-reader-hint world-graph-recap-mentions-hint">
        Read-only TipTap projection of the published session recap. Editing and corpus writes are intentionally out of
        scope here. Graph chips open exact durable World Graph node ids; evidence highlights show the recap paragraph
        that supports the selected graph context. {payload.mentions.length} graph mention
        {payload.mentions.length === 1 ? "" : "s"} projected.
      </p>

      <div className={`recap-reader-layout union-supergraph-layout${activeNodeView ? " graph-explorer-open" : ""}`}>
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
        {activeNodeView ? (
          <aside className="recap-graph-object-panel" aria-label="Graph object">
            <GraphObjectProjectionCard
              nodeView={activeNodeView}
              onSelectRelationshipTarget={handleSelectRelationshipTarget}
              selectedRelationshipId={selectedRelationshipId}
              actions={
                continueInBuildHref ? (
                  <a className="graph-object-card__action" href={continueInBuildHref}>
                    Continue in Build
                  </a>
                ) : null
              }
            />
          </aside>
        ) : null}
      </div>
    </div>
  );
}
