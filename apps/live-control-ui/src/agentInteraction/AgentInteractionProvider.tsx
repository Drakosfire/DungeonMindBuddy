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
import type { RunbookReferenceAttrs } from "../tiptap/references/runbookReferences";
import type { PlanGraphProjectionState, PlanReferenceResolution } from "../planSurface/reference/graphAwareReferenceResolver";
import type {
  GraphReviewDiagnosticsProjectionPayload,
  PlanReferenceProjectionBinding,
  RegisterableToolProjectionId,
  ToolProjectionPayloadMap,
} from "../planSurface/projection/projectionBindings";
import { GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID } from "../planSurface/projection/projectionBindings";
import type { ActiveProjection, ProjectionSize, SurfaceConfig } from "../planSurface/types";
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

interface SurfaceRegistration {
  token: symbol;
  validated: ValidatedProjectionSurface | null;
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

interface LeasedPlanReference {
  surfaceToken: symbol;
  resolution: PlanReferenceResolution;
}

interface LeasedPlanProjectionState {
  surfaceToken: symbol;
  state: PlanGraphProjectionState | null;
}

function contentSize(resolution: PlanReferenceResolution): ProjectionSize {
  if (resolution.kind === "graph-node" || resolution.kind === "corpus-index") return "wide";
  return "compact";
}

function revalidateLeasedProjection(
  config: SurfaceConfig,
  leased: LeasedActiveProjection | null,
): LeasedActiveProjection | null {
  if (!leased) return null;
  const { projection } = leased;
  if (projection.kind === "tool") {
    if (!config.tools.some((entry) => entry.id === projection.key)) return null;
    return leased;
  }
  if (!config.context) return null;
  return leased;
}

export function AgentInteractionProvider({ children }: { children: ReactNode }) {
  const [scope, setScope] = useState<AgentInteractionScope | null>(null);
  const [activeThread, setActiveThread] = useState<AgentInteractionThread | null>(null);
  const [threadSummaries, setThreadSummaries] = useState<AgentInteractionContextValue["threadSummaries"]>([]);
  const [paneState, setPaneState] = useState<AgentInteractionPaneState>({ isOpen: false, mode: "bar" });
  const [activeSurfaceContext, setActiveSurfaceContext] = useState<AgentInteractionSurfaceContext | null>(null);
  const [selectedSource, setSelectedSource] = useState<AgentInteractionSelectedSource | null>(null);

  const surfaceRegistrationRef = useRef<SurfaceRegistration | null>(null);
  const [surfaceRegistration, setSurfaceRegistration] = useState<SurfaceRegistration | null>(null);

  const [leasedActive, setLeasedActive] = useState<LeasedActiveProjection | null>(null);
  const leasedActiveRef = useRef<LeasedActiveProjection | null>(null);
  const [leasedPlanReference, setLeasedPlanReference] = useState<LeasedPlanReference | null>(null);
  const [leasedPlanProjectionState, setLeasedPlanProjectionState] = useState<LeasedPlanProjectionState | null>(
    null,
  );

  const planReferenceRegistrationRef = useRef<BindingRegistration<PlanReferenceProjectionBinding> | null>(null);
  const [planReferenceRegistration, setPlanReferenceRegistration] = useState<
    BindingRegistration<PlanReferenceProjectionBinding> | null
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
    setLeasedPlanReference(null);
    setLeasedPlanProjectionState(null);
  }, []);

  const publishProjectionSurface = useCallback(
    (publication: ProjectionSurfacePublication | null) => {
      const token = Symbol("projection-surface");
      const prevIdentity = surfaceRegistrationRef.current?.validated?.publication.identity ?? null;

      if (publication === null) {
        surfaceRegistrationRef.current = { token, validated: null };
        clearSelectedProjection();
        setSurfaceRegistration({ token, validated: null });
      } else {
        const validated = validateProjectionSurfacePublication(publication);
        const identityChanged = !sameProjectionSurfaceIdentity(prevIdentity, publication.identity);
        surfaceRegistrationRef.current = { token, validated };
        setSurfaceRegistration({ token, validated });
        if (identityChanged) {
          clearSelectedProjection();
        } else {
          const config = validated.publication.config;
          const nextLeased = revalidateLeasedProjection(config, leasedActiveRef.current);
          leasedActiveRef.current = nextLeased;
          setLeasedActive(nextLeased);
          if (!nextLeased || nextLeased.projection.kind !== "content") {
            setLeasedPlanReference(null);
            setLeasedPlanProjectionState(null);
          } else if (!config.context) {
            setLeasedPlanReference(null);
            setLeasedPlanProjectionState(null);
          }
        }
      }

      return () => {
        if (surfaceRegistrationRef.current?.token !== token) return;
        surfaceRegistrationRef.current = null;
        clearSelectedProjection();
        setSurfaceRegistration(null);
      };
    },
    [clearSelectedProjection],
  );

  const surfaceTokenGuard = (capturedToken: symbol | undefined, reg: SurfaceRegistration | null) => {
    if (!reg) return false;
    if (capturedToken !== undefined && reg.token !== capturedToken) return false;
    return true;
  };

  const currentSurfaceToken = surfaceRegistration?.token ?? null;

  const close = useCallback(() => {
    ((capturedToken: symbol | undefined) => {
      const reg = surfaceRegistrationRef.current;
      if (!surfaceTokenGuard(capturedToken, reg)) return;
      clearSelectedProjection();
    })(currentSurfaceToken ?? undefined);
  }, [clearSelectedProjection, currentSurfaceToken]);

  const openTool = useCallback(
    (toolId: string) => {
      ((capturedToken: symbol | undefined) => {
        const reg = surfaceRegistrationRef.current;
        if (!surfaceTokenGuard(capturedToken, reg) || !reg!.validated?.projectionsEnabled) return;
        const activeToken = reg!.token;
        const config = reg!.validated.publication.config;
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
        setLeasedPlanReference(null);
        setLeasedPlanProjectionState(null);
      })(currentSurfaceToken ?? undefined);
    },
    [currentSurfaceToken],
  );

  const openContentFromChip = useCallback(
    (
      ref: RunbookReferenceAttrs,
      resolution: PlanReferenceResolution,
      glanceOnly = true,
      projectionState: PlanGraphProjectionState | null = resolution.graphProjectionState ?? null,
    ) => {
      ((capturedToken: symbol | undefined) => {
        const reg = surfaceRegistrationRef.current;
        if (!surfaceTokenGuard(capturedToken, reg) || !reg!.validated?.projectionsEnabled) return;
        if (!reg!.validated.publication.config.context) return;
        const activeToken = reg!.token;
        const next: LeasedActiveProjection = {
          surfaceToken: activeToken,
          projection: {
            kind: "content",
            key: ref.refType,
            size: glanceOnly ? "compact" : contentSize(resolution),
            title: ref.label,
            glanceOnly,
          },
        };
        leasedActiveRef.current = next;
        setLeasedActive(next);
        setLeasedPlanReference({ surfaceToken: activeToken, resolution });
        setLeasedPlanProjectionState({ surfaceToken: activeToken, state: projectionState });
      })(currentSurfaceToken ?? undefined);
    },
    [currentSurfaceToken],
  );

  const openPlanReferenceResolution = useCallback(
    (
      resolution: PlanReferenceResolution,
      projectionState: PlanGraphProjectionState | null = resolution.graphProjectionState ?? null,
    ) => {
      ((capturedToken: symbol | undefined) => {
        const reg = surfaceRegistrationRef.current;
        if (!surfaceTokenGuard(capturedToken, reg) || !reg!.validated?.projectionsEnabled) return;
        if (!reg!.validated.publication.config.context) return;
        const activeToken = reg!.token;
        const title =
          resolution.graphObject?.label
          ?? resolution.fallback?.ref.label
          ?? resolution.locator
          ?? "Related object";
        const next: LeasedActiveProjection = {
          surfaceToken: activeToken,
          projection: {
            kind: "content",
            key: resolution.refType ?? resolution.graphNodeId ?? "plan-reference",
            size: contentSize(resolution),
            title,
            glanceOnly: false,
          },
        };
        leasedActiveRef.current = next;
        setLeasedActive(next);
        setLeasedPlanReference({ surfaceToken: activeToken, resolution });
        setLeasedPlanProjectionState({ surfaceToken: activeToken, state: projectionState });
      })(currentSurfaceToken ?? undefined);
    },
    [currentSurfaceToken],
  );

  const expandContent = useCallback(() => {
    ((capturedToken: symbol | undefined) => {
      const reg = surfaceRegistrationRef.current;
      if (!surfaceTokenGuard(capturedToken, reg)) return;
      const activeToken = reg!.token;
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
    })(currentSurfaceToken ?? undefined);
  }, [currentSurfaceToken]);

  const registerPlanReferenceBinding = useCallback((binding: PlanReferenceProjectionBinding) => {
    const surfaceToken = surfaceRegistrationRef.current?.token;
    if (!surfaceToken) return () => undefined;
    const token = Symbol("plan-reference-binding");
    const registration: BindingRegistration<PlanReferenceProjectionBinding> = {
      surfaceToken,
      token,
      value: binding,
    };
    planReferenceRegistrationRef.current = registration;
    setPlanReferenceRegistration(registration);
    return () => {
      if (planReferenceRegistrationRef.current?.token === token) {
        planReferenceRegistrationRef.current = null;
      }
      setPlanReferenceRegistration((current) => (current?.token === token ? null : current));
    };
  }, []);

  const registerToolProjectionPayload = useCallback(
    <K extends RegisterableToolProjectionId>(toolId: K, payload: ToolProjectionPayloadMap[K]) => {
      if (toolId !== GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID) {
        return () => undefined;
      }
      const surfaceToken = surfaceRegistrationRef.current?.token;
      if (!surfaceToken) return () => undefined;
      const token = Symbol(`tool-payload:${toolId}`);
      const typedPayload = payload as GraphReviewDiagnosticsProjectionPayload;
      const registration: BindingRegistration<GraphReviewDiagnosticsProjectionPayload> = {
        surfaceToken,
        token,
        value: typedPayload,
      };
      diagnosticsRegistrationRef.current = registration;
      setDiagnosticsRegistration(registration);
      return () => {
        if (diagnosticsRegistrationRef.current?.token === token) {
          diagnosticsRegistrationRef.current = null;
        }
        setDiagnosticsRegistration((current) => (current?.token === token ? null : current));
      };
    },
    [],
  );

  const planReferenceBinding = useMemo((): PlanReferenceProjectionBinding | null => {
    const registration = planReferenceRegistration;
    const surfaceToken = surfaceRegistrationRef.current?.token;
    if (!registration || !surfaceToken || registration.surfaceToken !== surfaceToken) return null;
    const { token, value: binding } = registration;
    return {
      resolverState: binding.resolverState,
      resolveRelationship: (relationship) => binding.resolveRelationship(relationship),
      openResolvedReference: (resolution, projectionState) => {
        const current = planReferenceRegistrationRef.current;
        if (!current || current.token !== token || current.surfaceToken !== surfaceToken) return;
        current.value.openResolvedReference(resolution, projectionState);
      },
      openTool: (toolId) => {
        const current = planReferenceRegistrationRef.current;
        if (!current || current.token !== token || current.surfaceToken !== surfaceToken) return;
        current.value.openTool(toolId);
      },
    };
  }, [planReferenceRegistration, surfaceRegistration]);

  const projectionSurface = surfaceRegistration?.validated ?? null;

  const active = useMemo(() => {
    if (!leasedActive || !currentSurfaceToken || leasedActive.surfaceToken !== currentSurfaceToken) return null;
    return leasedActive.projection;
  }, [currentSurfaceToken, leasedActive]);

  const activePlanReference = useMemo(() => {
    if (!leasedPlanReference || !currentSurfaceToken || leasedPlanReference.surfaceToken !== currentSurfaceToken) {
      return null;
    }
    return leasedPlanReference.resolution;
  }, [currentSurfaceToken, leasedPlanReference]);

  const planProjectionState = useMemo(() => {
    if (
      !leasedPlanProjectionState
      || !currentSurfaceToken
      || leasedPlanProjectionState.surfaceToken !== currentSurfaceToken
    ) {
      return null;
    }
    return leasedPlanProjectionState.state;
  }, [currentSurfaceToken, leasedPlanProjectionState]);

  const graphReviewDiagnosticsPayload = useMemo(() => {
    const registration = diagnosticsRegistration;
    const surfaceToken = surfaceRegistrationRef.current?.token;
    if (!registration || !surfaceToken || registration.surfaceToken !== surfaceToken) return null;
    return registration.value;
  }, [diagnosticsRegistration, surfaceRegistration]);

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
    active,
    activePlanReference,
    planProjectionState,
    planReferenceBinding,
    graphReviewDiagnosticsPayload,
    publishProjectionSurface,
    openTool,
    openContentFromChip,
    openPlanReferenceResolution,
    expandContent,
    close,
    registerPlanReferenceBinding,
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
    activePlanReference,
    activeSurfaceContext,
    activeThread,
    appendResponseTurn,
    clearThread,
    close,
    createThread,
    deleteThread,
    ensureThread,
    expandContent,
    graphReviewDiagnosticsPayload,
    openContentFromChip,
    openPlanReferenceResolution,
    openTool,
    paneState,
    planProjectionState,
    planReferenceBinding,
    projectionSurface,
    publishProjectionSurface,
    rehydrateScope,
    registerPlanReferenceBinding,
    registerToolProjectionPayload,
    renameThread,
    scope,
    selectedSource,
    switchThread,
    threadSummaries,
    updateActiveTurn,
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
