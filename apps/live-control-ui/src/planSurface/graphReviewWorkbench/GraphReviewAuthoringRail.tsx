import { useEffect, useMemo, useState, type ChangeEvent } from "react";

import { ExistingObjectResolverPanel } from "./ExistingObjectResolverPanel";
import type { GraphObjectAuthoringInspectedNode } from "./GraphObjectAuthoringObjectRefPicker";
import { GraphMergeReconciliationMaterializationPanel } from "./GraphMergeReconciliationMaterializationPanel";
import { GraphObjectAuthoringSurface } from "./GraphObjectAuthoringSurface";
import { buildGraphAuthoringSelectionFromRecapNode } from "./graphAuthoringSelection";
import { GraphReviewAuthoringPreparePreviewPanel } from "./GraphReviewAuthoringPreparePreviewPanel";
import { GraphReviewLocalStagingTray } from "./GraphReviewLocalStagingTray";
import { GraphReviewMergeCandidatesPanel } from "./GraphReviewMergeCandidatesPanel";
import type { GraphObjectMergeCandidate } from "./graphObjectMergeCandidates";
import { buildObjectRefFromInspectedNode } from "./graphObjectAuthoringDraft";
import {
  formatGraphObjectType,
  gameSummaryForNode,
  resolveGraphReviewSelectedNode,
  type GraphReviewSelectedNode,
} from "./graphReviewSelectionUtils";
import type { UseGraphObjectAuthoringDraftResult } from "./useGraphObjectAuthoringDraft";
import { useGraphReviewLiveState } from "./GraphReviewLiveStateContext";

export type AuthoringWorkflowTab =
  | "create_new"
  | "modify_existing"
  | "merge_candidates"
  | "relationships"
  | "stage_commit";

function toExistingNodeOptions(
  nodeViews: Record<string, import("../../api/types").GraphProjectionNodeView> | undefined,
): GraphObjectAuthoringInspectedNode[] {
  if (!nodeViews) return [];
  return Object.values(nodeViews).map((node) => ({
    node_id: node.node_id,
    label: node.label,
    kind: node.kind,
    role: node.role,
    aliases: node.aliases,
    authored:
      node.authored === true || node.source_domains.includes("authored_overlay"),
    sourceAnchorText: node.source_anchor_text ?? null,
  }));
}

export interface GraphReviewAuthoringRailProps {
  selectedAuthoringNode: GraphReviewSelectedNode | null;
  graphObjectAuthoringDraft: UseGraphObjectAuthoringDraftResult;
  activeTab: AuthoringWorkflowTab;
  onActiveTabChange: (tab: AuthoringWorkflowTab) => void;
}

export function GraphReviewAuthoringRail({
  selectedAuthoringNode,
  graphObjectAuthoringDraft,
  activeTab,
  onActiveTabChange,
}: GraphReviewAuthoringRailProps) {
  const {
    campaignId,
    sessionId,
    hasGold,
    liveRun,
    projection,
    goldProjection,
    deltaIndex,
    reloadLiveProjection,
    reloadGoldProjectionAndVerifyCommit,
    selectGoldNodeCard,
    authorDraft,
    stageNodeFromSelection,
  } = useGraphReviewLiveState();

  const selectedAuthoringViewModel = useMemo(
    () =>
      resolveGraphReviewSelectedNode(
        selectedAuthoringNode,
        { goldProjection, liveProjection: projection },
        deltaIndex,
      ),
    [selectedAuthoringNode, goldProjection, projection, deltaIndex],
  );

  const [linkRecapPillEnabled, setLinkRecapPillEnabled] = useState(false);
  const [focusedMergeCandidate, setFocusedMergeCandidate] =
    useState<GraphObjectMergeCandidate | null>(null);

  useEffect(() => {
    setLinkRecapPillEnabled(false);
  }, [activeTab, selectedAuthoringNode?.nodeId, selectedAuthoringNode?.laneRole]);

  const existingGraphObjectNodes = useMemo(
    () => [
      ...toExistingNodeOptions(projection?.node_views),
      ...toExistingNodeOptions(goldProjection?.node_views),
    ],
    [projection, goldProjection],
  );

  const sharedSurfaceProps = {
    selectedSource: graphObjectAuthoringDraft.selectedSource,
    formState: graphObjectAuthoringDraft.formState,
    proposals: graphObjectAuthoringDraft.proposals,
    onFormFieldChange: graphObjectAuthoringDraft.updateFormField,
    onStageProposal: graphObjectAuthoringDraft.stageProposal,
    onRemoveProposal: graphObjectAuthoringDraft.removeProposal,
    linkExistingFormState: graphObjectAuthoringDraft.linkExistingFormState,
    onLinkExistingFieldChange: graphObjectAuthoringDraft.updateLinkExistingField,
    onStageLinkExistingProposal: graphObjectAuthoringDraft.stageLinkExistingProposal,
    relationshipFormState: graphObjectAuthoringDraft.relationshipFormState,
    onRelationshipFieldChange: graphObjectAuthoringDraft.updateRelationshipField,
    onStageRelationshipProposal: graphObjectAuthoringDraft.stageRelationshipProposal,
    campaignId,
    sessionId,
    sourceRunId: liveRun?.run_id ?? null,
    sourceGraphId: projection?.graph_id ?? null,
    onCommittedProposals: graphObjectAuthoringDraft.clearCommittedProposals,
    onRefreshProjection: reloadLiveProjection,
    onReviewMerge: (candidate) => {
      setFocusedMergeCandidate(candidate);
      onActiveTabChange("merge_candidates");
    },
    existingNodes: existingGraphObjectNodes,
    laneRole: "live" as const,
    liveRunManifestPath: liveRun?.manifest_path ?? null,
    previewUnionStorePath: liveRun?.preview_union_store_path ?? null,
    projectionNodeViews: projection?.node_views,
  };

  return (
    <aside
      className="graph-review-author-draft-rail"
      aria-label="Author Draft rail"
      data-testid="graph-review-authoring-rail"
    >
      <nav
        className="graph-review-authoring-workflow-tabs"
        role="tablist"
        aria-label="Authoring workflow"
      >
        <button
          type="button"
          role="tab"
          id="authoring-tab-create-new"
          aria-selected={activeTab === "create_new"}
          aria-controls="authoring-panel-create-new"
          className={activeTab === "create_new" ? "is-active" : ""}
          onClick={() => onActiveTabChange("create_new")}
        >
          New object
        </button>
        <button
          type="button"
          role="tab"
          id="authoring-tab-modify-existing"
          aria-selected={activeTab === "modify_existing"}
          aria-controls="authoring-panel-modify-existing"
          className={activeTab === "modify_existing" ? "is-active" : ""}
          onClick={() => onActiveTabChange("modify_existing")}
        >
          Existing object
        </button>
        <button
          type="button"
          role="tab"
          id="authoring-tab-merge-candidates"
          aria-selected={activeTab === "merge_candidates"}
          aria-controls="authoring-panel-merge-candidates"
          className={activeTab === "merge_candidates" ? "is-active" : ""}
          onClick={() => onActiveTabChange("merge_candidates")}
        >
          Merge candidates
        </button>
        <button
          type="button"
          role="tab"
          id="authoring-tab-relationships"
          aria-selected={activeTab === "relationships"}
          aria-controls="authoring-panel-relationships"
          className={activeTab === "relationships" ? "is-active" : ""}
          onClick={() => onActiveTabChange("relationships")}
        >
          Relationships
        </button>
        <button
          type="button"
          role="tab"
          id="authoring-tab-stage-commit"
          aria-selected={activeTab === "stage_commit"}
          aria-controls="authoring-panel-stage-commit"
          className={activeTab === "stage_commit" ? "is-active" : ""}
          onClick={() => onActiveTabChange("stage_commit")}
        >
          Stage &amp; commit
        </button>
      </nav>

      {activeTab === "create_new" ? (
        <div
          id="authoring-panel-create-new"
          role="tabpanel"
          aria-labelledby="authoring-tab-create-new"
          className="graph-review-authoring-workflow-panel"
        >
          <GraphObjectAuthoringSurface
            {...sharedSurfaceProps}
            focusPanel="create_new"
          />
        </div>
      ) : null}

      <div
        id="authoring-panel-modify-existing"
        role="tabpanel"
        aria-labelledby="authoring-tab-modify-existing"
        className="graph-review-authoring-workflow-panel"
        hidden={activeTab !== "modify_existing"}
      >
        <section className="graph-review-authoring-modify-existing-panel">
          <header>
            <p className="plan-surface-kicker">Existing object</p>
            <h3>Search existing objects</h3>
            <p className="graph-object-authoring-surface-hint">
              Search by name across campaign sources. Use identity merge to
              collapse duplicate records. Recap alias links are separate — opt in
              below only when you want to associate recap text with a match.
            </p>
          </header>
          {selectedAuthoringViewModel ? (
            <div className="graph-review-existing-object-link-opt-in">
              <label className="graph-review-existing-object-link-opt-in-label">
                <input
                  type="checkbox"
                  checked={linkRecapPillEnabled}
                  onChange={(event: ChangeEvent<HTMLInputElement>) =>
                    setLinkRecapPillEnabled(event.target.checked)
                  }
                />
                Link recap text to existing object:{" "}
                {selectedAuthoringViewModel.node.label}
              </label>
              {linkRecapPillEnabled ? (
                <p className="graph-review-muted">
                  Recap alias link only — not an object identity merge.{" "}
                  {formatGraphObjectType(
                    selectedAuthoringViewModel.node.kind,
                    selectedAuthoringViewModel.node.role,
                  )}
                  {gameSummaryForNode(selectedAuthoringViewModel.node)
                    ? ` · ${gameSummaryForNode(selectedAuthoringViewModel.node)}`
                    : ""}
                </p>
              ) : null}
            </div>
          ) : null}
          <ExistingObjectResolverPanel
            campaignId={campaignId}
            sessionId={sessionId}
            laneRole="live"
            linkSourceNode={
              linkRecapPillEnabled && selectedAuthoringViewModel
                ? selectedAuthoringViewModel.node
                : null
            }
            mergeReviewSourceNode={
              selectedAuthoringViewModel ? selectedAuthoringViewModel.node : null
            }
            projectionGraphId={projection?.graph_id ?? null}
            liveRunManifestPath={liveRun?.manifest_path ?? null}
            nodeViews={projection?.node_views ?? null}
            overlayProposals={graphObjectAuthoringDraft.proposals}
            onStageLinkIntent={
              linkRecapPillEnabled && selectedAuthoringViewModel
                ? (candidate) => {
                    graphObjectAuthoringDraft.stageLinkExistingFromResolver({
                      selection: buildGraphAuthoringSelectionFromRecapNode({
                        campaignId,
                        sessionId,
                        graphId: projection?.graph_id ?? null,
                        sourceArtifactPath: liveRun?.manifest_path ?? null,
                        laneRole: selectedAuthoringViewModel.laneRole,
                        node: selectedAuthoringViewModel.node,
                      }),
                      candidate,
                    });
                  }
                : undefined
            }
            onStageLinkIntentComplete={() => onActiveTabChange("stage_commit")}
            onReviewMerge={(candidate) => {
              setFocusedMergeCandidate(candidate);
              onActiveTabChange("merge_candidates");
            }}
            onStageSearchMerge={(input) =>
              graphObjectAuthoringDraft.stageMergeProposal({
                survivorObjectRef: input.survivorObjectRef,
                mergedObjectRefs: input.mergedObjectRefs,
                mergeReason: input.mergeReason,
                matchedFeatures: input.matchedFeatures,
                sourceGraphId: input.sourceGraphId ?? projection?.graph_id ?? null,
              })
            }
            onStageSearchMergeComplete={() => onActiveTabChange("stage_commit")}
          />
        </section>
      </div>

      {activeTab === "merge_candidates" ? (
        <div
          id="authoring-panel-merge-candidates"
          role="tabpanel"
          aria-labelledby="authoring-tab-merge-candidates"
          className="graph-review-authoring-workflow-panel"
        >
          <GraphReviewMergeCandidatesPanel
            nodeViews={projection?.node_views ?? null}
            graphObjectAuthoringDraft={graphObjectAuthoringDraft}
            selectedPillLabel={selectedAuthoringViewModel?.node.label ?? null}
            focusedCandidate={focusedMergeCandidate}
          />
        </div>
      ) : null}

      {activeTab === "relationships" ? (
        <div
          id="authoring-panel-relationships"
          role="tabpanel"
          aria-labelledby="authoring-tab-relationships"
          className="graph-review-authoring-workflow-panel"
        >
          <GraphObjectAuthoringSurface
            {...sharedSurfaceProps}
            focusPanel="relationships"
          />
        </div>
      ) : null}

      {activeTab === "stage_commit" ? (
        <div
          id="authoring-panel-stage-commit"
          role="tabpanel"
          aria-labelledby="authoring-tab-stage-commit"
          className="graph-review-authoring-workflow-panel"
        >
          <GraphObjectAuthoringSurface
            {...sharedSurfaceProps}
            focusPanel="stage_overlay"
          />
          <details
            className="graph-review-advanced-materialization-panel"
            data-testid="graph-review-advanced-materialization-panel"
          >
            <summary>Advanced: backfill durable materialization</summary>
            <GraphMergeReconciliationMaterializationPanel
              campaignId={campaignId}
              sessionId={sessionId}
              previewUnionStorePath={liveRun?.preview_union_store_path ?? null}
              onRefreshProjection={reloadLiveProjection}
            />
          </details>
          {hasGold || authorDraft.localProposals.length > 0 ? (
            <details
              className="graph-review-gold-fixture-draft-panel"
              data-testid="graph-review-gold-fixture-draft-panel"
            >
              <summary>
                Gold fixture draft (whole-graph legacy path)
              </summary>
              <GraphReviewLocalStagingTray
                proposals={authorDraft.localProposals}
                onUpdateStatus={authorDraft.updateProposalStatus}
                onReset={authorDraft.resetLocalDraft}
                selectedText={authorDraft.selectedText}
                onStageNodeFromSelection={stageNodeFromSelection}
              />
              <GraphReviewAuthoringPreparePreviewPanel
                campaignId={campaignId}
                sessionId={sessionId}
                hasGold={hasGold}
                workflow={authorDraft}
                onReloadAndVerifyCommit={reloadGoldProjectionAndVerifyCommit}
                onShowCommittedObject={(targetId) => {
                  selectGoldNodeCard(targetId);
                }}
                canShowCommittedObject={(targetId) =>
                  Boolean(goldProjection?.node_views[targetId])
                }
              />
            </details>
          ) : null}
        </div>
      ) : null}
    </aside>
  );
}

export function nodeRefFromSelection(
  selection: GraphReviewSelectedNode,
  projection: import("../../api/types").UnionSupergraphProjectionResponse | null,
  goldProjection: import("../../api/types").GoldGraphProjectionResponse | null,
): { laneRole: GraphReviewSelectedNode["laneRole"]; nodeId: string; label: string } | null {
  const node =
    selection.laneRole === "gold"
      ? goldProjection?.node_views[selection.nodeId]
      : projection?.node_views[selection.nodeId];
  return node
    ? {
        laneRole: selection.laneRole,
        nodeId: selection.nodeId,
        label: node.label,
      }
    : null;
}

export function buildInspectedNodeRef(
  selection: GraphReviewSelectedNode,
  projection: import("../../api/types").UnionSupergraphProjectionResponse | null,
  goldProjection: import("../../api/types").GoldGraphProjectionResponse | null,
) {
  const node =
    selection.laneRole === "gold"
      ? goldProjection?.node_views[selection.nodeId]
      : projection?.node_views[selection.nodeId];
  if (!node) return null;
  return buildObjectRefFromInspectedNode({
    node_id: node.node_id,
    label: node.label,
    kind: node.kind,
    role: node.role,
  });
}

function relationshipSourceNodeId(
  formState: UseGraphObjectAuthoringDraftResult["relationshipFormState"],
): string | null {
  const ref = formState.sourceObjectRef;
  return ref?.refKind === "existing_graph_node" ? ref.nodeId : null;
}

export function applyAuthoringPillSelection(input: {
  nodeId: string;
  projection: import("../../api/types").UnionSupergraphProjectionResponse | null;
  goldProjection: import("../../api/types").GoldGraphProjectionResponse | null;
  relationshipFormState: UseGraphObjectAuthoringDraftResult["relationshipFormState"];
  updateRelationshipField: UseGraphObjectAuthoringDraftResult["updateRelationshipField"];
}): GraphReviewSelectedNode {
  const selected: GraphReviewSelectedNode = { laneRole: "live", nodeId: input.nodeId };
  const sourceNodeId = relationshipSourceNodeId(input.relationshipFormState);
  const inspectedRef = buildInspectedNodeRef(
    selected,
    input.projection,
    input.goldProjection,
  );

  if (sourceNodeId && sourceNodeId !== input.nodeId && inspectedRef) {
    input.updateRelationshipField("targetObjectRef", inspectedRef);
    return selected;
  }

  if (!sourceNodeId && inspectedRef) {
    input.updateRelationshipField("sourceObjectRef", inspectedRef);
  }

  return selected;
}
