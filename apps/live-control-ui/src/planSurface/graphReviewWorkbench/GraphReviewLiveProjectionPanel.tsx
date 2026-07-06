import { useMemo, useState } from "react";

import type { GraphProjectionNodeView } from "../../api/types";
import { ExistingObjectResolverPanel } from "./ExistingObjectResolverPanel";
import type { GraphObjectAuthoringInspectedNode } from "./GraphObjectAuthoringObjectRefPicker";
import { GraphObjectAuthoringSurface } from "./GraphObjectAuthoringSurface";
import { GraphReviewAuthoringReader } from "./GraphReviewAuthoringReader";
import { GraphReviewProjectionLane } from "./GraphReviewProjectionLane";
import { GraphReviewProjectedInteractionSurface } from "./GraphReviewProjectedInteractionSurface";
import { useGraphReviewLiveState } from "./GraphReviewLiveStateContext";
import { useGraphObjectAuthoringDraft } from "./useGraphObjectAuthoringDraft";

const FALLBACK_MARKDOWN = `# Projection unavailable\n\nThe selected live run did not return projected recap Markdown.`;

function metadataValue(value: string | null | undefined): string {
  return value && value.trim() ? value : "—";
}

function toExistingNodeOptions(
  nodeViews: Record<string, GraphProjectionNodeView> | undefined,
): GraphObjectAuthoringInspectedNode[] {
  if (!nodeViews) return [];
  return Object.values(nodeViews).map((node) => ({
    node_id: node.node_id,
    label: node.label,
    kind: node.kind,
    role: node.role,
  }));
}

export function GraphReviewLiveProjectionPanel() {
  const {
    campaignId,
    sessionId,
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
    selectedNode,
    setSelectedNode,
    selectedNodeViewModel,
    selectedRelationship,
    setSelectedRelationship,
    setSelectedDeltaNodeId,
    projectedInteractionOpen,
    setProjectedInteractionOpen,
    setSelectedEvidenceDeltaId,
    authorDraft,
    stageNodeAssertion,
    stageRelationship,
    runIdentity,
  } = useGraphReviewLiveState();

  const { authorMode } = authorDraft;
  const [graphAuthoringModeEnabled, setGraphAuthoringModeEnabled] = useState(false);
  const graphObjectAuthoringDraft = useGraphObjectAuthoringDraft({ campaignId, sessionId });
  const existingGraphObjectNodes = useMemo(
    () => [
      ...toExistingNodeOptions(projection?.node_views),
      ...toExistingNodeOptions(goldProjection?.node_views),
    ],
    [projection, goldProjection],
  );

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
          <div
            className={
              hasGold
                ? "graph-review-real-two-lane-projections"
                : "graph-review-live-only-projections"
            }
          >
            {hasGold && goldProjectionStatus === "loading" ? (
              <p className="graph-review-live-projection-status" role="status">
                Loading gold fixture projection…
              </p>
            ) : null}
            {hasGold && goldProjectionStatus === "error" ? (
              <p className="graph-review-error" role="alert">
                {goldProjectionError ??
                  "Failed to load gold fixture projection."}
              </p>
            ) : null}
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
                onSelectObject={(selection) => {
                  setSelectedNode(selection);
                  setSelectedRelationship(null);
                  setSelectedDeltaNodeId(selection.nodeId);
                  setProjectedInteractionOpen(true);
                }}
                onSelectText={authorDraft.setSelectedText}
                readerMode
              />
            ) : null}
            <div className="graph-authoring-mode-controls">
              <label className="graph-authoring-mode-toggle">
                <input
                  type="checkbox"
                  checked={graphAuthoringModeEnabled}
                  data-testid="graph-authoring-mode-toggle"
                  onChange={(event) => {
                    const enabled = event.target.checked;
                    setGraphAuthoringModeEnabled(enabled);
                    if (!enabled) {
                      graphObjectAuthoringDraft.dismissSelection();
                    }
                  }}
                />
                <span>Author graph objects</span>
              </label>
              {graphAuthoringModeEnabled ? (
                <p className="graph-authoring-mode-hint">
                  Highlight source text in the ingested recap to capture a selection.
                  No graph write happens until a later authoring step.
                </p>
              ) : null}
            </div>
            {hasGold && !graphAuthoringModeEnabled ? (
              <GraphReviewProjectionLane
                laneRole="live"
                title="Live Run · read-only"
                subtitle={runIdentity}
                markdown={projection.markdown ?? FALLBACK_MARKDOWN}
                nodeViews={projection.node_views}
                sourceSpans={paragraphSourceSpans}
                mentionsCount={projection.mentions.length}
                deltaIndex={deltaIndex}
                activeObject={activeLaneObject}
                onActiveObjectChange={setActiveLaneObject}
                onSelectObject={(selection) => {
                  setSelectedNode(selection);
                  setSelectedRelationship(null);
                  setSelectedDeltaNodeId(selection.nodeId);
                  setProjectedInteractionOpen(true);
                }}
                onSelectText={authorDraft.setSelectedText}
                readerMode
              />
            ) : (
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
                documentLabel={hasGold ? "Live run prose" : "Ingested recap"}
                authoringEnabled={graphAuthoringModeEnabled}
                onInspectNode={(nodeId) => {
                  setSelectedNode({ laneRole: "live", nodeId });
                  setSelectedRelationship(null);
                  setSelectedDeltaNodeId(nodeId);
                  setProjectedInteractionOpen(true);
                }}
                onGraphAuthoringAction={(selection) => {
                  graphObjectAuthoringDraft.openWithSelection(selection);
                }}
              />
            )}
          </div>
          {graphAuthoringModeEnabled ? (
            <GraphObjectAuthoringSurface
              selectedSource={graphObjectAuthoringDraft.selectedSource}
              formState={graphObjectAuthoringDraft.formState}
              proposals={graphObjectAuthoringDraft.proposals}
              onFormFieldChange={graphObjectAuthoringDraft.updateFormField}
              onStageProposal={graphObjectAuthoringDraft.stageProposal}
              onRemoveProposal={graphObjectAuthoringDraft.removeProposal}
              linkExistingFormState={graphObjectAuthoringDraft.linkExistingFormState}
              onLinkExistingFieldChange={graphObjectAuthoringDraft.updateLinkExistingField}
              onStageLinkExistingProposal={graphObjectAuthoringDraft.stageLinkExistingProposal}
              relationshipFormState={graphObjectAuthoringDraft.relationshipFormState}
              onRelationshipFieldChange={graphObjectAuthoringDraft.updateRelationshipField}
              onStageRelationshipProposal={graphObjectAuthoringDraft.stageRelationshipProposal}
              campaignId={campaignId}
              sessionId={sessionId}
              sourceRunId={liveRun?.run_id ?? null}
              sourceGraphId={projection.graph_id}
              onCommittedProposals={graphObjectAuthoringDraft.clearCommittedProposals}
              existingNodes={existingGraphObjectNodes}
            />
          ) : null}
          <GraphReviewProjectedInteractionSurface
            open={projectedInteractionOpen}
            selectedNode={selectedNodeViewModel}
            selectedRelationship={selectedRelationship}
            authorMode={authorMode}
            relationshipDraftSource={authorDraft.relationshipDraftSource}
            relationshipPredicate={authorDraft.relationshipPredicate}
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
            onSelectEvidenceDelta={setSelectedEvidenceDeltaId}
            onStageNodeAssertion={stageNodeAssertion}
            onUseAsRelationshipSource={() =>
              selectedNode &&
              authorDraft.setRelationshipDraftSource(selectedNode)
            }
            onRelationshipPredicateChange={authorDraft.setRelationshipPredicate}
            onStageRelationship={stageRelationship}
            resolver={
              <ExistingObjectResolverPanel
                campaignId={campaignId}
                sessionId={sessionId}
                laneRole={selectedNodeViewModel?.laneRole ?? "live"}
                selectedNode={selectedNodeViewModel?.node ?? null}
                projectionGraphId={
                  selectedNodeViewModel?.laneRole === "gold"
                    ? (goldProjection?.graph_id ?? null)
                    : projection.graph_id
                }
                liveRunManifestPath={liveRun.manifest_path}
                onStageLinkIntent={
                  authorMode === "author_draft" && selectedNodeViewModel
                    ? (candidate) =>
                        authorDraft.stageExistingObjectLinkIntent({
                          selectedNode: {
                            laneRole: selectedNodeViewModel.laneRole,
                            nodeId: selectedNodeViewModel.node.node_id,
                            label: selectedNodeViewModel.node.label,
                          },
                          candidate: {
                            ...candidate,
                            candidateId: candidate.candidate_id,
                          },
                        })
                    : undefined
                }
              />
            }
          />
        </>
      ) : null}
    </section>
  );
}
