import { useCallback, useMemo, useState } from "react";

import type { RecapArtifactRecord, WorldGraphRecapProjection } from "../../api/types";
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
import { useOptionalWorldGraphLensProjection } from "../../graphLens/useWorldGraphLensProjection";
import { PublishedRecapLocalAuthoring } from "../graphReviewWorkbench/PublishedRecapLocalAuthoring";
import { useGraphObjectAuthoringDraft } from "../graphReviewWorkbench/useGraphObjectAuthoringDraft";
import { derivePublishedRecapWorkingProjection } from "../graphReviewWorkbench/publishedRecapWorkingProjection";
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
  recapRecord?: RecapArtifactRecord | null;
  onRefreshProjection?: () => Promise<unknown>;
}

export function WorldGraphRecapProjectionView({
  payload,
  selectedSessionId,
  onSelectSession,
  sessionOptions,
  selectedCampaignId,
  onSelectCampaign,
  recapRecord = null,
  onRefreshProjection,
}: WorldGraphRecapProjectionProps) {
  const adaptedNodeViews = useMemo(
    () => adaptWorldGraphNodeViewMap(payload.nodeViews),
    [payload.nodeViews],
  );
  const worldLensProjection = useOptionalWorldGraphLensProjection();
  const governedWorldNodeViews = useMemo(() => {
    if (worldLensProjection == null) return undefined;
    if (worldLensProjection.projection == null) return null;
    return adaptWorldGraphNodeViewMap(
      Object.fromEntries(
        worldLensProjection.projection.nodes.map((node) => [node.nodeId, node]),
      ),
    );
  }, [worldLensProjection]);
  const authoringDraft = useGraphObjectAuthoringDraft({
    campaignId: selectedCampaignId,
    sessionId: selectedSessionId,
  });
  const workingProjection = useMemo(
    () => derivePublishedRecapWorkingProjection({
      markdown: payload.markdown,
      nodeViews: adaptedNodeViews,
      proposals: authoringDraft.proposals,
      sessionId: selectedSessionId,
    }),
    [adaptedNodeViews, authoringDraft.proposals, payload.markdown, selectedSessionId],
  );
  const [activeNodeId, setActiveNodeId] = useState<string | null>(null);
  const [selectedRelationshipId, setSelectedRelationshipId] = useState<string | null>(null);
  const [expandedRelatedNodeId, setExpandedRelatedNodeId] = useState<string | null>(null);
  const revisionId = payload.snapshot.revisionId;
  const objectOpen = Boolean(activeNodeId);
  const activeWorkingNode = activeNodeId ? workingProjection.nodeViews[activeNodeId] ?? null : null;
  const activeIsLocal = Boolean(activeWorkingNode?.authored && activeNodeId?.startsWith("local-authoring:"));
  const complete = useCompleteWorldObject({
    enabled: objectOpen && !activeIsLocal,
    worldId: worldLensProjection?.request?.worldId ?? payload.snapshot.worldId,
    campaignId: worldLensProjection?.request?.campaignId ?? selectedCampaignId,
    nodeId: activeNodeId,
    revisionPin: worldLensProjection?.projection?.snapshot.revisionId ?? revisionId,
    originSurface: recapOriginSurface(),
    focus: worldLensProjection?.request?.focus ?? {
      kind: "session",
      sessionId: selectedSessionId,
      campaignId: selectedCampaignId,
    },
  });

  const handleInspectNode = useCallback((nodeId: string) => {
    setSelectedRelationshipId(null);
    setExpandedRelatedNodeId(null);
    setActiveNodeId(nodeId);
  }, []);

  const handleSelectRelationship = useCallback((relationship: import("../../graphObjectCard/types").GraphObjectRelationshipViewModel) => {
    setSelectedRelationshipId((current) => current === relationship.id ? null : relationship.id);
    setExpandedRelatedNodeId((current) => current === relationship.targetId ? null : relationship.targetId ?? null);
  }, []);

  const handleCloseObject = useCallback(() => {
    setSelectedRelationshipId(null);
    setExpandedRelatedNodeId(null);
    setActiveNodeId(null);
  }, []);

  const peekLabel = activeWorkingNode?.label?.trim() || complete.nodeView?.label?.trim() || "Campaign memory";
  const rootNodeView = useMemo(() => {
    if (!activeNodeId) return null;
    const workingNode = workingProjection.nodeViews[activeNodeId] ?? null;
    if (activeIsLocal) return workingNode;
    if (!complete.nodeView) return workingNode;
    if (!workingNode) return complete.nodeView;
    const localEdges = workingNode.adjacency.filter((edge) =>
      edge.source_domains.includes("local_authoring"),
    );
    if (!localEdges.length) return complete.nodeView;
    const existingEdgeIds = new Set(complete.nodeView.adjacency.map((edge) => edge.edge_id));
    return {
      ...complete.nodeView,
      adjacency: [
        ...complete.nodeView.adjacency,
        ...localEdges.filter((edge) => !existingEdgeIds.has(edge.edge_id)),
      ],
      suggested_expansions: [
        ...(complete.nodeView.suggested_expansions ?? []),
        ...(workingNode.suggested_expansions ?? []).filter((edge) => !existingEdgeIds.has(edge.edge_id)),
      ],
    };
  }, [activeIsLocal, activeNodeId, complete.nodeView, workingProjection.nodeViews]);
  const expandedNodeView = useMemo(() => {
    if (!expandedRelatedNodeId) return null;
    return complete.nodeViews[expandedRelatedNodeId]
      ?? workingProjection.nodeViews[expandedRelatedNodeId]
      ?? null;
  }, [complete.nodeViews, expandedRelatedNodeId, workingProjection.nodeViews]);

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
      <PublishedRecapLocalAuthoring
        campaignId={selectedCampaignId}
        sessionId={selectedSessionId}
        worldId={payload.snapshot.worldId}
        graphId={payload.graphId}
        markdown={payload.markdown}
        nodeViews={adaptedNodeViews}
        governedWorldNodeViews={governedWorldNodeViews}
        recapRecord={recapRecord}
        onRefreshProjection={onRefreshProjection}
        onInspectNode={handleInspectNode}
        onActiveNodeChange={setActiveNodeId}
        draft={authoringDraft}
      />
      <PeekClaim
        kind="world-object"
        active={objectOpen}
        label={peekLabel}
        onDismiss={handleCloseObject}
      >
        {objectOpen ? (
          <aside className="recap-graph-object-panel" aria-label={peekLabel}>
            {usesCompleteWorldObjectPayload(complete.status) && complete.nodeView ? null : (
              <button
                type="button"
                className="recap-graph-object-panel__close"
                onClick={handleCloseObject}
                aria-label={`Close ${peekLabel}`}
              >
                ×
              </button>
            )}
            {activeIsLocal ? (
              <p
                className="module-muted"
                data-testid="recap-graph-local-object-state"
              >
                Local object · staged in this campaign and session. World memory was not loaded.
              </p>
            ) : complete.status === "loading" || complete.status === "idle" ? (
              <p className="module-muted">Loading campaign memory…</p>
            ) : null}
            {complete.status === "error" || complete.status === "missing" ? (
              <p className="graph-preview-error" role="alert">
                {complete.error}
              </p>
            ) : null}
            <CompleteObjectPartialWarning result={complete.result} />
            {rootNodeView ? (
              <GraphObjectProjectionCard
                mode="campaign-memory"
                nodeView={rootNodeView}
                onSelectRelationship={handleSelectRelationship}
                selectedRelationshipId={selectedRelationshipId}
                onDismiss={handleCloseObject}
                dismissLabel={`Close ${peekLabel}`}
                advancedSlot={complete.result ? (
                  <CompleteWorldObjectAdvancedDetails
                    result={complete.result}
                    originSurface={recapOriginSurface()}
                    bare
                  />
                ) : undefined}
              />
            ) : null}
            {expandedRelatedNodeId && expandedNodeView ? (
              <section
                className="recap-graph-related-object-expansion"
                data-testid="recap-graph-related-object-expansion"
                aria-label={`Expanded related object ${expandedNodeView.label}`}
              >
                <p className="plan-surface-kicker">Connected object</p>
                <GraphObjectProjectionCard
                  mode="campaign-memory"
                  nodeView={expandedNodeView}
                  onSelectRelationship={handleSelectRelationship}
                  selectedRelationshipId={selectedRelationshipId}
                />
              </section>
            ) : expandedRelatedNodeId ? (
              <p
                className="graph-preview-error recap-graph-related-object-unavailable"
                data-testid="recap-graph-related-object-unavailable"
                role="status"
              >
                The connected object is unavailable in this recap projection. The root object remains open.
              </p>
            ) : null}
          </aside>
        ) : null}
      </PeekClaim>
    </div>
  );
}
