import { useLayoutEffect, useRef, useState, type FormEvent } from "react";
import { createPortal } from "react-dom";

import { postIndexAgentTurn } from "../api/liveApi";
import type {
  AgentInteractionThread,
  AgentInteractionTurn,
  IndexAgentTurnRequestV1,
  IndexAgentTurnResponseV1,
  IndexAgentTurnResolvedSummary,
} from "../api/types";
import { useSelectedWorld } from "../selectedWorld/SelectedWorldContext";
import { AGENT_TURN_HISTORY_CAP, threadTitleFromQuestion } from "../planSurface/components/agentInteractionHistory";
import { useAskPluginSlotOptional, useRegisterAskPluginPresence } from "./AskPluginSlot";
import { useAgentInteraction } from "./useAgentInteraction";
import "./IndexAgentConversation.css";

const INDEX_NO_OWNER_STORAGE_KEY = "index-owner:none";

function indexStorageKey(worldId: string | null): string {
  // This is a browser-local thread namespace, never a campaign or wire owner ID.
  return worldId ? `index-owner:world:${worldId}` : INDEX_NO_OWNER_STORAGE_KEY;
}

function resolvedSummary(response: IndexAgentTurnResponseV1): IndexAgentTurnResolvedSummary {
  return {
    surfaceId: "index",
    instanceId: response.surface.instance_id,
    ownerStatus: response.owner_scope.status as "absent" | "resolved",
    ownerId: response.owner_scope.owner_id,
    ownerName: response.owner_scope.name,
    workStatus: "absent",
    graphStatus: "not_requested",
    pointerStatus: response.conversation.pointer_status,
  };
}

function validIndexResponse(
  response: IndexAgentTurnResponseV1,
  request: IndexAgentTurnRequestV1,
): boolean {
  const ownerMatches = request.owner_scope
    ? response?.owner_scope?.status === "resolved"
      && response.owner_scope.kind === "world"
      && response.owner_scope.owner_id === request.owner_scope.world_id
    : response?.owner_scope?.status === "absent"
      && response.owner_scope.kind === null
      && response.owner_scope.owner_id === null
      && response.owner_scope.name === null;
  return response?.schema === "dmb_agent_turn_response_v1"
    && response.client_thread_id === request.client_thread_id
    && response.turn_id === request.turn_id
    && response.conversation?.client_thread_id === request.client_thread_id
    && response.conversation.turn_id === request.turn_id
    && response.surface?.status === "resolved"
    && response.surface.surface_id === "index"
    && response.surface.instance_id === request.surface.instance_id
    && ownerMatches
    && response.primary_work?.status === "absent"
    && response.primary_work.kind === null
    && response.primary_work.object_id === null
    && response.primary_work.revision_used === null
    && response.primary_work.expected_revision === null
    && response.client_work_state_reported === "none"
    && response.graph?.status === "not_requested"
    && response.graph.world_id === null
    && response.graph.campaign_id === null
    && response.graph.scope_mode === null
    && response.graph.revision_id === null
    && response.graph.selection_node_id === null
    && response.graph.selection_found === null
    && response.answer?.status === "ok"
    && response.answer.graph_grounded === false
    && typeof response.answer.text === "string"
    && response.answer.text.trim().length > 0;
}

/** Index has no primary work; the selected World is independently verified. */
export function IndexAgentConversation() {
  const selectedWorld = useSelectedWorld();
  const agent = useAgentInteraction();
  const askSlot = useAskPluginSlotOptional();
  const publication = agent.surfaceInteractionBasePublication;
  const instanceId = publication?.surfaceId === "index" ? publication.identity.instanceKey : null;
  const worldId = selectedWorld.kind === "managed" ? selectedWorld.worldId : null;
  const selectionReady = selectedWorld.kind === "managed" || selectedWorld.kind === "legacy";
  const storageKey = selectionReady ? indexStorageKey(worldId) : null;
  const identityKey = `${instanceId ?? "unavailable"}:${storageKey ?? "unavailable"}`;
  const [scopeReadyKey, setScopeReadyKey] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const activeThread = agent.activeThread;
  const thread = activeThread?.surfaceId === "index" && activeThread.campaignId === storageKey
    ? activeThread : null;
  const latestRef = useRef({ identityKey, threadId: thread?.threadId ?? null, mounted: false });
  latestRef.current.identityKey = identityKey;
  latestRef.current.threadId = thread?.threadId ?? latestRef.current.threadId;
  const requestRef = useRef<symbol | null>(null);

  useRegisterAskPluginPresence(Boolean(instanceId && selectionReady));

  useLayoutEffect(() => {
    latestRef.current.mounted = true;
    return () => { latestRef.current.mounted = false; requestRef.current = null; };
  }, []);

  useLayoutEffect(() => {
    requestRef.current = null;
    latestRef.current.threadId = thread?.threadId ?? null;
    setQuestion("");
    setError(null);
    setSending(false);
    setScopeReadyKey(null);
    if (!storageKey) return;
    agent.rehydrateScope({ campaignId: storageKey, sessionNumber: null, surfaceId: "index", documentId: null });
    setScopeReadyKey(identityKey);
    // The local scope key changes only with verified owner or leased Index instance.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [identityKey, storageKey]);

  const ready = Boolean(instanceId && storageKey && scopeReadyKey === identityKey);

  function newThread() {
    if (!ready) return;
    requestRef.current = null;
    const next = agent.createThread("New Index conversation");
    latestRef.current.threadId = next.threadId;
    setQuestion("");
    setError(null);
    setSending(false);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = question.trim();
    if (!ready || !instanceId || !storageKey || !message || sending || requestRef.current) return;
    const currentThread: AgentInteractionThread = thread ?? agent.createThread(threadTitleFromQuestion(message));
    latestRef.current.threadId = currentThread.threadId;
    const request: IndexAgentTurnRequestV1 = {
      schema: "dmb_agent_turn_request_v1",
      client_thread_id: currentThread.threadId,
      turn_id: crypto.randomUUID(),
      surface: { surface_id: "index", instance_id: instanceId },
      owner_scope: worldId ? { kind: "world", world_id: worldId } : null,
      primary_work: null,
      client_work_state: "none",
      graph_request: { mode: "none" },
      graph_selection: null,
      message,
    };
    const token = Symbol("index-agent-turn");
    requestRef.current = token;
    setSending(true);
    setError(null);
    const isCurrent = () => latestRef.current.mounted
      && latestRef.current.identityKey === identityKey
      && latestRef.current.threadId === currentThread.threadId
      && requestRef.current === token;
    try {
      const response = await postIndexAgentTurn(request);
      if (!isCurrent()) return;
      if (!validIndexResponse(response, request)) {
        throw new Error("Agent response did not match this Index conversation. Try again.");
      }
      const now = new Date().toISOString();
      const turn: AgentInteractionTurn = {
        turnId: request.turn_id,
        askedAt: now,
        completedAt: now,
        question: message,
        answer: response.answer.text!,
        backend: "hermes",
        status: "ok",
        agentTurnResolved: resolvedSummary(response),
      };
      agent.updateThread({
        ...currentThread,
        title: currentThread.turns.length ? currentThread.title : threadTitleFromQuestion(message),
        updatedAt: now,
        turns: [turn, ...currentThread.turns].slice(0, AGENT_TURN_HISTORY_CAP),
      });
      setQuestion("");
    } catch (reason) {
      if (isCurrent()) setError(reason instanceof Error ? reason.message : "Agent turn failed. Try again.");
    } finally {
      if (isCurrent()) {
        requestRef.current = null;
        setSending(false);
      }
    }
  }

  if (!askSlot?.hostElement || !agent.paneState.isOpen || !ready) return null;
  return createPortal(
    <section className="index-agent-conversation" aria-label="Index conversation">
      <header>
        <h2>Ask DungeonBuddy</h2>
        <p>{worldId ? `World: ${selectedWorld.kind === "managed" ? selectedWorld.name : worldId}` : "No World selected"} · Conversation only</p>
        <button type="button" onClick={newThread}>New conversation</button>
      </header>
      <div className="index-agent-conversation__turns" aria-live="polite">
        {thread?.turns.length ? [...thread.turns].reverse().map((turn) => (
          <article key={turn.turnId}>
            <p><strong>You:</strong> {turn.question}</p>
            <p><strong>DungeonBuddy:</strong> {turn.answer}</p>
            {turn.agentTurnResolved ? <p className="index-agent-conversation__context">
              {turn.agentTurnResolved.ownerStatus === "resolved"
                ? `World: ${turn.agentTurnResolved.ownerName ?? turn.agentTurnResolved.ownerId}`
                : "No World"} · No work object · No graph requested · {turn.agentTurnResolved.pointerStatus}
            </p> : null}
          </article>
        )) : <p>Ask a question to start a browser-local conversation.</p>}
      </div>
      <form onSubmit={(event) => { void submit(event); }}>
        <label htmlFor="index-agent-question">Your question</label>
        <textarea id="index-agent-question" value={question} onChange={(event) => setQuestion(event.target.value)} maxLength={8000} />
        {error ? <p role="alert">{error}</p> : null}
        <button type="submit" disabled={sending || !question.trim()}>{sending ? "Asking…" : "Ask"}</button>
      </form>
    </section>,
    askSlot.hostElement,
  );
}
