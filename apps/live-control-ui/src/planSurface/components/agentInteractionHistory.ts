import type {
  AgentInteractionContextSummary,
  AgentInteractionThreadIndex,
  AgentInteractionThreadSummary,
  AgentInteractionThread,
  AgentInteractionTurn,
  AgentInteractionTurnMeta,
  LiveQueryBackend,
  AgentInteractionTrace,
  LiveQueryResponse,
} from "../../api/types";

export const AGENT_TURN_HISTORY_CAP = 20;
export const AGENT_THREAD_STORAGE_PREFIX = "agent-interaction-thread-v1";
export const AGENT_ACTIVE_THREAD_STORAGE_PREFIX = "agent-interaction-active-thread-v1";
export const AGENT_THREAD_INDEX_STORAGE_PREFIX = "agent-interaction-thread-index-v1";

export function activeThreadStorageKey(campaignId: string, surfaceId = "plan"): string {
  return `${AGENT_ACTIVE_THREAD_STORAGE_PREFIX}:${campaignId}:${surfaceId}`;
}

export function threadStorageKey(campaignId: string, threadId: string): string {
  return `${AGENT_THREAD_STORAGE_PREFIX}:${campaignId}:${threadId}`;
}

export function threadIndexStorageKey(campaignId: string, surfaceId = "plan"): string {
  return `${AGENT_THREAD_INDEX_STORAGE_PREFIX}:${campaignId}:${surfaceId}`;
}

export function historyStorageKey(campaignId: string): string {
  return `plan-agent-turns-v1:${campaignId}`;
}

function newId(prefix: string): string {
  return `${prefix}-${crypto.randomUUID?.() ?? Math.random().toString(36).slice(2)}`;
}

export function threadTitleFromQuestion(question: string): string {
  const trimmed = question.trim().replace(/\s+/g, " ");
  if (!trimmed) return "New prep thread";
  return trimmed.length > 56 ? `${trimmed.slice(0, 53)}…` : trimmed;
}

export function createAgentInteractionThread(
  campaignId: string,
  session: number,
  surfaceId = "plan",
  backend: LiveQueryBackend = "hermes",
  title = "New prep thread",
): AgentInteractionThread {
  const now = new Date().toISOString();
  return {
    threadId: newId("agent-thread"),
    title,
    createdAt: now,
    updatedAt: now,
    campaignId,
    session,
    surfaceId,
    activeBackend: backend,
    hermesSession: null,
    turns: [],
    uiState: { traceVisible: true, scrollAnchorTurnId: null },
  };
}

function emptyThreadIndex(campaignId: string, surfaceId = "plan"): AgentInteractionThreadIndex {
  return {
    schema: "agent_interaction_thread_index_v1",
    campaignId,
    surfaceId,
    activeThreadId: null,
    threads: [],
  };
}

function summarizeThread(thread: AgentInteractionThread): AgentInteractionThreadSummary {
  return {
    threadId: thread.threadId,
    title: thread.title || "New prep thread",
    createdAt: thread.createdAt,
    updatedAt: thread.updatedAt,
    turnCount: thread.turns.length,
    activeBackend: thread.activeBackend,
    hermesSessionId: thread.hermesSession?.sessionId ?? null,
  };
}

function contextSummaryFromResponse(response: LiveQueryResponse): AgentInteractionContextSummary | undefined {
  const traceSummary = response.agent_trace?.context_summary;
  if (traceSummary) return traceSummary;
  if (!response.context_packet) return undefined;
  return {
    admitted_count: response.context_packet.admitted_evidence?.length ?? 0,
    rejected_count: response.context_packet.rejected_evidence?.length ?? 0,
  };
}

function isAbsolutePath(path: string): boolean {
  return path.startsWith("/") || /^[A-Za-z]:[\\/]/.test(path);
}

export function safeTraceForPersistence(
  trace: AgentInteractionTrace | null | undefined,
): AgentInteractionTrace | null {
  if (!trace) return null;
  return {
    trace_id: trace.trace_id,
    runtime: trace.runtime,
    backend: trace.backend,
    mode: trace.mode,
    provider: trace.provider ?? null,
    model: trace.model ?? null,
    started_at: trace.started_at,
    completed_at: trace.completed_at,
    elapsed_ms: trace.elapsed_ms,
    status: trace.status,
    toolset: trace.toolset ?? null,
    command_summary: trace.command_summary ?? null,
    prompt_preview: undefined,
    prompt_char_count: trace.prompt_char_count ?? null,
    prompt_token_estimate: trace.prompt_token_estimate ?? null,
    usage: trace.usage,
    steps: (trace.steps ?? []).slice(0, 12).map((step) => ({
      name: step.name,
      summary: step.name,
    })),
    context_summary: trace.context_summary,
    artifact_refs: (trace.artifact_refs ?? []).map((ref) => ({
      kind: ref.kind,
      label: ref.label,
      path: ref.path && !isAbsolutePath(ref.path) ? ref.path : "",
    })),
    warnings: trace.warnings ?? [],
  };
}

export function turnFromResponse(
  question: string,
  response: LiveQueryResponse,
  backend: LiveQueryBackend,
): AgentInteractionTurn {
  const now = new Date().toISOString();
  return {
    turnId: response.turn_id ?? response.agent_trace?.trace_id ?? response.query_id ?? newId("agent-turn"),
    askedAt: response.agent_trace?.started_at ?? now,
    completedAt: response.agent_trace?.completed_at ?? now,
    question,
    answer: response.answer,
    backend,
    status: response.status ?? response.agent_trace?.status ?? "ok",
    contextSummary: contextSummaryFromResponse(response),
    citations: response.citations ?? [],
    trace: response.agent_trace ?? null,
    warnings: response.warnings ?? response.agent_trace?.warnings ?? [],
  };
}

export function turnMetaFromResponse(
  question: string,
  response: LiveQueryResponse,
  backend: LiveQueryBackend,
): AgentInteractionTurnMeta {
  const turn = turnFromResponse(question, response, backend);
  const trace = response.agent_trace;
  return {
    id: turn.turnId,
    question,
    answer: response.answer,
    backend,
    model: trace?.model ?? null,
    status: response.status ?? trace?.status ?? "unknown",
    askedAt: turn.askedAt,
    traceId: trace?.trace_id ?? null,
    admittedCount: turn.contextSummary?.admitted_count ?? null,
    rejectedCount: turn.contextSummary?.rejected_count ?? null,
    runtime: trace?.runtime ?? null,
    elapsedMs: trace?.elapsed_ms ?? null,
    provider: trace?.provider ?? null,
    stepCount: trace?.steps?.length ?? null,
  };
}

export function loadAgentThread(campaignId: string, surfaceId = "plan"): AgentInteractionThread | null {
  try {
    const index = loadAgentThreadIndex(campaignId, surfaceId);
    const activeThreadId =
      index.activeThreadId ?? localStorage.getItem(activeThreadStorageKey(campaignId, surfaceId));
    if (!activeThreadId) return null;
    const raw = localStorage.getItem(threadStorageKey(campaignId, activeThreadId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as AgentInteractionThread;
    if (!parsed || parsed.campaignId !== campaignId || !Array.isArray(parsed.turns)) return null;
    return { ...parsed, turns: parsed.turns.slice(0, AGENT_TURN_HISTORY_CAP) };
  } catch {
    return null;
  }
}

export function loadAgentThreadById(campaignId: string, threadId: string): AgentInteractionThread | null {
  try {
    const raw = localStorage.getItem(threadStorageKey(campaignId, threadId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as AgentInteractionThread;
    if (!parsed || parsed.campaignId !== campaignId || !Array.isArray(parsed.turns)) return null;
    return { ...parsed, turns: parsed.turns.slice(0, AGENT_TURN_HISTORY_CAP) };
  } catch {
    return null;
  }
}

export function loadAgentThreadIndex(campaignId: string, surfaceId = "plan"): AgentInteractionThreadIndex {
  const key = threadIndexStorageKey(campaignId, surfaceId);
  try {
    const raw = localStorage.getItem(key);
    if (raw) {
      const parsed = JSON.parse(raw) as AgentInteractionThreadIndex;
      if (
        parsed?.schema === "agent_interaction_thread_index_v1" &&
        parsed.campaignId === campaignId &&
        parsed.surfaceId === surfaceId &&
        Array.isArray(parsed.threads)
      ) {
        return {
          ...parsed,
          activeThreadId: parsed.activeThreadId ?? null,
          threads: parsed.threads.filter((summary) => Boolean(summary.threadId && summary.title)),
        };
      }
      return emptyThreadIndex(campaignId, surfaceId);
    }
    const activeThreadId = localStorage.getItem(activeThreadStorageKey(campaignId, surfaceId));
    if (!activeThreadId) return emptyThreadIndex(campaignId, surfaceId);
    const activeThread = loadAgentThreadById(campaignId, activeThreadId);
    if (!activeThread) return emptyThreadIndex(campaignId, surfaceId);
    const migrated = {
      ...emptyThreadIndex(campaignId, surfaceId),
      activeThreadId: activeThread.threadId,
      threads: [summarizeThread(activeThread)],
    };
    persistAgentThreadIndex(migrated);
    return migrated;
  } catch {
    return emptyThreadIndex(campaignId, surfaceId);
  }
}

export function persistAgentThreadIndex(index: AgentInteractionThreadIndex): void {
  const bounded: AgentInteractionThreadIndex = {
    ...index,
    threads: index.threads
      .map((summary) => ({
        threadId: summary.threadId,
        title: summary.title || "New prep thread",
        createdAt: summary.createdAt,
        updatedAt: summary.updatedAt,
        turnCount: summary.turnCount,
        activeBackend: summary.activeBackend,
        hermesSessionId: summary.hermesSessionId ?? null,
      }))
      .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)),
  };
  localStorage.setItem(threadIndexStorageKey(index.campaignId, index.surfaceId), JSON.stringify(bounded));
}

export function upsertThreadInIndex(thread: AgentInteractionThread): void {
  const index = loadAgentThreadIndex(thread.campaignId, thread.surfaceId);
  const summary = summarizeThread(thread);
  const threads = [summary, ...index.threads.filter((item) => item.threadId !== thread.threadId)];
  persistAgentThreadIndex({ ...index, activeThreadId: thread.threadId, threads });
}

export function listAgentThreads(campaignId: string, surfaceId = "plan"): AgentInteractionThreadSummary[] {
  return loadAgentThreadIndex(campaignId, surfaceId).threads;
}

export function setActiveAgentThread(campaignId: string, surfaceId: string, threadId: string | null): void {
  const index = loadAgentThreadIndex(campaignId, surfaceId);
  persistAgentThreadIndex({ ...index, activeThreadId: threadId });
  if (threadId) localStorage.setItem(activeThreadStorageKey(campaignId, surfaceId), threadId);
  else localStorage.removeItem(activeThreadStorageKey(campaignId, surfaceId));
}

export function renameAgentThread(thread: AgentInteractionThread, title: string): AgentInteractionThread {
  const trimmed = title.trim() || "New prep thread";
  const nextThread = { ...thread, title: trimmed, updatedAt: new Date().toISOString() };
  persistAgentThread(nextThread);
  return nextThread;
}

export function deleteAgentThread(thread: AgentInteractionThread): void {
  localStorage.removeItem(threadStorageKey(thread.campaignId, thread.threadId));
  const index = loadAgentThreadIndex(thread.campaignId, thread.surfaceId);
  const remaining = index.threads.filter((item) => item.threadId !== thread.threadId);
  const nextActive = index.activeThreadId === thread.threadId ? remaining[0]?.threadId ?? null : index.activeThreadId;
  persistAgentThreadIndex({ ...index, activeThreadId: nextActive, threads: remaining });
  setActiveAgentThread(thread.campaignId, thread.surfaceId, nextActive);
}

export function persistAgentThread(thread: AgentInteractionThread): void {
  const bounded: AgentInteractionThread = {
    ...thread,
    turns: thread.turns.slice(0, AGENT_TURN_HISTORY_CAP).map((turn) => ({
      ...turn,
      contextSummary: turn.contextSummary,
      citations: turn.citations ?? [],
      trace: safeTraceForPersistence(turn.trace),
      warnings: turn.warnings ?? [],
    })),
  };
  localStorage.setItem(activeThreadStorageKey(thread.campaignId, thread.surfaceId), thread.threadId);
  localStorage.setItem(threadStorageKey(thread.campaignId, thread.threadId), JSON.stringify(bounded));
  upsertThreadInIndex(bounded);
  localStorage.setItem(
    historyStorageKey(thread.campaignId),
    JSON.stringify(bounded.turns.map((turn) => ({
      id: turn.turnId,
      question: turn.question,
      answer: turn.answer,
      backend: turn.backend,
      model: turn.trace?.model ?? null,
      status: turn.status,
      askedAt: turn.askedAt,
      traceId: turn.trace?.trace_id ?? null,
      admittedCount: turn.contextSummary?.admitted_count ?? null,
      rejectedCount: turn.contextSummary?.rejected_count ?? null,
      runtime: turn.trace?.runtime ?? null,
      elapsedMs: turn.trace?.elapsed_ms ?? null,
      provider: turn.trace?.provider ?? null,
      stepCount: turn.trace?.steps?.length ?? null,
    }))),
  );
}

export function clearAgentThread(thread: AgentInteractionThread): void {
  const cleared: AgentInteractionThread = {
    ...thread,
    updatedAt: new Date().toISOString(),
    turns: [],
    uiState: { ...thread.uiState, scrollAnchorTurnId: null, traceVisible: thread.uiState?.traceVisible ?? false },
  };
  persistAgentThread(cleared);
  localStorage.setItem(historyStorageKey(thread.campaignId), "[]");
}

export function loadTurnHistory(campaignId: string): AgentInteractionTurnMeta[] {
  const thread = loadAgentThread(campaignId);
  if (thread) {
    return thread.turns.map((turn) => ({
      id: turn.turnId,
      question: turn.question,
      answer: turn.answer,
      backend: turn.backend,
      model: turn.trace?.model ?? null,
      status: turn.status,
      askedAt: turn.askedAt,
      traceId: turn.trace?.trace_id ?? null,
      admittedCount: turn.contextSummary?.admitted_count ?? null,
      rejectedCount: turn.contextSummary?.rejected_count ?? null,
      runtime: turn.trace?.runtime ?? null,
      elapsedMs: turn.trace?.elapsed_ms ?? null,
      provider: turn.trace?.provider ?? null,
      stepCount: turn.trace?.steps?.length ?? null,
    }));
  }
  try {
    const raw = localStorage.getItem(historyStorageKey(campaignId));
    if (!raw) return [];
    const parsed = JSON.parse(raw) as AgentInteractionTurnMeta[];
    return Array.isArray(parsed) ? parsed.slice(0, AGENT_TURN_HISTORY_CAP) : [];
  } catch {
    return [];
  }
}

export function persistTurnHistory(campaignId: string, turns: AgentInteractionTurnMeta[]): void {
  localStorage.setItem(historyStorageKey(campaignId), JSON.stringify(turns.slice(0, AGENT_TURN_HISTORY_CAP)));
}
