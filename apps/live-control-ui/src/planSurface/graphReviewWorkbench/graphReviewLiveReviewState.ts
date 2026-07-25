import { useCallback, useEffect, useMemo, useState } from "react";

import {
  getGoldGraphProjection,
  getGoldReviewEvidence,
  getUnionSupergraphProjection,
  postWorldGraphProjection,
  verifyGraphGoldAuthoringCommit,
  LiveApiError,
} from "../../api/liveApi";
import type {
  GoldGraphProjectionResponse,
  GraphGoldAuthoringCommitResponse,
  GraphGoldAuthoringVerifyCommitResponse,
  GoldReviewCompareResponse,
  GoldReviewEvidenceDiffResponse,
  GraphIngestRunSummary,
  GraphReviewLane,
  ManualReviewBedDetail,
  ManualReviewBedSummary,
  UnionSupergraphProjectionResponse,
  WorldGraphProjection,
} from "../../api/types";
import { buildPlanWorldGraphProjectionRequest } from "../reference/planGraphContextRequest";
import { useGraphReviewAuthorDraftWorkflow } from "./useGraphReviewAuthorDraftWorkflow";
import { buildGraphReviewDeltaIndex } from "./graphReviewDeltaUtils";
import { buildEvidenceSelectionForDelta } from "./graphReviewEvidenceSelectionUtils";
import {
  resolveGraphReviewSelectedNode,
  type GraphReviewSelectedNode,
  type GraphReviewSelectedRelationship,
} from "./graphReviewSelectionUtils";
import { buildSourceSpanDeltaIndex } from "./graphReviewSourceSpanOverlayUtils";
import type {
  GraphReviewManualVariantLaneView,
  GraphReviewManualVariantSelection,
} from "./graphReviewVariantReferenceUtils";
import { buildVariantLiveInventoryIndex } from "./graphReviewVariantReferenceUtils";

export type GraphReviewProjectionStatus =
  | "idle"
  | "loading"
  | "ready"
  | "error"
  | "unavailable";

export type GraphReviewEvidenceStatus =
  | "idle"
  | "loading"
  | "ready"
  | "error"
  | "unavailable";

export interface UseGraphReviewLiveReviewStateOptions {
  campaignId: string;
  sessionId: string;
  liveRun: GraphIngestRunSummary | null;
  hasGold?: boolean;
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

function friendlyProjectionError(error: unknown): string {
  if (error instanceof LiveApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Failed to load selected live lane projection.";
}

export function useGraphReviewLiveReviewState({
  campaignId,
  sessionId,
  liveRun,
  hasGold = false,
  compare = null,
  goldLane = null,
  liveLane = null,
  selectedVariantLaneView = null,
}: UseGraphReviewLiveReviewStateOptions) {
  const [projection, setProjection] =
    useState<UnionSupergraphProjectionResponse | null>(null);
  const [projectionStatus, setProjectionStatus] =
    useState<GraphReviewProjectionStatus>("idle");
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
  const [evidenceStatus, setEvidenceStatus] =
    useState<GraphReviewEvidenceStatus>("idle");
  const [evidenceError, setEvidenceError] = useState<string | null>(null);
  const [selectedVariantInventoryRowId, setSelectedVariantInventoryRowId] =
    useState<string | null>(null);
  const [goldProjection, setGoldProjection] =
    useState<GoldGraphProjectionResponse | null>(null);
  const [goldProjectionStatus, setGoldProjectionStatus] =
    useState<GraphReviewProjectionStatus>("idle");
  const [goldProjectionError, setGoldProjectionError] = useState<string | null>(
    null,
  );
  const [activeLaneObject, setActiveLaneObject] = useState<{
    laneRole: "gold" | "live";
    nodeId: string;
  } | null>(null);
  const [projectedInteractionOpen, setProjectedInteractionOpen] =
    useState(false);

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

  const reloadLiveProjection = useCallback(async () => {
    if (!liveRun?.preview_union_available) {
      throw new Error("Selected live run does not have a preview-union projection.");
    }
    setProjectionStatus("loading");
    setProjectionError(null);
    const response = await getUnionSupergraphProjection({
      campaignId,
      sessionId,
      graphRunManifestPath: liveRun.manifest_path,
      previewUnionStorePath: liveRun.preview_union_store_path ?? null,
    });
    setProjection(response);
    setProjectionStatus("ready");
    return response;
  }, [campaignId, sessionId, liveRun]);

  const reloadGoldProjection = useCallback(async () => {
    setGoldProjectionStatus("loading");
    setGoldProjectionError(null);
    const response = await getGoldGraphProjection({ campaignId, sessionId });
    setGoldProjection(response);
    setGoldProjectionStatus("ready");
    return response;
  }, [campaignId, sessionId]);

  const reloadCommittedWorldProjection = useCallback(
    async (revisionId: string, worldId: string): Promise<WorldGraphProjection> => {
      const trimmedRevision = revisionId.trim();
      if (!trimmedRevision) {
        throw new Error("Committed revision id is required to reload World Graph projection.");
      }
      const trimmedCampaign = (campaignId ?? "").trim();
      if (!trimmedCampaign) {
        throw new Error(
          "Committed revision preserved; campaignless exact runs cannot be reloaded through a campaign projection lens (degraded read).",
        );
      }
      const request = {
        ...buildPlanWorldGraphProjectionRequest({
          worldId,
          campaignId: trimmedCampaign,
          focus: sessionId
            ? { kind: "session" as const, sessionId }
            : { kind: "none" as const, sessionId: null },
        }),
        revisionPin: trimmedRevision,
      };
      const response = await postWorldGraphProjection(request);
      if (response.snapshot.revisionId !== trimmedRevision) {
        throw new Error(
          `World Graph projection revision mismatch: expected ${trimmedRevision}, got ${response.snapshot.revisionId}.`,
        );
      }
      return response;
    },
    [campaignId, sessionId],
  );

  useEffect(() => {
    let cancelled = false;
    setGoldProjection(null);
    setGoldProjectionError(null);
    if (!hasGold || !campaignId || !sessionId) {
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
  }, [campaignId, hasGold, sessionId]);

  const selectGoldNodeCard = useCallback(
    (
      targetId: string,
      projectionOverride?: GoldGraphProjectionResponse | null,
    ) => {
      const sourceProjection = projectionOverride ?? goldProjection;
      if (!sourceProjection?.node_views[targetId]) return false;
      setActiveLaneObject({ laneRole: "gold", nodeId: targetId });
      setSelectedDeltaNodeId(targetId);
      setSelectedNode({ laneRole: "gold", nodeId: targetId });
      setSelectedRelationship(null);
      setProjectedInteractionOpen(true);
      return true;
    },
    [goldProjection],
  );

  const selectDurableObjectIds = useCallback(
    (objectIds: string[]) => {
      const firstId = objectIds.map((id) => id.trim()).find(Boolean);
      if (!firstId) return;
      if (selectGoldNodeCard(firstId)) return;
      if (projection?.node_views[firstId]) {
        setActiveLaneObject({ laneRole: "live", nodeId: firstId });
        setSelectedDeltaNodeId(firstId);
        setSelectedNode({ laneRole: "live", nodeId: firstId });
        setSelectedRelationship(null);
        setProjectedInteractionOpen(true);
        return;
      }
      setActiveLaneObject({ laneRole: "live", nodeId: firstId });
      setSelectedDeltaNodeId(firstId);
      setSelectedNode({ laneRole: "live", nodeId: firstId });
      setSelectedRelationship(null);
      setProjectedInteractionOpen(true);
    },
    [projection?.node_views, selectGoldNodeCard],
  );

  const reloadGoldProjectionAndVerifyCommit = useCallback(
    async (
      commitResponse: GraphGoldAuthoringCommitResponse,
    ): Promise<GraphGoldAuthoringVerifyCommitResponse> => {
      try {
        const refreshed = await reloadGoldProjection();
        const verification = await verifyGraphGoldAuthoringCommit({
          schema: "dmb_graph_gold_authoring_verify_commit_request_v1",
          campaign_id: commitResponse.campaign_id,
          session_id: commitResponse.session_id,
          commit_id: commitResponse.commit_id,
          applied_operations: commitResponse.applied_operations,
        });
        const firstVisible = verification.checked_operations.find(
          (operation) =>
            operation.verification_status === "found_in_gold_projection" &&
            operation.target_id &&
            refreshed.node_views[operation.target_id],
        );
        if (firstVisible?.target_id) {
          selectGoldNodeCard(firstVisible.target_id, refreshed);
        }
        return verification;
      } catch (error) {
        setGoldProjectionStatus("error");
        setGoldProjectionError(friendlyProjectionError(error));
        throw error;
      }
    },
    [reloadGoldProjection, selectGoldNodeCard],
  );

  const authorDraft = useGraphReviewAuthorDraftWorkflow({
    campaignId,
    sessionId,
    onReloadAndVerifyCommit: reloadGoldProjectionAndVerifyCommit,
  });

  useEffect(() => {
    setSelectedSourceSpanId(null);
    setSelectedEvidenceDeltaId(null);
    setSelectedNode(null);
    setSelectedRelationship(null);
    setProjectedInteractionOpen(false);
    authorDraft.resetLocalDraft();
  }, [
    authorDraft.resetLocalDraft,
    liveRunKey,
    projection?.graph_id,
    sessionId,
  ]);

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

  return {
    projection,
    projectionStatus,
    projectionError,
    reloadLiveProjection,
    reloadCommittedWorldProjection,
    goldProjection,
    goldProjectionStatus,
    goldProjectionError,
    reloadGoldProjection,
    reloadGoldProjectionAndVerifyCommit,
    deltaIndex,
    sourceSpanDeltaIndex,
    paragraphSourceSpans,
    selectedDeltaNodeId,
    setSelectedDeltaNodeId,
    selectedNode,
    setSelectedNode,
    selectedNodeViewModel,
    selectedRelationship,
    setSelectedRelationship,
    selectedSourceSpanId,
    setSelectedSourceSpanId,
    selectedEvidenceDeltaId,
    setSelectedEvidenceDeltaId,
    evidenceSelection,
    evidenceDiff,
    evidenceStatus,
    evidenceError,
    variantInventoryIndex,
    selectedVariantInventoryRowId,
    setSelectedVariantInventoryRowId,
    selectedVariantInventoryRow,
    activeLaneObject,
    setActiveLaneObject,
    projectedInteractionOpen,
    setProjectedInteractionOpen,
    selectGoldNodeCard,
    selectDurableObjectIds,
    authorDraft,
    stageNodeFromSelection,
    stageNodeAssertion,
    stageRelationship,
    runIdentity,
  };
}

export type GraphReviewLiveReviewState = ReturnType<
  typeof useGraphReviewLiveReviewState
>;
