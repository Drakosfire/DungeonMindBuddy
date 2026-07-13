import {
  createContext,
  createElement,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { LiveApiError, postWorldGraphProjection } from "../../api/liveApi";
import type { WorldGraphProjection } from "../../api/types";
import type { GraphObjectRelationshipViewModel } from "../../graphObjectCard";
import type { RunbookReferenceAttrs } from "../../tiptap/references/runbookReferences";
import type { PlanSessionDescriptor } from "../types";
import {
  isCorpusFallbackAllowed,
  isGraphNativeReference,
  resolvePlanReferenceFromGraphProjection,
  type PlanGraphProjectionState,
  type PlanReferenceResolution,
} from "./graphAwareReferenceResolver";
import { resolveReference } from "./referenceResolver";
import { resolvePlanRelationshipTarget } from "./resolvePlanRelationshipTarget";
import {
  buildPlanWorldGraphProjectionRequest,
  getPlanWorldGraphContext,
} from "./planGraphContextRequest";

export interface UsePlanGraphReferenceResolverResult {
  projection: WorldGraphProjection | null;
  projectionState: PlanGraphProjectionState;
  projectionError: string | null;
  resolvePlanReference: (ref: RunbookReferenceAttrs) => Promise<PlanReferenceResolution>;
  resolvePlanRelationship: (
    relationship: GraphObjectRelationshipViewModel,
  ) => Promise<PlanReferenceResolution>;
}

const PlanGraphReferenceResolverContext =
  createContext<UsePlanGraphReferenceResolverResult | null>(null);

function isWorldGraphUnavailable(error: unknown): boolean {
  return (
    error instanceof LiveApiError
    && (error.status === 404 || error.code === "world_graph_unavailable")
  );
}

function formatProjectionLoadError(error: unknown): string {
  if (error instanceof LiveApiError) {
    return error.code ? `${error.message} (${error.code})` : error.message;
  }
  return error instanceof Error ? error.message : "Projection unavailable.";
}

export { isCorpusFallbackAllowed };

function unresolvedResolution(
  ref: RunbookReferenceAttrs,
  projectionState: PlanGraphProjectionState | null,
  message: string,
): PlanReferenceResolution {
  return {
    kind: "unresolved",
    locator: ref.refId ?? ref.label ?? "unknown",
    refType: ref.refType ?? null,
    refId: ref.refId ?? null,
    fallback: null,
    source: "unresolved",
    message,
    graphProjectionState: projectionState,
  };
}

function worldGraphErrorResolution(
  ref: RunbookReferenceAttrs,
  projectionState: PlanGraphProjectionState | null,
  message: string,
): PlanReferenceResolution {
  return {
    kind: "error",
    locator: ref.refId ?? ref.label ?? "unknown",
    refType: ref.refType ?? null,
    refId: ref.refId ?? null,
    fallback: null,
    source: "error",
    message,
    graphProjectionState: projectionState,
  };
}

export async function resolvePlanReferenceWithFallback(
  ref: RunbookReferenceAttrs,
  options: {
    projection?: WorldGraphProjection | null;
    projectionState?: PlanGraphProjectionState | null;
    fetchImpl?: typeof fetch;
  } = {},
): Promise<PlanReferenceResolution> {
  const projectionState = options.projectionState ?? null;

  if (projectionState === "loading") {
    return unresolvedResolution(
      ref,
      projectionState,
      "World Graph projection is loading; resolution deferred.",
    );
  }

  if (projectionState === "error") {
    return worldGraphErrorResolution(
      ref,
      projectionState,
      "World Graph projection failed; corpus fallback disabled.",
    );
  }

  // Graph-native chips: exact nodeId only. Never label rebind. Never corpus indexes.
  if (isGraphNativeReference(ref.refType)) {
    if (projectionState === "unavailable" || !options.projection) {
      return unresolvedResolution(
        ref,
        projectionState,
        "World Graph is unavailable; graph-native reference cannot be resolved.",
      );
    }

    const graphResolution = resolvePlanReferenceFromGraphProjection({
      ref,
      projection: options.projection,
    });

    return {
      ...graphResolution,
      graphProjectionState: projectionState,
    };
  }

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

function usePlanGraphReferenceResolverLoad(
  sessionDescriptor: PlanSessionDescriptor | null | undefined,
): UsePlanGraphReferenceResolverResult {
  const [projection, setProjection] = useState<WorldGraphProjection | null>(null);
  const [projectionState, setProjectionState] = useState<PlanGraphProjectionState>("loading");
  const [projectionError, setProjectionError] = useState<string | null>(null);

  const context = useMemo(
    () => getPlanWorldGraphContext(sessionDescriptor),
    [sessionDescriptor],
  );

  useEffect(() => {
    let cancelled = false;

    async function loadProjection() {
      if (!context) {
        setProjection(null);
        setProjectionState("unavailable");
        setProjectionError(null);
        return;
      }

      setProjection(null);
      setProjectionState("loading");
      setProjectionError(null);

      try {
        const response = await postWorldGraphProjection(
          buildPlanWorldGraphProjectionRequest(context),
        );
        if (cancelled) return;
        setProjection(response);
        setProjectionState("ready");
      } catch (error) {
        if (cancelled) return;
        setProjection(null);
        if (isWorldGraphUnavailable(error)) {
          setProjectionState("unavailable");
          setProjectionError(null);
          return;
        }
        setProjectionState("error");
        setProjectionError(formatProjectionLoadError(error));
      }
    }

    void loadProjection();

    return () => {
      cancelled = true;
    };
  }, [context]);

  const resolvePlanReference = useCallback(
    async (ref: RunbookReferenceAttrs) =>
      resolvePlanReferenceWithFallback(ref, {
        projection,
        projectionState,
      }),
    [projection, projectionState],
  );

  const resolvePlanRelationship = useCallback(
    async (relationship: GraphObjectRelationshipViewModel) =>
      resolvePlanRelationshipTarget({
        relationship,
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
    resolvePlanRelationship,
  };
}

export function PlanGraphReferenceResolverProvider({
  sessionDescriptor,
  children,
}: {
  sessionDescriptor: PlanSessionDescriptor | null | undefined;
  children: ReactNode;
}) {
  const resolver = usePlanGraphReferenceResolverLoad(sessionDescriptor);
  return createElement(
    PlanGraphReferenceResolverContext.Provider,
    { value: resolver },
    children,
  );
}

export function usePlanGraphReferenceResolver(): UsePlanGraphReferenceResolverResult {
  const resolver = useContext(PlanGraphReferenceResolverContext);
  if (!resolver) {
    throw new Error("usePlanGraphReferenceResolver must be used inside its provider.");
  }
  return resolver;
}
