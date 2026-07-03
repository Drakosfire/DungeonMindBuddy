import { useCallback, useEffect, useMemo, useState } from "react";

import {
  getGoldGraphProjection,
  getGoldReviewEvidence,
  getUnionSupergraphProjection,
  verifyGraphGoldAuthoringCommit,
  LiveApiError,
} from "../../api/liveApi";
import type {
  GoldGraphProjectionResponse,
  GraphGoldAuthoringCommitResponse,
  GraphGoldAuthoringVerifyCommitResponse,
  GoldReviewCompareResponse,
  GoldReviewEvidenceDiffResponse,
  GoldReviewSessionSummary,
  GraphIngestRunSummary,
  GraphReviewLane,
  ManualReviewBedDetail,
  ManualReviewBedSummary,
  UnionSupergraphProjectionResponse,
} from "../../api/types";
import { GraphProjectionReader } from "../graphProjectionReader/GraphProjectionReader";
import type { SourceSpanDomOverlay } from "../graphProjectionReader/sourceSpanHighlight";
import { GraphReviewAdvancedAccordion } from "./GraphReviewAdvancedAccordion";
import { GraphReviewDeltaInspectorPanel } from "./GraphReviewDeltaInspectorPanel";
import { GraphReviewDeltaSummaryPanel } from "./GraphReviewDeltaSummaryPanel";
import { GraphReviewEvidenceSplitPanel } from "./GraphReviewEvidenceSplitPanel";
import { GraphReviewSourceSpanInspectorPanel } from "./GraphReviewSourceSpanInspectorPanel";
import { GraphReviewSourceSpanRail } from "./GraphReviewSourceSpanRail";
import { GraphReviewVariantInventoryPanel } from "./GraphReviewVariantInventoryPanel";
import { GraphReviewVariantLanePanel } from "./GraphReviewVariantLanePanel";
import { GraphReviewVariantObjectInspectorPanel } from "./GraphReviewVariantObjectInspectorPanel";
import { GraphReviewSelectedObjectPanel } from "./GraphReviewSelectedObjectPanel";
import { ExistingObjectResolverPanel } from "./ExistingObjectResolverPanel";
import { GraphReviewLocalStagingTray } from "./GraphReviewLocalStagingTray";
import { GraphReviewAuthoringPreparePreviewPanel } from "./GraphReviewAuthoringPreparePreviewPanel";
import { GRAPH_REVIEW_RELATIONSHIP_PREDICATES } from "./graphReviewLocalAuthoringState";
import { useGraphReviewAuthorDraftWorkflow } from "./useGraphReviewAuthorDraftWorkflow";
import { buildGraphReviewDeltaIndex, buildNodeDeltaPresentationIndex } from "./graphReviewDeltaUtils";
import {
  resolveGraphReviewSelectedNode,
  type GraphReviewSelectedNode,
  type GraphReviewSelectedRelationship,
} from "./graphReviewSelectionUtils";
import { buildEvidenceSelectionForDelta } from "./graphReviewEvidenceSelectionUtils";
import { buildSourceSpanDeltaIndex } from "./graphReviewSourceSpanOverlayUtils";
import type {
  GraphReviewManualVariantLaneView,
  GraphReviewManualVariantSelection,
} from "./graphReviewVariantReferenceUtils";
import { buildVariantLiveInventoryIndex } from "./graphReviewVariantReferenceUtils";

interface GraphReviewLiveProjectionPanelProps {
  campaignId: string;
  sessionId: string;
  liveRun: GraphIngestRunSummary | null;
  selectedSession?: GoldReviewSessionSummary | null;
  compare?: GoldReviewCompareResponse | null;
  compareStatus?: "idle" | "loading" | "ready" | "error";
  goldLane?: GraphReviewLane | null;
  liveLane?: GraphReviewLane | null;
  manualBeds?: ManualReviewBedSummary[];
  manualBedsStatus?: "idle" | "loading" | "ready" | "error";
  manualBedsError?: string | null;
  selectedManualBed?: ManualReviewBedDetail | null;
  selectedVariantLaneView?: GraphReviewManualVariantLaneView | null;
  selectedManualVariant?: GraphReviewManualVariantSelection | null;
  onSelectManualBedId?: (bedId: string | null) => void;
  onSelectManualVariantName?: (variantName: string | null) => void;
}

type ProjectionStatus = "idle" | "loading" | "ready" | "error" | "unavailable";
type EvidenceStatus = "idle" | "loading" | "ready" | "error" | "unavailable";

const FALLBACK_MARKDOWN = `# Projection unavailable\n\nThe selected live run did not return projected recap Markdown.`;

function friendlyProjectionError(error: unknown): string {
  if (error instanceof LiveApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Failed to load selected live lane projection.";
}

function metadataValue(value: string | null | undefined): string {
  return value && value.trim() ? value : "—";
}

export function GraphReviewLiveProjectionPanel({
  campaignId,
  sessionId,
  liveRun,
  compare = null,
  compareStatus = "idle",
  goldLane = null,
  liveLane = null,
  manualBeds = [],
  manualBedsStatus = "idle",
  manualBedsError = null,
  selectedManualBed = null,
  selectedVariantLaneView = null,
  selectedManualVariant = null,
  onSelectManualBedId = () => undefined,
  onSelectManualVariantName = () => undefined,
}: GraphReviewLiveProjectionPanelProps) {
  const [projection, setProjection] =
    useState<UnionSupergraphProjectionResponse | null>(null);
  const [projectionStatus, setProjectionStatus] =
    useState<ProjectionStatus>("idle");
  const [projectionError, setProjectionError] = useState<string | null>(null);
  const [selectedDeltaNodeId, setSelectedDeltaNodeId] = useState<string | null>(
    null,
  );
  const [selectedNode, setSelectedNode] =
    useState<GraphReviewSelectedNode | null>(null);
  const [selectedRelationship, setSelectedRelationship] =
    useState<GraphReviewSelectedRelationship | null>(null);
  const [selectedSourceSpanId, setSelectedSourceSpanId] = useState<
    string | null
  >(null);
  const [selectedEvidenceDeltaId, setSelectedEvidenceDeltaId] = useState<
    string | null
  >(null);
  const [evidenceDiff, setEvidenceDiff] =
    useState<GoldReviewEvidenceDiffResponse | null>(null);
  const [evidenceStatus, setEvidenceStatus] = useState<EvidenceStatus>("idle");
  const [evidenceError, setEvidenceError] = useState<string | null>(null);
  const [selectedVariantInventoryRowId, setSelectedVariantInventoryRowId] =
    useState<string | null>(null);
  const [goldProjection, setGoldProjection] =
    useState<GoldGraphProjectionResponse | null>(null);
  const [goldProjectionStatus, setGoldProjectionStatus] =
    useState<ProjectionStatus>("idle");
  const [goldProjectionError, setGoldProjectionError] = useState<string | null>(
    null,
  );
  const [activeLaneObject, setActiveLaneObject] = useState<{
    laneRole: "gold" | "live";
    nodeId: string;
  } | null>(null);

  const liveRunKey = liveRun
    ? `${liveRun.manifest_path}:${liveRun.preview_union_store_path ?? ""}:${liveRun.preview_union_available}`
    : "";


  useEffect(() => {
    let cancelled = false;

    setProjection(null);
    setProjectionError(null);

    if (!liveRun) {
      setProjectionStatus("idle");
      return () => {
        cancelled = true;
      };
    }

    if (!liveRun.preview_union_available) {
      setProjectionStatus("unavailable");
      return () => {
        cancelled = true;
      };
    }

    setProjectionStatus("loading");

    void getUnionSupergraphProjection({
      campaignId,
      sessionId,
      graphRunManifestPath: liveRun.manifest_path,
      previewUnionStorePath: liveRun.preview_union_store_path ?? null,
    })
      .then((response) => {
        if (cancelled) return;
        setProjection(response);
        setProjectionStatus("ready");
      })
      .catch((error) => {
        if (cancelled) return;
        setProjection(null);
        setProjectionStatus("error");
        setProjectionError(friendlyProjectionError(error));
      });

    return () => {
      cancelled = true;
    };
  }, [campaignId, sessionId, liveRun, liveRunKey]);

  const reloadGoldProjection = useCallback(async () => {
    setGoldProjectionStatus("loading");
    setGoldProjectionError(null);
    const response = await getGoldGraphProjection({ campaignId, sessionId });
    setGoldProjection(response);
    setGoldProjectionStatus("ready");
    return response;
  }, [campaignId, sessionId]);

  useEffect(() => {
    let cancelled = false;
    setGoldProjection(null);
    setGoldProjectionError(null);
    if (!campaignId || !sessionId) {
      setGoldProjectionStatus("idle");
      return () => {
        cancelled = true;
      };
    }
    setGoldProjectionStatus("loading");
    void getGoldGraphProjection({ campaignId, sessionId })
      .then((response) => {
        if (cancelled) return;
        setGoldProjection(response);
        setGoldProjectionStatus("ready");
      })
      .catch((error) => {
        if (cancelled) return;
        setGoldProjection(null);
        setGoldProjectionStatus("error");
        setGoldProjectionError(friendlyProjectionError(error));
      });
    return () => {
      cancelled = true;
    };
  }, [campaignId, sessionId]);


  const selectGoldNodeCard = useCallback((targetId: string, projectionOverride?: GoldGraphProjectionResponse | null) => {
    const sourceProjection = projectionOverride ?? goldProjection;
    if (!sourceProjection?.node_views[targetId]) return false;
    setActiveLaneObject({ laneRole: "gold", nodeId: targetId });
    setSelectedDeltaNodeId(targetId);
    setSelectedNode({ laneRole: "gold", nodeId: targetId });
    setSelectedRelationship(null);
    return true;
  }, [goldProjection]);

  const reloadGoldProjectionAndVerifyCommit = useCallback(async (commitResponse: GraphGoldAuthoringCommitResponse): Promise<GraphGoldAuthoringVerifyCommitResponse> => {
    try {
      const refreshed = await reloadGoldProjection();
      const verification = await verifyGraphGoldAuthoringCommit({
        schema: "dmb_graph_gold_authoring_verify_commit_request_v1",
        campaign_id: commitResponse.campaign_id,
        session_id: commitResponse.session_id,
        commit_id: commitResponse.commit_id,
        applied_operations: commitResponse.applied_operations,
      });
      const firstVisible = verification.checked_operations.find((operation) => operation.verification_status === "found_in_gold_projection" && operation.target_id && refreshed.node_views[operation.target_id]);
      if (firstVisible?.target_id) {
        selectGoldNodeCard(firstVisible.target_id, refreshed);
      }
      return verification;
    } catch (error) {
      setGoldProjectionStatus("error");
      setGoldProjectionError(friendlyProjectionError(error));
      throw error;
    }
  }, [reloadGoldProjection, selectGoldNodeCard]);

  const authorDraft = useGraphReviewAuthorDraftWorkflow({
    campaignId,
    sessionId,
    onReloadAndVerifyCommit: reloadGoldProjectionAndVerifyCommit,
  });
  const { authorMode } = authorDraft;

  useEffect(() => {
    setSelectedSourceSpanId(null);
    setSelectedEvidenceDeltaId(null);
    setSelectedNode(null);
    setSelectedRelationship(null);
    authorDraft.resetLocalDraft();
  }, [authorDraft.resetLocalDraft, liveRunKey, projection?.graph_id, sessionId]);

  const paragraphSourceSpans = useMemo(
    () =>
      (projection?.source_spans ?? [])
        .filter((span) => span.kind === "paragraph")
        .sort((a, b) => (a.ordinal ?? 0) - (b.ordinal ?? 0)),
    [projection?.source_spans],
  );

  const deltaIndex = useMemo(
    () =>
      buildGraphReviewDeltaIndex({
        compare: compare ?? null,
        liveProjection: projection,
        goldLane: goldLane ?? null,
        liveLane: liveLane ?? null,
      }),
    [compare, projection, goldLane, liveLane],
  );

  const sourceSpanDeltaIndex = useMemo(
    () =>
      buildSourceSpanDeltaIndex({
        sourceSpans: paragraphSourceSpans,
        deltas: deltaIndex.deltas,
      }),
    [paragraphSourceSpans, deltaIndex.deltas],
  );

  const liveSourceSpanDeltaOverlays = useMemo(() => {
    const overlays: Record<string, SourceSpanDomOverlay> = {};
    for (const [spanId, presentation] of Object.entries(sourceSpanDeltaIndex.spansById)) {
      overlays[spanId] = { status: presentation.status, label: presentation.label };
    }
    return overlays;
  }, [sourceSpanDeltaIndex]);

  const goldNodeDeltaPresentations = useMemo(
    () => buildNodeDeltaPresentationIndex(deltaIndex, "gold"),
    [deltaIndex],
  );
  const liveNodeDeltaPresentations = useMemo(
    () => buildNodeDeltaPresentationIndex(deltaIndex, "live"),
    [deltaIndex],
  );

  const variantInventoryIndex = useMemo(
    () =>
      buildVariantLiveInventoryIndex({
        variant: selectedVariantLaneView?.variant ?? null,
        compare: compare ?? null,
      }),
    [selectedVariantLaneView?.variant, compare],
  );

  const selectedVariantInventoryRow = useMemo(
    () =>
      variantInventoryIndex.rows.find(
        (row) => row.rowId === selectedVariantInventoryRowId,
      ) ?? null,
    [variantInventoryIndex.rows, selectedVariantInventoryRowId],
  );

  useEffect(() => {
    setSelectedVariantInventoryRowId(null);
  }, [selectedVariantLaneView?.lane.laneId, liveRunKey]);

  const selectedEvidenceDelta = useMemo(
    () =>
      deltaIndex.deltas.find(
        (delta) => delta.deltaId === selectedEvidenceDeltaId,
      ) ?? null,
    [deltaIndex.deltas, selectedEvidenceDeltaId],
  );

  const evidenceSelection = useMemo(
    () => buildEvidenceSelectionForDelta(selectedEvidenceDelta),
    [selectedEvidenceDelta],
  );

  useEffect(() => {
    let cancelled = false;

    setEvidenceDiff(null);
    setEvidenceError(null);

    if (!selectedEvidenceDeltaId) {
      setEvidenceStatus("idle");
      return () => {
        cancelled = true;
      };
    }

    if (evidenceSelection.status !== "queryable") {
      setEvidenceStatus("unavailable");
      return () => {
        cancelled = true;
      };
    }

    if (!liveRun) {
      setEvidenceStatus("unavailable");
      return () => {
        cancelled = true;
      };
    }

    setEvidenceStatus("loading");

    void getGoldReviewEvidence({
      campaignId,
      sessionId,
      manifestPath: liveRun.manifest_path,
      objectKind: evidenceSelection.queryObjectKind!,
      objectId: evidenceSelection.queryObjectId!,
    })
      .then((response) => {
        if (cancelled) return;
        setEvidenceDiff(response);
        setEvidenceStatus("ready");
      })
      .catch((error) => {
        if (cancelled) return;
        setEvidenceDiff(null);
        setEvidenceStatus("error");
        setEvidenceError(
          error instanceof Error
            ? error.message
            : "Failed to load gold/live evidence.",
        );
      });

    return () => {
      cancelled = true;
    };
  }, [
    campaignId,
    sessionId,
    liveRun,
    liveRun?.manifest_path,
    selectedEvidenceDeltaId,
    evidenceSelection.status,
    evidenceSelection.queryObjectKind,
    evidenceSelection.queryObjectId,
  ]);

  const selectedNodeViewModel = useMemo(
    () =>
      resolveGraphReviewSelectedNode(
        selectedNode,
        { goldProjection, liveProjection: projection },
        deltaIndex,
      ),
    [selectedNode, goldProjection, projection, deltaIndex],
  );

  const runIdentity =
    liveRun?.run_label || liveRun?.manifest_path || "selected run";

  const stageNodeFromSelection = () => {
    authorDraft.stageNodeFromSpan();
  };
  const stageNodeAssertion = () => {
    if (!selectedNodeViewModel) return;
    authorDraft.stageNodeAssertion({
        laneRole: selectedNodeViewModel.laneRole,
        nodeId: selectedNodeViewModel.node.node_id,
        label: selectedNodeViewModel.node.label,
        kind: selectedNodeViewModel.node.kind ?? null,
        role: selectedNodeViewModel.node.role ?? null,
    });
  };
  const nodeRef = (selection: GraphReviewSelectedNode) => {
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
  };
  const stageRelationship = () => {
    if (!authorDraft.relationshipDraftSource || !selectedNode) return;
    const sourceNode = nodeRef(authorDraft.relationshipDraftSource);
    const targetNode = nodeRef(selectedNode);
    if (!sourceNode || !targetNode) return;
    authorDraft.stageRelationshipAssertion({
      sourceNode,
      targetNode,
      predicate: authorDraft.relationshipPredicate,
    });
  };

  return (
    <section
      className="graph-review-live-projection-panel"
      aria-label="Selected live lane source projection"
    >
      <header className="graph-review-live-projection-header">
        <div>
          <p className="plan-surface-kicker">Selected live lane</p>
          <h3>Source projection</h3>
          <p>
            Read-only projected source Markdown for the selected graph-ingest
            run. Graph chips are candidate graph behavior; source text remains
            the review surface.
          </p>
        </div>
        {liveRun ? <span>{runIdentity}</span> : null}
      </header>

      <div
        className="graph-review-author-draft-mode-bar"
        aria-label="Mode switch"
      >
        <span>Mode:</span>
        <button
          type="button"
          aria-pressed={authorMode === "review"}
          onClick={() => authorDraft.setAuthorMode("review")}
        >
          Review
        </button>
        <button
          type="button"
          aria-pressed={authorMode === "author_draft"}
          onClick={() => authorDraft.setAuthorMode("author_draft")}
        >
          Author Draft
        </button>
        {authorMode === "author_draft" ? (
          <strong>
            Draft only. No gold fixture, graph state, or corpus file has been
            changed.
          </strong>
        ) : null}
      </div>

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
            className="graph-review-comparison-summary-strip"
            aria-label="Gold vs live comparison summary"
          >
            <strong>Gold vs Live</strong>
            <span>
              {compareStatus === "loading"
                ? "Compare loading…"
                : `${deltaIndex.countsByObjectKind.node} indexed nodes`}
            </span>
            <span>{deltaIndex.countsByStatus.matched} matched</span>
            <span>{deltaIndex.countsByStatus.gold_only} gold-only</span>
            <span>{deltaIndex.countsByStatus.live_only} live-only</span>
            {compareStatus === "error" ? (
              <span>Compare unavailable</span>
            ) : null}
          </div>

          <div className="graph-review-real-two-lane-projections">
            {goldProjectionStatus === "loading" ? (
              <p className="graph-review-live-projection-status" role="status">
                Loading gold fixture projection…
              </p>
            ) : null}
            {goldProjectionStatus === "error" ? (
              <p className="graph-review-error" role="alert">
                {goldProjectionError ??
                  "Failed to load gold fixture projection."}
              </p>
            ) : null}
            {goldProjectionStatus === "ready" && goldProjection ? (
              <section
                className="graph-review-projection-lane"
                aria-label="Gold fixture source projection"
                data-lane-role="gold"
              >
                <header>
                  <p className="plan-surface-kicker">Gold Fixture · read-only</p>
                </header>
                <GraphProjectionReader
                  markdown={goldProjection.markdown ?? FALLBACK_MARKDOWN}
                  nodeViews={goldProjection.node_views}
                  sourceSpans={goldProjection.source_spans}
                  nodeDeltaPresentations={goldNodeDeltaPresentations}
                  disableInlineExplorer
                  resetKey={`gold:${goldProjection.graph_id ?? ""}`}
                  highlightedNodeId={
                    activeLaneObject && activeLaneObject.laneRole !== "gold"
                      ? activeLaneObject.nodeId
                      : null
                  }
                  onHoverNode={(nodeId) => {
                    if (!nodeId) {
                      setActiveLaneObject(null);
                      return;
                    }
                    setActiveLaneObject({
                      laneRole: "gold",
                      nodeId: goldNodeDeltaPresentations[nodeId]?.counterpartNodeId ?? nodeId,
                    });
                  }}
                  onActiveNodeChange={(nodeId) => {
                    if (!nodeId) return;
                    setSelectedNode({ laneRole: "gold", nodeId });
                    setSelectedRelationship(null);
                    setSelectedDeltaNodeId(nodeId);
                  }}
                  onSelectText={(text) =>
                    authorDraft.setSelectedText({ laneRole: "gold", text, sourceOffsets: null })
                  }
                />
              </section>
            ) : null}
            <section
              className="graph-review-projection-lane"
              aria-label="Selected live lane source projection"
              data-lane-role="live"
              data-testid="graph-projection-reader"
            >
              <header>
                <p className="plan-surface-kicker">Live Run · read-only</p>
              </header>
              <GraphProjectionReader
                markdown={projection.markdown ?? FALLBACK_MARKDOWN}
                nodeViews={projection.node_views}
                sourceSpans={paragraphSourceSpans}
                nodeDeltaPresentations={liveNodeDeltaPresentations}
                sourceSpanDeltaOverlays={liveSourceSpanDeltaOverlays}
                selectedSourceSpanId={selectedSourceSpanId}
                disableInlineExplorer
                resetKey={liveRunKey}
                highlightedNodeId={
                  activeLaneObject && activeLaneObject.laneRole !== "live"
                    ? activeLaneObject.nodeId
                    : null
                }
                onHoverNode={(nodeId) => {
                  if (!nodeId) {
                    setActiveLaneObject(null);
                    return;
                  }
                  setActiveLaneObject({
                    laneRole: "live",
                    nodeId: liveNodeDeltaPresentations[nodeId]?.counterpartNodeId ?? nodeId,
                  });
                }}
                onActiveNodeChange={(nodeId) => {
                  if (!nodeId) return;
                  setSelectedNode({ laneRole: "live", nodeId });
                  setSelectedRelationship(null);
                  setSelectedDeltaNodeId(nodeId);
                }}
                onSelectText={(text) =>
                  authorDraft.setSelectedText({ laneRole: "live", text, sourceOffsets: null })
                }
              />
            </section>
          </div>
          <GraphReviewSelectedObjectPanel
            selectedNode={selectedNodeViewModel}
            selectedRelationship={selectedRelationship}
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
          />
          {authorMode === "author_draft" ? (
            <section
              className="graph-review-author-draft-actions"
              aria-label="Author Draft local actions"
            >
              <h3>Author Draft local actions</h3>
              <p>Local staging is ephemeral and not saved.</p>
              <button
                type="button"
                onClick={stageNodeFromSelection}
                disabled={!authorDraft.selectedText?.text.trim()}
              >
                Stage node from selection
              </button>
              {authorDraft.selectedText?.text ? (
                <p>
                  Selected {authorDraft.selectedText.laneRole} text: “{authorDraft.selectedText.text}”
                  (offset approximate/unanchored)
                </p>
              ) : null}
              <button
                type="button"
                onClick={stageNodeAssertion}
                disabled={!selectedNodeViewModel}
              >
                {selectedNodeViewModel?.laneRole === "live"
                  ? "Stage as possible gold node"
                  : "Stage node assertion"}
              </button>
              <button
                type="button"
                onClick={() =>
                  selectedNode && authorDraft.setRelationshipDraftSource(selectedNode)
                }
                disabled={!selectedNode}
              >
                Use as relationship source
              </button>
              <label>
                Predicate{" "}
                <select
                  value={authorDraft.relationshipPredicate}
                  onChange={(event) =>
                    authorDraft.setRelationshipPredicate(
                      event.target.value as typeof authorDraft.relationshipPredicate,
                    )
                  }
                >
                  {GRAPH_REVIEW_RELATIONSHIP_PREDICATES.map((predicate) => (
                    <option key={predicate} value={predicate}>
                      {predicate}
                    </option>
                  ))}
                </select>
              </label>
              <button
                type="button"
                onClick={stageRelationship}
                disabled={
                  !authorDraft.relationshipDraftSource ||
                  !selectedNode ||
                  authorDraft.relationshipDraftSource.nodeId === selectedNode.nodeId
                }
              >
                Stage relationship
              </button>
              {authorDraft.relationshipDraftSource ? (
                <p>
                  Relationship source: {authorDraft.relationshipDraftSource.laneRole}:
                  {authorDraft.relationshipDraftSource.nodeId}
                </p>
              ) : null}
            </section>
          ) : null}
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
          {authorMode === "author_draft" ? (
            <>
              <GraphReviewLocalStagingTray
                proposals={authorDraft.localProposals}
                onUpdateStatus={authorDraft.updateProposalStatus}
                onReset={authorDraft.resetLocalDraft}
              />
              <GraphReviewAuthoringPreparePreviewPanel
                campaignId={campaignId}
                sessionId={sessionId}
                workflow={authorDraft}
                onReloadAndVerifyCommit={reloadGoldProjectionAndVerifyCommit}
                onShowCommittedObject={(targetId) => {
                  selectGoldNodeCard(targetId);
                }}
                canShowCommittedObject={(targetId) => Boolean(goldProjection?.node_views[targetId])}
              />
            </>
          ) : null}
        </>
      ) : null}

      <GraphReviewAdvancedAccordion
        title="Advanced: deltas, evidence & variant inventory"
        description="Diagnostic drill-in for this run: delta/evidence detail and manual-review variant inventory. Prose review, object cards, and authoring above remain the primary surface."
      >
        {projectionStatus === "ready" && projection ? (
          <>
            <GraphReviewDeltaInspectorPanel
              selectedNodeId={selectedDeltaNodeId}
              selectedNode={
                selectedDeltaNodeId
                  ? projection.node_views[selectedDeltaNodeId]
                  : null
              }
              presentation={null}
              onSelectEvidenceDelta={setSelectedEvidenceDeltaId}
              selectedEvidenceDeltaId={selectedEvidenceDeltaId}
            />
            <GraphReviewSourceSpanRail
              index={sourceSpanDeltaIndex}
              selectedSourceSpanId={selectedSourceSpanId}
              onSelectSourceSpan={setSelectedSourceSpanId}
            />
            <GraphReviewSourceSpanInspectorPanel
              selectedSourceSpanId={selectedSourceSpanId}
              presentation={
                selectedSourceSpanId
                  ? sourceSpanDeltaIndex.spansById[selectedSourceSpanId]
                  : null
              }
              onSelectEvidenceDelta={setSelectedEvidenceDeltaId}
              selectedEvidenceDeltaId={selectedEvidenceDeltaId}
            />
            <GraphReviewEvidenceSplitPanel
              selection={evidenceSelection}
              evidence={evidenceDiff}
              status={evidenceStatus}
              errorMessage={evidenceError}
              onClearSelection={() => setSelectedEvidenceDeltaId(null)}
            />
          </>
        ) : null}
        <GraphReviewVariantLanePanel
          campaignId={campaignId}
          sessionId={sessionId}
          beds={manualBeds}
          bedsStatus={manualBedsStatus}
          bedsError={manualBedsError}
          selectedBed={selectedManualBed}
          selectedLaneView={selectedVariantLaneView}
          selectedVariant={selectedManualVariant}
          onSelectBedId={onSelectManualBedId}
          onSelectVariantName={onSelectManualVariantName}
        />
        <GraphReviewVariantInventoryPanel
          index={variantInventoryIndex}
          selectedRowId={selectedVariantInventoryRowId}
          onSelectRow={setSelectedVariantInventoryRowId}
        />
        <GraphReviewVariantObjectInspectorPanel
          selectedRow={selectedVariantInventoryRow}
        />
        {compareStatus === "ready" ||
        projectionStatus === "ready" ||
        projectionStatus === "error" ||
        projectionStatus === "unavailable" ? (
          <GraphReviewDeltaSummaryPanel
            deltaIndex={deltaIndex}
            compareReady={compareStatus === "ready"}
            projectionReady={projectionStatus === "ready"}
            onSelectEvidenceDelta={setSelectedEvidenceDeltaId}
            selectedEvidenceDeltaId={selectedEvidenceDeltaId}
          />
        ) : null}
      </GraphReviewAdvancedAccordion>
    </section>
  );
}
