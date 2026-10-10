import { createContext, useCallback, useContext, useLayoutEffect, useMemo, useRef, useState, type Dispatch, type ReactNode, type SetStateAction } from "react";
import type { WorldAgentConversationHistoryResponse } from "../api/types";
import { WorldPlanAgentConversation, type WorldPlanAgentConversationProps } from "../planSurface/components/WorldPlanAgentConversation";
import "./WorldAgentConversation.css";

export interface AdmittedWorldPlayConversationContext {
  worldId: string;
  runId: string;
  runRevision: number;
  surfaceInstanceId: string;
  beatTitle?: string | null;
  sceneTitle?: string | null;
}

interface Registration<T> { token: symbol; value: T }

interface WorldConversationRegistry {
  worldId: string | null;
  plan: Registration<WorldPlanAgentConversationProps> | null;
  play: Registration<AdmittedWorldPlayConversationContext | null> | null;
  registerPlan: (token: symbol, value: WorldPlanAgentConversationProps) => void;
  unregisterPlan: (token: symbol) => void;
  registerPlay: (token: symbol, value: AdmittedWorldPlayConversationContext | null) => void;
  unregisterPlay: (token: symbol) => void;
  history: WorldAgentConversationHistoryResponse | null;
  setHistory: Dispatch<SetStateAction<WorldAgentConversationHistoryResponse | null>>;
  message: string;
  setMessage: Dispatch<SetStateAction<string>>;
  pendingTurn: { surface: "plan" | "play"; turnId: string } | null;
  setPendingTurn: Dispatch<SetStateAction<{ surface: "plan" | "play"; turnId: string } | null>>;
  historyRefreshNonce: number;
  setHistoryRefreshNonce: Dispatch<SetStateAction<number>>;
}

const Registry = createContext<WorldConversationRegistry | null>(null);

export function WorldAgentConversationProvider({ children, worldId }: { children: ReactNode; worldId: string | null }) {
  const [plan, setPlan] = useState<Registration<WorldPlanAgentConversationProps> | null>(null);
  const [play, setPlay] = useState<Registration<AdmittedWorldPlayConversationContext | null> | null>(null);
  const [history, setHistory] = useState<WorldAgentConversationHistoryResponse | null>(null);
  const [message, setMessage] = useState("");
  const [pendingTurn, setPendingTurn] = useState<{ surface: "plan" | "play"; turnId: string } | null>(null);
  const [historyRefreshNonce, setHistoryRefreshNonce] = useState(0);
  const registerPlan = useCallback((token: symbol, value: WorldPlanAgentConversationProps) => setPlan({ token, value }), []);
  const unregisterPlan = useCallback((token: symbol) => setPlan((current) => current?.token === token ? null : current), []);
  const registerPlay = useCallback((token: symbol, value: AdmittedWorldPlayConversationContext | null) => setPlay({ token, value }), []);
  const unregisterPlay = useCallback((token: symbol) => setPlay((current) => current?.token === token ? null : current), []);
  const value = useMemo(() => ({ worldId, plan, play, registerPlan, unregisterPlan, registerPlay, unregisterPlay,
    history, setHistory, message, setMessage, pendingTurn, setPendingTurn, historyRefreshNonce, setHistoryRefreshNonce }),
  [worldId, plan, play, registerPlan, unregisterPlan, registerPlay, unregisterPlay, history, message, pendingTurn, historyRefreshNonce]);
  return <Registry.Provider value={value}>{children}</Registry.Provider>;
}

/** Optional because isolated Plan tests mount the component without the App shell. */
export function useWorldAgentConversationState(): WorldConversationRegistry | null { return useContext(Registry); }

export function WorldPlanConversationRegistration(props: WorldPlanAgentConversationProps) {
  const registry = useContext(Registry);
  const token = useRef(Symbol("world-plan-conversation"));
  useLayoutEffect(() => {
    if (!registry || registry.worldId !== props.worldId) return;
    registry.registerPlan(token.current, props);
    return () => registry.unregisterPlan(token.current);
  }, [registry?.registerPlan, registry?.unregisterPlan, registry?.worldId, props]);
  return registry ? null : <WorldPlanAgentConversation {...props} />;
}

/** A Play route may publish only the Run admitted by its current native projection. */
export function usePublishWorldPlayConversation(context: AdmittedWorldPlayConversationContext | null): void {
  const registry = useContext(Registry);
  const token = useRef(Symbol("world-play-conversation"));
  const worldId = context?.worldId ?? null;
  const runId = context?.runId ?? null;
  const runRevision = context?.runRevision ?? null;
  const surfaceInstanceId = context?.surfaceInstanceId ?? null;
  const beatTitle = context?.beatTitle ?? null;
  const sceneTitle = context?.sceneTitle ?? null;
  useLayoutEffect(() => {
    if (!registry) return;
    registry.registerPlay(token.current, context);
    return () => registry.unregisterPlay(token.current);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [registry?.registerPlay, registry?.unregisterPlay, worldId, runId, runRevision, surfaceInstanceId, beatTitle, sceneTitle]);
}

/** One persistent conversation controller; route adapters supply current context and portal hosts. */
export function WorldAgentConversation({ surface, worldId, worldName }: {
  surface: "plan" | "play" | "other";
  worldId: string | null;
  worldName?: string;
}) {
  const registry = useContext(Registry);
  const lastPlan = useRef<WorldPlanAgentConversationProps | null>(null);
  if (registry?.plan?.value.worldId === worldId) lastPlan.current = registry.plan.value;
  if (!worldId || !registry || registry.worldId !== worldId) return null;
  const props: WorldPlanAgentConversationProps = lastPlan.current ?? {
    worldId, worldName: worldName ?? "World", documentId: null, surfaceInstanceId: "",
    revision: null, editBridge: null, draftGeneration: 0, selectionGeneration: 0,
    savedDirty: false, pageReady: false, saveInFlight: false,
  };
  const run = registry.play?.value;
  const admittedRun = run && run.worldId === worldId && run.runId.trim()
    && Number.isSafeInteger(run.runRevision) && run.runRevision > 0 && run.surfaceInstanceId.trim()
    ? run : null;
  return <WorldPlanAgentConversation {...props} worldName={worldName ?? props.worldName}
    visible={(surface === "plan" && registry.plan?.value.worldId === worldId) || surface === "play"}
    playMode={surface === "play" ? { admittedRun } : null} />;
}
