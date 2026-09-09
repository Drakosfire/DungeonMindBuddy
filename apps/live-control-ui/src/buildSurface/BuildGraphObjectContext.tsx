import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { LiveApiError } from "../api/liveApi";
import type { GraphProjectionNodeView, WorldGraphObjectProjectionResult } from "../api/types";
import {
  GraphObjectProjectionCard,
  resolveExactProjectedNode,
} from "../graphObjectCard/GraphObjectProjectionCard";
import { loadCompleteWorldObject, completeObjectNodeMap } from "../graphReference/fullWorldObjectProjection";
import { CompleteObjectPartialWarning } from "../graphReference/CompleteObjectPartialWarning";
import {
  admitBuildDocumentScope,
  getWorldIdForCampaign,
} from "../worldGraph/worldGraphSurfaceContext";

export interface BuildGraphPointer {
  campaignId: string;
  graphNodeId: string;
  graphRevision: string | null;
}

export function parseBuildGraphPointerFromLocation(): BuildGraphPointer | null {
  if (typeof window === "undefined") return null;
  const params = new URLSearchParams(window.location.search);
  const campaignId = params.get("campaign")?.trim() ?? "";
  const graphNodeId = params.get("graphNodeId")?.trim() ?? "";
  const graphRevision = params.get("graphRevision")?.trim() || null;
  if (!campaignId || !graphNodeId) return null;
  return { campaignId, graphNodeId, graphRevision };
}

export interface BuildGraphObjectContextProps {
  documentCampaignId?: string | null;
  /**
   * When true, refuse to load until document campaign admission succeeds.
   * Use for document-backed Build shell; leave false when no admitted document campaign is available.
   */
  requireDocumentScope?: boolean;
}

type ContextStatus =
  | "idle"
  | "loading"
  | "ready"
  | "partial"
  | "error"
  | "scope_mismatch"
  | "missing_node";

export function BuildGraphObjectContext({
  documentCampaignId,
  requireDocumentScope = false,
}: BuildGraphObjectContextProps) {
  const pointer = useMemo(() => parseBuildGraphPointerFromLocation(), []);
  const [status, setStatus] = useState<ContextStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [nodeViews, setNodeViews] = useState<Record<string, GraphProjectionNodeView>>({});
  const [loadedResult, setLoadedResult] = useState<WorldGraphObjectProjectionResult | null>(null);
  const [activeNodeId, setActiveNodeId] = useState<string | null>(null);
  const [revisionId, setRevisionId] = useState<string | null>(null);
  const [selectedRelationshipId, setSelectedRelationshipId] = useState<string | null>(null);
  const requestGenerationRef = useRef(0);

  const loadProjection = useCallback(async () => {
    const generation = ++requestGenerationRef.current;
    const isCurrent = () => generation === requestGenerationRef.current;

    if (!pointer) {
      if (isCurrent()) setStatus("idle");
      return;
    }

    if (requireDocumentScope) {
      const admission = admitBuildDocumentScope({
        documentCampaignId,
        incomingCampaignId: pointer.campaignId,
      });
      if (!admission.ok) {
        if (!isCurrent()) return;
        setStatus("scope_mismatch");
        setError(admission.reason);
        setNodeViews({});
        setLoadedResult(null);
        setActiveNodeId(null);
        return;
      }
    } else if (documentCampaignId?.trim()) {
      const admission = admitBuildDocumentScope({
        documentCampaignId,
        incomingCampaignId: pointer.campaignId,
      });
      if (!admission.ok) {
        if (!isCurrent()) return;
        setStatus("scope_mismatch");
        setError(admission.reason);
        setNodeViews({});
        setLoadedResult(null);
        setActiveNodeId(null);
        return;
      }
    }

    const worldId = getWorldIdForCampaign(pointer.campaignId);
    if (!worldId) {
      if (!isCurrent()) return;
      setStatus("error");
      setError(`Unknown campaign mapping for ${pointer.campaignId}.`);
      return;
    }

    if (isCurrent()) {
      setStatus("loading");
      setError(null);
    }
    try {
      const result = await loadCompleteWorldObject({
        schema: "dmb_world_graph_object_projection_request_v1",
        worldId,
        campaignId: pointer.campaignId,
        nodeId: pointer.graphNodeId,
        admissibility: "gm",
        revisionPin: pointer.graphRevision,
        originSurface: "build",
        focus: { kind: "none", sessionId: null },
      });
      if (!isCurrent()) return;
      const adapted = completeObjectNodeMap(result);
      setNodeViews(adapted);
      setLoadedResult(result);
      setRevisionId(result.snapshot?.revisionId ?? pointer.graphRevision);
      const resolvedId = result.resolvedNodeId ?? pointer.graphNodeId;
      setActiveNodeId(resolvedId);
      if (!result.found || !adapted[resolvedId]) {
        setStatus("missing_node");
        setError(`Exact node ${pointer.graphNodeId} is not present in the complete World object read.`);
        return;
      }
      setStatus(result.completeness.status === "complete" ? "ready" : "partial");
    } catch (loadError) {
      if (!isCurrent()) return;
      setNodeViews({});
      setLoadedResult(null);
      setStatus("error");
      setError(
        loadError instanceof LiveApiError
          ? loadError.message
          : loadError instanceof Error
            ? loadError.message
            : "Failed to load World Graph context.",
      );
    }
  }, [documentCampaignId, pointer, requireDocumentScope]);

  useEffect(() => {
    void loadProjection();
    return () => {
      // Invalidate in-flight responses when admission inputs change or the lane unmounts.
      requestGenerationRef.current += 1;
    };
  }, [loadProjection]);

  const handleSelectRelationshipTarget = useCallback(
    (targetId: string) => {
      setSelectedRelationshipId(targetId);
      if (!pointer) return;
      const worldId = getWorldIdForCampaign(pointer.campaignId);
      if (!worldId) return;
      void loadCompleteWorldObject({
        schema: "dmb_world_graph_object_projection_request_v1",
        worldId,
        campaignId: pointer.campaignId,
        nodeId: targetId,
        admissibility: "gm",
        revisionPin: pointer.graphRevision,
        originSurface: "build",
        focus: { kind: "none", sessionId: null },
      }).then((next) => {
        const adaptedNext = completeObjectNodeMap(next);
        setNodeViews(adaptedNext);
        setLoadedResult(next);
        setRevisionId(next.snapshot?.revisionId ?? pointer.graphRevision);
        if (next.found && next.resolvedNodeId) {
          setActiveNodeId(next.resolvedNodeId);
        }
        if (!next.found || !adaptedNext[next.resolvedNodeId ?? targetId]) {
          setStatus("missing_node");
          setError(`Exact node ${targetId} is not present in the complete World object read.`);
          return;
        }
        setStatus(next.completeness.status === "complete" ? "ready" : "partial");
      });
    },
    [pointer],
  );

  if (!pointer) {
    return null;
  }

  const activeNodeView = activeNodeId ? resolveExactProjectedNode(nodeViews, activeNodeId) : null;

  return (
    <section
      className="build-graph-object-context"
      data-testid="build-graph-object-context"
      data-complete-object-status={status}
      aria-label="Published World Graph context"
    >
      <header>
        <p className="plan-surface-kicker">Published World Graph context</p>
        <h2>Exact object from revision {revisionId ?? pointer.graphRevision ?? "head"}</h2>
        <p className="module-muted">Read-only context for this Build source. No graph or document writes.</p>
      </header>

      {status === "loading" ? <p className="module-muted">Loading World Graph context…</p> : null}
      {status === "scope_mismatch" || status === "error" || status === "missing_node" ? (
        <p className="graph-preview-error" role="alert">
          {error}
        </p>
      ) : null}
      <CompleteObjectPartialWarning result={loadedResult} />

      {activeNodeView && (status === "ready" || status === "partial") ? (
        <GraphObjectProjectionCard
          mode="plan"
          nodeView={activeNodeView}
          onSelectRelationshipTarget={handleSelectRelationshipTarget}
          selectedRelationshipId={selectedRelationshipId}
        />
      ) : null}
    </section>
  );
}
