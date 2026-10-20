import {
  createContext,
  createElement,
  useContext,
  useCallback,
  useRef,
  useEffect,
  useLayoutEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  LiveApiError,
  getNativeGraphAccessGeneration,
  NATIVE_GRAPH_ACCESS_TOKEN_CHANGED_EVENT,
  postManagedWorldGraphProjection,
  postWorldGraphProjection,
} from "../api/liveApi";
import type {
  ManagedWorldGraphProjectionResponse,
  WorldGraphProjection,
  WorldGraphProjectionRequest,
} from "../api/types";
import type { GraphReferenceProjectionState } from "../graphReference/types";
import {
  createSurfaceInformationChannel,
  type SurfaceInformationChannel,
} from "../surfaceInformation";
import { worldGraphProjectionRequestKey } from "../worldGraph/worldGraphProjectionRequestKey";
import { verifyWorldGraphProjectionResponse } from "../worldGraph/verifyWorldGraphProjectionResponse";
import { verifyManagedWorldGraphProjectionResponse } from "../worldGraph/verifyManagedWorldGraphProjectionResponse";
import { useSelectedWorld } from "../selectedWorld/SelectedWorldContext";
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

export type WorldGraphLensProjectionState = GraphReferenceProjectionState | "idle";

export interface WorldGraphLensProjectionValue {
  /** Desired exact request identity (may precede loaded bytes during transitions). */
  request: WorldGraphProjectionRequest | null;
  requestKey: string | null;
  /**
   * Loaded projection bytes — null unless stored load identity matches the
   * current desired requestKey + revision refresh generation.
   */
  projection: WorldGraphProjection | null;
  projectionState: WorldGraphLensProjectionState;
  projectionError: string | null;
  nodeCount: number;
  lastProjectionLoadMs: number | null;
  lastProjectionLoadOutcome: GraphReferenceProjectionState | null;
}

type StoredProjectionLoad = {
  scope: ProjectionDemandScope;
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

interface ProjectionDemandScope { readonly key: string | null }
interface ProjectionDemandOwner {
  scope: ProjectionDemandScope;
  acquire: (scope: ProjectionDemandScope) => () => void;
  retry: () => void;
}
const ProjectionDemandContext = createContext<ProjectionDemandOwner | null>(null);

/** Explicit ownership; observer hooks never acquire projection bytes. */
export function useWorldGraphLensProjectionDemand(enabled: boolean): (() => void) | undefined {
  const owner = useContext(ProjectionDemandContext);
  useEffect(() => {
    if (!enabled || !owner?.scope.key) return;
    return owner.acquire(owner.scope);
  }, [enabled, owner]);
  return owner?.retry;
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

function channelMatchesDesiredRequest(
  channel: SurfaceInformationChannel<WorldGraphProjection> | null,
  request: WorldGraphProjectionRequest | null,
  ownerKind: "managed" | "native",
): channel is SurfaceInformationChannel<WorldGraphProjection> {
  if (!channel || !request) return false;
  return channel.descriptor.channelId === worldGraphLensInformationDescriptor(request, ownerKind).channelId;
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
  const selectedWorld = useSelectedWorld();
  const managedWorldId = selectedWorld.kind === "managed" ? selectedWorld.worldId : null;
  const ownerKind = managedWorldId ? "managed" : "native";
  const [stored, setStored] = useState<StoredProjectionLoad | null>(null);
  const [revisionEventBump, setRevisionEventBump] = useState(0);
  const currentScope = useRef<ProjectionDemandScope | null>(null);
  const revisionGeneration = useRef(0);
  const retry = useCallback(() => {
    revisionGeneration.current += 1;
    setRevisionEventBump(previous => previous + 1);
  }, []);
  const [demands, setDemands] = useState<ReadonlyMap<symbol, ProjectionDemandScope>>(new Map());
  const acquire = useCallback((scope: ProjectionDemandScope) => {
    if (scope !== currentScope.current) return () => {};
    const lease = Symbol("projection-demand");
    setDemands(previous => new Map(previous).set(lease, scope));
    return () => setDemands(previous => {
      if (!previous.has(lease)) return previous;
      const next = new Map(previous); next.delete(lease); return next;
    });
  }, []);

  const focusValidationStatus = graphLens?.focusValidationStatus ?? "none";
  const focusValidationPending = isFocusValidationBlocking(focusValidationStatus);
  const lensState = graphLens?.lens ?? null;

  const context = useMemo(() => {
    if (selectedWorld.kind === "managed") {
      return {
        worldId: selectedWorld.worldId,
        campaignId: "",
        scopeMode: "world" as const,
        focus: { kind: "none" as const, sessionId: null as null },
      };
    }
    if (selectedWorld.kind !== "legacy") return null;
    if (!lensState) return null;
    return getWorldGraphContextFromLens(lensState, defaultCampaignId);
  }, [defaultCampaignId, lensState, selectedWorld]);

  const desiredRequest = useMemo(() => {
    if (!context) return null;
    return buildWorldGraphLensProjectionRequest(context);
  }, [context]);

  const desiredRequestKey = useMemo(
    () => (desiredRequest
      ? `${ownerKind}:${worldGraphProjectionRequestKey(desiredRequest)}`
      : null),
    [desiredRequest, ownerKind],
  );

  useEffect(() => {
    if (typeof window === "undefined") return;
    let accessGeneration = getNativeGraphAccessGeneration();
    const onAccessChanged = () => {
      const next = getNativeGraphAccessGeneration();
      // Initial cookie bootstrap notifies at the same epoch; its own load stays owned.
      if (next === accessGeneration) return;
      accessGeneration = next;
      retry();
    };
    const onProjectionRefresh = () => {
      retry();
    };
    window.addEventListener(WORLD_GRAPH_REVISION_COMMITTED_EVENT, onProjectionRefresh);
    window.addEventListener(NATIVE_GRAPH_ACCESS_TOKEN_CHANGED_EVENT, onAccessChanged);
    return () => {
      window.removeEventListener(WORLD_GRAPH_REVISION_COMMITTED_EVENT, onProjectionRefresh);
      window.removeEventListener(NATIVE_GRAPH_ACCESS_TOKEN_CHANGED_EVENT, onAccessChanged);
    };
  }, [retry]);

  const projectionRefreshKey = `${revisionRefreshToken ?? ""}:${revisionEventBump}`;
  // Object identity is a unique generation even for A→B→A request identities.
  const demandScope = useMemo<ProjectionDemandScope>(() => ({ key: desiredRequestKey }),
    [desiredRequestKey, projectionRefreshKey]);
  useLayoutEffect(() => { currentScope.current = demandScope; }, [demandScope]);
  const demandOwner = useMemo(() => ({ scope: demandScope, acquire, retry: () => {
    if (currentScope.current === demandScope) retry();
  } }), [demandScope, acquire, retry]);
  const active = [...demands.values()].some(scope => scope === demandScope);
  const wanted = useRef({ scope: demandScope, active });
  useLayoutEffect(() => { wanted.current = { scope: demandScope, active }; }, [demandScope, active]);
  const [channelOwner, setChannelOwner] = useState<{
    scope: ProjectionDemandScope; channel: SurfaceInformationChannel<WorldGraphProjection>;
  } | null>(null);
  const informationChannel = active && channelOwner?.scope === demandScope ? channelOwner.channel : null;

  useEffect(() => {
    if (!active || !desiredRequest || !desiredRequestKey) {
      setStored(null);
      setChannelOwner(null);
      return;
    }
    const channel = createSurfaceInformationChannel<WorldGraphProjection>(
      worldGraphLensInformationDescriptor(desiredRequest, ownerKind),
    );
    setChannelOwner({ scope: demandScope, channel });
    return () => {
      // Drop the value retained by this channel as well as the provider's private load.
      channel.beginObservation();
      channel.dispose();
    };
  }, [active, desiredRequest, desiredRequestKey, demandScope, ownerKind]);


  useEffect(() => {
    const controller = new AbortController();
    const loadScope = demandScope;
    const loadRevision = revisionGeneration.current;
    const loadAccess = getNativeGraphAccessGeneration();
    const stillOwned = () => !controller.signal.aborted
      && wanted.current.active && wanted.current.scope === loadScope
      && loadRevision === revisionGeneration.current
      && loadAccess === getNativeGraphAccessGeneration();

    async function loadProjection() {
      if (!active) return;
      if (focusValidationPending) {
        if (channelMatchesDesiredRequest(informationChannel, desiredRequest, ownerKind)) {
          informationChannel.beginObservation();
        }
        return;
      }

      if (!context || !desiredRequest || !desiredRequestKey) {
        setStored(null);
        return;
      }

      if (!channelMatchesDesiredRequest(informationChannel, desiredRequest, ownerKind)) {
        return;
      }

      const loadRequest = desiredRequest;
      const loadRequestKey = desiredRequestKey;
      const loadRefreshKey = projectionRefreshKey;
      const loadChannel = informationChannel;
      const ticket = loadChannel.beginObservation();
      if (!ticket) {
        return;
      }
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
        managedResponse?: ManagedWorldGraphProjectionResponse | null,
      ): void => {
        loadChannel.commit(
          ticket,
          mapWorldGraphLensObservation({ request: loadRequest, response, managedResponse, error }),
        );
      };

      try {
        let managedResponse: ManagedWorldGraphProjectionResponse | null = null;
        let response: WorldGraphProjection;
        if (managedWorldId) {
          managedResponse = await postManagedWorldGraphProjection({
            schema: "dmb_managed_world_graph_projection_request_v1",
            managedWorldId,
            revisionPin: loadRequest.revisionPin ?? null,
            queryText: loadRequest.queryText ?? null,
          }, controller.signal);
          response = managedResponse.projection;
        } else {
          response = await postWorldGraphProjection(loadRequest, controller.signal);
        }
        if (!stillOwned()) return;
        const revisionKind = loadRequest.revisionPin ? "pinned" : "head";
        const mismatch = managedResponse
          ? verifyManagedWorldGraphProjectionResponse({
              managedWorldId: loadRequest.worldId,
              request: loadRequest,
              response: managedResponse,
              revisionKind,
              pinnedRevisionId: loadRequest.revisionPin ?? null,
            })
          : verifyWorldGraphProjectionResponse({
              request: loadRequest,
              response,
              revisionKind,
              pinnedRevisionId: loadRequest.revisionPin ?? null,
            });
        if (!stillOwned()) return;
        // Verification and ownership admission precede both shared-channel and private commits.
        commitObservation(response, undefined, managedResponse);
        if (!stillOwned()) return;
        if (mismatch) {
          setStored({
            scope: loadScope,
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
          scope: loadScope,
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
        if (!stillOwned()) return;
        commitObservation(null, error);
        if (!stillOwned()) return;
        if (isWorldGraphUnavailable(error)) {
          setStored({
            scope: loadScope,
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
          scope: loadScope,
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
      controller.abort();
    };
  }, [
    active,
    demandScope,
    context,
    desiredRequest,
    desiredRequestKey,
    focusValidationPending,
    informationChannel,
    managedWorldId,
    ownerKind,
    projectionRefreshKey,
  ]);

  const value = useMemo<WorldGraphLensProjectionValue>(() => {
    const coherent =
      stored != null
      && desiredRequestKey != null
      && stored.scope === demandScope
      && stored.requestKey === desiredRequestKey
      && stored.refreshKey === projectionRefreshKey
      && !focusValidationPending
      && active;

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

    if (!active) {
      return { request: desiredRequest, requestKey: desiredRequestKey, projection: null,
        projectionState: "idle", projectionError: null, nodeCount: 0,
        lastProjectionLoadMs: null, lastProjectionLoadOutcome: null };
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
    active,
    demandScope,
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
      createElement(ProjectionDemandContext.Provider, { value: demandOwner }, children),
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
