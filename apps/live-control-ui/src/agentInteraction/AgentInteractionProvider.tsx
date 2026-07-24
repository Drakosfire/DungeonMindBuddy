import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

import type { AgentInteractionThread, LiveQueryBackend } from "../api/types";
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

export function AgentInteractionProvider({ children }: { children: ReactNode }) {
  const [scope, setScope] = useState<AgentInteractionScope | null>(null);
  const [activeThread, setActiveThread] = useState<AgentInteractionThread | null>(null);
  const [threadSummaries, setThreadSummaries] = useState<AgentInteractionContextValue["threadSummaries"]>([]);
  const [paneState, setPaneState] = useState<AgentInteractionPaneState>({ isOpen: false, mode: "bar" });
  const [activeSurfaceContext, setActiveSurfaceContext] = useState<AgentInteractionSurfaceContext | null>(null);
  const [selectedSource, setSelectedSource] = useState<AgentInteractionSelectedSource | null>(null);

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
  }), [activeSurfaceContext, activeThread, appendResponseTurn, clearThread, createThread, deleteThread, ensureThread, paneState, rehydrateScope, renameThread, scope, selectedSource, switchThread, threadSummaries, updateActiveTurn, updateThread, updateTurnFreshness]);

  return <AgentInteractionContext.Provider value={value}>{children}</AgentInteractionContext.Provider>;
}

export function useAgentInteraction(): AgentInteractionContextValue {
  const context = useContext(AgentInteractionContext);
  if (!context) throw new Error("useAgentInteraction must be used within AgentInteractionProvider");
  return context;
}
