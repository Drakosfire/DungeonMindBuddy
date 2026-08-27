import { useMemo, useState } from "react";

import type {
  AgentInteractionModelCallTrace,
  AgentInteractionTrace,
  AgentInteractionTraceCost,
  AgentInteractionTraceSpan,
  AgentInteractionTraceUsage,
  HermesConversationTraceContext,
  HermesGraphToolTraceEvent,
} from "../../api/types";

import "./agentTraceInspector.css";

interface AgentTraceInspectorProps {
  trace: AgentInteractionTrace;
}

type CopyStatus = "idle" | "copied" | "error";

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

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function stringField(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function stringArrayField(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string" && item.trim().length > 0);
}

function displayString(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function displayOptionalString(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

function displayScalar(value: unknown): string | number | null {
  return typeof value === "string" || typeof value === "number" ? value : null;
}

function finiteNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function formatYesNo(value: boolean): string {
  return value ? "yes" : "no";
}

function formatIdList(ids: string[]): string {
  if (!ids.length) return "none";
  if (ids.length <= 3) return ids.join(", ");
  return `${ids.slice(0, 3).join(", ")} (+${ids.length - 3} more)`;
}

function formatCompactCount(value: number): string {
  const abs = Math.abs(value);
  if (abs < 1000) return String(value);
  const thousands = value / 1000;
  const text = abs >= 10000 ? thousands.toFixed(1) : thousands.toFixed(1);
  return `${text.replace(/\.0$/, "")}k`;
}

export function formatElapsedMs(ms: unknown): string | null {
  const value = finiteNumber(ms);
  if (value == null) return null;
  if (value < 1000) return `${Math.round(value)} ms`;
  const seconds = value / 1000;
  const text = seconds >= 10 ? seconds.toFixed(1) : seconds.toFixed(2);
  return `${text.replace(/\.?0+$/, "")} s`;
}

function formatUsd(usd: number): string {
  if (Math.abs(usd) >= 1) return `$${usd.toFixed(2)}`;
  const text = usd.toFixed(4).replace(/0+$/, "").replace(/\.$/, "");
  return `$${text}`;
}

function formatCostStatus(cost: AgentInteractionTraceCost | null | undefined): string | null {
  if (!cost || typeof cost.status !== "string") return null;
  if (cost.status === "unavailable" || cost.usd == null) {
    return cost.status === "no_provider_fee" ? "no provider fee" : "unavailable";
  }
  const amount = formatUsd(cost.usd);
  if (cost.status === "estimated") return `${amount} estimated`;
  if (cost.status === "partial") return `${amount} partial`;
  if (cost.status === "reported") return amount;
  if (cost.status === "no_provider_fee") return "no provider fee";
  return `${amount} ${cost.status}`;
}

function formatCompactCost(cost: AgentInteractionTraceCost | null | undefined): string | null {
  if (!cost || typeof cost.status !== "string") return null;
  if (cost.status === "unavailable" || cost.usd == null) {
    return cost.status === "no_provider_fee" ? "no provider fee" : "cost unavailable";
  }
  const amount = formatUsd(cost.usd);
  if (cost.status === "estimated") return `${amount} est.`;
  if (cost.status === "partial") return `${amount} partial`;
  return amount;
}

function usageIsUnavailable(usage: AgentInteractionTraceUsage | null | undefined): boolean {
  if (!usage) return true;
  if (usage.status === "unavailable") return true;
  if (usage.available === false && usage.status !== "partial" && usage.status !== "reported") return true;
  return usage.input_tokens == null && usage.output_tokens == null && usage.total_tokens == null;
}

function formatCompactTokens(usage: AgentInteractionTraceUsage | null | undefined): string | null {
  if (!usage) return null;
  if (usage.status === "unavailable" || usageIsUnavailable(usage)) {
    return usage.status === "partial" ? "usage partial" : null;
  }
  const parts: string[] = [];
  if (typeof usage.input_tokens === "number") parts.push(`${formatCompactCount(usage.input_tokens)} in`);
  if (typeof usage.output_tokens === "number") parts.push(`${formatCompactCount(usage.output_tokens)} out`);
  if (usage.status === "partial") parts.push("usage partial");
  return parts.length ? parts.join(" → ") : null;
}

function formatTokenBreakdown(usage: AgentInteractionTraceUsage | null | undefined): string {
  if (!usage || usageIsUnavailable(usage)) return "unavailable";
  const parts: string[] = [];
  if (typeof usage.input_tokens === "number") parts.push(`in ${usage.input_tokens}`);
  if (typeof usage.cached_input_tokens === "number") parts.push(`cached ${usage.cached_input_tokens}`);
  if (typeof usage.cache_write_input_tokens === "number") parts.push(`cache-write ${usage.cache_write_input_tokens}`);
  if (typeof usage.uncached_input_tokens === "number") parts.push(`uncached ${usage.uncached_input_tokens}`);
  if (typeof usage.output_tokens === "number") parts.push(`out ${usage.output_tokens}`);
  if (typeof usage.reasoning_tokens === "number") parts.push(`reasoning ${usage.reasoning_tokens}`);
  if (typeof usage.total_tokens === "number") parts.push(`total ${usage.total_tokens}`);
  if (usage.status === "partial") parts.push("partial");
  return parts.length ? parts.join(" · ") : "unavailable";
}

function stripForbiddenKeys(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(stripForbiddenKeys);
  if (!isRecord(value)) return value;
  const next: Record<string, unknown> = {};
  for (const [key, nested] of Object.entries(value)) {
    if (FORBIDDEN_TRACE_KEYS.has(key) || FORBIDDEN_TRACE_KEYS.has(key.toLowerCase())) continue;
    next[key] = stripForbiddenKeys(nested);
  }
  return next;
}

export function formatSafeTraceDiagnostics(trace: AgentInteractionTrace): string {
  const safe = stripForbiddenKeys({
    ...trace,
    prompt_preview: undefined,
    warnings: stringArrayField(trace.warnings),
  });
  return `${JSON.stringify(safe, null, 2)}\n`;
}

function normalizeGraphToolEvent(raw: unknown): HermesGraphToolTraceEvent | null {
  if (!raw || typeof raw !== "object") return null;
  const event = raw as Record<string, unknown>;
  const toolName = stringField(event.tool_name);
  if (!toolName) return null;
  const focusRaw = event.focus;
  const focus = focusRaw && typeof focusRaw === "object"
    ? {
        kind: stringField((focusRaw as Record<string, unknown>).kind),
        session_id: stringField((focusRaw as Record<string, unknown>).session_id)
          ?? (typeof (focusRaw as Record<string, unknown>).session_id === "string"
            ? (focusRaw as Record<string, unknown>).session_id as string
            : null),
      }
    : null;
  return {
    tool_name: toolName,
    state: stringField(event.state) ?? "unknown",
    duration_ms: typeof event.duration_ms === "number" ? event.duration_ms : null,
    world_id: stringField(event.world_id),
    campaign_id: stringField(event.campaign_id),
    focus,
    admissibility: stringField(event.admissibility),
    revision_pin: stringField(event.revision_pin),
    bounded_ids: event.bounded_ids && typeof event.bounded_ids === "object" && !Array.isArray(event.bounded_ids)
      ? event.bounded_ids as Record<string, unknown>
      : {},
    retrieval_schema: stringField(event.retrieval_schema),
    outcome: stringField(event.outcome),
    matched_node_ids: stringArrayField(event.matched_node_ids),
    relationship_ids: stringArrayField(event.relationship_ids),
    source_anchor_ids: stringArrayField(event.source_anchor_ids),
    diagnostic_codes: stringArrayField(event.diagnostic_codes),
  };
}

function normalizeConversationContext(raw: unknown): HermesConversationTraceContext | null {
  if (!isRecord(raw)) return null;
  if (typeof raw.history_present !== "boolean") return null;
  if (typeof raw.message_count !== "number") return null;
  if (typeof raw.pair_count !== "number") return null;
  if (typeof raw.payload_shape !== "string" || !raw.payload_shape.trim()) return null;
  if (typeof raw.graph_metadata_in_history !== "boolean") return null;
  if (typeof raw.hermes_session_pointer_in_request !== "boolean") return null;
  return {
    history_present: raw.history_present,
    message_count: raw.message_count,
    pair_count: raw.pair_count,
    payload_shape: raw.payload_shape,
    graph_metadata_in_history: raw.graph_metadata_in_history,
    hermes_session_pointer_in_request: raw.hermes_session_pointer_in_request,
    hermes_session_pointer_status: typeof raw.hermes_session_pointer_status === "string"
      && raw.hermes_session_pointer_status.trim()
      ? raw.hermes_session_pointer_status
      : undefined,
    worker_pid_changed: typeof raw.worker_pid_changed === "boolean"
      ? raw.worker_pid_changed
      : undefined,
    fresh_graph_revision_used: typeof raw.fresh_graph_revision_used === "boolean"
      ? raw.fresh_graph_revision_used
      : undefined,
  };
}

export function formatTraceConversationContextSummary(
  conversationContext: HermesConversationTraceContext | null,
  options: { isHermesGraphAgent: boolean },
): string {
  if (!options.isHermesGraphAgent || !conversationContext) return "";
  const contextLabel = conversationContext.history_present
    ? `ctx: ${conversationContext.message_count} msgs · ${conversationContext.pair_count} pairs · ${
        conversationContext.graph_metadata_in_history
          ? "graph meta in history"
          : "graph meta excluded"
      }`
    : "ctx: no history";
  const lifecycleLabels = [
    conversationContext.hermes_session_pointer_status
      ? `pointer: ${conversationContext.hermes_session_pointer_status}`
      : null,
    typeof conversationContext.worker_pid_changed === "boolean"
      ? `worker: ${conversationContext.worker_pid_changed ? "changed" : "same"}`
      : null,
    typeof conversationContext.fresh_graph_revision_used === "boolean"
      ? `graph: ${conversationContext.fresh_graph_revision_used ? "fresh" : "not fresh"}`
      : null,
  ].filter((label): label is string => label != null);
  return [contextLabel, ...lifecycleLabels].join(" · ");
}

export function formatTraceToolSummary(
  toolEvents: HermesGraphToolTraceEvent[],
  options: { isHermesGraphAgent: boolean },
): string {
  if (toolEvents.length === 0) {
    return options.isHermesGraphAgent ? "tools: none" : "";
  }
  const names = toolEvents.map((event) => event.tool_name);
  const unique = [...new Set(names)];
  const preview = unique.slice(0, 3).join(", ");
  const extra = unique.length > 3 ? ` (+${unique.length - 3} more)` : "";
  const count = toolEvents.length !== unique.length ? ` ×${toolEvents.length}` : "";
  return `tools: ${preview}${extra}${count}`;
}

function parseTimestampMs(value: unknown): number | null {
  if (typeof value !== "string" || !value.trim()) return null;
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : null;
}

/**
 * Infer source timestamp resolution from the ISO string.
 * A0 `utc_now_z()` emits whole seconds (`%Y-%m-%dT%H:%M:%SZ`) with no fractional part.
 */
function timestampResolutionMs(value: unknown): number | null {
  if (typeof value !== "string" || !value.trim()) return null;
  if (parseTimestampMs(value) == null) return null;
  const fractional = value.match(/\.(\d+)/);
  if (!fractional) return 1000;
  const digits = fractional[1].length;
  if (digits >= 3) return 1;
  if (digits === 2) return 10;
  return 100;
}

function clampPercent(value: number): number {
  if (!Number.isFinite(value) || value < 0) return 0;
  if (value > 100) return 100;
  return value;
}

type PhaseTimingPlacement = "relative-offset" | "duration-only";

function traceInterval(trace: AgentInteractionTrace, spans: AgentInteractionTraceSpan[]): { start: number; end: number } | null {
  const start = parseTimestampMs(trace.started_at);
  const end = parseTimestampMs(trace.completed_at);
  if (start != null && end != null && end >= start) return { start, end };
  const stampStarts = spans
    .map((span) => parseTimestampMs(span.started_at))
    .filter((value): value is number => value != null);
  const stampEnds = spans
    .map((span) => parseTimestampMs(span.completed_at))
    .filter((value): value is number => value != null);
  if (!stampStarts.length || !stampEnds.length) return null;
  return { start: Math.min(...stampStarts), end: Math.max(...stampEnds) };
}

function resolvePhaseTimingPlacement(
  trace: AgentInteractionTrace,
  spans: AgentInteractionTraceSpan[],
): PhaseTimingPlacement {
  const timedSpans = spans.filter((span) => finiteNumber(span.duration_ms) != null);
  const durations = timedSpans
    .map((span) => finiteNumber(span.duration_ms))
    .filter((ms): ms is number => ms != null && ms > 0);
  if (!durations.length) return "duration-only";
  if (timedSpans.some((span) => timestampResolutionMs(span.started_at) == null)) {
    return "duration-only";
  }

  const interval = traceInterval(trace, spans);
  if (!interval) return "duration-only";

  const usesTraceBounds = parseTimestampMs(trace.started_at) != null
    && parseTimestampMs(trace.completed_at) != null;
  const intervalStamps: unknown[] = usesTraceBounds
    ? [trace.started_at, trace.completed_at]
    : spans.flatMap((span) => [span.started_at, span.completed_at]);
  const resolutions = [...intervalStamps, ...timedSpans.map((span) => span.started_at)]
    .map((stamp) => timestampResolutionMs(stamp))
    .filter((ms): ms is number => ms != null);
  if (!resolutions.length) return "duration-only";

  const coarsestResolution = Math.max(...resolutions);
  const finestDuration = Math.min(...durations);
  if (coarsestResolution >= finestDuration) return "duration-only";

  const intervalMs = interval.end - interval.start;
  const maxDuration = Math.max(...durations);
  if (intervalMs < maxDuration) return "duration-only";
  return "relative-offset";
}

function timingBarStyle(
  startedAt: unknown,
  durationMs: unknown,
  interval: { start: number; end: number } | null,
  maxDuration: number | null,
  placement: PhaseTimingPlacement,
): { offset: number; width: number } | null {
  const duration = finiteNumber(durationMs);
  if (duration == null) return null;
  const widthFromDuration = maxDuration && maxDuration > 0
    ? clampPercent((duration / maxDuration) * 100)
    : 0;
  if (placement === "relative-offset" && interval) {
    const startMs = parseTimestampMs(startedAt);
    if (startMs != null) {
      const span = Math.max(1, interval.end - interval.start);
      const offset = clampPercent(((startMs - interval.start) / span) * 100);
      const width = clampPercent((duration / span) * 100);
      return { offset, width: Math.max(width, 0.5) };
    }
  }
  return { offset: 0, width: Math.max(widthFromDuration, 0.5) };
}

function normalizeModelCall(raw: unknown): AgentInteractionModelCallTrace | null {
  if (!isRecord(raw)) return null;
  const callId = stringField(raw.call_id);
  const sequence = finiteNumber(raw.sequence);
  if (!callId && sequence == null) return null;
  const usage = isRecord(raw.usage)
    ? {
        available: raw.usage.available === true || raw.usage.status === "reported" || raw.usage.status === "partial",
        status: typeof raw.usage.status === "string" ? raw.usage.status : undefined,
        input_tokens: finiteNumber(raw.usage.input_tokens),
        cached_input_tokens: finiteNumber(raw.usage.cached_input_tokens) ?? undefined,
        cache_write_input_tokens: finiteNumber(raw.usage.cache_write_input_tokens) ?? undefined,
        uncached_input_tokens: finiteNumber(raw.usage.uncached_input_tokens) ?? undefined,
        output_tokens: finiteNumber(raw.usage.output_tokens),
        reasoning_tokens: finiteNumber(raw.usage.reasoning_tokens) ?? undefined,
        total_tokens: finiteNumber(raw.usage.total_tokens),
      }
    : { available: false, status: "unavailable", input_tokens: null, output_tokens: null, total_tokens: null };
  const cost = isRecord(raw.cost)
    ? {
        status: typeof raw.cost.status === "string" ? raw.cost.status : "unavailable",
        usd: finiteNumber(raw.cost.usd),
        currency: typeof raw.cost.currency === "string" ? raw.cost.currency : undefined,
      }
    : undefined;
  return {
    call_id: callId ?? `call-${sequence ?? 0}`,
    sequence: sequence ?? 0,
    status: stringField(raw.status) ?? "unknown",
    provider: stringField(raw.provider),
    requested_model: stringField(raw.requested_model),
    response_model: stringField(raw.response_model),
    api_mode: stringField(raw.api_mode),
    started_at: stringField(raw.started_at),
    completed_at: stringField(raw.completed_at),
    duration_ms: finiteNumber(raw.duration_ms),
    usage,
    cost,
    finish_reason: stringField(raw.finish_reason),
    retry_count: finiteNumber(raw.retry_count) ?? undefined,
    retryable: typeof raw.retryable === "boolean" ? raw.retryable : undefined,
    status_code: finiteNumber(raw.status_code),
    error_type: stringField(raw.error_type),
  };
}

function normalizeSpan(raw: unknown): AgentInteractionTraceSpan | null {
  if (!isRecord(raw)) return null;
  const name = stringField(raw.name);
  const spanId = stringField(raw.span_id);
  if (!name || !spanId) return null;
  const attributes: Record<string, string | number | boolean | null> = {};
  if (isRecord(raw.attributes)) {
    for (const [key, value] of Object.entries(raw.attributes)) {
      if (FORBIDDEN_TRACE_KEYS.has(key)) continue;
      if (value === null || typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
        attributes[key] = value;
      }
    }
  }
  return {
    span_id: spanId,
    parent_span_id: stringField(raw.parent_span_id),
    kind: stringField(raw.kind) ?? "phase",
    name,
    status: stringField(raw.status) ?? "unknown",
    started_at: stringField(raw.started_at),
    completed_at: stringField(raw.completed_at),
    duration_ms: finiteNumber(raw.duration_ms),
    attributes: Object.keys(attributes).length ? attributes : undefined,
  };
}

function formatCallCountLabel(trace: AgentInteractionTrace, retained: number): string | null {
  const observed = finiteNumber(trace.usage?.observed_model_call_count);
  const truncated = stringArrayField(trace.warnings).includes("model_calls_truncated")
    || (observed != null && observed > retained);
  if (truncated) {
    const observedLabel = observed != null && observed > retained ? observed : retained;
    return `${retained} retained / ${observedLabel} observed calls`;
  }
  if (retained > 0) return `${retained} model call${retained === 1 ? "" : "s"}`;
  const count = finiteNumber(trace.usage?.model_call_count);
  if (count != null) return `${count} model call${count === 1 ? "" : "s"}`;
  return null;
}

function Definition({ label, value }: { label: string; value: string | number | null | undefined }) {
  if (value == null || value === "") return null;
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

export function AgentTraceInspector({ trace }: AgentTraceInspectorProps) {
  const [copyStatus, setCopyStatus] = useState<CopyStatus>("idle");
  const context = isRecord(trace.context_summary) ? trace.context_summary : {};
  const steps = Array.isArray(trace.steps) ? trace.steps : [];
  const backend = displayString(trace.backend);
  const runtime = displayString(trace.runtime);
  const status = displayString(trace.status, "unknown");
  const mode = displayString(trace.mode);
  const provider = displayOptionalString(trace.provider);
  const model = displayOptionalString(trace.model);
  const toolset = displayOptionalString(trace.toolset);
  const traceId = displayString(trace.trace_id);
  const startedAt = displayString(trace.started_at);
  const hermesSessionId = displayOptionalString(trace.hermes_session_id);
  const commandSummary = displayOptionalString(trace.command_summary);
  const promptPreview = displayOptionalString(trace.prompt_preview);
  const warnings = stringArrayField(trace.warnings);
  const isHermesGraphAgent = mode === "hermes_graph_agent";
  const rawToolEvents = Array.isArray(trace.tool_events) ? trace.tool_events : [];
  const normalizedToolEvents = rawToolEvents
    .map((event) => normalizeGraphToolEvent(event))
    .filter((event): event is HermesGraphToolTraceEvent => event != null);
  const skippedToolEvents = !Array.isArray(trace.tool_events) && trace.tool_events != null
    ? 1
    : rawToolEvents.length - normalizedToolEvents.length;
  const elapsedMs = finiteNumber(trace.elapsed_ms);
  const elapsedLabel = elapsedMs != null ? `${elapsedMs} ms` : "timing unavailable";
  const compactElapsed = formatElapsedMs(elapsedMs);
  const hasAnswerScopeTool = normalizedToolEvents.some(
    (event) => event.tool_name === "declare_conversation_context",
  );
  const toolActivityLabel = hasAnswerScopeTool ? "Tool activity" : "Graph tool activity";
  const answerScope = displayOptionalString(trace.answer_scope);
  const toolEventCount = typeof trace.tool_event_count === "number" ? trace.tool_event_count : null;
  const evidenceEventCount = typeof trace.evidence_event_count === "number" ? trace.evidence_event_count : null;
  const finalResponsePresent = typeof trace.final_response_present === "boolean" ? trace.final_response_present : null;
  const validatorPath = displayOptionalString(trace.validator_path);
  const toolSummary = formatTraceToolSummary(normalizedToolEvents, { isHermesGraphAgent });
  const conversationContext = normalizeConversationContext(trace.conversation_context);
  const conversationContextSummary = formatTraceConversationContextSummary(
    conversationContext,
    { isHermesGraphAgent },
  );
  const modelCalls = useMemo(
    () => (Array.isArray(trace.model_calls) ? trace.model_calls : [])
      .map((call) => normalizeModelCall(call))
      .filter((call): call is AgentInteractionModelCallTrace => call != null),
    [trace.model_calls],
  );
  const spans = useMemo(
    () => (Array.isArray(trace.spans) ? trace.spans : [])
      .map((span) => normalizeSpan(span))
      .filter((span): span is AgentInteractionTraceSpan => span != null),
    [trace.spans],
  );
  const callCountLabel = formatCallCountLabel(trace, modelCalls.length);
  const costLabel = formatCostStatus(trace.cost);
  const compactCost = formatCompactCost(trace.cost);
  const compactTokens = formatCompactTokens(trace.usage);
  const usagePartial = trace.usage?.status === "partial" || warnings.includes("model_calls_truncated");
  const phaseTimingPlacement = resolvePhaseTimingPlacement(trace, spans);
  const interval = phaseTimingPlacement === "relative-offset" ? traceInterval(trace, spans) : null;
  const maxSpanDuration = spans.reduce((max, span) => {
    const duration = finiteNumber(span.duration_ms);
    return duration != null && duration > max ? duration : max;
  }, 0);
  const summaryParts = [
    compactElapsed,
    compactTokens,
    compactCost,
    callCountLabel,
    toolSummary,
    conversationContextSummary,
    usagePartial && !compactTokens ? "usage partial" : null,
  ].filter((part): part is string => Boolean(part && part.length));
  const metaLine = summaryParts.length
    ? summaryParts.join(" · ")
    : [backend, runtime, status, compactElapsed ?? elapsedLabel].filter((part) => part.length > 0).join(" · ");
  const diagnosticsText = formatSafeTraceDiagnostics(trace);

  const handleCopyDiagnostics = async () => {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(diagnosticsText);
        setCopyStatus("copied");
        return;
      }
      throw new Error("Clipboard API unavailable");
    } catch {
      setCopyStatus("error");
    }
  };

  return (
    <section className="agent-trace" aria-label="Agent interaction trace">
      <div className="agent-trace-toolbar">
        <button
          type="button"
          className="agent-trace-copy"
          onClick={() => void handleCopyDiagnostics()}
        >
          {copyStatus === "copied" ? "Copied" : "Copy diagnostics"}
        </button>
        {copyStatus === "error" ? (
          <span className="agent-trace-warning" role="alert">
            Could not copy diagnostics
          </span>
        ) : null}
      </div>

      <details className="agent-trace-details">
        <summary>
          <span>Advanced diagnostics</span>
          <span className="agent-trace-muted" data-testid="agent-trace-summary-meta">
            {metaLine}
          </span>
        </summary>

        <section className="agent-trace-section" data-testid="agent-trace-overview">
          <h5>Overview</h5>
          <dl className="agent-trace-grid">
            {traceId ? (
              <div>
                <dt>Trace id</dt>
                <dd><code>{traceId}</code></dd>
              </div>
            ) : (
              <Definition label="Trace id" value="n/a" />
            )}
            <Definition label="Status" value={status} />
            <Definition label="Runtime" value={runtime || null} />
            <Definition label="Backend" value={backend || null} />
            <Definition label="Mode" value={mode || null} />
            <Definition label="Elapsed" value={elapsedLabel} />
            <Definition
              label="Provider / model"
              value={`${provider ?? "n/a"} / ${model ?? "n/a"}`}
            />
            <Definition label="Model calls" value={callCountLabel} />
            <Definition
              label="Tokens"
              value={trace.usage || trace.schema === "dmb_agent_turn_trace_v1"
                ? formatTokenBreakdown(trace.usage)
                : null}
            />
            <Definition
              label="Cost"
              value={trace.cost || trace.schema === "dmb_agent_turn_trace_v1"
                ? (costLabel ?? "unavailable")
                : null}
            />
            <Definition
              label="Priced calls"
              value={trace.cost && (trace.cost.priced_call_count != null || trace.cost.unpriced_call_count != null)
                ? `${trace.cost.priced_call_count ?? 0} priced / ${trace.cost.unpriced_call_count ?? 0} unpriced`
                : null}
            />
            {!isHermesGraphAgent ? <Definition label="Toolset" value={toolset} /> : null}
            <Definition label="Started" value={startedAt || null} />
            {isHermesGraphAgent && hermesSessionId ? (
              <div>
                <dt>Hermes session (observability)</dt>
                <dd><code>{hermesSessionId}</code></dd>
              </div>
            ) : null}
            {isHermesGraphAgent ? <Definition label="Answer scope" value={answerScope} /> : null}
            {isHermesGraphAgent ? <Definition label="Tool events" value={toolEventCount} /> : null}
            {isHermesGraphAgent ? <Definition label="Evidence events" value={evidenceEventCount} /> : null}
            {isHermesGraphAgent && finalResponsePresent != null ? (
              <Definition label="Final response" value={finalResponsePresent ? "present" : "absent"} />
            ) : null}
            {isHermesGraphAgent && validatorPath ? (
              <div>
                <dt>Validator path</dt>
                <dd><code>{validatorPath}</code></dd>
              </div>
            ) : null}
            {trace.prompt_char_count != null && !isHermesGraphAgent ? (
              <div>
                <dt>Prompt size</dt>
                <dd>
                  {trace.prompt_char_count} chars
                  {trace.prompt_token_estimate != null
                    ? ` (~${trace.prompt_token_estimate} est.)`
                    : null}
                </dd>
              </div>
            ) : null}
          </dl>
        </section>

        {spans.length ? (
          <section
            className="agent-trace-section"
            data-testid="agent-trace-phases"
            data-timing-placement={phaseTimingPlacement}
          >
            <h5>Product phases</h5>
            <ul className="agent-trace-list">
              {spans.map((span) => {
                const durationLabel = span.duration_ms == null
                  ? "timing unavailable"
                  : `${span.duration_ms} ms`;
                const bar = timingBarStyle(
                  span.started_at,
                  span.duration_ms,
                  interval,
                  maxSpanDuration,
                  phaseTimingPlacement,
                );
                return (
                  <li key={span.span_id} className="agent-trace-item" data-testid="agent-trace-phase">
                    <div className="agent-trace-item-header">
                      <strong>{span.name}</strong>
                      <span className="agent-trace-muted">{span.status} · {durationLabel}</span>
                    </div>
                    {bar ? (
                      <div
                        className={
                          phaseTimingPlacement === "duration-only"
                            ? "agent-trace-bar-track agent-trace-bar-track--duration-only"
                            : "agent-trace-bar-track"
                        }
                        aria-hidden="true"
                        data-testid="agent-trace-phase-bar"
                        style={{
                          ["--trace-bar-offset" as string]: `${bar.offset}%`,
                          ["--trace-bar-width" as string]: `${bar.width}%`,
                        }}
                      >
                        <div className="agent-trace-bar-fill" />
                      </div>
                    ) : (
                      <p className="agent-trace-muted">timing unavailable</p>
                    )}
                  </li>
                );
              })}
            </ul>
          </section>
        ) : null}

        {modelCalls.length ? (
          <section className="agent-trace-section" data-testid="agent-trace-model-calls">
            <h5>Model calls ({modelCalls.length})</h5>
            <ul className="agent-trace-list">
              {modelCalls.map((call) => (
                <li key={call.call_id} className="agent-trace-item" data-testid="agent-trace-model-call">
                  <div className="agent-trace-item-header">
                    <strong>#{call.sequence} {call.response_model || call.requested_model || "model"}</strong>
                    <span className="agent-trace-muted">
                      {call.status}
                      {call.duration_ms != null ? ` · ${call.duration_ms} ms` : " · timing unavailable"}
                    </span>
                  </div>
                  <dl className="agent-trace-grid">
                    <Definition label="Provider" value={call.provider} />
                    <Definition label="Requested model" value={call.requested_model} />
                    <Definition label="Response model" value={call.response_model} />
                    <Definition label="API mode" value={call.api_mode} />
                    <Definition
                      label="Duration"
                      value={call.duration_ms != null ? `${call.duration_ms} ms` : "timing unavailable"}
                    />
                    <Definition label="Tokens" value={formatTokenBreakdown(call.usage)} />
                    <Definition label="Cost" value={formatCostStatus(call.cost) ?? "unavailable"} />
                    <Definition label="Finish reason" value={call.finish_reason} />
                    <Definition
                      label="Retry"
                      value={
                        call.retry_count != null || call.retryable != null
                          ? `${call.retry_count ?? 0}${call.retryable != null ? ` · ${call.retryable ? "retryable" : "not retryable"}` : ""}`
                          : null
                      }
                    />
                    <Definition label="Status code" value={call.status_code} />
                    <Definition label="Error type" value={call.error_type} />
                  </dl>
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {!isHermesGraphAgent && commandSummary ? (
          <div className="agent-trace-command">
            <h5>Command</h5>
            <code>{commandSummary}</code>
          </div>
        ) : null}

        {!isHermesGraphAgent && promptPreview ? (
          <details className="agent-trace-prompt">
            <summary>Prompt sent to Hermes ({trace.prompt_char_count ?? promptPreview.length} chars)</summary>
            <pre>{promptPreview}</pre>
          </details>
        ) : null}

        {(context.admitted_count != null || context.rejected_count != null) ? (
          <div className="agent-trace-context">
            <h5>Context summary</h5>
            <ul>
              {context.admitted_count != null ? (
                <li>Admitted evidence: {displayScalar(context.admitted_count)}</li>
              ) : null}
              {context.rejected_count != null ? (
                <li>Rejected evidence: {displayScalar(context.rejected_count)}</li>
              ) : null}
              {context.admitted_excerpt_char_count != null ? (
                <li>
                  Admitted excerpt payload: {displayScalar(context.admitted_excerpt_char_count)} chars
                  {context.admitted_excerpt_token_estimate != null
                    ? ` (~${context.admitted_excerpt_token_estimate} tokens est.)`
                    : null}
                </li>
              ) : null}
              {context.total_excerpt_char_count != null ? (
                <li>
                  Total retrieved excerpt payload: {displayScalar(context.total_excerpt_char_count)} chars
                  {context.total_excerpt_token_estimate != null
                    ? ` (~${context.total_excerpt_token_estimate} tokens est.)`
                    : null}
                </li>
              ) : null}
              {context.context_payload_kind ? (
                <li>Payload kind: {displayScalar(context.context_payload_kind)}</li>
              ) : null}
              {!isHermesGraphAgent && context.manifest_path ? (
                <li>
                  Manifest: <code>{displayScalar(context.manifest_path)}</code>
                </li>
              ) : null}
              {context.intent_class ? <li>Intent: {displayScalar(context.intent_class)}</li> : null}
              {context.answerable_now != null ? (
                <li>Answerable now: {context.answerable_now ? "yes" : "no"}</li>
              ) : null}
              {context.verdict ? <li>Verdict: {displayScalar(context.verdict)}</li> : null}
            </ul>
          </div>
        ) : null}

        {isHermesGraphAgent && conversationContext ? (
          <div className="agent-trace-context" data-testid="agent-trace-conversation-context">
            <h5>Conversation context</h5>
            <dl className="agent-trace-grid">
              <Definition label="History present" value={formatYesNo(conversationContext.history_present)} />
              <Definition label="Message count" value={conversationContext.message_count} />
              <Definition label="Pair count" value={conversationContext.pair_count} />
              <Definition label="Payload shape" value={conversationContext.payload_shape} />
              <Definition label="Graph metadata in history" value={formatYesNo(conversationContext.graph_metadata_in_history)} />
              <Definition
                label="Hermes session pointer in request"
                value={formatYesNo(conversationContext.hermes_session_pointer_in_request)}
              />
              <Definition
                label="Hermes session pointer status"
                value={conversationContext.hermes_session_pointer_status ?? "not reported"}
              />
              <Definition
                label="Worker PID changed"
                value={
                  typeof conversationContext.worker_pid_changed === "boolean"
                    ? formatYesNo(conversationContext.worker_pid_changed)
                    : "not reported"
                }
              />
              <Definition
                label="Fresh graph revision used"
                value={
                  typeof conversationContext.fresh_graph_revision_used === "boolean"
                    ? formatYesNo(conversationContext.fresh_graph_revision_used)
                    : "not reported"
                }
              />
            </dl>
          </div>
        ) : null}

        {isHermesGraphAgent ? (
          <details className="agent-trace-tool-events" open data-testid="agent-trace-tools">
            <summary>{toolActivityLabel} ({normalizedToolEvents.length})</summary>
            {normalizedToolEvents.length === 0 ? (
              <p className="agent-trace-muted agent-trace-tool-empty" data-testid="agent-trace-tools-none">
                No graph tools were called on this turn.
              </p>
            ) : (
              <ul>
                {normalizedToolEvents.map((event, index) => (
                  <li key={`${event.tool_name}-${index}`} className="agent-trace-tool-event">
                    <div className="agent-trace-tool-event-header">
                      <strong>{event.tool_name}</strong>
                      <span className="agent-trace-muted">
                        {event.state}
                        {event.duration_ms != null ? ` · ${event.duration_ms}ms` : ""}
                        {event.outcome ? ` · ${event.outcome}` : ""}
                      </span>
                    </div>
                    <dl className="agent-trace-tool-event-grid">
                      {event.world_id ? (
                        <div>
                          <dt>World</dt>
                          <dd><code>{event.world_id}</code></dd>
                        </div>
                      ) : null}
                      {event.campaign_id ? (
                        <div>
                          <dt>Campaign</dt>
                          <dd><code>{event.campaign_id}</code></dd>
                        </div>
                      ) : null}
                      {event.revision_pin ? (
                        <div>
                          <dt>Revision pin</dt>
                          <dd><code>{event.revision_pin}</code></dd>
                        </div>
                      ) : null}
                      {event.focus?.kind ? (
                        <div>
                          <dt>Focus</dt>
                          <dd>
                            {event.focus.kind}
                            {event.focus.session_id ? ` · ${event.focus.session_id}` : ""}
                          </dd>
                        </div>
                      ) : null}
                      {event.admissibility ? (
                        <div>
                          <dt>Admissibility</dt>
                          <dd>{event.admissibility}</dd>
                        </div>
                      ) : null}
                      <div>
                        <dt>Matched nodes</dt>
                        <dd>{formatIdList(event.matched_node_ids)}</dd>
                      </div>
                      <div>
                        <dt>Relationships</dt>
                        <dd>{formatIdList(event.relationship_ids)}</dd>
                      </div>
                      <div>
                        <dt>Source anchors</dt>
                        <dd>{formatIdList(event.source_anchor_ids)}</dd>
                      </div>
                      <div>
                        <dt>Diagnostic codes</dt>
                        <dd>{formatIdList(event.diagnostic_codes)}</dd>
                      </div>
                    </dl>
                  </li>
                ))}
              </ul>
            )}
            {skippedToolEvents > 0 ? (
              <p className="agent-trace-warning agent-trace-tool-event-warning">
                Skipped {skippedToolEvents} malformed graph tool event{skippedToolEvents === 1 ? "" : "s"}.
              </p>
            ) : null}
          </details>
        ) : null}

        {!isHermesGraphAgent && steps.length ? (
          <details className="agent-trace-steps">
            <summary>Tool / step trace ({steps.length})</summary>
            <ul>
              {steps.map((step, index) => {
                const record = step && typeof step === "object" ? step as unknown as Record<string, unknown> : {};
                const name = typeof record.name === "string" ? record.name : `step-${index}`;
                const summary = typeof record.summary === "string" ? record.summary : "";
                return (
                  <li key={`${name}-${index}`}>
                    <strong>{name}</strong>
                    <span>{summary}</span>
                  </li>
                );
              })}
            </ul>
          </details>
        ) : null}

        {!isHermesGraphAgent && Array.isArray(trace.artifact_refs) && trace.artifact_refs.length ? (
          <div className="agent-trace-artifacts">
            <h5>Artifact refs</h5>
            <ul>
              {trace.artifact_refs.map((ref, index) => {
                const record = ref && typeof ref === "object" ? ref as unknown as Record<string, unknown> : {};
                const kind = typeof record.kind === "string" ? record.kind : "ref";
                const path = typeof record.path === "string" ? record.path : "";
                const label = typeof record.label === "string" ? record.label : null;
                return (
                  <li key={`${kind}-${path}-${index}`}>
                    <div className="agent-trace-artifact-meta">
                      <strong>{kind}</strong>
                      {label ? <span>{label}</span> : null}
                    </div>
                    <code>{path}</code>
                  </li>
                );
              })}
            </ul>
          </div>
        ) : null}

        {warnings.length ? (
          <div className="agent-trace-warnings">
            <h5>Warnings</h5>
            <ul>
              {warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          </div>
        ) : null}

        <details className="agent-trace-section agent-trace-structured" data-testid="agent-trace-structured">
          <summary>Structured trace</summary>
          <pre>{diagnosticsText}</pre>
        </details>
      </details>
    </section>
  );
}
