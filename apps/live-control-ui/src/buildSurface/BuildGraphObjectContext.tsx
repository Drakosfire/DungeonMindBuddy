import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { LiveApiError, postWorldGraphProjection } from "../api/liveApi";
import type { GraphProjectionNodeView, WorldGraphProjection } from "../api/types";
import {
  GraphObjectProjectionCard,
  resolveExactProjectedNode,
} from "../graphObjectCard/GraphObjectProjectionCard";
import {
  admitBuildDocumentScope,
  buildBuildWorldGraphProjectionRequest,
} from "../worldGraph/worldGraphSurfaceContext";
import { adaptWorldGraphNodeView } from "../worldGraph/worldGraphNodeViewAdapter";

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

function adaptProjectionNodeMap(projection: WorldGraphProjection): Record<string, GraphProjectionNodeView> {
  return Object.fromEntries(
    projection.nodes.map((node) => [node.nodeId, adaptWorldGraphNodeView(node)]),
  );
}

export interface BuildGraphObjectContextProps {
  documentCampaignId?: string | null;
  /**
   * When true, refuse to load until document campaign admission succeeds.
   * Use for document-backed Build shell; leave false when no admitted document campaign is available.
   */
  requireDocumentScope?: boolean;
}

type ContextStatus = "idle" | "loading" | "ready" | "error" | "scope_mismatch" | "missing_node";

export function BuildGraphObjectContext({
  documentCampaignId,
  requireDocumentScope = false,
}: BuildGraphObjectContextProps) {
  const pointer = useMemo(() => parseBuildGraphPointerFromLocation(), []);
  const [status, setStatus] = useState<ContextStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [nodeViews, setNodeViews] = useState<Record<string, GraphProjectionNodeView>>({});
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
        setActiveNodeId(null);
        return;
      }
    }

    const request = buildBuildWorldGraphProjectionRequest({
      campaignId: pointer.campaignId,
      revisionPin: pointer.graphRevision,
    });
    if (!request) {
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
      const projection = await postWorldGraphProjection(request);
      if (!isCurrent()) return;
      const adapted = adaptProjectionNodeMap(projection);
      setNodeViews(adapted);
      setRevisionId(projection.snapshot.revisionId);
      setActiveNodeId(pointer.graphNodeId);
      if (!adapted[pointer.graphNodeId]) {
        setStatus("missing_node");
        setError(`Exact node ${pointer.graphNodeId} is not present in the pinned World Graph projection.`);
        return;
      }
      setStatus("ready");
    } catch (loadError) {
      if (!isCurrent()) return;
      setNodeViews({});
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
      if (resolveExactProjectedNode(nodeViews, targetId)) {
        setActiveNodeId(targetId);
      }
    },
    [nodeViews],
  );

  if (!pointer) {
    return null;
  }

  const activeNodeView = activeNodeId ? resolveExactProjectedNode(nodeViews, activeNodeId) : null;

  return (
    <section
      className="build-graph-object-context"
      data-testid="build-graph-object-context"
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

      {activeNodeView && status === "ready" ? (
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
