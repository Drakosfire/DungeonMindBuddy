import {
  createContext,
  createElement,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { LiveApiError, postWorldGraphProjection } from "../api/liveApi";
import type { WorldGraphProjection, WorldGraphProjectionRequest } from "../api/types";
import type { GraphReferenceProjectionState } from "../graphReference/types";
import { worldGraphProjectionRequestKey } from "../worldGraph/worldGraphProjectionRequestKey";
import { verifyWorldGraphProjectionResponse } from "../worldGraph/verifyWorldGraphProjectionResponse";
import { isFocusValidationBlocking } from "./planGraphFocusOptions";
import { useOptionalWorldGraphLens } from "./WorldGraphLensContext";
import { WORLD_GRAPH_REVISION_COMMITTED_EVENT } from "../planSurface/reference/planGraphContextRequest";
import {
  buildWorldGraphLensProjectionRequest,
  getWorldGraphContextFromLens,
} from "./worldGraphContextFromLens";

export { WORLD_GRAPH_REVISION_COMMITTED_EVENT };

export interface WorldGraphLensProjectionValue {
  /** Exact request identity for the current shared load (null when lens cannot form a request). */
  request: WorldGraphProjectionRequest | null;
  requestKey: string | null;
  projection: WorldGraphProjection | null;
  projectionState: GraphReferenceProjectionState;
  projectionError: string | null;
  nodeCount: number;
  lastProjectionLoadMs: number | null;
  lastProjectionLoadOutcome: GraphReferenceProjectionState | null;
}

const WorldGraphLensProjectionContext = createContext<WorldGraphLensProjectionValue | null>(null);

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

export function WorldGraphLensProjectionProvider({
  defaultCampaignId,
  revisionRefreshToken,
  children,
}: {
  defaultCampaignId: string;
  revisionRefreshToken?: string | number | null;
  children: ReactNode;
}) {
  const graphLens = useOptionalWorldGraphLens();
  const [projection, setProjection] = useState<WorldGraphProjection | null>(null);
  const [projectionState, setProjectionState] = useState<GraphReferenceProjectionState>("loading");
  const [projectionError, setProjectionError] = useState<string | null>(null);
  const [lastProjectionLoadMs, setLastProjectionLoadMs] = useState<number | null>(null);
  const [lastProjectionLoadOutcome, setLastProjectionLoadOutcome] =
    useState<GraphReferenceProjectionState | null>(null);
  const [revisionEventBump, setRevisionEventBump] = useState(0);

  const focusValidationStatus = graphLens?.focusValidationStatus ?? "none";
  const focusValidationPending = isFocusValidationBlocking(focusValidationStatus);
  const lensState = graphLens?.lens ?? null;

  const context = useMemo(() => {
    if (!lensState) return null;
    return getWorldGraphContextFromLens(lensState, defaultCampaignId);
  }, [defaultCampaignId, lensState]);

  const request = useMemo(() => {
    if (!context) return null;
    return buildWorldGraphLensProjectionRequest(context);
  }, [context]);

  const requestKey = useMemo(
    () => (request ? worldGraphProjectionRequestKey(request) : null),
    [request],
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
      if (focusValidationPending) {
        setProjection(null);
        setProjectionState("loading");
        setProjectionError(null);
        setLastProjectionLoadMs(null);
        setLastProjectionLoadOutcome(null);
        return;
      }

      if (!context || !request) {
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
        const response = await postWorldGraphProjection(request);
        if (cancelled) return;
        const mismatch = verifyWorldGraphProjectionResponse({
          request,
          response,
          revisionKind: "head",
          pinnedRevisionId: request.revisionPin ?? null,
        });
        if (mismatch) {
          setProjection(null);
          setProjectionState("error");
          setProjectionError(mismatch);
          finish("error");
          return;
        }
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
  }, [context, focusValidationPending, projectionRefreshKey, request]);

  const value = useMemo<WorldGraphLensProjectionValue>(
    () => ({
      request,
      requestKey,
      projection,
      projectionState,
      projectionError,
      nodeCount: projection?.nodes.length ?? 0,
      lastProjectionLoadMs,
      lastProjectionLoadOutcome,
    }),
    [
      lastProjectionLoadMs,
      lastProjectionLoadOutcome,
      projection,
      projectionError,
      projectionState,
      request,
      requestKey,
    ],
  );

  return createElement(
    WorldGraphLensProjectionContext.Provider,
    { value },
    children,
  );
}

export function useWorldGraphLensProjection(): WorldGraphLensProjectionValue {
  const value = useContext(WorldGraphLensProjectionContext);
  if (!value) {
    throw new Error(
      "useWorldGraphLensProjection must be used inside WorldGraphLensProjectionProvider",
    );
  }
  return value;
}

export function useOptionalWorldGraphLensProjection(): WorldGraphLensProjectionValue | null {
  return useContext(WorldGraphLensProjectionContext);
}
