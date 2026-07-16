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
  LiveQueryCitation,
  AgentEvidenceSnapshot,
  CitationFreshnessStatus,
  AgentWorldGraphQueryContext,
  PersistedWorldGraphContextSummary,
  HermesGraphToolTraceEvent,
  LegacyPathCitation,
} from "../../api/types";
import {
  parseHermesGraphGrounding,
  s1SupportFromAnswer,
  validateHermesGraphCitations,
} from "./prepMemoryQa";

export const AGENT_TURN_HISTORY_CAP = 20;
export const AGENT_THREAD_SUGGEST_NEW_AFTER_TURNS = 6;
export const AGENT_THREAD_STORAGE_PREFIX = "agent-interaction-thread-v2";
export const AGENT_ACTIVE_THREAD_STORAGE_PREFIX = "agent-interaction-active-thread-v2";
export const AGENT_THREAD_INDEX_STORAGE_PREFIX = "agent-interaction-thread-index-v2";

function scopedStorageSuffix(
  campaignId: string,
  surfaceId: string,
  documentId?: string | null,
): string {
  return documentId
    ? `${campaignId}:${surfaceId}:${documentId}`
    : `${campaignId}:${surfaceId}`;
}

export function activeThreadStorageKey(
  campaignId: string,
  surfaceId = "plan",
  documentId?: string | null,
): string {
  return `${AGENT_ACTIVE_THREAD_STORAGE_PREFIX}:${scopedStorageSuffix(campaignId, surfaceId, documentId)}`;
}

export function threadStorageKey(campaignId: string, threadId: string): string {
  return `${AGENT_THREAD_STORAGE_PREFIX}:${campaignId}:${threadId}`;
}

export function threadIndexStorageKey(
  campaignId: string,
  surfaceId = "plan",
  documentId?: string | null,
): string {
  return `${AGENT_THREAD_INDEX_STORAGE_PREFIX}:${scopedStorageSuffix(campaignId, surfaceId, documentId)}`;
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
  documentId?: string | null,
): AgentInteractionThread {
  const now = new Date().toISOString();
  return {
    threadId: newId("agent-thread"),
    title,
    createdAt: now,
    updatedAt: now,
    campaignId,
    session,
    documentId: documentId ?? null,
    surfaceId,
    activeBackend: backend,
    hermesSession: null,
    turns: [],
    uiState: { traceVisible: true, scrollAnchorTurnId: null, newThreadSuggestionDismissed: false },
  };
}

function emptyThreadIndex(
  campaignId: string,
  surfaceId = "plan",
  documentId?: string | null,
): AgentInteractionThreadIndex {
  return {
    schema: "agent_interaction_thread_index_v2",
    campaignId,
    surfaceId,
    documentId: documentId ?? null,
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

const MAX_PERSISTED_TOOL_EVENTS = 24;
const MAX_PERSISTED_IDS = 32;
const MAX_PERSISTED_DIAGNOSTIC_CODES = 32;
const MAX_PERSISTED_WARNINGS = 16;
const MAX_PERSISTED_STRING_SCALAR = 512;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function truncatePersistedString(value: unknown): string | null {
  if (typeof value !== "string") return null;
  return value.length > MAX_PERSISTED_STRING_SCALAR ? value.slice(0, MAX_PERSISTED_STRING_SCALAR) : value;
}

function sanitizePersistedIdList(ids: unknown): string[] {
  if (!Array.isArray(ids)) return [];
  return ids
    .slice(0, MAX_PERSISTED_IDS)
    .map((id) => truncatePersistedString(id) ?? "")
    .filter(Boolean);
}

function sanitizePersistedToolEvent(
  event: unknown,
): Omit<HermesGraphToolTraceEvent, "bounded_ids"> | null {
  if (!isRecord(event)) return null;
  const toolName = truncatePersistedString(event.tool_name);
  if (!toolName) return null;
  const focusRaw = event.focus;
  const focus = isRecord(focusRaw)
    ? {
        kind: truncatePersistedString(focusRaw.kind),
        session_id: truncatePersistedString(focusRaw.session_id),
      }
    : null;
  return {
    tool_name: toolName,
    state: truncatePersistedString(event.state) ?? "unknown",
    duration_ms: typeof event.duration_ms === "number" ? event.duration_ms : null,
    world_id: truncatePersistedString(event.world_id),
    campaign_id: truncatePersistedString(event.campaign_id),
    focus,
    admissibility: truncatePersistedString(event.admissibility),
    revision_pin: truncatePersistedString(event.revision_pin),
    retrieval_schema: truncatePersistedString(event.retrieval_schema),
    outcome: truncatePersistedString(event.outcome),
    matched_node_ids: sanitizePersistedIdList(event.matched_node_ids),
    relationship_ids: sanitizePersistedIdList(event.relationship_ids),
    source_anchor_ids: sanitizePersistedIdList(event.source_anchor_ids),
    diagnostic_codes: sanitizePersistedIdList(event.diagnostic_codes).slice(0, MAX_PERSISTED_DIAGNOSTIC_CODES),
  };
}

function isLegacyPathCitationForSnapshot(
  citation: unknown,
): citation is LegacyPathCitation & { path: string } {
  if (!citation || typeof citation !== "object") return false;
  const candidate = citation as LegacyPathCitation;
  if (candidate.kind === "world_graph_anchor") return false;
  return Boolean(candidate.path)
    && typeof candidate.path === "string"
    && !isAbsolutePath(candidate.path);
}

function sanitizeHermesGraphToolEvents(toolEvents: unknown): HermesGraphToolTraceEvent[] {
  if (!Array.isArray(toolEvents)) return [];
  return toolEvents
    .slice(0, MAX_PERSISTED_TOOL_EVENTS)
    .map((event) => sanitizePersistedToolEvent(event))
    .filter((event): event is Omit<HermesGraphToolTraceEvent, "bounded_ids"> => event !== null)
    .map((event) => event as HermesGraphToolTraceEvent);
}

export function sanitizePersistedWarnings(warnings: unknown): string[] {
  if (!Array.isArray(warnings)) return [];
  return warnings
    .slice(0, MAX_PERSISTED_WARNINGS)
    .map((warning) => truncatePersistedString(warning) ?? "")
    .filter(Boolean);
}

function firstPersistedString(...values: unknown[]): string | null {
  for (const value of values) {
    const truncated = truncatePersistedString(value);
    if (truncated) return truncated;
  }
  return null;
}

/** Prefer top-level warnings when they are an array; otherwise fall back to agent_trace.warnings. */
function warningsFromResponse(response: LiveQueryResponse): string[] {
  if (Array.isArray(response.warnings)) {
    return sanitizePersistedWarnings(response.warnings);
  }
  return sanitizePersistedWarnings(response.agent_trace?.warnings);
}

/** Strict Hermes graph-agent trace projection — only the handoff whitelist. */
function safeHermesGraphTraceForPersistence(
  trace: Record<string, unknown>,
): AgentInteractionTrace {
  const droppedEvents = Array.isArray(trace.tool_events)
    ? Math.max(0, trace.tool_events.length - sanitizeHermesGraphToolEvents(trace.tool_events).length)
    : 0;
  const warnings = sanitizePersistedWarnings(trace.warnings);
  if (droppedEvents > 0) {
    warnings.push("One or more malformed graph tool events were ignored.");
  } else if (trace.tool_events != null && !Array.isArray(trace.tool_events)) {
    warnings.push("Malformed graph tool_events collection was ignored.");
  }
  return {
    trace_id: truncatePersistedString(trace.trace_id) ?? "",
    runtime: truncatePersistedString(trace.runtime) ?? "",
    backend: truncatePersistedString(trace.backend) ?? "hermes",
    mode: "hermes_graph_agent",
    started_at: truncatePersistedString(trace.started_at) ?? "",
    completed_at: truncatePersistedString(trace.completed_at) ?? "",
    elapsed_ms: typeof trace.elapsed_ms === "number" ? trace.elapsed_ms : 0,
    status: truncatePersistedString(trace.status) ?? "unknown",
    usage: {
      available: false,
      input_tokens: null,
      output_tokens: null,
      total_tokens: null,
    },
    steps: [],
    context_summary: {},
    artifact_refs: [],
    tool_events: sanitizeHermesGraphToolEvents(trace.tool_events),
    // Rung 5: never persist a Hermes session pointer. Rung 6 owns durable session ids.
    process_isolation: truncatePersistedString(trace.process_isolation),
    warnings: warnings.slice(0, MAX_PERSISTED_WARNINGS),
  };
}

export function safeTraceForPersistence(
  trace: unknown,
): AgentInteractionTrace | null {
  if (!isRecord(trace)) return null;
  if (trace.mode === "hermes_graph_agent") {
    return safeHermesGraphTraceForPersistence(trace);
  }

  const steps = Array.isArray(trace.steps) ? trace.steps : [];
  const artifactRefs = Array.isArray(trace.artifact_refs) ? trace.artifact_refs : [];
  const usage = isRecord(trace.usage)
    ? {
        available: Boolean(trace.usage.available),
        input_tokens: typeof trace.usage.input_tokens === "number" ? trace.usage.input_tokens : null,
        output_tokens: typeof trace.usage.output_tokens === "number" ? trace.usage.output_tokens : null,
        total_tokens: typeof trace.usage.total_tokens === "number" ? trace.usage.total_tokens : null,
      }
    : { available: false, input_tokens: null, output_tokens: null, total_tokens: null };

  return {
    trace_id: truncatePersistedString(trace.trace_id) ?? "",
    runtime: truncatePersistedString(trace.runtime) ?? "",
    backend: truncatePersistedString(trace.backend) ?? "",
    mode: truncatePersistedString(trace.mode) ?? "",
    provider: truncatePersistedString(trace.provider),
    model: truncatePersistedString(trace.model),
    started_at: truncatePersistedString(trace.started_at) ?? "",
    completed_at: truncatePersistedString(trace.completed_at) ?? "",
    elapsed_ms: typeof trace.elapsed_ms === "number" ? trace.elapsed_ms : 0,
    status: truncatePersistedString(trace.status) ?? "unknown",
    toolset: truncatePersistedString(trace.toolset),
    command_summary: truncatePersistedString(trace.command_summary),
    prompt_preview: undefined,
    prompt_char_count: typeof trace.prompt_char_count === "number" ? trace.prompt_char_count : null,
    prompt_token_estimate: typeof trace.prompt_token_estimate === "number" ? trace.prompt_token_estimate : null,
    usage,
    steps: steps.slice(0, 12).map((step) => {
      const record = isRecord(step) ? step : {};
      return {
        name: truncatePersistedString(record.name) ?? "",
        summary: truncatePersistedString(record.name) ?? "",
      };
    }),
    context_summary: isRecord(trace.context_summary) ? trace.context_summary as AgentInteractionTrace["context_summary"] : {},
    artifact_refs: artifactRefs.map((ref) => {
      const record = isRecord(ref) ? ref : {};
      const path = typeof record.path === "string" && !isAbsolutePath(record.path) ? record.path : "";
      return {
        kind: truncatePersistedString(record.kind) ?? "",
        label: truncatePersistedString(record.label),
        path,
      };
    }),
    tool_events: undefined,
    hermes_session_id: truncatePersistedString(trace.hermes_session_id),
    process_isolation: truncatePersistedString(trace.process_isolation),
    warnings: sanitizePersistedWarnings(trace.warnings),
  };
}

function isHermesGraphTurn(turn: Pick<AgentInteractionTurn, "backend" | "grounding" | "trace">): boolean {
  return turn.trace?.mode === "hermes_graph_agent"
    || turn.grounding?.schema === "dmb_hermes_graph_grounding_v1"
    || (turn.backend === "hermes" && Boolean(turn.grounding));
}

/** Re-validate grounding/citations and re-project Hermes traces on load and write. */
export function sanitizePersistedTurn(turn: AgentInteractionTurn): AgentInteractionTurn {
  if (isHermesGraphTurn(turn)) {
    const validated = validateHermesGraphCitations(turn.citations, turn.grounding);
    const rawTrace = turn.trace && isRecord(turn.trace)
      ? { ...turn.trace, mode: "hermes_graph_agent" }
      : turn.trace;
    return {
      ...turn,
      grounding: validated.grounding,
      citations: validated.citations,
      evidenceSnapshots: [],
      corpusFreshness: null,
      worldGraphContext: null,
      trace: safeTraceForPersistence(rawTrace),
    };
  }

  const citations = Array.isArray(turn.citations) ? turn.citations : [];
  return {
    ...turn,
    citations: citations.filter((citation) => {
      if (!citation || typeof citation !== "object") return false;
      return isLegacyPathCitationForSnapshot(citation) || Boolean((citation as LegacyPathCitation).path);
    }),
    trace: safeTraceForPersistence(turn.trace),
  };
}

/** Drop only a malformed turn; never throw through to discard the thread. */
export function sanitizePersistedTurnSafe(turn: unknown): AgentInteractionTurn | null {
  try {
    if (!isRecord(turn)) return null;
    if (typeof turn.turnId !== "string" || typeof turn.question !== "string") return null;
    return sanitizePersistedTurn(turn as unknown as AgentInteractionTurn);
  } catch {
    return null;
  }
}


export function buildEvidenceSnapshots(
  citations: LiveQueryCitation[] | null | undefined,
  capturedAt = new Date().toISOString(),
): AgentEvidenceSnapshot[] {
  return (citations ?? []).filter(isLegacyPathCitationForSnapshot).map((citation) => {
    const locator = [
      citation.path,
      citation.line_start ?? "",
      citation.line_end ?? "",
      citation.evidence_id,
      citation.source_role,
      citation.authority,
    ].join("\n");
    return {
      schema: "dmb_agent_evidence_snapshot_v1",
      evidence_id: citation.evidence_id,
      path: citation.path,
      line_start: citation.line_start ?? null,
      line_end: citation.line_end ?? null,
      source_role: citation.source_role ?? null,
      authority: citation.authority ?? null,
      fingerprint: `locator-v1:${btoa(unescape(encodeURIComponent(locator)))}`,
      fingerprint_algorithm: "locator-v1",
      captured_at: capturedAt,
    };
  });
}

const freshnessRank: Record<CitationFreshnessStatus, number> = { current: 0, unknown: 1, unavailable: 2, changed: 3 };

export function worstCorpusFreshnessStatus(statuses: CitationFreshnessStatus[]): CitationFreshnessStatus {
  return statuses.reduce<CitationFreshnessStatus>(
    (worst, status) => (freshnessRank[status] > freshnessRank[worst] ? status : worst),
    "current",
  );
}

function buildWorldGraphContextSummary(
  context: AgentWorldGraphQueryContext | null | undefined,
  response?: LiveQueryResponse | null,
): PersistedWorldGraphContextSummary | null {
  if (!context) return null;
  const warningCodes = [...(context.warning_codes ?? [])];
  if (!warningCodes.includes("graph_context_detail_not_persisted")) {
    warningCodes.push("graph_context_detail_not_persisted");
  }
  const grounding = response?.grounding ?? null;
  const graphReferences = response?.graph_references ?? [];
  const sourceCitations = response?.source_citations ?? [];
  return {
    schema: "dmb_agent_world_graph_context_summary_v1",
    status: context.status,
    worldId: context.world_id,
    campaignId: context.campaign_id,
    revisionId: context.revision_id,
    isHead: context.is_head,
    focus: {
      kind: context.focus.kind,
      sessionId: context.focus.session_id,
    },
    admissibility: context.admissibility,
    matchedNodeIds: context.matched_node_ids,
    projectionTruncated: context.projection_truncated,
    warningCodes,
    retrievalSessionId: response?.retrieval_session_id ?? null,
    acceptanceState: grounding?.acceptance_state ?? null,
    acceptedClaimIds: grounding?.accepted_claim_ids ?? [],
    graphReferenceCount: grounding?.graph_reference_count ?? graphReferences.length,
    sourceCitationCount: grounding?.source_anchor_count ?? sourceCitations.length,
    reasonCodes: grounding?.reason_codes ?? [],
    graphReferencePreview: graphReferences.slice(0, 6).map((ref) => ({
      objectId: ref.object_id,
      label: ref.label ?? null,
      claimId: ref.claim_id ?? null,
    })),
    sourceCitationPreview: sourceCitations.slice(0, 6).map((cite) => ({
      anchorId: cite.anchor_id,
      sourceArtifactId: cite.source_artifact_id ?? null,
    })),
  };
}

export function turnFromResponse(
  question: string,
  response: LiveQueryResponse,
  backend: LiveQueryBackend,
): AgentInteractionTurn {
  const now = new Date().toISOString();
  const isHermesGraph = response.mode === "hermes_graph_agent";
  const turnId = firstPersistedString(response.turn_id, response.agent_trace?.trace_id, response.query_id)
    ?? newId("agent-turn");
  const askedAt = firstPersistedString(response.agent_trace?.started_at) ?? now;
  const completedAt = firstPersistedString(response.agent_trace?.completed_at) ?? now;
  const status = firstPersistedString(response.status, response.agent_trace?.status) ?? "ok";
  const warnings = warningsFromResponse(response);

  if (isHermesGraph) {
    const validated = validateHermesGraphCitations(response.citations, response.grounding);
    const rawTrace = isRecord(response.agent_trace)
      ? { ...response.agent_trace, mode: "hermes_graph_agent" }
      : response.agent_trace == null
        ? null
        : { mode: "hermes_graph_agent" };
    return {
      turnId,
      askedAt,
      completedAt,
      question,
      answer: typeof response.answer === "string" ? response.answer : "",
      backend,
      status,
      contextSummary: undefined,
      citations: validated.citations,
      trace: safeTraceForPersistence(rawTrace),
      warnings,
      retrievalFreshness: null,
      evidenceSnapshots: [],
      corpusFreshness: null,
      worldGraphContext: response.world_graph_context ?? null,
      worldGraphContextSummary: buildWorldGraphContextSummary(
        response.world_graph_context,
        response,
      ),
      grounding: validated.grounding,
      s1Support: s1SupportFromAnswer(response),
    };
  }

  return {
    turnId,
    askedAt,
    completedAt,
    question,
    answer: typeof response.answer === "string" ? response.answer : "",
    backend,
    status,
    contextSummary: contextSummaryFromResponse(response),
    citations: (Array.isArray(response.citations) ? response.citations : []).filter(
      (citation) => citation && typeof citation === "object",
    ),
    // Normalize shell fields for render, but keep truncated prompt_preview in-memory.
    // Persistence re-runs safeTraceForPersistence and strips prompt_preview.
    trace: (() => {
      const normalized = safeTraceForPersistence(response.agent_trace);
      if (!normalized || !isRecord(response.agent_trace)) return normalized;
      const promptPreview = truncatePersistedString(response.agent_trace.prompt_preview);
      return promptPreview ? { ...normalized, prompt_preview: promptPreview } : normalized;
    })(),
    warnings,
    retrievalFreshness: response.retrieval_freshness ?? null,
    evidenceSnapshots: response.evidence_snapshots ?? buildEvidenceSnapshots(
      Array.isArray(response.citations) ? response.citations : [],
      now,
    ),
    corpusFreshness: null,
    worldGraphContext: response.world_graph_context ?? null,
    worldGraphContextSummary: buildWorldGraphContextSummary(
      response.world_graph_context,
      response,
    ),
    grounding: parseHermesGraphGrounding(response.grounding),
    s1Support: s1SupportFromAnswer(response),
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

export function loadAgentThread(
  campaignId: string,
  surfaceId = "plan",
  documentId?: string | null,
): AgentInteractionThread | null {
  try {
    const index = loadAgentThreadIndex(campaignId, surfaceId, documentId);
    const activeThreadId =
      index.activeThreadId ?? localStorage.getItem(activeThreadStorageKey(campaignId, surfaceId, documentId));
    if (!activeThreadId) return null;
    const raw = localStorage.getItem(threadStorageKey(campaignId, activeThreadId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as AgentInteractionThread;
    if (!parsed || parsed.campaignId !== campaignId || !Array.isArray(parsed.turns)) return null;
    return {
      ...parsed,
      turns: parsed.turns
        .slice(0, AGENT_TURN_HISTORY_CAP)
        .map((turn) => sanitizePersistedTurnSafe(turn))
        .filter((turn): turn is AgentInteractionTurn => turn !== null),
    };
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
    return {
      ...parsed,
      turns: parsed.turns
        .slice(0, AGENT_TURN_HISTORY_CAP)
        .map((turn) => sanitizePersistedTurnSafe(turn))
        .filter((turn): turn is AgentInteractionTurn => turn !== null),
    };
  } catch {
    return null;
  }
}

export function loadAgentThreadIndex(
  campaignId: string,
  surfaceId = "plan",
  documentId?: string | null,
): AgentInteractionThreadIndex {
  const key = threadIndexStorageKey(campaignId, surfaceId, documentId);
  try {
    const raw = localStorage.getItem(key);
    if (raw) {
      const parsed = JSON.parse(raw) as AgentInteractionThreadIndex;
      if (
        parsed?.schema === "agent_interaction_thread_index_v2"
        && parsed.campaignId === campaignId
        && parsed.surfaceId === surfaceId
        && (parsed.documentId ?? null) === (documentId ?? null)
        && Array.isArray(parsed.threads)
      ) {
        return {
          ...parsed,
          activeThreadId: parsed.activeThreadId ?? null,
          threads: parsed.threads.filter((summary) => Boolean(summary.threadId && summary.title)),
        };
      }
      return emptyThreadIndex(campaignId, surfaceId, documentId);
    }
    const activeThreadId = localStorage.getItem(activeThreadStorageKey(campaignId, surfaceId, documentId));
    if (!activeThreadId) return emptyThreadIndex(campaignId, surfaceId, documentId);
    const activeThread = loadAgentThreadById(campaignId, activeThreadId);
    if (!activeThread) return emptyThreadIndex(campaignId, surfaceId, documentId);
    const migrated = {
      ...emptyThreadIndex(campaignId, surfaceId, documentId),
      activeThreadId: activeThread.threadId,
      threads: [summarizeThread(activeThread)],
    };
    persistAgentThreadIndex(migrated);
    return migrated;
  } catch {
    return emptyThreadIndex(campaignId, surfaceId, documentId);
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
  localStorage.setItem(
    threadIndexStorageKey(index.campaignId, index.surfaceId, index.documentId),
    JSON.stringify(bounded),
  );
}

export function upsertThreadInIndex(thread: AgentInteractionThread): void {
  const index = loadAgentThreadIndex(thread.campaignId, thread.surfaceId, thread.documentId);
  const summary = summarizeThread(thread);
  const threads = [summary, ...index.threads.filter((item) => item.threadId !== thread.threadId)];
  persistAgentThreadIndex({ ...index, activeThreadId: thread.threadId, threads });
}

export function listAgentThreads(
  campaignId: string,
  surfaceId = "plan",
  documentId?: string | null,
): AgentInteractionThreadSummary[] {
  return loadAgentThreadIndex(campaignId, surfaceId, documentId).threads;
}

export function setActiveAgentThread(
  campaignId: string,
  surfaceId: string,
  threadId: string | null,
  documentId?: string | null,
): void {
  const index = loadAgentThreadIndex(campaignId, surfaceId, documentId);
  persistAgentThreadIndex({ ...index, activeThreadId: threadId });
  if (threadId) localStorage.setItem(activeThreadStorageKey(campaignId, surfaceId, documentId), threadId);
  else localStorage.removeItem(activeThreadStorageKey(campaignId, surfaceId, documentId));
}

export function renameAgentThread(thread: AgentInteractionThread, title: string): AgentInteractionThread {
  const trimmed = title.trim() || "New prep thread";
  const nextThread = { ...thread, title: trimmed, updatedAt: new Date().toISOString() };
  persistAgentThread(nextThread);
  return nextThread;
}

export function deleteAgentThread(thread: AgentInteractionThread): void {
  localStorage.removeItem(threadStorageKey(thread.campaignId, thread.threadId));
  const index = loadAgentThreadIndex(thread.campaignId, thread.surfaceId, thread.documentId);
  const remaining = index.threads.filter((item) => item.threadId !== thread.threadId);
  const nextActive = index.activeThreadId === thread.threadId ? remaining[0]?.threadId ?? null : index.activeThreadId;
  persistAgentThreadIndex({ ...index, activeThreadId: nextActive, threads: remaining });
  setActiveAgentThread(thread.campaignId, thread.surfaceId, nextActive, thread.documentId);
}

export function persistAgentThread(thread: AgentInteractionThread): void {
  const bounded: AgentInteractionThread = {
    ...thread,
    turns: thread.turns.slice(0, AGENT_TURN_HISTORY_CAP).flatMap((turn) => {
      const sanitized = sanitizePersistedTurnSafe(turn);
      if (!sanitized) return [];
      const { worldGraphContext: _stripped, ...persistedTurn } = sanitized;
      return [{
        ...persistedTurn,
        contextSummary: sanitized.contextSummary,
        citations: sanitized.citations ?? [],
        trace: safeTraceForPersistence(sanitized.trace),
        warnings: sanitized.warnings ?? [],
        retrievalFreshness: sanitized.retrievalFreshness ?? null,
        evidenceSnapshots: sanitized.evidenceSnapshots ?? [],
        corpusFreshness: sanitized.corpusFreshness ?? null,
        worldGraphContextSummary: sanitized.worldGraphContextSummary ?? null,
        grounding: sanitized.grounding ?? null,
        s1Support: sanitized.s1Support ?? null,
      }];
    }),
  };
  localStorage.setItem(activeThreadStorageKey(thread.campaignId, thread.surfaceId, thread.documentId), thread.threadId);
  localStorage.setItem(threadStorageKey(thread.campaignId, thread.threadId), JSON.stringify(bounded));
  upsertThreadInIndex(bounded);
}

export function clearAgentThread(thread: AgentInteractionThread): void {
  const cleared: AgentInteractionThread = {
    ...thread,
    updatedAt: new Date().toISOString(),
    turns: [],
    uiState: {
      ...thread.uiState,
      scrollAnchorTurnId: null,
      traceVisible: thread.uiState?.traceVisible ?? false,
      newThreadSuggestionDismissed: false,
    },
  };
  persistAgentThread(cleared);
}

export function loadTurnHistory(campaignId: string, documentId?: string | null): AgentInteractionTurnMeta[] {
  const thread = loadAgentThread(campaignId, "plan", documentId);
  if (!thread) return [];
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
