import { useCallback, useEffect, useMemo, useState } from "react";

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
}

type ContextStatus = "idle" | "loading" | "ready" | "error" | "scope_mismatch" | "missing_node";

export function BuildGraphObjectContext({ documentCampaignId }: BuildGraphObjectContextProps) {
  const pointer = useMemo(() => parseBuildGraphPointerFromLocation(), []);
  const [status, setStatus] = useState<ContextStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [nodeViews, setNodeViews] = useState<Record<string, GraphProjectionNodeView>>({});
  const [activeNodeId, setActiveNodeId] = useState<string | null>(null);
  const [revisionId, setRevisionId] = useState<string | null>(null);
  const [selectedRelationshipId, setSelectedRelationshipId] = useState<string | null>(null);

  const loadProjection = useCallback(async () => {
    if (!pointer) {
      setStatus("idle");
      return;
    }

    if (documentCampaignId?.trim()) {
      const admission = admitBuildDocumentScope({
        documentCampaignId,
        incomingCampaignId: pointer.campaignId,
      });
      if (!admission.ok) {
        setStatus("scope_mismatch");
        setError(admission.reason);
        setNodeViews({});
        return;
      }
    }

    const request = buildBuildWorldGraphProjectionRequest({
      campaignId: pointer.campaignId,
      revisionPin: pointer.graphRevision,
    });
    if (!request) {
      setStatus("error");
      setError(`Unknown campaign mapping for ${pointer.campaignId}.`);
      return;
    }

    setStatus("loading");
    setError(null);
    try {
      const projection = await postWorldGraphProjection(request);
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
  }, [documentCampaignId, pointer]);

  useEffect(() => {
    void loadProjection();
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
