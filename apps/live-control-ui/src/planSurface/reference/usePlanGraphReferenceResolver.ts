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
import { useOptionalPlanGraphLens } from "../PlanGraphLensContext";
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
  WORLD_GRAPH_REVISION_COMMITTED_EVENT,
} from "./planGraphContextRequest";

export interface UsePlanGraphReferenceResolverResult {
  projection: WorldGraphProjection | null;
  projectionState: PlanGraphProjectionState;
  projectionError: string | null;
  /** Dogfood: last projection load duration in ms (null until a terminal outcome). */
  lastProjectionLoadMs: number | null;
  /** Dogfood: last projection load outcome. */
  lastProjectionLoadOutcome: PlanGraphProjectionState | null;
  resolvePlanReference: (ref: RunbookReferenceAttrs) => Promise<PlanReferenceResolution>;
  resolvePlanRelationship: (
    relationship: GraphObjectRelationshipViewModel,
  ) => Promise<PlanReferenceResolution>;
}

const PlanGraphReferenceResolverContext =
  createContext<UsePlanGraphReferenceResolverResult | null>(null);

let projectionLoadGeneration = 0;

function markProjectionLoadStart(): string {
  projectionLoadGeneration += 1;
  const markName = `dmb:wg-projection:start:${projectionLoadGeneration}`;
  if (typeof performance !== "undefined" && typeof performance.mark === "function") {
    performance.mark(markName);
  }
  return markName;
}

function measureProjectionLoad(
  startMark: string,
  outcome: PlanGraphProjectionState,
  meta: {
    campaignId: string;
    scopeMode: string;
    focusSessionId: string | null;
  },
): number | null {
  const endMark = `dmb:wg-projection:end:${projectionLoadGeneration}`;
  const measureName = `dmb:wg-projection:load:${projectionLoadGeneration}`;
  let durationMs: number | null = null;
  if (typeof performance !== "undefined" && typeof performance.mark === "function") {
    performance.mark(endMark);
    try {
      if (typeof performance.measure === "function") {
        performance.measure(measureName, startMark, endMark);
        const entries = performance.getEntriesByName(measureName);
        const last = entries[entries.length - 1];
        if (last) {
          durationMs = Math.round(last.duration);
        }
      }
    } catch {
      durationMs = null;
    }
  }
  console.debug("[dmb] world-graph projection", {
    campaignId: meta.campaignId,
    scopeMode: meta.scopeMode,
    focusSessionId: meta.focusSessionId,
    outcome,
    durationMs,
  });
  return durationMs;
}

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
    lensSummary?: string | null;
    fetchImpl?: typeof fetch;
  } = {},
): Promise<PlanReferenceResolution> {
  const projectionState = options.projectionState ?? null;
  const lensSummary = options.lensSummary ?? null;

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
      lensSummary,
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
      lensSummary,
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
      lensSummary,
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
    lensSummary,
  });

  return {
    ...resolution,
    graphProjectionState: projectionState,
  };
}

function usePlanGraphReferenceResolverLoad(
  sessionDescriptor: PlanSessionDescriptor | null | undefined,
  revisionRefreshToken?: string | number | null,
): UsePlanGraphReferenceResolverResult {
  const [projection, setProjection] = useState<WorldGraphProjection | null>(null);
  const [projectionState, setProjectionState] = useState<PlanGraphProjectionState>("loading");
  const [projectionError, setProjectionError] = useState<string | null>(null);
  const [lastProjectionLoadMs, setLastProjectionLoadMs] = useState<number | null>(null);
  const [lastProjectionLoadOutcome, setLastProjectionLoadOutcome] = useState<PlanGraphProjectionState | null>(null);
  const [revisionEventBump, setRevisionEventBump] = useState(0);
  const graphLens = useOptionalPlanGraphLens();
  const focusValidationStatus = graphLens?.focusValidationStatus ?? "none";
  const focusValidationPending =
    focusValidationStatus === "pending" || focusValidationStatus === "invalid";

  const context = useMemo(
    () =>
      getPlanWorldGraphContext(
        sessionDescriptor,
        graphLens ? { lens: graphLens.lens } : undefined,
      ),
    [sessionDescriptor, graphLens?.lens],
  );

  useEffect(() => {
    if (typeof window === "undefined") return;
    const onRevisionCommitted = () => {
      setRevisionEventBump((previous) => previous + 1);
    };
    window.addEventListener(WORLD_GRAPH_REVISION_COMMITTED_EVENT, onRevisionCommitted);
    return () => {
      window.removeEventListener(WORLD_GRAPH_REVISION_COMMITTED_EVENT, onRevisionCommitted);
    };
  }, []);

  const projectionRefreshKey = `${revisionRefreshToken ?? ""}:${revisionEventBump}`;

  useEffect(() => {
    let cancelled = false;

    async function loadProjection() {
      // Shared focus gate: do not forward URL-initialized focus until bundles validate it.
      if (focusValidationPending) {
        setProjection(null);
        setProjectionState("loading");
        setProjectionError(null);
        setLastProjectionLoadMs(null);
        setLastProjectionLoadOutcome(null);
        return;
      }

      if (!context) {
        setProjection(null);
        setProjectionState("unavailable");
        setProjectionError(null);
        setLastProjectionLoadMs(null);
        setLastProjectionLoadOutcome("unavailable");
        return;
      }

      setProjection(null);
      setProjectionState("loading");
      setProjectionError(null);
      const startMark = markProjectionLoadStart();
      const focusSessionId =
        context.focus.kind === "session" ? context.focus.sessionId : null;

      const finish = (outcome: PlanGraphProjectionState) => {
        const durationMs = measureProjectionLoad(startMark, outcome, {
          campaignId: context.campaignId,
          scopeMode: context.scopeMode,
          focusSessionId,
        });
        setLastProjectionLoadMs(durationMs);
        setLastProjectionLoadOutcome(outcome);
      };

      try {
        const response = await postWorldGraphProjection(
          buildPlanWorldGraphProjectionRequest(context),
        );
        if (cancelled) return;
        setProjection(response);
        setProjectionState("ready");
        finish("ready");
      } catch (error) {
        if (cancelled) return;
        setProjection(null);
        if (isWorldGraphUnavailable(error)) {
          setProjectionState("unavailable");
          setProjectionError(null);
          finish("unavailable");
          return;
        }
        setProjectionState("error");
        setProjectionError(formatProjectionLoadError(error));
        finish("error");
      }
    }

    void loadProjection();

    return () => {
      cancelled = true;
    };
  }, [context, focusValidationPending, projectionRefreshKey]);

  const resolvePlanReference = useCallback(
    async (ref: RunbookReferenceAttrs) =>
      resolvePlanReferenceWithFallback(ref, {
        projection,
        projectionState,
        lensSummary: graphLens?.summaryLabel ?? null,
      }),
    [graphLens?.summaryLabel, projection, projectionState],
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
    lastProjectionLoadMs,
    lastProjectionLoadOutcome,
    resolvePlanReference,
    resolvePlanRelationship,
  };
}

export function PlanGraphReferenceResolverProvider({
  sessionDescriptor,
  revisionRefreshToken,
  children,
}: {
  sessionDescriptor: PlanSessionDescriptor | null | undefined;
  revisionRefreshToken?: string | number | null;
  children: ReactNode;
}) {
  const resolver = usePlanGraphReferenceResolverLoad(sessionDescriptor, revisionRefreshToken);
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
