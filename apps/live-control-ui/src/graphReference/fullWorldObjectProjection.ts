import { useEffect, useRef, useState } from "react";

import { LiveApiError, postWorldGraphCompleteObject } from "../api/liveApi";
import type {
  GraphProjectionNodeView,
  WorldGraphObjectProjectionRequest,
  WorldGraphObjectProjectionResult,
  WorldGraphProjectionNodeView,
} from "../api/types";
import { adaptWorldGraphNodeView } from "../worldGraph/worldGraphNodeViewAdapter";

export function completeObjectNodeMap(
  result: WorldGraphObjectProjectionResult,
): Record<string, GraphProjectionNodeView> {
  const nodes: WorldGraphProjectionNodeView[] = [];
  if (result.node) nodes.push(result.node);
  nodes.push(...result.relatedNodes);
  return Object.fromEntries(nodes.map((node) => [node.nodeId, adaptWorldGraphNodeView(node)]));
}

export function completeWorldObjectRequest(
  request: Omit<WorldGraphObjectProjectionRequest, "schema">,
): WorldGraphObjectProjectionRequest {
  return {
    schema: "dmb_world_graph_object_projection_request_v1",
    focus: { kind: "none", sessionId: null },
    admissibility: "gm",
    ...request,
  };
}

export async function loadCompleteWorldObject(
  request: WorldGraphObjectProjectionRequest,
): Promise<WorldGraphObjectProjectionResult> {
  return postWorldGraphCompleteObject(request);
}

export type CompleteWorldObjectStatus =
  | "idle"
  | "loading"
  | "ready"
  | "partial"
  | "missing"
  | "error";

export function usesCompleteWorldObjectPayload(
  status: CompleteWorldObjectStatus,
): boolean {
  return status === "ready" || status === "partial";
}

export function completeWorldObjectPartialCopy(
  result: WorldGraphObjectProjectionResult,
): string {
  const fields = result.completeness.truncatedFields;
  const fieldText = fields.length > 0 ? fields.join(", ") : "unspecified fields";
  const reason = result.completeness.reason?.trim();
  return reason
    ? `Partial World object: truncated ${fieldText} (${reason}). This is not a complete admitted view.`
    : `Partial World object: truncated ${fieldText}. This is not a complete admitted view.`;
}

export interface UseCompleteWorldObjectArgs {
  enabled: boolean;
  worldId: string | null | undefined;
  campaignId: string;
  nodeId: string | null;
  originSurface: NonNullable<WorldGraphObjectProjectionRequest["originSurface"]>;
  revisionPin?: string | null;
  focus?: WorldGraphObjectProjectionRequest["focus"];
  admissibility?: "gm" | "player";
}

export interface UseCompleteWorldObjectResult {
  status: CompleteWorldObjectStatus;
  error: string | null;
  result: WorldGraphObjectProjectionResult | null;
  nodeView: GraphProjectionNodeView | null;
  nodeViews: Record<string, GraphProjectionNodeView>;
}

export function useCompleteWorldObject({
  enabled,
  worldId,
  campaignId,
  nodeId,
  originSurface,
  revisionPin = null,
  focus,
  admissibility = "gm",
}: UseCompleteWorldObjectArgs): UseCompleteWorldObjectResult {
  const [status, setStatus] = useState<CompleteWorldObjectStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<WorldGraphObjectProjectionResult | null>(null);
  const generationRef = useRef(0);
  const focusKind = focus?.kind ?? "none";
  const focusSessionId = focus?.sessionId ?? null;
  const focusCampaignId = focus?.campaignId ?? null;

  useEffect(() => {
    const generation = ++generationRef.current;
    const isCurrent = () => generation === generationRef.current;

    if (!enabled || !worldId || !nodeId) {
      if (isCurrent()) {
        setStatus("idle");
        setError(null);
        setResult(null);
      }
      return;
    }

    const requestFocus: WorldGraphObjectProjectionRequest["focus"] =
      focusKind === "session" && focusSessionId
        ? {
            kind: "session",
            sessionId: focusSessionId,
            ...(focusCampaignId ? { campaignId: focusCampaignId } : {}),
          }
        : { kind: "none", sessionId: null };

    setStatus("loading");
    setError(null);
    void loadCompleteWorldObject(
      completeWorldObjectRequest({
        worldId,
        campaignId,
        nodeId,
        originSurface,
        revisionPin,
        focus: requestFocus,
        admissibility,
      }),
    )
      .then((loaded) => {
        if (!isCurrent()) return;
        setResult(loaded);
        const resolvedId = loaded.resolvedNodeId ?? nodeId;
        if (!loaded.found || !loaded.node || !completeObjectNodeMap(loaded)[resolvedId]) {
          setStatus("missing");
          setError(`Exact node ${nodeId} is not present in the complete World object read.`);
          return;
        }
        if (loaded.completeness.status !== "complete") {
          setStatus("partial");
          return;
        }
        setStatus("ready");
      })
      .catch((loadError: unknown) => {
        if (!isCurrent()) return;
        setResult(null);
        setStatus("error");
        setError(
          loadError instanceof LiveApiError
            ? loadError.message
            : loadError instanceof Error
              ? loadError.message
              : "Failed to load complete World object.",
        );
      });

    return () => {
      generationRef.current += 1;
    };
  }, [
    admissibility,
    campaignId,
    enabled,
    focusCampaignId,
    focusKind,
    focusSessionId,
    nodeId,
    originSurface,
    revisionPin,
    worldId,
  ]);

  const nodeViews = result ? completeObjectNodeMap(result) : {};
  const resolvedId = result?.resolvedNodeId ?? nodeId;
  const nodeView = resolvedId ? nodeViews[resolvedId] ?? null : null;

  return { status, error, result, nodeView, nodeViews };
}
