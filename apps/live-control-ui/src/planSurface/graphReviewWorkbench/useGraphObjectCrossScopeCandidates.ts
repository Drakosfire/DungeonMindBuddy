import { useEffect, useMemo, useState } from "react";

import { resolveGraphReviewExistingObjectCandidates } from "../../api/liveApi";
import type {
  GraphProjectionNodeView,
  GraphReviewExistingObjectCandidate,
  GraphReviewExistingObjectResolverResponse,
  GraphReviewResolverSelectedNode,
} from "../../api/types";

export function useGraphObjectCrossScopeCandidates({
  campaignId,
  sessionId,
  laneRole,
  query,
  selectedNode,
  nodeViews,
  liveRunManifestPath,
  enabled = true,
}: {
  campaignId?: string;
  sessionId?: string;
  laneRole: "gold" | "live";
  query: string;
  selectedNode: GraphReviewResolverSelectedNode | null;
  nodeViews?: Record<string, GraphProjectionNodeView>;
  liveRunManifestPath?: string | null;
  enabled?: boolean;
}) {
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [response, setResponse] = useState<GraphReviewExistingObjectResolverResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const normalizedQuery = query.trim();
  const canSearch = Boolean(
    enabled &&
      campaignId &&
      sessionId &&
      selectedNode &&
      normalizedQuery.length > 0,
  );

  useEffect(() => {
    if (!canSearch || !campaignId || !sessionId || !selectedNode) {
      setStatus("idle");
      setResponse(null);
      setError(null);
      return;
    }

    let cancelled = false;
    setStatus("loading");
    setError(null);

    void resolveGraphReviewExistingObjectCandidates({
      schema: "dmb_graph_review_existing_object_resolver_request_v1",
      campaign_id: campaignId,
      session_id: sessionId,
      lane_role: laneRole,
      selected_node: selectedNode,
      live_run_manifest_path: liveRunManifestPath ?? null,
      query: normalizedQuery,
      node_views: nodeViews ?? null,
      include_gm_private: true,
    })
      .then((next) => {
        if (cancelled) return;
        setResponse(next);
        setStatus("ready");
      })
      .catch((err) => {
        if (cancelled) return;
        setResponse(null);
        setError(err instanceof Error ? err.message : "Could not load cross-scope candidates.");
        setStatus("error");
      });

    return () => {
      cancelled = true;
    };
  }, [
    campaignId,
    sessionId,
    laneRole,
    selectedNode,
    normalizedQuery,
    nodeViews,
    liveRunManifestPath,
    canSearch,
  ]);

  const candidates = useMemo<GraphReviewExistingObjectCandidate[]>(
    () => response?.candidates ?? [],
    [response],
  );

  return {
    status,
    error,
    candidates,
    diagnostics: response?.diagnostics ?? [],
    scopesSearched: response?.scopes_searched ?? [],
  };
}
