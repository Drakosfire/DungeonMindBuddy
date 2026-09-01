import type {
  AgentInteractionContextSummary,
  AgentInteractionThreadIndex,
  AgentInteractionThreadSummary,
  AgentInteractionThread,
  AgentInteractionTurn,
  AgentInteractionTurnMeta,
  LiveQueryBackend,
  AgentInteractionTrace,
  AgentInteractionTraceCost,
  AgentInteractionTraceUsage,
  AgentInteractionModelCallTrace,
  AgentInteractionTraceSpan,
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
  surfaceInstanceId?: string | null,
): string {
  if (surfaceInstanceId) {
    return `${campaignId}:${surfaceId}:instance:${surfaceInstanceId}`;
  }
  return documentId
    ? `${campaignId}:${surfaceId}:${documentId}`
    : `${campaignId}:${surfaceId}`;
}

export function activeThreadStorageKey(
  campaignId: string,
  surfaceId = "plan",
  documentId?: string | null,
  surfaceInstanceId?: string | null,
): string {
  return `${AGENT_ACTIVE_THREAD_STORAGE_PREFIX}:${scopedStorageSuffix(campaignId, surfaceId, documentId, surfaceInstanceId)}`;
}

export function threadStorageKey(campaignId: string, threadId: string): string {
  return `${AGENT_THREAD_STORAGE_PREFIX}:${campaignId}:${threadId}`;
}

export function threadIndexStorageKey(
  campaignId: string,
  surfaceId = "plan",
  documentId?: string | null,
  surfaceInstanceId?: string | null,
): string {
  return `${AGENT_THREAD_INDEX_STORAGE_PREFIX}:${scopedStorageSuffix(campaignId, surfaceId, documentId, surfaceInstanceId)}`;
}

function newId(prefix: string): string {
  return `${prefix}-${crypto.randomUUID?.() ?? Math.random().toString(36).slice(2)}`;
}

export function threadTitleFromQuestion(question: string): string {
  const trimmed = question.trim().replace(/\s+/g, " ");
  if (!trimmed) return "New prep thread";
  return trimmed.length > 56 ? `${trimmed.slice(0, 53)}…` : trimmed;
}

/** Plan Agent Interaction is Hermes-only (Rung 7). Live remains for /surface ChatModule. */
export function normalizePlanAgentBackend(
  thread: AgentInteractionThread,
): AgentInteractionThread {
  if (thread.surfaceId !== "plan" || thread.activeBackend === "hermes") {
    return thread;
  }
  return { ...thread, activeBackend: "hermes" };
}

export function createAgentInteractionThread(
  campaignId: string,
  session: number | null,
  surfaceId = "plan",
  backend: LiveQueryBackend = "hermes",
  title = "New prep thread",
  documentId?: string | null,
  surfaceInstanceId?: string | null,
): AgentInteractionThread {
  const now = new Date().toISOString();
  const resolvedBackend: LiveQueryBackend = surfaceId === "plan" ? "hermes" : backend;
  return {
    threadId: newId("agent-thread"),
    title,
    createdAt: now,
    updatedAt: now,
    campaignId,
    session,
    documentId: documentId ?? null,
    surfaceInstanceId: surfaceInstanceId ?? null,
    surfaceId,
    activeBackend: resolvedBackend,
    hermesSession: null,
    turns: [],
    uiState: { traceVisible: false, scrollAnchorTurnId: null, newThreadSuggestionDismissed: false },
  };
}

function emptyThreadIndex(
  campaignId: string,
  surfaceId = "plan",
  documentId?: string | null,
  surfaceInstanceId?: string | null,
): AgentInteractionThreadIndex {
  return {
    schema: "agent_interaction_thread_index_v2",
    campaignId,
    surfaceId,
    documentId: documentId ?? null,
    surfaceInstanceId: surfaceInstanceId ?? null,
    activeThreadId: null,
    threads: [],
  };
}

function summarizeThread(thread: AgentInteractionThread): AgentInteractionThreadSummary {
  const normalized = normalizePlanAgentBackend(thread);
  return {
    threadId: normalized.threadId,
    title: normalized.title || "New prep thread",
    createdAt: normalized.createdAt,
    updatedAt: normalized.updatedAt,
    turnCount: normalized.turns.length,
    activeBackend: normalized.activeBackend,
    hermesSessionId: normalized.hermesSession?.sessionId ?? null,
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
const MAX_PERSISTED_MODEL_CALLS = 64;
const MAX_PERSISTED_SPANS = 128;
const MAX_PERSISTED_RATE_KEYS = 16;
const MAX_PERSISTED_SPAN_ATTRIBUTES = 16;
const MODEL_CALLS_TRUNCATED_WARNING = "model_calls_truncated";

const FORBIDDEN_TRACE_KEYS = new Set([
  "request",
  "response",
  "question",
  "prompt",
  "system_prompt",
  "user_message",
  "assistant_response",
  "conversation_history",
  "messages",
  "content",
  "body",
  "args",
  "arguments",
  "result",
  "raw_result",
  "tool_result",
  "assistant_message",
]);

const MODEL_CALL_REQUEST_SUMMARY_KEYS = new Set([
  "api_call_count",
  "message_count",
  "tool_count",
  "approx_input_tokens",
  "request_char_count",
  "max_tokens",
  "assistant_content_chars",
  "assistant_tool_call_count",
]);

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
  const candidate = citation as { kind?: string; path?: unknown };
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

function isForbiddenTraceKey(key: string): boolean {
  return FORBIDDEN_TRACE_KEYS.has(key) || FORBIDDEN_TRACE_KEYS.has(key.toLowerCase());
}

function optionalFiniteNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function optionalNonnegInt(value: unknown): number | null {
  const parsed = optionalFiniteNumber(value);
  if (parsed == null || parsed < 0 || !Number.isInteger(parsed)) return null;
  return parsed;
}

function optionalBool(value: unknown): boolean | undefined {
  return typeof value === "boolean" ? value : undefined;
}

function sanitizeRatesPer1m(raw: unknown): Record<string, number> | undefined {
  if (!isRecord(raw)) return undefined;
  const rates: Record<string, number> = {};
  for (const [key, value] of Object.entries(raw).slice(0, MAX_PERSISTED_RATE_KEYS)) {
    if (isForbiddenTraceKey(key)) continue;
    const name = truncatePersistedString(key);
    if (!name) continue;
    if (typeof value === "number" && Number.isFinite(value)) rates[name] = value;
  }
  return Object.keys(rates).length ? rates : undefined;
}

function sanitizeTraceUsage(raw: unknown): AgentInteractionTraceUsage {
  if (!isRecord(raw)) {
    return { available: false, input_tokens: null, output_tokens: null, total_tokens: null };
  }
  const status = truncatePersistedString(raw.status) ?? undefined;
  const available = typeof raw.available === "boolean"
    ? raw.available
    : status === "reported" || status === "partial";
  const usage: AgentInteractionTraceUsage = {
    available,
    input_tokens: optionalFiniteNumber(raw.input_tokens),
    output_tokens: optionalFiniteNumber(raw.output_tokens),
    total_tokens: optionalFiniteNumber(raw.total_tokens),
  };
  if (status) usage.status = status;
  const cached = optionalFiniteNumber(raw.cached_input_tokens);
  if (cached != null) usage.cached_input_tokens = cached;
  const cacheWrite = optionalFiniteNumber(raw.cache_write_input_tokens);
  if (cacheWrite != null) usage.cache_write_input_tokens = cacheWrite;
  const uncached = optionalFiniteNumber(raw.uncached_input_tokens);
  if (uncached != null) usage.uncached_input_tokens = uncached;
  const reasoning = optionalFiniteNumber(raw.reasoning_tokens);
  if (reasoning != null) usage.reasoning_tokens = reasoning;
  const modelCallCount = optionalNonnegInt(raw.model_call_count);
  if (modelCallCount != null) usage.model_call_count = modelCallCount;
  const reportedCount = optionalNonnegInt(raw.usage_reported_call_count);
  if (reportedCount != null) usage.usage_reported_call_count = reportedCount;
  const observedCount = optionalNonnegInt(raw.observed_model_call_count);
  if (observedCount != null) usage.observed_model_call_count = observedCount;
  return usage;
}

function sanitizeTraceCost(raw: unknown): AgentInteractionTraceCost | undefined {
  if (!isRecord(raw)) return undefined;
  const cost: AgentInteractionTraceCost = {
    status: truncatePersistedString(raw.status) ?? "unavailable",
    usd: optionalFiniteNumber(raw.usd),
  };
  const currency = truncatePersistedString(raw.currency);
  if (currency) cost.currency = currency;
  const priced = optionalNonnegInt(raw.priced_call_count);
  if (priced != null) cost.priced_call_count = priced;
  const unpriced = optionalNonnegInt(raw.unpriced_call_count);
  if (unpriced != null) cost.unpriced_call_count = unpriced;
  const rates = sanitizeRatesPer1m(raw.rates_per_1m_usd);
  if (rates) cost.rates_per_1m_usd = rates;
  const matched = optionalBool(raw.pricing_table_matched);
  if (matched != null) cost.pricing_table_matched = matched;
  return cost;
}

function sanitizeRequestSummary(raw: unknown): Record<string, number> | undefined {
  if (!isRecord(raw)) return undefined;
  const summary: Record<string, number> = {};
  for (const [key, value] of Object.entries(raw)) {
    if (!MODEL_CALL_REQUEST_SUMMARY_KEYS.has(key) || isForbiddenTraceKey(key)) continue;
    const parsed = optionalFiniteNumber(value);
    if (parsed != null) summary[key] = parsed;
  }
  return Object.keys(summary).length ? summary : undefined;
}

function sanitizeModelCall(raw: unknown): AgentInteractionModelCallTrace | null {
  if (!isRecord(raw)) return null;
  const sequence = optionalNonnegInt(raw.sequence);
  const callId = truncatePersistedString(raw.call_id) ?? (sequence != null ? `call-${sequence}` : null);
  if (!callId) return null;
  const call: AgentInteractionModelCallTrace = {
    call_id: callId,
    sequence: sequence ?? 0,
    status: truncatePersistedString(raw.status) ?? "unknown",
    usage: sanitizeTraceUsage(raw.usage),
  };
  const runtimeRequestId = truncatePersistedString(raw.runtime_api_request_id);
  if (runtimeRequestId) call.runtime_api_request_id = runtimeRequestId;
  const runtimeTurnId = truncatePersistedString(raw.runtime_turn_id);
  if (runtimeTurnId) call.runtime_turn_id = runtimeTurnId;
  const provider = truncatePersistedString(raw.provider);
  if (provider) call.provider = provider;
  const requestedModel = truncatePersistedString(raw.requested_model);
  if (requestedModel) call.requested_model = requestedModel;
  const responseModel = truncatePersistedString(raw.response_model);
  if (responseModel) call.response_model = responseModel;
  const apiMode = truncatePersistedString(raw.api_mode);
  if (apiMode) call.api_mode = apiMode;
  const startedAt = truncatePersistedString(raw.started_at);
  if (startedAt) call.started_at = startedAt;
  const completedAt = truncatePersistedString(raw.completed_at);
  if (completedAt) call.completed_at = completedAt;
  call.duration_ms = optionalFiniteNumber(raw.duration_ms);
  const requestSummary = sanitizeRequestSummary(raw.request_summary);
  if (requestSummary) call.request_summary = requestSummary;
  const cost = sanitizeTraceCost(raw.cost);
  if (cost) call.cost = cost;
  const finishReason = truncatePersistedString(raw.finish_reason);
  if (finishReason) call.finish_reason = finishReason;
  const retryCount = optionalNonnegInt(raw.retry_count);
  if (retryCount != null) call.retry_count = retryCount;
  const retryable = optionalBool(raw.retryable);
  if (retryable != null) call.retryable = retryable;
  const statusCode = optionalNonnegInt(raw.status_code);
  if (statusCode != null) call.status_code = statusCode;
  const errorType = truncatePersistedString(raw.error_type);
  if (errorType) call.error_type = errorType;
  return call;
}

function sanitizeModelCalls(raw: unknown): { calls: AgentInteractionModelCallTrace[]; truncated: boolean } {
  if (!Array.isArray(raw)) return { calls: [], truncated: false };
  const sanitized = raw
    .map((entry) => sanitizeModelCall(entry))
    .filter((entry): entry is AgentInteractionModelCallTrace => entry != null);
  const truncated = sanitized.length > MAX_PERSISTED_MODEL_CALLS || raw.length > MAX_PERSISTED_MODEL_CALLS;
  return { calls: sanitized.slice(0, MAX_PERSISTED_MODEL_CALLS), truncated };
}

function sanitizeSpanAttributes(
  raw: unknown,
): Record<string, string | number | boolean | null> | undefined {
  if (!isRecord(raw)) return undefined;
  const attributes: Record<string, string | number | boolean | null> = {};
  let count = 0;
  for (const [key, value] of Object.entries(raw)) {
    if (count >= MAX_PERSISTED_SPAN_ATTRIBUTES) break;
    if (isForbiddenTraceKey(key)) continue;
    const name = truncatePersistedString(key);
    if (!name) continue;
    if (value === null || typeof value === "boolean") {
      attributes[name] = value;
      count += 1;
      continue;
    }
    if (typeof value === "number" && Number.isFinite(value)) {
      attributes[name] = value;
      count += 1;
      continue;
    }
    if (typeof value === "string") {
      const truncated = truncatePersistedString(value);
      if (truncated) {
        attributes[name] = truncated;
        count += 1;
      }
    }
  }
  return Object.keys(attributes).length ? attributes : undefined;
}

function sanitizeSpan(raw: unknown): AgentInteractionTraceSpan | null {
  if (!isRecord(raw)) return null;
  const name = truncatePersistedString(raw.name);
  const spanId = truncatePersistedString(raw.span_id);
  if (!name || !spanId) return null;
  const span: AgentInteractionTraceSpan = {
    span_id: spanId,
    kind: truncatePersistedString(raw.kind) ?? "phase",
    name,
    status: truncatePersistedString(raw.status) ?? "unknown",
    duration_ms: optionalFiniteNumber(raw.duration_ms),
  };
  const parent = truncatePersistedString(raw.parent_span_id);
  if (parent) span.parent_span_id = parent;
  const startedAt = truncatePersistedString(raw.started_at);
  if (startedAt) span.started_at = startedAt;
  const completedAt = truncatePersistedString(raw.completed_at);
  if (completedAt) span.completed_at = completedAt;
  const attributes = sanitizeSpanAttributes(raw.attributes);
  if (attributes) span.attributes = attributes;
  return span;
}

function sanitizeSpans(raw: unknown): AgentInteractionTraceSpan[] {
  if (!Array.isArray(raw)) return [];
  return raw
    .map((entry) => sanitizeSpan(entry))
    .filter((entry): entry is AgentInteractionTraceSpan => entry != null)
    .slice(0, MAX_PERSISTED_SPANS);
}

function sanitizeConversationContext(raw: unknown): AgentInteractionTrace["conversation_context"] {
  if (!isRecord(raw)) return undefined;
  return {
    history_present: Boolean(raw.history_present),
    message_count: typeof raw.message_count === "number" ? raw.message_count : 0,
    pair_count: typeof raw.pair_count === "number" ? raw.pair_count : 0,
    payload_shape: truncatePersistedString(raw.payload_shape) ?? "role_content_only",
    graph_metadata_in_history: Boolean(raw.graph_metadata_in_history),
    hermes_session_pointer_in_request: Boolean(raw.hermes_session_pointer_in_request),
    hermes_session_pointer_status: truncatePersistedString(raw.hermes_session_pointer_status) ?? undefined,
    worker_pid_changed: typeof raw.worker_pid_changed === "boolean"
      ? raw.worker_pid_changed
      : undefined,
    fresh_graph_revision_used: typeof raw.fresh_graph_revision_used === "boolean"
      ? raw.fresh_graph_revision_used
      : undefined,
  };
}

function assignA0DiagnosticFields(
  projected: AgentInteractionTrace,
  trace: Record<string, unknown>,
  warnings: string[],
): void {
  const schema = truncatePersistedString(trace.schema);
  if (schema) projected.schema = schema;
  const agentThreadId = truncatePersistedString(trace.agent_thread_id);
  if (agentThreadId) projected.agent_thread_id = agentThreadId;
  const turnId = truncatePersistedString(trace.turn_id);
  if (turnId) projected.turn_id = turnId;
  const provider = truncatePersistedString(trace.provider);
  if (provider) projected.provider = provider;
  const model = truncatePersistedString(trace.model);
  if (model) projected.model = model;
  projected.usage = sanitizeTraceUsage(trace.usage);
  const cost = sanitizeTraceCost(trace.cost);
  if (cost) projected.cost = cost;
  const { calls, truncated } = sanitizeModelCalls(trace.model_calls);
  if (calls.length || Array.isArray(trace.model_calls)) projected.model_calls = calls;
  if (truncated && !warnings.includes(MODEL_CALLS_TRUNCATED_WARNING)) {
    warnings.push(MODEL_CALLS_TRUNCATED_WARNING);
  }
  if (Array.isArray(trace.spans)) projected.spans = sanitizeSpans(trace.spans);
}

/** Prefer top-level warnings when they are an array; otherwise fall back to agent_trace.warnings. */
function warningsFromResponse(response: LiveQueryResponse): string[] {
  if (Array.isArray(response.warnings)) {
    return sanitizePersistedWarnings(response.warnings);
  }
  return sanitizePersistedWarnings(response.agent_trace?.warnings);
}

/** Strict Hermes graph-agent trace projection — A0 whitelist plus existing safe Hermes fields. */
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
  const projected: AgentInteractionTrace = {
    trace_id: truncatePersistedString(trace.trace_id) ?? "",
    runtime: truncatePersistedString(trace.runtime) ?? "",
    backend: truncatePersistedString(trace.backend) ?? "hermes",
    mode: "hermes_graph_agent",
    started_at: truncatePersistedString(trace.started_at) ?? "",
    completed_at: truncatePersistedString(trace.completed_at) ?? "",
    elapsed_ms: typeof trace.elapsed_ms === "number" && Number.isFinite(trace.elapsed_ms)
      ? trace.elapsed_ms
      : 0,
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
    conversation_context: sanitizeConversationContext(trace.conversation_context),
    process_isolation: truncatePersistedString(trace.process_isolation) ?? undefined,
    warnings: [],
  };
  const hermesSessionId = truncatePersistedString(trace.hermes_session_id);
  if (hermesSessionId) projected.hermes_session_id = hermesSessionId;
  const answerScope = truncatePersistedString(trace.answer_scope);
  if (answerScope === "graph" || answerScope === "conversation_context") {
    projected.answer_scope = answerScope;
  }
  const toolEventCount = optionalFiniteNumber(trace.tool_event_count);
  if (toolEventCount != null) projected.tool_event_count = toolEventCount;
  const evidenceEventCount = optionalFiniteNumber(trace.evidence_event_count);
  if (evidenceEventCount != null) projected.evidence_event_count = evidenceEventCount;
  const finalResponsePresent = optionalBool(trace.final_response_present);
  if (finalResponsePresent != null) projected.final_response_present = finalResponsePresent;
  const validatorPath = truncatePersistedString(trace.validator_path);
  if (validatorPath) projected.validator_path = validatorPath;
  assignA0DiagnosticFields(projected, trace, warnings);
  projected.warnings = warnings.slice(0, MAX_PERSISTED_WARNINGS);
  return projected;
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
  const warnings = sanitizePersistedWarnings(trace.warnings);
  const projected: AgentInteractionTrace = {
    trace_id: truncatePersistedString(trace.trace_id) ?? "",
    runtime: truncatePersistedString(trace.runtime) ?? "",
    backend: truncatePersistedString(trace.backend) ?? "",
    mode: truncatePersistedString(trace.mode) ?? "",
    provider: truncatePersistedString(trace.provider),
    model: truncatePersistedString(trace.model),
    started_at: truncatePersistedString(trace.started_at) ?? "",
    completed_at: truncatePersistedString(trace.completed_at) ?? "",
    elapsed_ms: typeof trace.elapsed_ms === "number" && Number.isFinite(trace.elapsed_ms)
      ? trace.elapsed_ms
      : 0,
    status: truncatePersistedString(trace.status) ?? "unknown",
    toolset: truncatePersistedString(trace.toolset),
    command_summary: truncatePersistedString(trace.command_summary),
    prompt_preview: undefined,
    prompt_char_count: typeof trace.prompt_char_count === "number" ? trace.prompt_char_count : null,
    prompt_token_estimate: typeof trace.prompt_token_estimate === "number" ? trace.prompt_token_estimate : null,
    usage: sanitizeTraceUsage(trace.usage),
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
    warnings,
  };
  assignA0DiagnosticFields(projected, trace, warnings);
  projected.warnings = warnings.slice(0, MAX_PERSISTED_WARNINGS);
  return projected;
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
      return isLegacyPathCitationForSnapshot(citation) || Boolean((citation as unknown as LegacyPathCitation).path);
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
  surfaceInstanceId?: string | null,
): AgentInteractionThread | null {
  try {
    const index = loadAgentThreadIndex(campaignId, surfaceId, documentId, surfaceInstanceId);
    const activeThreadId =
      index.activeThreadId ?? localStorage.getItem(
        activeThreadStorageKey(campaignId, surfaceId, documentId, surfaceInstanceId),
      );
    if (!activeThreadId) return null;
    const raw = localStorage.getItem(threadStorageKey(campaignId, activeThreadId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as AgentInteractionThread;
    if (!parsed || parsed.campaignId !== campaignId || !Array.isArray(parsed.turns)) return null;
    return normalizePlanAgentBackend({
      ...parsed,
      turns: parsed.turns
        .slice(0, AGENT_TURN_HISTORY_CAP)
        .map((turn) => sanitizePersistedTurnSafe(turn))
        .filter((turn): turn is AgentInteractionTurn => turn !== null),
    });
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
    return normalizePlanAgentBackend({
      ...parsed,
      turns: parsed.turns
        .slice(0, AGENT_TURN_HISTORY_CAP)
        .map((turn) => sanitizePersistedTurnSafe(turn))
        .filter((turn): turn is AgentInteractionTurn => turn !== null),
    });
  } catch {
    return null;
  }
}

export function loadAgentThreadIndex(
  campaignId: string,
  surfaceId = "plan",
  documentId?: string | null,
  surfaceInstanceId?: string | null,
): AgentInteractionThreadIndex {
  const key = threadIndexStorageKey(campaignId, surfaceId, documentId, surfaceInstanceId);
  try {
    const raw = localStorage.getItem(key);
    if (raw) {
      const parsed = JSON.parse(raw) as AgentInteractionThreadIndex;
      if (
        parsed?.schema === "agent_interaction_thread_index_v2"
        && parsed.campaignId === campaignId
        && parsed.surfaceId === surfaceId
        && (parsed.documentId ?? null) === (documentId ?? null)
        && (parsed.surfaceInstanceId ?? null) === (surfaceInstanceId ?? null)
        && Array.isArray(parsed.threads)
      ) {
        return {
          ...parsed,
          activeThreadId: parsed.activeThreadId ?? null,
          threads: parsed.threads.filter((summary) => Boolean(summary.threadId && summary.title)),
        };
      }
      return emptyThreadIndex(campaignId, surfaceId, documentId, surfaceInstanceId);
    }
    const activeThreadId = localStorage.getItem(
      activeThreadStorageKey(campaignId, surfaceId, documentId, surfaceInstanceId),
    );
    if (!activeThreadId) return emptyThreadIndex(campaignId, surfaceId, documentId, surfaceInstanceId);
    const activeThread = loadAgentThreadById(campaignId, activeThreadId);
    if (!activeThread) return emptyThreadIndex(campaignId, surfaceId, documentId, surfaceInstanceId);
    const migrated = {
      ...emptyThreadIndex(campaignId, surfaceId, documentId, surfaceInstanceId),
      activeThreadId: activeThread.threadId,
      threads: [summarizeThread(activeThread)],
    };
    persistAgentThreadIndex(migrated);
    return migrated;
  } catch {
    return emptyThreadIndex(campaignId, surfaceId, documentId, surfaceInstanceId);
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
    threadIndexStorageKey(
      index.campaignId,
      index.surfaceId,
      index.documentId,
      index.surfaceInstanceId,
    ),
    JSON.stringify(bounded),
  );
}

export function upsertThreadInIndex(thread: AgentInteractionThread): void {
  const index = loadAgentThreadIndex(
    thread.campaignId,
    thread.surfaceId,
    thread.documentId,
    thread.surfaceInstanceId,
  );
  const summary = summarizeThread(thread);
  const threads = [summary, ...index.threads.filter((item) => item.threadId !== thread.threadId)];
  persistAgentThreadIndex({ ...index, activeThreadId: thread.threadId, threads });
}

export function listAgentThreads(
  campaignId: string,
  surfaceId = "plan",
  documentId?: string | null,
  surfaceInstanceId?: string | null,
): AgentInteractionThreadSummary[] {
  return loadAgentThreadIndex(campaignId, surfaceId, documentId, surfaceInstanceId).threads;
}

export function setActiveAgentThread(
  campaignId: string,
  surfaceId: string,
  threadId: string | null,
  documentId?: string | null,
  surfaceInstanceId?: string | null,
): void {
  const index = loadAgentThreadIndex(campaignId, surfaceId, documentId, surfaceInstanceId);
  persistAgentThreadIndex({ ...index, activeThreadId: threadId });
  if (threadId) {
    localStorage.setItem(
      activeThreadStorageKey(campaignId, surfaceId, documentId, surfaceInstanceId),
      threadId,
    );
  } else {
    localStorage.removeItem(
      activeThreadStorageKey(campaignId, surfaceId, documentId, surfaceInstanceId),
    );
  }
}

export function renameAgentThread(thread: AgentInteractionThread, title: string): AgentInteractionThread {
  const trimmed = title.trim() || "New prep thread";
  const nextThread = { ...thread, title: trimmed, updatedAt: new Date().toISOString() };
  persistAgentThread(nextThread);
  return nextThread;
}

export function deleteAgentThread(thread: AgentInteractionThread): void {
  localStorage.removeItem(threadStorageKey(thread.campaignId, thread.threadId));
  const index = loadAgentThreadIndex(
    thread.campaignId,
    thread.surfaceId,
    thread.documentId,
    thread.surfaceInstanceId,
  );
  const remaining = index.threads.filter((item) => item.threadId !== thread.threadId);
  const nextActive = index.activeThreadId === thread.threadId ? remaining[0]?.threadId ?? null : index.activeThreadId;
  persistAgentThreadIndex({ ...index, activeThreadId: nextActive, threads: remaining });
  setActiveAgentThread(
    thread.campaignId,
    thread.surfaceId,
    nextActive,
    thread.documentId,
    thread.surfaceInstanceId,
  );
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
  localStorage.setItem(
    activeThreadStorageKey(
      thread.campaignId,
      thread.surfaceId,
      thread.documentId,
      thread.surfaceInstanceId,
    ),
    thread.threadId,
  );
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
