import { useEffect, useLayoutEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { createPortal } from "react-dom";

import { postWorldPlanAgentTurn } from "../../api/liveApi";
import type {
  AgentInteractionThread,
  AgentInteractionTurn,
  WorldPlanAgentTurnRequestV1,
  WorldPlanAgentTurnResolvedSummary,
} from "../../api/types";
import { useAskPluginSlotOptional, useRegisterAskPluginPresence } from "../../agentInteraction/AskPluginSlot";
import { usePublishAgentSurfaceContext } from "../../agentInteraction/usePublishAgentSurfaceContext";
import { useAgentInteraction } from "../../agentInteraction/useAgentInteraction";
import { useSelectedWorld } from "../../selectedWorld/SelectedWorldContext";
import {
  AGENT_TURN_HISTORY_CAP,
  createAgentInteractionThread,
  safeTraceForPersistence,
  threadTitleFromQuestion,
} from "./agentInteractionHistory";
import "./WorldPlanAgentConversation.css";

interface WorldPlanAgentConversationProps {
  worldId: string;
  worldName: string;
  documentId: string | null;
  surfaceInstanceId: string;
  revision: number | null;
  savedDirty: boolean;
  pageReady: boolean;
  saveInFlight: boolean;
}

interface ValidatedWorldPlanResponse {
  answer: string;
  trace: Record<string, unknown>;
  summary: WorldPlanAgentTurnResolvedSummary;
}

type ValidationResult =
  | { ok: true; value: ValidatedWorldPlanResponse }
  | { ok: false; message: string };

const RESPONSE_MISMATCH = "DungeonBuddy's response did not match this saved Plan. Try again.";
const POINTER_STATUSES = ["absent", "accepted", "recovered", "rejected", "reused"] as const;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasExactKeys(value: unknown, keys: readonly string[]): value is Record<string, unknown> {
  if (!isRecord(value)) return false;
  const actual = Object.keys(value);
  return actual.length === keys.length && keys.every((key) => Object.prototype.hasOwnProperty.call(value, key));
}

function isNullableString(value: unknown): value is string | null {
  return value === null || typeof value === "string";
}

function isPositiveRevision(value: unknown): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= 1;
}

function planThreadNamespace(worldId: string, documentId: string): string {
  return `world-plan-agent:world:${encodeURIComponent(worldId)}:document:${encodeURIComponent(documentId)}`;
}

function validateWorldPlanResponse(
  value: unknown,
  request: WorldPlanAgentTurnRequestV1,
): ValidationResult {
  const topKeys = [
    "schema",
    "client_thread_id",
    "turn_id",
    "surface",
    "owner_scope",
    "primary_work",
    "client_work_state_reported",
    "graph",
    "conversation",
    "answer",
  ];
  if (!hasExactKeys(value, topKeys)
    || value.schema !== "dmb_agent_turn_response_v1"
    || value.client_thread_id !== request.client_thread_id
    || value.turn_id !== request.turn_id) {
    return { ok: false, message: RESPONSE_MISMATCH };
  }

  const surface = value.surface;
  if (!hasExactKeys(surface, ["surface_id", "instance_id", "status"])
    || surface.surface_id !== "plan"
    || surface.instance_id !== request.surface.instance_id
    || surface.status !== "resolved") {
    return { ok: false, message: RESPONSE_MISMATCH };
  }

  const owner = value.owner_scope;
  if (!hasExactKeys(owner, ["status", "kind", "owner_id", "name"])
    || owner.status !== "resolved"
    || owner.kind !== "world"
    || owner.owner_id !== request.owner_scope.world_id
    || !isNullableString(owner.name)) {
    return { ok: false, message: "The selected World could not be verified for this Plan response." };
  }

  const work = value.primary_work;
  if (!hasExactKeys(work, ["status", "kind", "object_id", "revision_used", "expected_revision"])
    || work.kind !== "plan"
    || work.object_id !== request.primary_work.object_id
    || work.expected_revision !== request.primary_work.expected_revision
    || !isPositiveRevision(work.revision_used)
    || !["resolved", "changed_since_expected"].includes(String(work.status))
    || (work.status === "resolved") !== (work.revision_used === request.primary_work.expected_revision)) {
    return { ok: false, message: "The saved Plan identity or revision could not be verified. Reopen the Plan and try again." };
  }

  if (value.client_work_state_reported !== request.client_work_state) {
    return { ok: false, message: RESPONSE_MISMATCH };
  }

  const graph = value.graph;
  if (!hasExactKeys(graph, [
    "status",
    "world_id",
    "campaign_id",
    "scope_mode",
    "revision_id",
    "focus",
    "selection_node_id",
    "selection_found",
    "head_revision_id",
    "is_head",
  ])
    || graph.status !== "not_requested"
    || graph.world_id !== null
    || graph.campaign_id !== null
    || graph.scope_mode !== null
    || graph.revision_id !== null
    || graph.focus !== null
    || graph.selection_node_id !== null
    || graph.selection_found !== null
    || graph.head_revision_id !== null
    || graph.is_head !== null) {
    return { ok: false, message: RESPONSE_MISMATCH };
  }

  const conversation = value.conversation;
  if (!hasExactKeys(conversation, ["client_thread_id", "turn_id", "pointer_status", "pointer_id"])
    || conversation.client_thread_id !== request.client_thread_id
    || conversation.turn_id !== request.turn_id
    || !POINTER_STATUSES.includes(conversation.pointer_status as (typeof POINTER_STATUSES)[number])
    || !isNullableString(conversation.pointer_id)) {
    return { ok: false, message: RESPONSE_MISMATCH };
  }

  const answer = value.answer;
  if (!hasExactKeys(answer, ["status", "text", "code", "message", "graph_grounded", "trace"])
    || !["ok", "error"].includes(String(answer.status))
    || !isNullableString(answer.text)
    || !isNullableString(answer.code)
    || !isNullableString(answer.message)
    || answer.graph_grounded !== false
    || !isRecord(answer.trace)) {
    return { ok: false, message: RESPONSE_MISMATCH };
  }
  if (answer.status !== "ok" || typeof answer.text !== "string" || !answer.text.trim()
    || answer.code !== null || answer.message !== null) {
    return { ok: false, message: "DungeonBuddy could not complete this turn. Try again." };
  }

  const summary: WorldPlanAgentTurnResolvedSummary = {
    surfaceId: "plan",
    instanceId: request.surface.instance_id,
    ownerStatus: "resolved",
    ownerId: request.owner_scope.world_id,
    workKind: "plan",
    workObjectId: request.primary_work.object_id,
    workStatus: work.status as WorldPlanAgentTurnResolvedSummary["workStatus"],
    expectedRevision: request.primary_work.expected_revision,
    revisionUsed: work.revision_used,
    clientWorkState: request.client_work_state,
    graphStatus: "not_requested",
    pointerStatus: conversation.pointer_status as WorldPlanAgentTurnResolvedSummary["pointerStatus"],
  };
  return { ok: true, value: { answer: answer.text, trace: answer.trace, summary } };
}

function isScopedPlanThread(
  thread: AgentInteractionThread | null,
  namespace: string,
  documentId: string,
): thread is AgentInteractionThread {
  return Boolean(thread
    && thread.campaignId === namespace
    && thread.surfaceId === "plan"
    && thread.session === null
    && thread.documentId === documentId);
}

export function WorldPlanAgentConversation({
  worldId,
  worldName,
  documentId,
  surfaceInstanceId,
  revision,
  savedDirty,
  pageReady,
  saveInFlight,
}: WorldPlanAgentConversationProps) {
  const selectedWorld = useSelectedWorld();
  const agent = useAgentInteraction();
  const askSlot = useAskPluginSlotOptional();
  const verifiedWorldId = selectedWorld.kind === "managed" ? selectedWorld.worldId : null;
  const planReady = Boolean(pageReady
    && verifiedWorldId === worldId
    && documentId
    && surfaceInstanceId
    && isPositiveRevision(revision));
  const namespace = planReady && documentId ? planThreadNamespace(worldId, documentId) : null;
  const surfaceContext = useMemo(() => namespace && documentId ? ({
    surfaceId: "plan" as const,
    label: "World Plan conversation",
    campaignId: namespace,
    documentId,
    sessionNumber: null,
    ambientSummary: "Conversation only · saved Plan text is not read",
    sourceEnvelope: null,
  }) : null, [documentId, namespace]);
  usePublishAgentSurfaceContext(surfaceContext);
  useRegisterAskPluginPresence(planReady);

  const scopeMatches = Boolean(namespace
    && documentId
    && agent.scope?.campaignId === namespace
    && agent.scope.surfaceId === "plan"
    && agent.scope.sessionNumber === null
    && agent.scope.documentId === documentId);
  const activeThread = isScopedPlanThread(agent.activeThread, namespace ?? "", documentId ?? "")
    ? agent.activeThread
    : null;
  const scopeKey = `${worldId}\u001f${documentId ?? ""}`;
  const requestFenceKey = JSON.stringify({
    worldId: verifiedWorldId,
    documentId,
    surfaceInstanceId,
    revision,
    planReady,
    saveInFlight,
  });
  const [question, setQuestion] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const requestRef = useRef<{ token: symbol; threadId: string; fenceKey: string } | null>(null);
  const sanitizedPointerRef = useRef<string | null>(null);
  const latestRef = useRef({ fenceKey: requestFenceKey, threadId: activeThread?.threadId ?? null, mounted: false });
  latestRef.current.fenceKey = requestFenceKey;
  latestRef.current.threadId = activeThread?.threadId ?? requestRef.current?.threadId ?? null;

  useLayoutEffect(() => {
    latestRef.current.mounted = true;
    return () => {
      latestRef.current.mounted = false;
      requestRef.current = null;
    };
  }, []);

  useLayoutEffect(() => {
    requestRef.current = null;
    setSending(false);
  }, [requestFenceKey]);

  useLayoutEffect(() => {
    const pending = requestRef.current;
    if (pending && activeThread?.threadId && pending.threadId !== activeThread.threadId) {
      requestRef.current = null;
      setSending(false);
    }
  }, [activeThread?.threadId]);

  useLayoutEffect(() => {
    setQuestion("");
    setError(null);
  }, [scopeKey]);

  useEffect(() => {
    if (!activeThread?.hermesSession) {
      sanitizedPointerRef.current = null;
      return;
    }
    const pointerKey = `${activeThread.threadId}:${activeThread.hermesSession.sessionId}`;
    if (sanitizedPointerRef.current === pointerKey) return;
    sanitizedPointerRef.current = pointerKey;
    // The generic endpoint owns its continuity pointer; never carry a legacy provider pointer into it.
    agent.updateThread({ ...activeThread, hermesSession: null });
  }, [activeThread, agent.updateThread]);

  function startNewConversation() {
    if (!scopeMatches) return;
    requestRef.current = null;
    const next = agent.createThread("New World Plan conversation");
    latestRef.current.threadId = next.threadId;
    setQuestion("");
    setError(null);
    setSending(false);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = question.trim();
    if (!planReady || !scopeMatches || !namespace || !documentId || !surfaceInstanceId
      || !isPositiveRevision(revision) || saveInFlight || !message || sending || requestRef.current) return;

    // Keep a first-turn candidate in memory only. A failed or mismatched response
    // must not create a persisted empty thread, turn summary, or question title.
    const currentThread = activeThread ?? createAgentInteractionThread(
      namespace,
      null,
      "plan",
      "hermes",
      threadTitleFromQuestion(message),
      documentId,
    );
    latestRef.current.threadId = currentThread.threadId;
    const request: WorldPlanAgentTurnRequestV1 = {
      schema: "dmb_agent_turn_request_v1",
      client_thread_id: currentThread.threadId,
      turn_id: crypto.randomUUID(),
      surface: { surface_id: "plan", instance_id: surfaceInstanceId },
      owner_scope: { kind: "world", world_id: worldId },
      primary_work: { kind: "plan", object_id: documentId, expected_revision: revision },
      client_work_state: savedDirty ? "saved_dirty" : "saved_clean",
      graph_request: { mode: "none" },
      graph_selection: null,
      message,
    };
    const token = Symbol("world-plan-agent-turn");
    requestRef.current = { token, threadId: currentThread.threadId, fenceKey: requestFenceKey };
    setSending(true);
    setError(null);
    const isCurrent = () => latestRef.current.mounted
      && latestRef.current.fenceKey === requestFenceKey
      && latestRef.current.threadId === currentThread.threadId
      && requestRef.current?.token === token;

    try {
      const response: unknown = await postWorldPlanAgentTurn(request);
      if (!isCurrent()) return;
      const validation = validateWorldPlanResponse(response, request);
      if (!validation.ok) throw new Error(validation.message);

      const now = new Date().toISOString();
      const turn: AgentInteractionTurn = {
        turnId: request.turn_id,
        askedAt: now,
        completedAt: now,
        question: message,
        answer: validation.value.answer,
        backend: "hermes",
        status: "ok",
        trace: safeTraceForPersistence(validation.value.trace),
        agentTurnResolved: validation.value.summary,
      };
      agent.updateThread({
        ...currentThread,
        campaignId: namespace,
        session: null,
        documentId,
        surfaceId: "plan",
        activeBackend: "hermes",
        hermesSession: null,
        title: currentThread.turns.length ? currentThread.title : threadTitleFromQuestion(message),
        updatedAt: now,
        turns: [turn, ...currentThread.turns].slice(0, AGENT_TURN_HISTORY_CAP),
      });
      setQuestion("");
    } catch (reason) {
      if (isCurrent()) setError(reason instanceof Error ? reason.message : "The Agent turn failed. Try again.");
    } finally {
      if (isCurrent()) {
        requestRef.current = null;
        setSending(false);
      }
    }
  }

  if (!pageReady) return null;
  if (!documentId) {
    return <p className="world-plan-agent-draft-note" role="status">Save this Plan to start an Agent conversation.</p>;
  }
  if (!planReady || !askSlot?.hostElement || !agent.paneState.isOpen || !scopeMatches) return null;

  return createPortal(
    <section className="world-plan-agent-conversation" aria-label="Saved World Plan conversation">
      <header className="world-plan-agent-conversation__header">
        <div>
          <h2>Ask DungeonBuddy</h2>
          <p>World: {worldName} · Saved Plan · Conversation only</p>
        </div>
        <button type="button" onClick={startNewConversation}>New conversation</button>
      </header>
      <p className="world-plan-agent-conversation__notice" role="note">
        DungeonBuddy sees this Plan’s title and revision, but does not read its text. It cannot answer from or edit the saved prose.
      </p>
      {saveInFlight ? (
        <p className="world-plan-agent-conversation__saving" role="status">Conversation paused while the Plan is saving.</p>
      ) : null}
      <div className="world-plan-agent-conversation__turns" aria-live="polite">
        {activeThread?.turns.length ? [...activeThread.turns].reverse().map((turn) => (
          <article key={turn.turnId}>
            <p><strong>You:</strong> {turn.question}</p>
            <p><strong>DungeonBuddy:</strong> {turn.answer}</p>
            {turn.agentTurnResolved?.surfaceId === "plan" ? (
              <p className="world-plan-agent-conversation__context">
                {turn.agentTurnResolved.workStatus === "changed_since_expected"
                  ? `Expected revision ${turn.agentTurnResolved.expectedRevision}; answered from revision ${turn.agentTurnResolved.revisionUsed}.`
                  : `Saved Plan revision ${turn.agentTurnResolved.revisionUsed}.`}
                {" "}Editor was {turn.agentTurnResolved.clientWorkState === "saved_dirty" ? "edited since save" : "unchanged"} when asked.
              </p>
            ) : null}
          </article>
        )) : (
          <p>Ask a general question to start a conversation associated with this Plan.</p>
        )}
      </div>
      <form onSubmit={(event) => { void submit(event); }}>
        <label htmlFor="world-plan-agent-question">Your question</label>
        <textarea
          id="world-plan-agent-question"
          value={question}
          onChange={(event) => setQuestion(event.currentTarget.value)}
          maxLength={8000}
          disabled={sending || saveInFlight || !scopeMatches}
        />
        {error ? <p role="alert">{error}</p> : null}
        <button type="submit" disabled={sending || saveInFlight || !scopeMatches || !question.trim()}>
          {sending ? "Asking…" : saveInFlight ? "Saving…" : "Ask"}
        </button>
      </form>
    </section>,
    askSlot.hostElement,
  );
}
