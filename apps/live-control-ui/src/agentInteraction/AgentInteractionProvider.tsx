import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import type { AgentInteractionThread, LiveQueryBackend } from "../api/types";
import type {
  GraphReferenceProjectionBinding,
  GraphReferenceProjectionState,
  GraphReferenceResolution,
} from "../graphReference/types";
import type {
  GraphReviewDiagnosticsProjectionPayload,
  RegisterableToolProjectionId,
  ToolProjectionPayloadMap,
} from "../planSurface/projection/projectionBindings";
import { GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID } from "../planSurface/projection/projectionBindings";
import type { ActiveProjection, ProjectionSize } from "../planSurface/types";
import {
  AGENT_TURN_HISTORY_CAP,
  clearAgentThread,
  createAgentInteractionThread,
  deleteAgentThread as deleteStoredAgentThread,
  listAgentThreads,
  loadAgentThread,
  loadAgentThreadById,
  persistAgentThread,
  renameAgentThread,
  setActiveAgentThread,
  threadTitleFromQuestion,
  turnFromResponse,
} from "./agentInteractionStorage";
import type {
  AgentInteractionContextValue,
  AgentInteractionPaneState,
  AgentInteractionScope,
  AgentInteractionSelectedSource,
  AgentInteractionSurfaceContext,
} from "./agentInteractionTypes";
import type { OpenGraphReferenceArgs } from "../graphReference/types";
import {
  adaptProjectionSurfaceToNeutralBase,
} from "./surfaceInteractionCompat";
import {
  bindSurfaceInteractionLease,
  createLeaseCallbackGate,
  registerChromeCompatibilityFragment,
  unregisterChromeCompatibilityFragment,
  updateSurfaceInteractionLease,
  type SurfaceInteractionChromeFragment,
  type SurfaceInteractionLeaseSnapshot,
} from "./surfaceInteractionLease";
import {
  sameProjectionSurfaceIdentity,
  validateProjectionSurfacePublication,
  type ProjectionSurfacePublication,
  type ValidatedProjectionSurface,
} from "./projectionSurfacePublication";

const AgentInteractionContext = createContext<AgentInteractionContextValue | null>(null);

function sameScope(left: AgentInteractionScope | null, right: AgentInteractionScope): boolean {
  return Boolean(
    left &&
      left.campaignId === right.campaignId &&
      left.sessionNumber === right.sessionNumber &&
      (left.surfaceId ?? "plan") === (right.surfaceId ?? "plan") &&
      (left.documentId ?? null) === (right.documentId ?? null),
  );
}

interface LegacyProjectionAttachment {
  validated: ValidatedProjectionSurface | null;
}

interface ProviderLeaseBundle {
  snapshot: SurfaceInteractionLeaseSnapshot;
  legacyProjection: LegacyProjectionAttachment | null;
  authorizationEpoch: number;
  appChromePublisherEpoch: number;
}

interface BindingRegistration<T> {
  surfaceToken: symbol;
  token: symbol;
  value: T;
}

interface LeasedActiveProjection {
  surfaceToken: symbol;
  projection: ActiveProjection;
}

interface LeasedGraphReference {
  surfaceToken: symbol;
  resolution: GraphReferenceResolution;
}

interface LeasedGraphProjectionState {
  surfaceToken: symbol;
  state: GraphReferenceProjectionState | null;
}

function contentSize(resolution: GraphReferenceResolution): ProjectionSize {
  if (resolution.kind === "resolved_graph" || resolution.kind === "resolved_corpus_fallback") return "wide";
  return "compact";
}

function revalidateLeasedProjection(
  validated: ValidatedProjectionSurface,
  leased: LeasedActiveProjection | null,
): LeasedActiveProjection | null {
  if (!leased) return null;
  // Canonical disabled state clears every active projection, including tools
  // whose IDs still appear in a contradictory or otherwise invalid config.
  if (!validated.projectionsEnabled) return null;
  const config = validated.publication.config;
  const { projection } = leased;
  if (projection.kind === "tool") {
    const tool = config.tools.find((entry) => entry.id === projection.key);
    if (!tool) return null;
    // Same tool ID may still change label/size — rebuild from latest config
    // while preserving the lease and exact tool ID.
    return {
      surfaceToken: leased.surfaceToken,
      projection: {
        kind: "tool",
        key: tool.id,
        size: tool.size,
        title: tool.label,
      },
    };
  }
  return leased;
}

/**
 * Plan-only authorization for graph-reference content: projections enabled,
 * identity/config modes agree as plan, and required render context is present.
 * Build remains disabled by design; this is not a fully surface-neutral auth policy.
 */
function isAuthorizedPlanPublication(bundle: ProviderLeaseBundle | null): boolean {
  if (!bundle?.snapshot.effectivePublication) return false;
  const validated = bundle?.legacyProjection?.validated;
  if (!validated?.projectionsEnabled) return false;
  const { identity, config } = validated.publication;
  if (identity.surfaceId !== "plan" || config.id !== "plan") return false;
  return config.context != null;
}

function isAuthorizedDiagnosticsPublication(bundle: ProviderLeaseBundle | null): boolean {
  if (!bundle?.snapshot.effectivePublication) return false;
  const validated = bundle?.legacyProjection?.validated;
  if (!validated?.projectionsEnabled) return false;
  const { identity, config } = validated.publication;
  if (identity.surfaceId !== "ingest" || config.id !== "ingest") return false;
  return config.tools.some((entry) => entry.id === GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID);
}

function computeAuthorizationEpoch(bundle: ProviderLeaseBundle): number {
  const plan = isAuthorizedPlanPublication(bundle) ? 1 : 0;
  const diagnostics = isAuthorizedDiagnosticsPublication(bundle) ? 1 : 0;
  const effective = bundle.snapshot.effectivePublication ? 1 : 0;
  return (plan << 2) | (diagnostics << 1) | effective;
}

export function AgentInteractionProvider({ children }: { children: ReactNode }) {
  const [scope, setScope] = useState<AgentInteractionScope | null>(null);
  const [activeThread, setActiveThread] = useState<AgentInteractionThread | null>(null);
  const [threadSummaries, setThreadSummaries] = useState<AgentInteractionContextValue["threadSummaries"]>([]);
  const [paneState, setPaneState] = useState<AgentInteractionPaneState>({ isOpen: false, mode: "bar" });
  const [activeSurfaceContext, setActiveSurfaceContext] = useState<AgentInteractionSurfaceContext | null>(null);
  const [selectedSource, setSelectedSource] = useState<AgentInteractionSelectedSource | null>(null);

  const leaseBundleRef = useRef<ProviderLeaseBundle | null>(null);
  const [leaseBundle, setLeaseBundle] = useState<ProviderLeaseBundle | null>(null);
  const leaseCallbackGateRef = useRef(createLeaseCallbackGate(() => leaseBundleRef.current?.snapshot ?? null));

  const applyLeaseBundle = useCallback((next: ProviderLeaseBundle) => {
    const nextEpoch = computeAuthorizationEpoch(next);
    const priorEpoch = leaseBundleRef.current ? computeAuthorizationEpoch(leaseBundleRef.current) : -1;
    const bundle: ProviderLeaseBundle = {
      ...next,
      authorizationEpoch: nextEpoch,
      appChromePublisherEpoch: priorEpoch !== nextEpoch
        ? (leaseBundleRef.current?.appChromePublisherEpoch ?? 0) + 1
        : (next.appChromePublisherEpoch ?? leaseBundleRef.current?.appChromePublisherEpoch ?? 0),
    };
    leaseBundleRef.current = bundle;
    setLeaseBundle(bundle);
  }, []);

  const clearLeaseBundle = useCallback(() => {
    leaseBundleRef.current = null;
    setLeaseBundle(null);
  }, []);

  const [leasedActive, setLeasedActive] = useState<LeasedActiveProjection | null>(null);
  const leasedActiveRef = useRef<LeasedActiveProjection | null>(null);
  const [leasedGraphReference, setLeasedGraphReference] = useState<LeasedGraphReference | null>(null);
  const [leasedGraphProjectionState, setLeasedGraphProjectionState] = useState<LeasedGraphProjectionState | null>(
    null,
  );

  const graphReferenceRegistrationRef = useRef<BindingRegistration<GraphReferenceProjectionBinding> | null>(null);
  const [graphReferenceRegistration, setGraphReferenceRegistration] = useState<
    BindingRegistration<GraphReferenceProjectionBinding> | null
  >(null);
  const diagnosticsRegistrationRef = useRef<BindingRegistration<GraphReviewDiagnosticsProjectionPayload> | null>(
    null,
  );
  const [diagnosticsRegistration, setDiagnosticsRegistration] = useState<
    BindingRegistration<GraphReviewDiagnosticsProjectionPayload> | null
  >(null);

  const clearSelectedProjection = useCallback(() => {
    leasedActiveRef.current = null;
    setLeasedActive(null);
    setLeasedGraphReference(null);
    setLeasedGraphProjectionState(null);
  }, []);

  const revalidateLeasedAttachmentsAfterSnapshot = useCallback(() => {
    const bundle = leaseBundleRef.current;
    if (!bundle?.snapshot.effectivePublication) {
      clearSelectedProjection();
      graphReferenceRegistrationRef.current = null;
      setGraphReferenceRegistration(null);
      diagnosticsRegistrationRef.current = null;
      setDiagnosticsRegistration(null);
      return;
    }
    const legacyValidated = bundle.legacyProjection?.validated;
    if (legacyValidated) {
      const nextLeased = revalidateLeasedProjection(legacyValidated, leasedActiveRef.current);
      leasedActiveRef.current = nextLeased;
      setLeasedActive(nextLeased);
      if (!nextLeased || nextLeased.projection.kind !== "content") {
        setLeasedGraphReference(null);
        setLeasedGraphProjectionState(null);
      }
    }
    if (!isAuthorizedPlanPublication(bundle)) {
      graphReferenceRegistrationRef.current = null;
      setGraphReferenceRegistration(null);
    }
    if (!isAuthorizedDiagnosticsPublication(bundle)) {
      diagnosticsRegistrationRef.current = null;
      setDiagnosticsRegistration(null);
    }
  }, [clearSelectedProjection]);

  const applySameIdentityConfigUpdate = useCallback(
    (validated: ValidatedProjectionSurface): boolean => {
      const current = leaseBundleRef.current;
      if (!current?.legacyProjection?.validated) return false;
      if (
        !sameProjectionSurfaceIdentity(
          current.legacyProjection.validated.publication.identity,
          validated.publication.identity,
        )
      ) {
        return false;
      }
      const neutralBase = adaptProjectionSurfaceToNeutralBase(validated);
      const updated = updateSurfaceInteractionLease(
        current.snapshot,
        current.snapshot.token,
        neutralBase,
        leaseCallbackGateRef.current,
      );
      if (!updated) return false;
      applyLeaseBundle({
        snapshot: updated,
        legacyProjection: { validated },
        authorizationEpoch: current.authorizationEpoch,
        appChromePublisherEpoch: current.appChromePublisherEpoch,
      });
      revalidateLeasedAttachmentsAfterSnapshot();
      return true;
    },
    [applyLeaseBundle, revalidateLeasedAttachmentsAfterSnapshot],
  );

  const publishSurfaceInteractionPublication = useCallback(
    (publication: unknown | null) => {
      const snapshot = bindSurfaceInteractionLease(
        publication,
        "legacy_route",
        leaseCallbackGateRef.current,
      );
      clearSelectedProjection();
      applyLeaseBundle({
        snapshot,
        legacyProjection: null,
        authorizationEpoch: 0,
        appChromePublisherEpoch: leaseBundleRef.current?.appChromePublisherEpoch ?? 0,
      });
      const token = snapshot.token;
      return () => {
        if (leaseBundleRef.current?.snapshot.token !== token) return;
        clearSelectedProjection();
        clearLeaseBundle();
      };
    },
    [applyLeaseBundle, clearLeaseBundle, clearSelectedProjection],
  );

  const updateSurfaceInteractionPublication = useCallback((publication: unknown) => {
    const current = leaseBundleRef.current;
    if (!current?.snapshot.boundIdentity) return;
    const updated = updateSurfaceInteractionLease(
      current.snapshot,
      current.snapshot.token,
      publication,
      leaseCallbackGateRef.current,
    );
    if (!updated) return;
    applyLeaseBundle({
      ...current,
      snapshot: updated,
    });
    revalidateLeasedAttachmentsAfterSnapshot();
  }, [applyLeaseBundle, revalidateLeasedAttachmentsAfterSnapshot]);

  const publishAppChromeCompatibility = useCallback((fragment: SurfaceInteractionChromeFragment) => {
    const current = leaseBundleRef.current;
    const capturedToken = current?.snapshot.token ?? null;
    const capturedPublisherEpoch = current?.appChromePublisherEpoch ?? 0;
    if (!capturedToken || !current) return () => undefined;
    const fragmentToken = Symbol("app-chrome-fragment");
    const next = registerChromeCompatibilityFragment(
      current.snapshot,
      capturedToken,
      fragmentToken,
      fragment,
      leaseCallbackGateRef.current,
    );
    if (!next) return () => undefined;
    applyLeaseBundle({ ...current, snapshot: next });
    revalidateLeasedAttachmentsAfterSnapshot();
    return () => {
      const live = leaseBundleRef.current;
      if (!live || live.snapshot.token !== capturedToken) return;
      if (live.appChromePublisherEpoch !== capturedPublisherEpoch) return;
      const updated = unregisterChromeCompatibilityFragment(
        live.snapshot,
        capturedToken,
        fragmentToken,
        leaseCallbackGateRef.current,
      );
      if (!updated) return;
      applyLeaseBundle({ ...live, snapshot: updated });
      revalidateLeasedAttachmentsAfterSnapshot();
    };
  }, [applyLeaseBundle, leaseBundle?.appChromePublisherEpoch, leaseBundle?.authorizationEpoch, revalidateLeasedAttachmentsAfterSnapshot]);

  const publishProjectionSurface = useCallback(
    (publication: ProjectionSurfacePublication | null) => {
      if (publication !== null) {
        const validated = validateProjectionSurfacePublication(publication);
        if (applySameIdentityConfigUpdate(validated)) {
          return () => undefined;
        }
        const neutralBase = adaptProjectionSurfaceToNeutralBase(validated);
        const snapshot = bindSurfaceInteractionLease(
          neutralBase,
          "legacy_projection",
          leaseCallbackGateRef.current,
        );
        clearSelectedProjection();
        applyLeaseBundle({
          snapshot,
          legacyProjection: { validated },
          authorizationEpoch: 0,
          appChromePublisherEpoch: leaseBundleRef.current?.appChromePublisherEpoch ?? 0,
        });
        const token = snapshot.token;
        return () => {
          if (leaseBundleRef.current?.snapshot.token !== token) return;
          clearSelectedProjection();
          clearLeaseBundle();
        };
      }

      const snapshot = bindSurfaceInteractionLease(
        null,
        "legacy_projection",
        leaseCallbackGateRef.current,
      );
      clearSelectedProjection();
      applyLeaseBundle({
        snapshot,
        legacyProjection: { validated: null },
        authorizationEpoch: 0,
        appChromePublisherEpoch: leaseBundleRef.current?.appChromePublisherEpoch ?? 0,
      });
      const token = snapshot.token;
      return () => {
        if (leaseBundleRef.current?.snapshot.token !== token) return;
        clearSelectedProjection();
        clearLeaseBundle();
      };
    },
    [applyLeaseBundle, applySameIdentityConfigUpdate, clearLeaseBundle, clearSelectedProjection],
  );

  const updateProjectionSurfaceConfig = useCallback(
    (publication: ProjectionSurfacePublication) => {
      applySameIdentityConfigUpdate(validateProjectionSurfacePublication(publication));
    },
    [applySameIdentityConfigUpdate],
  );

  // Exact lease authorization: a callback captured without a current surface
  // lease (null token) must stay a no-op permanently, never a wildcard.
  const surfaceTokenGuard = (capturedToken: symbol | null, bundle: ProviderLeaseBundle | null) => {
    if (capturedToken === null || !bundle) return false;
    return bundle.snapshot.token === capturedToken;
  };

  const currentSurfaceToken = leaseBundle?.snapshot.token ?? null;

  const close = useCallback(() => {
    const capturedToken = currentSurfaceToken;
    const bundle = leaseBundleRef.current;
    if (!surfaceTokenGuard(capturedToken, bundle)) return;
    clearSelectedProjection();
  }, [clearSelectedProjection, currentSurfaceToken]);

  const openTool = useCallback(
    (toolId: string) => {
      const capturedToken = currentSurfaceToken;
      const bundle = leaseBundleRef.current;
      if (!surfaceTokenGuard(capturedToken, bundle) || !bundle!.legacyProjection?.validated?.projectionsEnabled) {
        return;
      }
      if (!bundle!.snapshot.effectivePublication) return;
      const { identity, config } = bundle!.legacyProjection!.validated!.publication;
      if (identity.surfaceId !== config.id) return;
      const activeToken = bundle!.snapshot.token;
      const tool = config.tools.find((entry) => entry.id === toolId);
      if (!tool) return;
      const next: LeasedActiveProjection = {
        surfaceToken: activeToken,
        projection: {
          kind: "tool",
          key: toolId,
          size: tool.size,
          title: tool.label,
        },
      };
      leasedActiveRef.current = next;
      setLeasedActive(next);
      setLeasedGraphReference(null);
      setLeasedGraphProjectionState(null);
    },
    [currentSurfaceToken],
  );

  const openGraphReference = useCallback(
    (args: OpenGraphReferenceArgs) => {
      const {
        resolution,
        projectionState = resolution.projectionState ?? null,
        glanceOnly = false,
        reference = resolution.reference,
      } = args;
      const capturedToken = currentSurfaceToken;
      const bundle = leaseBundleRef.current;
      if (!surfaceTokenGuard(capturedToken, bundle) || !isAuthorizedPlanPublication(bundle)) return;
      const activeToken = bundle!.snapshot.token;
      const title =
        (resolution.kind === "resolved_graph" ? resolution.graphObject?.label : null)
        ?? (resolution.kind === "resolved_corpus_fallback" ? resolution.fallback.ref.label : null)
        ?? reference?.label
        ?? resolution.locator
        ?? "Related object";
      const next: LeasedActiveProjection = {
        surfaceToken: activeToken,
        projection: {
          kind: "content",
          key: reference?.refType ?? (resolution.kind === "resolved_graph" ? resolution.graphNodeId : resolution.locator) ?? "graph-reference",
          size: glanceOnly ? "compact" : contentSize(resolution),
          title,
          glanceOnly,
        },
      };
      leasedActiveRef.current = next;
      setLeasedActive(next);
      setLeasedGraphReference({ surfaceToken: activeToken, resolution });
      setLeasedGraphProjectionState({ surfaceToken: activeToken, state: projectionState });
    },
    [currentSurfaceToken],
  );

  const expandContent = useCallback(() => {
    const capturedToken = currentSurfaceToken;
    const bundle = leaseBundleRef.current;
    if (!surfaceTokenGuard(capturedToken, bundle) || !isAuthorizedPlanPublication(bundle)) return;
    const activeToken = bundle!.snapshot.token;
    setLeasedActive((current) => {
      if (!current || current.surfaceToken !== activeToken || current.projection.kind !== "content") {
        return current;
      }
      const next: LeasedActiveProjection = {
        surfaceToken: activeToken,
        projection: { ...current.projection, size: "wide", glanceOnly: false },
      };
      leasedActiveRef.current = next;
      return next;
    });
  }, [currentSurfaceToken]);

  // Registrars capture the surface lease they were supplied under AND require
  // an authorized capability on that lease. Token/surfaceId alone is not enough.
  const registerGraphReferenceBinding = useCallback(
    (binding: GraphReferenceProjectionBinding) => {
      const capturedToken = currentSurfaceToken;
      const capturedEpoch = leaseBundleRef.current?.authorizationEpoch ?? -1;
      const bundle = leaseBundleRef.current;
      if (!capturedToken || bundle?.snapshot.token !== capturedToken || !isAuthorizedPlanPublication(bundle)) {
        return () => undefined;
      }
      const token = Symbol("graph-reference-binding");
      const registration: BindingRegistration<GraphReferenceProjectionBinding> = {
        surfaceToken: capturedToken,
        token,
        value: binding,
      };
      graphReferenceRegistrationRef.current = registration;
      setGraphReferenceRegistration(registration);
      return () => {
        if (graphReferenceRegistrationRef.current?.token === token) {
          graphReferenceRegistrationRef.current = null;
        }
        if (leaseBundleRef.current?.authorizationEpoch !== capturedEpoch) return;
        setGraphReferenceRegistration((current) => (current?.token === token ? null : current));
      };
    },
    [currentSurfaceToken, leaseBundle?.authorizationEpoch],
  );

  const registerToolProjectionPayload = useCallback(
    <K extends RegisterableToolProjectionId>(toolId: K, payload: ToolProjectionPayloadMap[K]) => {
      if (toolId !== GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID) {
        return () => undefined;
      }
      const capturedToken = currentSurfaceToken;
      const capturedEpoch = leaseBundleRef.current?.authorizationEpoch ?? -1;
      const bundle = leaseBundleRef.current;
      if (
        !capturedToken
        || bundle?.snapshot.token !== capturedToken
        || !isAuthorizedDiagnosticsPublication(bundle)
      ) {
        return () => undefined;
      }
      const token = Symbol(`tool-payload:${toolId}`);
      const typedPayload = payload as GraphReviewDiagnosticsProjectionPayload;
      const registration: BindingRegistration<GraphReviewDiagnosticsProjectionPayload> = {
        surfaceToken: capturedToken,
        token,
        value: typedPayload,
      };
      diagnosticsRegistrationRef.current = registration;
      setDiagnosticsRegistration(registration);
      return () => {
        if (diagnosticsRegistrationRef.current?.token === token) {
          diagnosticsRegistrationRef.current = null;
        }
        if (leaseBundleRef.current?.authorizationEpoch !== capturedEpoch) return;
        setDiagnosticsRegistration((current) => (current?.token === token ? null : current));
      };
    },
    [currentSurfaceToken, leaseBundle?.authorizationEpoch],
  );

  const graphReferenceBinding = useMemo((): GraphReferenceProjectionBinding | null => {
    const registration = graphReferenceRegistration;
    const bundle = leaseBundle;
    const surfaceToken = bundle?.snapshot.token;
    if (!registration || !surfaceToken || registration.surfaceToken !== surfaceToken) return null;
    if (!isAuthorizedPlanPublication(bundle)) return null;
    const { token, value: binding } = registration;
    return {
      resolverState: binding.resolverState,
      resolveRelationship: (relationship) => binding.resolveRelationship(relationship),
      openResolvedReference: (resolution, projectionState) => {
        const current = graphReferenceRegistrationRef.current;
        const live = leaseBundleRef.current;
        if (!current || current.token !== token || current.surfaceToken !== surfaceToken) return;
        if (!isAuthorizedPlanPublication(live) || live?.snapshot.token !== surfaceToken) return;
        current.value.openResolvedReference(resolution, projectionState);
      },
      openTool: (toolId) => {
        const current = graphReferenceRegistrationRef.current;
        const live = leaseBundleRef.current;
        if (!current || current.token !== token || current.surfaceToken !== surfaceToken) return;
        if (!isAuthorizedPlanPublication(live) || live?.snapshot.token !== surfaceToken) return;
        current.value.openTool(toolId);
      },
    };
  }, [graphReferenceRegistration, leaseBundle]);

  const projectionSurface = leaseBundle?.legacyProjection?.validated ?? null;
  const surfaceInteractionPublication = leaseBundle?.snapshot.effectivePublication ?? null;
  const surfaceInteractionBasePublication = leaseBundle?.snapshot.rawBasePublication ?? null;

  const active = useMemo(() => {
    if (!leasedActive || !currentSurfaceToken || leasedActive.surfaceToken !== currentSurfaceToken) return null;
    if (leasedActive.projection.kind === "content" && !isAuthorizedPlanPublication(leaseBundle)) {
      return null;
    }
    if (leasedActive.projection.kind === "tool" && !leaseBundle?.legacyProjection?.validated?.projectionsEnabled) {
      return null;
    }
    if (!leaseBundle?.snapshot.effectivePublication) return null;
    return leasedActive.projection;
  }, [currentSurfaceToken, leasedActive, leaseBundle]);

  const activeGraphReference = useMemo(() => {
    if (!leasedGraphReference || !currentSurfaceToken || leasedGraphReference.surfaceToken !== currentSurfaceToken) {
      return null;
    }
    if (!isAuthorizedPlanPublication(leaseBundle)) return null;
    return leasedGraphReference.resolution;
  }, [currentSurfaceToken, leasedGraphReference, leaseBundle]);

  const graphReferenceProjectionState = useMemo(() => {
    if (
      !leasedGraphProjectionState
      || !currentSurfaceToken
      || leasedGraphProjectionState.surfaceToken !== currentSurfaceToken
    ) {
      return null;
    }
    if (!isAuthorizedPlanPublication(leaseBundle)) return null;
    return leasedGraphProjectionState.state;
  }, [currentSurfaceToken, leasedGraphProjectionState, leaseBundle]);

  const graphReviewDiagnosticsPayload = useMemo(() => {
    const registration = diagnosticsRegistration;
    const bundle = leaseBundle;
    const surfaceToken = bundle?.snapshot.token;
    if (!registration || !surfaceToken || registration.surfaceToken !== surfaceToken) return null;
    if (!isAuthorizedDiagnosticsPublication(bundle)) return null;
    return registration.value;
  }, [diagnosticsRegistration, leaseBundle]);

  const refreshSummaries = useCallback((nextScope: AgentInteractionScope | null = scope) => {
    if (!nextScope) {
      setThreadSummaries([]);
      return;
    }
    setThreadSummaries(listAgentThreads(
      nextScope.campaignId,
      nextScope.surfaceId ?? "plan",
      nextScope.documentId,
    ));
  }, [scope]);

  const rehydrateScope = useCallback((nextScope: AgentInteractionScope) => {
    if (sameScope(scope, nextScope)) return;
    const surfaceId = nextScope.surfaceId ?? "plan";
    const storedThread = loadAgentThread(nextScope.campaignId, surfaceId, nextScope.documentId);
    setScope(nextScope);
    setActiveThread(storedThread);
    setSelectedSource(null);
    setThreadSummaries(listAgentThreads(nextScope.campaignId, surfaceId, nextScope.documentId));
  }, [scope]);

  const updateThread = useCallback((thread: AgentInteractionThread) => {
    persistAgentThread(thread);
    setActiveThread(thread);
    refreshSummaries({
      campaignId: thread.campaignId,
      sessionNumber: thread.session ?? null,
      surfaceId: thread.surfaceId,
      documentId: thread.documentId,
    });
    return thread;
  }, [refreshSummaries]);

  const ensureThread = useCallback((title = "New prep thread", backend: LiveQueryBackend = "hermes") => {
    if (activeThread) return activeThread;
    if (!scope) throw new Error("Agent Interaction scope has not been published");
    const nextThread = createAgentInteractionThread(
      scope.campaignId,
      scope.sessionNumber,
      scope.surfaceId ?? "plan",
      backend,
      title,
      scope.documentId,
    );
    return updateThread(nextThread);
  }, [activeThread, scope, updateThread]);

  const createThread = useCallback((title = "New prep thread") => {
    if (!scope) throw new Error("Agent Interaction scope has not been published");
    const nextThread = createAgentInteractionThread(
      scope.campaignId,
      scope.sessionNumber,
      scope.surfaceId ?? "plan",
      "hermes",
      title,
      scope.documentId,
    );
    setActiveAgentThread(scope.campaignId, scope.surfaceId ?? "plan", nextThread.threadId, scope.documentId);
    setSelectedSource(null);
    return updateThread(nextThread);
  }, [scope, updateThread]);

  const switchThread = useCallback((threadId: string) => {
    if (!scope) return null;
    const nextThread = loadAgentThreadById(scope.campaignId, threadId);
    if (!nextThread) return null;
    setActiveAgentThread(scope.campaignId, scope.surfaceId ?? "plan", threadId, scope.documentId);
    setSelectedSource(null);
    setActiveThread(nextThread);
    refreshSummaries(scope);
    return nextThread;
  }, [refreshSummaries, scope]);

  const deleteThread = useCallback((threadId: string) => {
    if (!scope) return;
    const doomed = loadAgentThreadById(scope.campaignId, threadId);
    if (!doomed) return;
    deleteStoredAgentThread(doomed);
    const nextThread = loadAgentThread(scope.campaignId, scope.surfaceId ?? "plan", scope.documentId);
    setActiveThread(nextThread);
    setSelectedSource(null);
    refreshSummaries(scope);
  }, [refreshSummaries, scope]);

  const renameThread = useCallback((title: string) => {
    const baseThread = activeThread ?? ensureThread(title);
    return updateThread(renameAgentThread(baseThread, title));
  }, [activeThread, ensureThread, updateThread]);

  const clearThread = useCallback(() => {
    if (!activeThread) return null;
    clearAgentThread(activeThread);
    const nextThread = { ...activeThread, updatedAt: new Date().toISOString(), turns: [], uiState: { traceVisible: activeThread.uiState?.traceVisible ?? false, scrollAnchorTurnId: null, newThreadSuggestionDismissed: false } };
    setSelectedSource(null);
    return updateThread(nextThread);
  }, [activeThread, updateThread]);

  const updateActiveTurn = useCallback((turnId: string) => {
    if (!activeThread) return;
    updateThread({ ...activeThread, uiState: { traceVisible: activeThread.uiState?.traceVisible ?? false, ...activeThread.uiState, scrollAnchorTurnId: turnId } });
    setSelectedSource(null);
  }, [activeThread, updateThread]);

  const appendResponseTurn = useCallback((question: string, response: Parameters<typeof turnFromResponse>[1]) => {
    const backend = activeThread?.activeBackend ?? "hermes";
    const currentThread = activeThread ?? ensureThread(threadTitleFromQuestion(question), backend);
    const nextTurn = turnFromResponse(question, response, backend);
    const nextTurns = [nextTurn, ...currentThread.turns].slice(0, AGENT_TURN_HISTORY_CAP);
    const nextThread: AgentInteractionThread = {
      ...currentThread,
      threadId: response.agent_thread_id ?? currentThread.threadId,
      title: currentThread.turns.length ? currentThread.title : threadTitleFromQuestion(question),
      updatedAt: new Date().toISOString(),
      activeBackend: backend,
      hermesSession: response.mode === "hermes_graph_agent"
        ? (response.hermes_session ?? currentThread.hermesSession ?? null)
        : (response.hermes_session ?? currentThread.hermesSession ?? null),
      turns: nextTurns,
      uiState: {
        traceVisible: currentThread.uiState?.traceVisible ?? false,
        scrollAnchorTurnId: nextTurn.turnId,
        newThreadSuggestionDismissed: currentThread.uiState?.newThreadSuggestionDismissed ?? false,
      },
    };
    setSelectedSource(null);
    return updateThread(nextThread);
  }, [activeThread, ensureThread, updateThread]);

  const updateTurnFreshness: AgentInteractionContextValue["updateTurnFreshness"] = useCallback((turnId, freshness) => {
    if (!activeThread) return null;
    return updateThread({
      ...activeThread,
      updatedAt: new Date().toISOString(),
      turns: activeThread.turns.map((turn) => (turn.turnId === turnId ? { ...turn, corpusFreshness: freshness } : turn)),
    });
  }, [activeThread, updateThread]);

  const value = useMemo<AgentInteractionContextValue>(() => ({
    scope,
    activeThread,
    activeThreadId: activeThread?.threadId ?? null,
    threads: activeThread ? [activeThread] : [],
    threadSummaries,
    turns: activeThread?.turns ?? [],
    traceVisible: activeThread?.uiState?.traceVisible ?? false,
    paneState,
    activeSurfaceContext,
    selectedSource,
    projectionSurface,
    surfaceInteractionPublication,
    surfaceInteractionBasePublication,
    active,
    activeGraphReference,
    graphReferenceProjectionState,
    graphReferenceBinding,
    graphReviewDiagnosticsPayload,
    publishProjectionSurface,
    updateProjectionSurfaceConfig,
    publishSurfaceInteractionPublication,
    updateSurfaceInteractionPublication,
    publishAppChromeCompatibility,
    openTool,
    openGraphReference,
    expandContent,
    close,
    registerGraphReferenceBinding,
    registerToolProjectionPayload,
    publishSurfaceContext: setActiveSurfaceContext,
    setPaneOpen: (isOpen) => setPaneState((current) => ({ ...current, isOpen, mode: isOpen ? "pane" : "bar" })),
    setPaneMode: (mode) => setPaneState((current) => ({ ...current, mode })),
    setSelectedSource,
    rehydrateScope,
    ensureThread,
    createThread,
    switchThread,
    deleteThread,
    renameThread,
    clearThread,
    updateThread,
    updateActiveTurn,
    appendResponseTurn,
    updateTurnFreshness,
  }), [
    active,
    activeGraphReference,
    activeSurfaceContext,
    activeThread,
    appendResponseTurn,
    clearThread,
    close,
    createThread,
    deleteThread,
    ensureThread,
    expandContent,
    graphReferenceBinding,
    graphReferenceProjectionState,
    graphReviewDiagnosticsPayload,
    openGraphReference,
    openTool,
    paneState,
    projectionSurface,
    surfaceInteractionPublication,
    surfaceInteractionBasePublication,
    publishProjectionSurface,
    publishSurfaceInteractionPublication,
    publishAppChromeCompatibility,
    rehydrateScope,
    registerGraphReferenceBinding,
    registerToolProjectionPayload,
    renameThread,
    scope,
    selectedSource,
    switchThread,
    threadSummaries,
    updateActiveTurn,
    updateProjectionSurfaceConfig,
    updateSurfaceInteractionPublication,
    updateThread,
    updateTurnFreshness,
  ]);

  return <AgentInteractionContext.Provider value={value}>{children}</AgentInteractionContext.Provider>;
}

export function useAgentInteraction(): AgentInteractionContextValue {
  const context = useContext(AgentInteractionContext);
  if (!context) throw new Error("useAgentInteraction must be used within AgentInteractionProvider");
  return context;
}

export function useOptionalAgentInteraction(): AgentInteractionContextValue | null {
  return useContext(AgentInteractionContext);
}
