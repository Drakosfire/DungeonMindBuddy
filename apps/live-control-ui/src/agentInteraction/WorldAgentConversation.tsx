import type { BuildComposeBridge } from "../buildSurface/buildComposeBridge";
import { createContext, useCallback, useContext, useLayoutEffect, useMemo, useRef, useState, type Dispatch, type ReactNode, type SetStateAction } from "react";
import type { PlanConversationPresentationHosts } from "../planSurface/components/PlanConversationDockAdapter";
import type { WorldAgentConversationHistoryResponse } from "../api/types";
import { WorldPlanAgentConversation, type WorldPlanAgentConversationProps } from "../planSurface/components/WorldPlanAgentConversation";
import "./WorldAgentConversation.css";

export interface AdmittedWorldPlayConversationContext {
  worldId: string;
  runId: string;
  runRevision: number;
  contentBasis?: import("../api/types").WorldPlayContentBasis;
  surfaceInstanceId: string;
  beatTitle?: string | null;
  sceneTitle?: string | null;
}

export interface SavedWorldBuildConversationContext {
  worldId: string; documentId: string; revision: number; contentSha256: string;
  surfaceInstanceId: string; title: string; dirty: boolean;
}

interface BuildConversationRegistration { savedSource: SavedWorldBuildConversationContext | null; composeBridge?: BuildComposeBridge | null; presentationHosts?: PlanConversationPresentationHosts }

interface Registration<T> { token: symbol; value: T; unavailableReason?: string | null }

interface WorldConversationRegistry {
  worldId: string | null;
  plan: Registration<WorldPlanAgentConversationProps> | null;
  build: Registration<BuildConversationRegistration> | null;
  registerBuild: (token: symbol, value: BuildConversationRegistration) => void;
  unregisterBuild: (token: symbol) => void;
  play: Registration<AdmittedWorldPlayConversationContext | null> | null;
  registerPlan: (token: symbol, value: WorldPlanAgentConversationProps) => void;
  unregisterPlan: (token: symbol) => void;
  registerPlay: (token: symbol, value: AdmittedWorldPlayConversationContext | null, unavailableReason?: string | null) => void;
  unregisterPlay: (token: symbol) => void;
  history: WorldAgentConversationHistoryResponse | null;
  setHistory: Dispatch<SetStateAction<WorldAgentConversationHistoryResponse | null>>;
  pendingTurn: { surface: "plan" | "play" | "build"; turnId: string } | null;
  setPendingTurn: Dispatch<SetStateAction<{ surface: "plan" | "play" | "build"; turnId: string } | null>>;
  historyRefreshNonce: number;
  setHistoryRefreshNonce: Dispatch<SetStateAction<number>>;
}

const Registry = createContext<WorldConversationRegistry | null>(null);

export function WorldAgentConversationProvider({ children, worldId }: { children: ReactNode; worldId: string | null }) {
  const [plan, setPlan] = useState<Registration<WorldPlanAgentConversationProps> | null>(null);
  const [build, setBuild] = useState<Registration<BuildConversationRegistration> | null>(null);
  const registerBuild = useCallback((token: symbol, value: BuildConversationRegistration) => setBuild({ token, value }), []);
  const unregisterBuild = useCallback((token: symbol) => setBuild(current => current?.token === token ? null : current), []);
  const [play, setPlay] = useState<Registration<AdmittedWorldPlayConversationContext | null> | null>(null);
  const [history, setHistory] = useState<WorldAgentConversationHistoryResponse | null>(null);
  const [pendingTurn, setPendingTurn] = useState<{ surface: "plan" | "play" | "build"; turnId: string } | null>(null);
  const [historyRefreshNonce, setHistoryRefreshNonce] = useState(0);
  const registerPlan = useCallback((token: symbol, value: WorldPlanAgentConversationProps) => setPlan({ token, value }), []);
  const unregisterPlan = useCallback((token: symbol) => setPlan((current) => current?.token === token ? null : current), []);
  const registerPlay = useCallback((token: symbol, value: AdmittedWorldPlayConversationContext | null, unavailableReason: string | null = null) => setPlay({ token, value, unavailableReason }), []);
  const unregisterPlay = useCallback((token: symbol) => setPlay((current) => current?.token === token ? null : current), []);
  const value = useMemo(() => ({ worldId, plan, play, build, registerBuild, unregisterBuild, registerPlan, unregisterPlan, registerPlay, unregisterPlay,
    history, setHistory, pendingTurn, setPendingTurn, historyRefreshNonce, setHistoryRefreshNonce }),
  [worldId, plan, play, build, registerBuild, unregisterBuild, registerPlan, unregisterPlan, registerPlay, unregisterPlay, history, pendingTurn, historyRefreshNonce]);
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
export function usePublishWorldPlayConversation(context: AdmittedWorldPlayConversationContext | null, unavailableReason: string | null = null): void {
  const registry = useContext(Registry);
  const token = useRef(Symbol("world-play-conversation"));
  const worldId = context?.worldId ?? null;
  const runId = context?.runId ?? null;
  const runRevision = context?.runRevision ?? null;
  const editionRevision = context?.contentBasis?.edition_revision ?? null;
  const editionRevisionId = context?.contentBasis?.edition_revision_id ?? null;
  const contentSha = context?.contentBasis?.content_sha256 ?? null;
  const surfaceInstanceId = context?.surfaceInstanceId ?? null;
  const beatTitle = context?.beatTitle ?? null;
  const sceneTitle = context?.sceneTitle ?? null;
  useLayoutEffect(() => {
    if (!registry) return;
    registry.registerPlay(token.current, context, unavailableReason);
    return () => registry.unregisterPlay(token.current);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [registry?.registerPlay, registry?.unregisterPlay, worldId, runId, runRevision, editionRevision, editionRevisionId, contentSha, surfaceInstanceId, beatTitle, sceneTitle, unavailableReason]);
}

export function usePublishWorldBuildConversation(context: SavedWorldBuildConversationContext | null, presentationHosts?: PlanConversationPresentationHosts, composeBridge?: BuildComposeBridge | null) {
  const registry = useContext(Registry);
  const token = useRef(Symbol("world-build-conversation"));
  useLayoutEffect(() => {
    if (!registry) return;
    registry.registerBuild(token.current, { savedSource: context, presentationHosts, composeBridge });
    return () => registry.unregisterBuild(token.current);
  }, [registry?.registerBuild, registry?.unregisterBuild, context, presentationHosts, composeBridge]);
}

/** One persistent conversation controller; route adapters supply current context and portal hosts. */
export function WorldAgentConversation({ surface, worldId, worldName }: {
  surface: "plan" | "play" | "build" | "other";
  worldId: string | null;
  worldName?: string;
}) {
  const registry = useContext(Registry);
  const lastPlan = useRef<WorldPlanAgentConversationProps | null>(null);
  if (registry?.plan?.value.worldId === worldId) lastPlan.current = registry.plan.value;
  if (!worldId || !registry || registry.worldId !== worldId) return null;
  // Unmount the transport/recovery controller, not just its composer. Late
  // history and in-flight replies cannot reactivate a session-copy transport.
  if (surface === "play" && registry.play?.unavailableReason) {
    return <section aria-label="Play conversation unavailable" role="status">{registry.play.unavailableReason}</section>;
  }
  const props: WorldPlanAgentConversationProps = lastPlan.current ?? {
    worldId, worldName: worldName ?? "World", documentId: null, surfaceInstanceId: "",
    revision: null, editBridge: null, draftGeneration: 0, selectionGeneration: 0,
    savedDirty: false, pageReady: false, saveInFlight: false,
  };
  const build = registry.build?.value;
  const savedSource = build?.savedSource?.worldId === worldId ? build.savedSource : null;
  const run = registry.play?.value;
  const admittedRun = run && run.worldId === worldId && run.runId.trim()
    && Number.isSafeInteger(run.runRevision) && run.runRevision > 0 && run.surfaceInstanceId.trim()
    ? run : null;
  return <WorldPlanAgentConversation {...props} worldName={worldName ?? props.worldName}
    presentationHosts={surface === "plan" ? props.presentationHosts : surface === "build" ? build?.presentationHosts : undefined}
    visible={(surface === "plan" && registry.plan?.value.worldId === worldId) || surface === "play" || surface === "build"}
    buildMode={surface === "build" ? { savedSource, composeBridge: build?.composeBridge ?? null } : null}
    playMode={surface === "play" ? { admittedRun } : null} />;
}
