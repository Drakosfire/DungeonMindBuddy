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
import { isFocusValidationBlocking } from "../planGraphFocusOptions";
import { useOptionalWorldGraphLensProjection } from "../../graphLens/useWorldGraphLensProjection";
import {
  extractExactGraphReferenceScope,
} from "../../graphReference/resolveGraphReference";
import type {
  ExactGraphReferenceScope,
  GraphReferenceProjectionState,
  GraphReferenceResolution,
} from "../../graphReference/types";
import {
  isCorpusFallbackAllowed,
  isGraphNativeReference,
  resolvePlanReferenceFromGraphProjection,
} from "./graphAwareReferenceResolver";
import { resolveReference } from "./referenceResolver";
import { resolvePlanRelationshipTarget } from "./resolvePlanRelationshipTarget";
import {
  buildPlanWorldGraphProjectionRequest,
  getPlanWorldGraphContext,
  WORLD_GRAPH_REVISION_COMMITTED_EVENT,
  type PlanWorldGraphContext,
} from "./planGraphContextRequest";

export interface UsePlanGraphReferenceResolverResult {
  projection: WorldGraphProjection | null;
  projectionState: GraphReferenceProjectionState;
  projectionError: string | null;
  /** Dogfood: last projection load duration in ms (null until a terminal outcome). */
  lastProjectionLoadMs: number | null;
  /** Dogfood: last projection load outcome. */
  lastProjectionLoadOutcome: GraphReferenceProjectionState | null;
  resolvePlanReference: (ref: RunbookReferenceAttrs) => Promise<GraphReferenceResolution>;
  resolvePlanRelationship: (
    relationship: GraphObjectRelationshipViewModel,
    originatingScope?: ExactGraphReferenceScope,
  ) => Promise<GraphReferenceResolution>;
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
  outcome: GraphReferenceProjectionState,
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

function projectionMatchesScope(
  projection: WorldGraphProjection | null,
  scope: ExactGraphReferenceScope,
): boolean {
  const actual = extractExactGraphReferenceScope(projection);
  return (
    actual?.worldId === scope.worldId
    && actual.campaignId === scope.campaignId
    && actual.scopeMode === scope.scopeMode
    && actual.revisionId === scope.revisionId
  );
}

function pinnedRelationshipError(
  relationship: GraphObjectRelationshipViewModel,
  message: string,
): GraphReferenceResolution {
  const targetId = String(relationship.targetId || "").trim();
  const targetKind = String(relationship.targetKind || "").trim();
  return {
    kind: "error",
    locator: targetId ? `dmb-node:${targetId}` : relationship.label,
    reference: targetId && targetKind
      ? { kind: "ref", refType: targetKind, refId: targetId, label: relationship.label }
      : null,
    projectionState: "error",
    message,
  };
}

export { isCorpusFallbackAllowed };

function unresolvedResolution(
  ref: RunbookReferenceAttrs,
  projectionState: GraphReferenceProjectionState | null,
  message: string,
): GraphReferenceResolution {
  return {
    kind: "unresolved",
    locator: ref.refId ?? ref.label ?? "unknown",
    reference: ref,
    projectionState,
    message,
  };
}

function worldGraphErrorResolution(
  ref: RunbookReferenceAttrs,
  projectionState: GraphReferenceProjectionState | null,
  message: string,
): GraphReferenceResolution {
  return {
    kind: "error",
    locator: ref.refId ?? ref.label ?? "unknown",
    reference: ref,
    projectionState,
    message,
  };
}

export async function resolvePlanReferenceWithFallback(
  ref: RunbookReferenceAttrs,
  options: {
    projection?: WorldGraphProjection | null;
    projectionState?: GraphReferenceProjectionState | null;
    lensSummary?: string | null;
    fetchImpl?: typeof fetch;
  } = {},
): Promise<GraphReferenceResolution> {
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
      projectionState,
    });

    return graphResolution;
  }

  if (options.projection) {
    const graphResolution = resolvePlanReferenceFromGraphProjection({
      ref,
      projection: options.projection,
      lensSummary,
      projectionState,
    });

    if (graphResolution.kind === "resolved_graph") {
      return graphResolution;
    }

    if (graphResolution.kind === "ambiguous") {
      return graphResolution;
    }

    const fallbackResolution = await resolveReference(ref, options.fetchImpl);
    return resolvePlanReferenceFromGraphProjection({
      ref,
      projection: options.projection,
      fallbackResolution,
      lensSummary,
      projectionState,
    });
  }

  const fallbackResolution = await resolveReference(ref, options.fetchImpl);
  return resolvePlanReferenceFromGraphProjection({
    ref,
    projection: null,
    fallbackResolution,
    lensSummary,
    projectionState,
  });
}

function usePlanGraphReferenceResolverLoad(
  sessionDescriptor: PlanSessionDescriptor | null | undefined,
  revisionRefreshToken?: string | number | null,
): UsePlanGraphReferenceResolverResult {
  const sharedProjection = useOptionalWorldGraphLensProjection();
  const [projection, setProjection] = useState<WorldGraphProjection | null>(null);
  const [projectionState, setProjectionState] = useState<GraphReferenceProjectionState>("loading");
  const [projectionError, setProjectionError] = useState<string | null>(null);
  const [lastProjectionLoadMs, setLastProjectionLoadMs] = useState<number | null>(null);
  const [lastProjectionLoadOutcome, setLastProjectionLoadOutcome] = useState<GraphReferenceProjectionState | null>(null);
  const [revisionEventBump, setRevisionEventBump] = useState(0);
  const graphLens = useOptionalPlanGraphLens();
  const focusValidationStatus = graphLens?.focusValidationStatus ?? "none";
  const focusValidationPending = isFocusValidationBlocking(focusValidationStatus);
  const skipLocalProjectionLoad = sharedProjection != null;

  const context = useMemo(
    () =>
      getPlanWorldGraphContext(
        sessionDescriptor,
        graphLens ? { lens: graphLens.lens } : undefined,
      ),
    [sessionDescriptor, graphLens?.lens],
  );

  useEffect(() => {
    if (skipLocalProjectionLoad || typeof window === "undefined") return;
    const onRevisionCommitted = () => {
      setRevisionEventBump((previous) => previous + 1);
    };
    window.addEventListener(WORLD_GRAPH_REVISION_COMMITTED_EVENT, onRevisionCommitted);
    return () => {
      window.removeEventListener(WORLD_GRAPH_REVISION_COMMITTED_EVENT, onRevisionCommitted);
    };
  }, [skipLocalProjectionLoad]);

  const projectionRefreshKey = `${revisionRefreshToken ?? ""}:${revisionEventBump}`;

  useEffect(() => {
    if (skipLocalProjectionLoad) return;

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

      const finish = (outcome: GraphReferenceProjectionState) => {
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
  }, [context, focusValidationPending, projectionRefreshKey, skipLocalProjectionLoad]);

  const effectiveProjection = sharedProjection?.projection ?? projection;
  const effectiveProjectionState = sharedProjection?.projectionState ?? projectionState;
  const effectiveProjectionError = sharedProjection?.projectionError ?? projectionError;
  const effectiveLastProjectionLoadMs = sharedProjection?.lastProjectionLoadMs ?? lastProjectionLoadMs;
  const effectiveLastProjectionLoadOutcome =
    sharedProjection?.lastProjectionLoadOutcome ?? lastProjectionLoadOutcome;

  const resolvePlanReference = useCallback(
    async (ref: RunbookReferenceAttrs) =>
      resolvePlanReferenceWithFallback(ref, {
        projection: effectiveProjection,
        projectionState: effectiveProjectionState,
        lensSummary: graphLens?.summaryLabel ?? null,
      }),
    [effectiveProjection, effectiveProjectionState, graphLens?.summaryLabel],
  );

  const resolvePlanRelationship = useCallback(
    async (
      relationship: GraphObjectRelationshipViewModel,
      originatingScope?: ExactGraphReferenceScope,
    ) => {
      let relationshipProjection = effectiveProjection;
      let relationshipProjectionState = effectiveProjectionState;

      if (
        originatingScope
        && !projectionMatchesScope(relationshipProjection, originatingScope)
      ) {
        try {
          const pinnedContext: PlanWorldGraphContext = {
            worldId: originatingScope.worldId,
            campaignId: originatingScope.campaignId,
            scopeMode: originatingScope.scopeMode,
            focus: { kind: "none", sessionId: null },
          };
          relationshipProjection = await postWorldGraphProjection({
            ...buildPlanWorldGraphProjectionRequest(pinnedContext),
            revisionPin: originatingScope.revisionId,
          });
          if (!projectionMatchesScope(relationshipProjection, originatingScope)) {
            return pinnedRelationshipError(
              relationship,
              "Pinned World Graph response did not match the Threat Sheet scope.",
            );
          }
          relationshipProjectionState = "ready";
        } catch (error) {
          return pinnedRelationshipError(
            relationship,
            formatProjectionLoadError(error),
          );
        }
      }

      return resolvePlanRelationshipTarget({
        relationship,
        projection: relationshipProjection,
        projectionState: relationshipProjectionState,
      });
    },
    [effectiveProjection, effectiveProjectionState],
  );

  return {
    projection: effectiveProjection,
    projectionState: effectiveProjectionState,
    projectionError: effectiveProjectionError,
    lastProjectionLoadMs: effectiveLastProjectionLoadMs,
    lastProjectionLoadOutcome: effectiveLastProjectionLoadOutcome,
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
