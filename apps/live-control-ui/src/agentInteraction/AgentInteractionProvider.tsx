import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

import type { AgentInteractionThread, AgentInteractionThreadSummary } from "../api/types";
import {
  deleteAgentThread,
  listAgentThreads,
  loadAgentThread,
  loadAgentThreadById,
  persistAgentThread,
  renameAgentThread,
  setActiveAgentThread,
} from "./agentInteractionStorage";
import type {
  AgentInteractionPaneState,
  AgentInteractionSelectedSource,
  AgentInteractionSurfaceContext,
  AgentInteractionSurfaceId,
} from "./agentInteractionTypes";

const emptySelectedSource: AgentInteractionSelectedSource = {
  citationKey: null,
  status: "idle",
  error: null,
  response: null,
};

interface AgentInteractionContextValue {
  activeThread: AgentInteractionThread | null;
  activeThreadId: string | null;
  threadSummaries: AgentInteractionThreadSummary[];
  paneState: AgentInteractionPaneState;
  activeSurfaceContext: AgentInteractionSurfaceContext | null;
  selectedSource: AgentInteractionSelectedSource;
  hydrateSurface: (campaignId: string, surfaceId?: AgentInteractionSurfaceId) => AgentInteractionThread | null;
  publishSurfaceContext: (context: Omit<AgentInteractionSurfaceContext, "updatedAt"> & { updatedAt?: string }) => void;
  setPaneOpen: (isOpen: boolean) => void;
  setPaneMode: (mode: AgentInteractionPaneState["mode"]) => void;
  setActiveThread: (thread: AgentInteractionThread | null) => void;
  persistThread: (thread: AgentInteractionThread) => void;
  loadThreadById: (campaignId: string, threadId: string) => AgentInteractionThread | null;
  switchThread: (campaignId: string, surfaceId: string, threadId: string) => AgentInteractionThread | null;
  renameThread: (thread: AgentInteractionThread, title: string) => AgentInteractionThread;
  deleteThread: (thread: AgentInteractionThread) => AgentInteractionThread | null;
  refreshThreadSummaries: (campaignId: string, surfaceId?: AgentInteractionSurfaceId) => void;
  resetSelectedSource: () => void;
  setSelectedSource: (source: AgentInteractionSelectedSource) => void;
}

const AgentInteractionContext = createContext<AgentInteractionContextValue | null>(null);

interface AgentInteractionProviderProps {
  children: ReactNode;
}

export function AgentInteractionProvider({ children }: AgentInteractionProviderProps) {
  const [activeThread, setActiveThreadState] = useState<AgentInteractionThread | null>(null);
  const [threadSummaries, setThreadSummaries] = useState<AgentInteractionThreadSummary[]>([]);
  const [paneState, setPaneState] = useState<AgentInteractionPaneState>({ isOpen: false, mode: "bar" });
  const [activeSurfaceContext, setActiveSurfaceContext] = useState<AgentInteractionSurfaceContext | null>(null);
  const [selectedSource, setSelectedSourceState] = useState<AgentInteractionSelectedSource>(emptySelectedSource);

  const refreshThreadSummaries = useCallback((campaignId: string, surfaceId: AgentInteractionSurfaceId = "plan") => {
    setThreadSummaries(listAgentThreads(campaignId, surfaceId));
  }, []);

  const hydrateSurface = useCallback((campaignId: string, surfaceId: AgentInteractionSurfaceId = "plan") => {
    const storedThread = loadAgentThread(campaignId, surfaceId);
    setThreadSummaries(listAgentThreads(campaignId, surfaceId));
    setActiveThreadState(storedThread);
    return storedThread;
  }, []);

  const publishSurfaceContext = useCallback((context: Omit<AgentInteractionSurfaceContext, "updatedAt"> & { updatedAt?: string }) => {
    setActiveSurfaceContext({ ...context, updatedAt: context.updatedAt ?? new Date().toISOString() });
  }, []);

  const setPaneOpen = useCallback((isOpen: boolean) => {
    setPaneState({ isOpen, mode: isOpen ? "pane" : "bar" });
  }, []);

  const setPaneMode = useCallback((mode: AgentInteractionPaneState["mode"]) => {
    setPaneState((current) => ({ ...current, mode }));
  }, []);

  const setActiveThread = useCallback((thread: AgentInteractionThread | null) => {
    setActiveThreadState(thread);
  }, []);

  const persistThread = useCallback((thread: AgentInteractionThread) => {
    persistAgentThread(thread);
    setActiveThreadState(thread);
    setThreadSummaries(listAgentThreads(thread.campaignId, thread.surfaceId));
  }, []);

  const loadThreadById = useCallback((campaignId: string, threadId: string) => loadAgentThreadById(campaignId, threadId), []);

  const switchThread = useCallback((campaignId: string, surfaceId: string, threadId: string) => {
    const nextThread = loadAgentThreadById(campaignId, threadId);
    if (!nextThread) return null;
    setActiveAgentThread(campaignId, surfaceId, threadId);
    setActiveThreadState(nextThread);
    setThreadSummaries(listAgentThreads(campaignId, surfaceId));
    setSelectedSourceState(emptySelectedSource);
    return nextThread;
  }, []);

  const renameThread = useCallback((thread: AgentInteractionThread, title: string) => {
    const renamed = renameAgentThread(thread, title);
    setActiveThreadState(renamed);
    setThreadSummaries(listAgentThreads(renamed.campaignId, renamed.surfaceId));
    return renamed;
  }, []);

  const deleteThread = useCallback((thread: AgentInteractionThread) => {
    deleteAgentThread(thread);
    const nextActive = loadAgentThread(thread.campaignId, thread.surfaceId);
    setActiveThreadState(nextActive);
    setThreadSummaries(listAgentThreads(thread.campaignId, thread.surfaceId));
    setSelectedSourceState(emptySelectedSource);
    return nextActive;
  }, []);

  const resetSelectedSource = useCallback(() => setSelectedSourceState(emptySelectedSource), []);

  const value = useMemo<AgentInteractionContextValue>(() => ({
    activeThread,
    activeThreadId: activeThread?.threadId ?? null,
    threadSummaries,
    paneState,
    activeSurfaceContext,
    selectedSource,
    hydrateSurface,
    publishSurfaceContext,
    setPaneOpen,
    setPaneMode,
    setActiveThread,
    persistThread,
    loadThreadById,
    switchThread,
    renameThread,
    deleteThread,
    refreshThreadSummaries,
    resetSelectedSource,
    setSelectedSource: setSelectedSourceState,
  }), [activeSurfaceContext, activeThread, deleteThread, hydrateSurface, loadThreadById, paneState, persistThread, publishSurfaceContext, refreshThreadSummaries, renameThread, resetSelectedSource, selectedSource, setActiveThread, setPaneMode, setPaneOpen, switchThread, threadSummaries]);

  return <AgentInteractionContext.Provider value={value}>{children}</AgentInteractionContext.Provider>;
}

export function useAgentInteraction() {
  const context = useContext(AgentInteractionContext);
  if (!context) throw new Error("useAgentInteraction must be used within AgentInteractionProvider");
  return context;
}
