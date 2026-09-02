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
import {
  createSurfaceInformationChannel,
  type SurfaceInformationChannel,
} from "../surfaceInformation";
import { worldGraphProjectionRequestKey } from "../worldGraph/worldGraphProjectionRequestKey";
import { verifyWorldGraphProjectionResponse } from "../worldGraph/verifyWorldGraphProjectionResponse";
import { isFocusValidationBlocking } from "./planGraphFocusOptions";
import { useOptionalWorldGraphLens } from "./WorldGraphLensContext";
import { WORLD_GRAPH_REVISION_COMMITTED_EVENT } from "../planSurface/reference/planGraphContextRequest";
import {
  buildWorldGraphLensProjectionRequest,
  getWorldGraphContextFromLens,
} from "./worldGraphContextFromLens";
import {
  mapWorldGraphLensObservation,
  worldGraphLensInformationDescriptor,
} from "./worldGraphLensSurfaceInformation";

export { WORLD_GRAPH_REVISION_COMMITTED_EVENT };

export interface WorldGraphLensProjectionValue {
  /** Desired exact request identity (may precede loaded bytes during transitions). */
  request: WorldGraphProjectionRequest | null;
  requestKey: string | null;
  /**
   * Loaded projection bytes — null unless stored load identity matches the
   * current desired requestKey + revision refresh generation.
   */
  projection: WorldGraphProjection | null;
  projectionState: GraphReferenceProjectionState;
  projectionError: string | null;
  nodeCount: number;
  lastProjectionLoadMs: number | null;
  lastProjectionLoadOutcome: GraphReferenceProjectionState | null;
}

type StoredProjectionLoad = {
  requestKey: string;
  refreshKey: string;
  request: WorldGraphProjectionRequest;
  projection: WorldGraphProjection | null;
  projectionState: GraphReferenceProjectionState;
  projectionError: string | null;
  lastProjectionLoadMs: number | null;
  lastProjectionLoadOutcome: GraphReferenceProjectionState | null;
};

const WorldGraphLensProjectionContext = createContext<WorldGraphLensProjectionValue | null>(null);
const WorldGraphLensInformationChannelContext = createContext<
  SurfaceInformationChannel<WorldGraphProjection> | null
>(null);

export function WorldGraphLensInformationChannelProvider({
  channel,
  children,
}: {
  channel: SurfaceInformationChannel<WorldGraphProjection> | null;
  children: ReactNode;
}) {
  return createElement(WorldGraphLensInformationChannelContext.Provider, { value: channel }, children);
}

export function useOptionalWorldGraphLensInformationChannel(): SurfaceInformationChannel<WorldGraphProjection> | null {
  return useContext(WorldGraphLensInformationChannelContext);
}

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
  const [stored, setStored] = useState<StoredProjectionLoad | null>(null);
  const [revisionEventBump, setRevisionEventBump] = useState(0);

  const focusValidationStatus = graphLens?.focusValidationStatus ?? "none";
  const focusValidationPending = isFocusValidationBlocking(focusValidationStatus);
  const lensState = graphLens?.lens ?? null;

  const context = useMemo(() => {
    if (!lensState) return null;
    return getWorldGraphContextFromLens(lensState, defaultCampaignId);
  }, [defaultCampaignId, lensState]);

  const desiredRequest = useMemo(() => {
    if (!context) return null;
    return buildWorldGraphLensProjectionRequest(context);
  }, [context]);

  const desiredRequestKey = useMemo(
    () => (desiredRequest ? worldGraphProjectionRequestKey(desiredRequest) : null),
    [desiredRequest],
  );

  const [informationChannel, setInformationChannel] = useState<
    SurfaceInformationChannel<WorldGraphProjection> | null
  >(null);

  useEffect(() => {
    if (!desiredRequest || !desiredRequestKey) {
      setInformationChannel(null);
      return;
    }
    const channel = createSurfaceInformationChannel<WorldGraphProjection>(
      worldGraphLensInformationDescriptor(desiredRequest),
    );
    setInformationChannel(channel);
    return () => {
      channel.dispose();
    };
  }, [desiredRequest, desiredRequestKey]);

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
        informationChannel?.beginObservation();
        return;
      }

      if (!context || !desiredRequest || !desiredRequestKey) {
        setStored(null);
        return;
      }

      if (!informationChannel) {
        return;
      }

      const loadRequest = desiredRequest;
      const loadRequestKey = desiredRequestKey;
      const loadRefreshKey = projectionRefreshKey;
      const loadChannel = informationChannel;
      const ticket = loadChannel?.beginObservation() ?? null;
      const startMark = markProjectionLoadStart();
      const focusSessionId =
        context.focus.kind === "session" ? context.focus.sessionId : null;

      const finish = (outcome: GraphReferenceProjectionState): number | null =>
        measureProjectionLoad(startMark, outcome, {
          campaignId: context.campaignId,
          scopeMode: context.scopeMode,
          focusSessionId,
        });

      const commitObservation = (
        response: WorldGraphProjection | null,
        error?: unknown,
      ): void => {
        if (!loadChannel || !ticket) return;
        loadChannel.commit(
          ticket,
          mapWorldGraphLensObservation({ request: loadRequest, response, error }),
        );
      };

      try {
        const response = await postWorldGraphProjection(loadRequest);
        commitObservation(response);
        if (cancelled) return;
        const mismatch = verifyWorldGraphProjectionResponse({
          request: loadRequest,
          response,
          revisionKind: "head",
          pinnedRevisionId: loadRequest.revisionPin ?? null,
        });
        if (mismatch) {
          setStored({
            requestKey: loadRequestKey,
            refreshKey: loadRefreshKey,
            request: loadRequest,
            projection: null,
            projectionState: "error",
            projectionError: mismatch,
            lastProjectionLoadMs: finish("error"),
            lastProjectionLoadOutcome: "error",
          });
          return;
        }
        setStored({
          requestKey: loadRequestKey,
          refreshKey: loadRefreshKey,
          request: loadRequest,
          projection: response,
          projectionState: "ready",
          projectionError: null,
          lastProjectionLoadMs: finish("ready"),
          lastProjectionLoadOutcome: "ready",
        });
      } catch (error) {
        commitObservation(null, error);
        if (cancelled) return;
        if (isWorldGraphUnavailable(error)) {
          setStored({
            requestKey: loadRequestKey,
            refreshKey: loadRefreshKey,
            request: loadRequest,
            projection: null,
            projectionState: "unavailable",
            projectionError: null,
            lastProjectionLoadMs: finish("unavailable"),
            lastProjectionLoadOutcome: "unavailable",
          });
          return;
        }
        setStored({
          requestKey: loadRequestKey,
          refreshKey: loadRefreshKey,
          request: loadRequest,
          projection: null,
          projectionState: "error",
          projectionError: formatProjectionLoadError(error),
          lastProjectionLoadMs: finish("error"),
          lastProjectionLoadOutcome: "error",
        });
      }
    }

    void loadProjection();

    return () => {
      cancelled = true;
    };
  }, [
    context,
    desiredRequest,
    desiredRequestKey,
    focusValidationPending,
    informationChannel,
    projectionRefreshKey,
  ]);

  const value = useMemo<WorldGraphLensProjectionValue>(() => {
    const coherent =
      stored != null
      && desiredRequestKey != null
      && stored.requestKey === desiredRequestKey
      && stored.refreshKey === projectionRefreshKey
      && !focusValidationPending;

    if (!desiredRequest || !desiredRequestKey) {
      return {
        request: null,
        requestKey: null,
        projection: null,
        projectionState: "unavailable",
        projectionError: null,
        nodeCount: 0,
        lastProjectionLoadMs: null,
        lastProjectionLoadOutcome: "unavailable",
      };
    }

    if (!coherent) {
      return {
        request: desiredRequest,
        requestKey: desiredRequestKey,
        projection: null,
        projectionState: "loading",
        projectionError: null,
        nodeCount: 0,
        lastProjectionLoadMs: null,
        lastProjectionLoadOutcome: null,
      };
    }

    return {
      request: desiredRequest,
      requestKey: desiredRequestKey,
      projection: stored.projection,
      projectionState: stored.projectionState,
      projectionError: stored.projectionError,
      nodeCount: stored.projection?.nodes.length ?? 0,
      lastProjectionLoadMs: stored.lastProjectionLoadMs,
      lastProjectionLoadOutcome: stored.lastProjectionLoadOutcome,
    };
  }, [
    desiredRequest,
    desiredRequestKey,
    focusValidationPending,
    projectionRefreshKey,
    stored,
  ]);

  return createElement(
    WorldGraphLensProjectionContext.Provider,
    { value },
    createElement(
      WorldGraphLensInformationChannelContext.Provider,
      { value: informationChannel },
      children,
    ),
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
