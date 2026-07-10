import { useCallback, useEffect, useMemo, useState } from "react";

import { getUnionSupergraphProjection, LiveApiError } from "../../api/liveApi";
import type { UnionSupergraphProjectionResponse } from "../../api/types";
import type { RunbookReferenceAttrs } from "../../tiptap/references/runbookReferences";
import type { PlanSessionDescriptor } from "../types";
import {
  resolvePlanReferenceFromGraphProjection,
  type PlanGraphProjectionState,
  type PlanReferenceResolution,
} from "./graphAwareReferenceResolver";
import { resolveReference } from "./referenceResolver";

export interface UsePlanGraphReferenceResolverResult {
  projection: UnionSupergraphProjectionResponse | null;
  projectionState: PlanGraphProjectionState;
  projectionError: string | null;
  resolvePlanReference: (ref: RunbookReferenceAttrs) => Promise<PlanReferenceResolution>;
}

function isExpectedProjectionMiss(error: unknown): boolean {
  return error instanceof LiveApiError && (error.status === 400 || error.status === 404);
}

export async function resolvePlanReferenceWithFallback(
  ref: RunbookReferenceAttrs,
  options: {
    projection?: UnionSupergraphProjectionResponse | null;
    projectionState?: PlanGraphProjectionState | null;
    fetchImpl?: typeof fetch;
  } = {},
): Promise<PlanReferenceResolution> {
  const projectionState = options.projectionState ?? null;

  if (options.projection) {
    const graphResolution = resolvePlanReferenceFromGraphProjection({
      ref,
      projection: options.projection,
    });

    if (graphResolution.kind === "graph-node") {
      return {
        ...graphResolution,
        graphProjectionState: projectionState,
      };
    }

    if (graphResolution.ambiguousNodeIds?.length) {
      return {
        ...graphResolution,
        graphProjectionState: projectionState,
      };
    }

    const fallbackResolution = await resolveReference(ref, options.fetchImpl);
    const resolution = resolvePlanReferenceFromGraphProjection({
      ref,
      projection: options.projection,
      fallbackResolution,
    });

    return {
      ...resolution,
      graphProjectionState: projectionState,
    };
  }

  const fallbackResolution = await resolveReference(ref, options.fetchImpl);
  const resolution = resolvePlanReferenceFromGraphProjection({
    ref,
    projection: null,
    fallbackResolution,
  });

  return {
    ...resolution,
    graphProjectionState: projectionState,
  };
}

export function usePlanGraphReferenceResolver(
  sessionDescriptor: PlanSessionDescriptor,
): UsePlanGraphReferenceResolverResult {
  const [projection, setProjection] = useState<UnionSupergraphProjectionResponse | null>(null);
  const [projectionState, setProjectionState] = useState<PlanGraphProjectionState>("loading");
  const [projectionError, setProjectionError] = useState<string | null>(null);

  const sessionId = useMemo(
    () => `session-${sessionDescriptor.memorySession}`,
    [sessionDescriptor.memorySession],
  );

  useEffect(() => {
    let cancelled = false;

    async function loadProjection() {
      setProjectionState("loading");
      setProjectionError(null);

      try {
        const response = await getUnionSupergraphProjection({
          campaignId: sessionDescriptor.campaignId,
          sessionId,
          useLatestGraphIngest: true,
        });
        if (cancelled) return;
        setProjection(response);
        setProjectionState("ready");
      } catch (error) {
        if (cancelled) return;
        setProjection(null);
        if (isExpectedProjectionMiss(error)) {
          setProjectionState("unavailable");
          setProjectionError(null);
          return;
        }
        setProjectionState("error");
        setProjectionError(error instanceof Error ? error.message : "Projection unavailable.");
      }
    }

    void loadProjection();

    return () => {
      cancelled = true;
    };
  }, [sessionDescriptor.campaignId, sessionId]);

  const resolvePlanReference = useCallback(
    async (ref: RunbookReferenceAttrs) =>
      resolvePlanReferenceWithFallback(ref, {
        projection,
        projectionState,
      }),
    [projection, projectionState],
  );

  return {
    projection,
    projectionState,
    projectionError,
    resolvePlanReference,
  };
}
