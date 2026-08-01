import { useState } from "react";

import type {
  AgentInteractionTrace,
  HermesConversationTraceContext,
  HermesGraphToolTraceEvent,
} from "../../api/types";

interface TraceDetailsPanelProps {
  trace: AgentInteractionTrace;
  question?: string | null;
  answer?: string | null;
}

type CopyStatus = "idle" | "copied" | "error";

function formatTokens(usage: unknown): string {
  if (!isRecord(usage) || usage.available !== true) {
    return "not reported";
  }
  const parts: string[] = [];
  if (typeof usage.input_tokens === "number") parts.push(`in ${usage.input_tokens}`);
  if (typeof usage.output_tokens === "number") parts.push(`out ${usage.output_tokens}`);
  if (typeof usage.total_tokens === "number") parts.push(`total ${usage.total_tokens}`);
  return parts.length ? parts.join(" · ") : "available (no counts)";
}

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

// Trace context_summary values arrive as unknown record fields; only scalars are
// safe React children (objects would throw at render).
function displayScalar(value: unknown): string | number | null {
  return typeof value === "string" || typeof value === "number" ? value : null;
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

function formatIdList(ids: string[]): string {
  if (!ids.length) return "none";
  if (ids.length <= 3) return ids.join(", ");
  return `${ids.slice(0, 3).join(", ")} (+${ids.length - 3} more)`;
}

function formatYesNo(value: boolean): string {
  return value ? "yes" : "no";
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

/** Collapsed summary fragment for Hermes request-context telemetry (Thread B isolation). */
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

function formatConversationContextForClipboard(
  conversationContext: HermesConversationTraceContext,
): string[] {
  return [
    "Conversation context",
    `history_present: ${formatYesNo(conversationContext.history_present)}`,
    `message_count: ${conversationContext.message_count}`,
    `pair_count: ${conversationContext.pair_count}`,
    `payload_shape: ${conversationContext.payload_shape}`,
    `graph_metadata_in_history: ${formatYesNo(conversationContext.graph_metadata_in_history)}`,
    `hermes_session_pointer_in_request: ${formatYesNo(conversationContext.hermes_session_pointer_in_request)}`,
    ...(conversationContext.hermes_session_pointer_status
      ? [`hermes_session_pointer_status: ${conversationContext.hermes_session_pointer_status}`]
      : []),
    ...(typeof conversationContext.worker_pid_changed === "boolean"
      ? [`worker_pid_changed: ${formatYesNo(conversationContext.worker_pid_changed)}`]
      : []),
    ...(typeof conversationContext.fresh_graph_revision_used === "boolean"
      ? [`fresh_graph_revision_used: ${formatYesNo(conversationContext.fresh_graph_revision_used)}`]
      : []),
  ];
}

/** Collapsed summary fragment: tool names, or explicit none for Hermes graph turns. */
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

function formatToolEventForClipboard(event: HermesGraphToolTraceEvent, index: number): string {
  const lines = [
    `${index + 1}. ${event.tool_name} · ${event.state}`
      + (event.duration_ms != null ? ` · ${event.duration_ms}ms` : "")
      + (event.outcome ? ` · ${event.outcome}` : ""),
  ];
  if (event.revision_pin) lines.push(`   revision: ${event.revision_pin}`);
  if (event.world_id) lines.push(`   world: ${event.world_id}`);
  if (event.campaign_id) lines.push(`   campaign: ${event.campaign_id}`);
  if (event.focus?.kind) {
    lines.push(
      `   focus: ${event.focus.kind}`
        + (event.focus.session_id ? ` · ${event.focus.session_id}` : ""),
    );
  }
  if (event.admissibility) lines.push(`   admissibility: ${event.admissibility}`);
  lines.push(`   matched_nodes: ${formatIdList(event.matched_node_ids)}`);
  lines.push(`   relationships: ${formatIdList(event.relationship_ids)}`);
  lines.push(`   source_anchors: ${formatIdList(event.source_anchor_ids)}`);
  if (event.diagnostic_codes.length) {
    lines.push(`   diagnostics: ${formatIdList(event.diagnostic_codes)}`);
  }
  return lines.join("\n");
}

/** Plain-text dump for dogfood paste into chat / notes. */
export function formatTraceForClipboard(
  trace: AgentInteractionTrace,
  options: {
    question?: string | null;
    answer?: string | null;
    toolEvents: HermesGraphToolTraceEvent[];
    skippedToolEvents: number;
  },
): string {
  const mode = displayString(trace.mode);
  const isHermesGraphAgent = mode === "hermes_graph_agent";
  const lines: string[] = [
    "Agent trace",
  ];

  if (options.question?.trim()) {
    lines.push("");
    lines.push("You");
    lines.push(options.question.trim());
  }
  if (options.answer?.trim()) {
    lines.push("");
    lines.push("Hermes");
    lines.push(options.answer.trim());
  }

  lines.push("");
  lines.push(
    [
      displayString(trace.backend),
      displayString(trace.runtime),
      displayString(trace.status, "unknown"),
      `${typeof trace.elapsed_ms === "number" ? trace.elapsed_ms : 0}ms`,
    ].filter(Boolean).join(" · "),
  );
  lines.push(`mode: ${mode || "n/a"}`);
  lines.push(`trace_id: ${displayString(trace.trace_id) || "n/a"}`);
  lines.push(`started_at: ${displayString(trace.started_at) || "n/a"}`);

  const provider = displayOptionalString(trace.provider);
  const model = displayOptionalString(trace.model);
  if (provider || model) {
    lines.push(`provider/model: ${provider ?? "n/a"} / ${model ?? "n/a"}`);
  }
  if (displayOptionalString(trace.toolset)) {
    lines.push(`toolset: ${trace.toolset}`);
  }
  lines.push(`tokens: ${formatTokens(trace.usage)}`);

  if (isHermesGraphAgent) {
    if (displayOptionalString(trace.hermes_session_id)) {
      lines.push(`hermes_session_id: ${trace.hermes_session_id}`);
    }
    if (displayOptionalString(trace.answer_scope)) {
      lines.push(`answer_scope: ${trace.answer_scope}`);
    }
    if (typeof trace.tool_event_count === "number") {
      lines.push(`tool_event_count: ${trace.tool_event_count}`);
    }
    if (typeof trace.evidence_event_count === "number") {
      lines.push(`evidence_event_count: ${trace.evidence_event_count}`);
    }
    if (typeof trace.final_response_present === "boolean") {
      lines.push(`final_response_present: ${trace.final_response_present ? "yes" : "no"}`);
    }
    if (displayOptionalString(trace.validator_path)) {
      lines.push(`validator_path: ${trace.validator_path}`);
    }
    const conversationContext = normalizeConversationContext(trace.conversation_context);
    if (conversationContext) {
      lines.push("");
      lines.push(...formatConversationContextForClipboard(conversationContext));
    }
  }

  lines.push("");
  lines.push(`Graph tool activity (${options.toolEvents.length})`);
  if (options.toolEvents.length === 0) {
    lines.push(isHermesGraphAgent ? "none" : "(no tool events)");
  } else {
    for (const [index, event] of options.toolEvents.entries()) {
      lines.push(formatToolEventForClipboard(event, index));
    }
  }
  if (options.skippedToolEvents > 0) {
    lines.push(`skipped_malformed_tool_events: ${options.skippedToolEvents}`);
  }

  const warnings = stringArrayField(trace.warnings);
  if (warnings.length) {
    lines.push("");
    lines.push("Warnings");
    for (const warning of warnings) {
      lines.push(`- ${warning}`);
    }
  }

  return `${lines.join("\n")}\n`;
}

export function TraceDetailsPanel({ trace, question, answer }: TraceDetailsPanelProps) {
  const [copyStatus, setCopyStatus] = useState<CopyStatus>("idle");
  const context = isRecord(trace.context_summary) ? trace.context_summary : {};
  const steps = Array.isArray(trace.steps) ? trace.steps : [];
  const stepCount = steps.length;
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
  const elapsedMs = typeof trace.elapsed_ms === "number" ? trace.elapsed_ms : 0;
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
  const metaLine = [backend, runtime, status, `${elapsedMs}ms`, toolSummary, conversationContextSummary]
    .filter((part) => part.length > 0)
    .join(" · ");

  const handleCopyTrace = async () => {
    const text = formatTraceForClipboard(trace, {
      question,
      answer,
      toolEvents: normalizedToolEvents,
      skippedToolEvents,
    });
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
        setCopyStatus("copied");
        return;
      }
      throw new Error("Clipboard API unavailable");
    } catch {
      setCopyStatus("error");
    }
  };

  return (
    <section className="plan-agent-trace" aria-label="Agent interaction trace">
      <div className="plan-agent-trace-toolbar">
        <button
          type="button"
          className="plan-agent-trace-copy"
          onClick={() => void handleCopyTrace()}
        >
          {copyStatus === "copied" ? "Copied" : "Copy trace"}
        </button>
        {copyStatus === "error" ? (
          <span className="plan-agent-warning" role="alert">
            Could not copy trace
          </span>
        ) : null}
      </div>

      <details className="plan-agent-trace-details">
        <summary>
          <span>Agent trace</span>
          <span className="plan-agent-muted" data-testid="plan-agent-trace-summary-meta">
            {metaLine}
          </span>
        </summary>

        {(question?.trim() || answer?.trim()) ? (
          <div className="plan-agent-trace-prose" data-testid="plan-agent-trace-prose">
            {question?.trim() ? (
              <div className="plan-agent-trace-prose-turn">
                <h5>You</h5>
                <p>{question.trim()}</p>
              </div>
            ) : null}
            {answer?.trim() ? (
              <div className="plan-agent-trace-prose-turn">
                <h5>Hermes</h5>
                <p>{answer.trim()}</p>
              </div>
            ) : null}
          </div>
        ) : null}

        <dl className="plan-agent-trace-grid">
          <div>
            <dt>Mode</dt>
            <dd>{mode}</dd>
          </div>
          <div>
            <dt>Provider / model</dt>
            <dd>
              {provider ?? "n/a"} / {model ?? "n/a"}
            </dd>
          </div>
          <div>
            <dt>Toolset</dt>
            <dd>{toolset ?? "n/a"}</dd>
          </div>
          <div>
            <dt>Elapsed</dt>
            <dd>{elapsedMs} ms</dd>
          </div>
          <div>
            <dt>Steps</dt>
            <dd>{stepCount}</dd>
          </div>
          <div>
            <dt>Tokens</dt>
            <dd>{formatTokens(trace.usage)}</dd>
          </div>
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
          <div>
            <dt>Trace id</dt>
            <dd><code>{traceId}</code></dd>
          </div>
          <div>
            <dt>Started</dt>
            <dd>{startedAt}</dd>
          </div>
          {isHermesGraphAgent && hermesSessionId ? (
            <div>
              <dt>Hermes session (observability)</dt>
              <dd><code>{hermesSessionId}</code></dd>
            </div>
          ) : null}
          {isHermesGraphAgent && answerScope ? (
            <div>
              <dt>Answer scope</dt>
              <dd>{answerScope}</dd>
            </div>
          ) : null}
          {isHermesGraphAgent && toolEventCount != null ? (
            <div>
              <dt>Tool events</dt>
              <dd>{toolEventCount}</dd>
            </div>
          ) : null}
          {isHermesGraphAgent && evidenceEventCount != null ? (
            <div>
              <dt>Evidence events</dt>
              <dd>{evidenceEventCount}</dd>
            </div>
          ) : null}
          {isHermesGraphAgent && finalResponsePresent != null ? (
            <div>
              <dt>Final response</dt>
              <dd>{finalResponsePresent ? "present" : "absent"}</dd>
            </div>
          ) : null}
          {isHermesGraphAgent && validatorPath ? (
            <div>
              <dt>Validator path</dt>
              <dd><code>{validatorPath}</code></dd>
            </div>
          ) : null}
        </dl>

        {!isHermesGraphAgent && commandSummary ? (
          <div className="plan-agent-trace-command">
            <h5>Command</h5>
            <code>{commandSummary}</code>
          </div>
        ) : null}

        {!isHermesGraphAgent && promptPreview ? (
          <details className="plan-agent-trace-prompt">
            <summary>Prompt sent to Hermes ({trace.prompt_char_count ?? promptPreview.length} chars)</summary>
            <pre>{promptPreview}</pre>
          </details>
        ) : null}

        {(context.admitted_count != null || context.rejected_count != null) ? (
          <div className="plan-agent-trace-context">
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
          <div className="plan-agent-trace-context" data-testid="plan-agent-trace-conversation-context">
            <h5>Conversation context</h5>
            <dl className="plan-agent-trace-grid">
              <div>
                <dt>History present</dt>
                <dd>{formatYesNo(conversationContext.history_present)}</dd>
              </div>
              <div>
                <dt>Message count</dt>
                <dd>{conversationContext.message_count}</dd>
              </div>
              <div>
                <dt>Pair count</dt>
                <dd>{conversationContext.pair_count}</dd>
              </div>
              <div>
                <dt>Payload shape</dt>
                <dd>{conversationContext.payload_shape}</dd>
              </div>
              <div>
                <dt>Graph metadata in history</dt>
                <dd>{formatYesNo(conversationContext.graph_metadata_in_history)}</dd>
              </div>
              <div>
                <dt>Hermes session pointer in request</dt>
                <dd>{formatYesNo(conversationContext.hermes_session_pointer_in_request)}</dd>
              </div>
              <div>
                <dt>Hermes session pointer status</dt>
                <dd>{conversationContext.hermes_session_pointer_status ?? "not reported"}</dd>
              </div>
              <div>
                <dt>Worker PID changed</dt>
                <dd>
                  {typeof conversationContext.worker_pid_changed === "boolean"
                    ? formatYesNo(conversationContext.worker_pid_changed)
                    : "not reported"}
                </dd>
              </div>
              <div>
                <dt>Fresh graph revision used</dt>
                <dd>
                  {typeof conversationContext.fresh_graph_revision_used === "boolean"
                    ? formatYesNo(conversationContext.fresh_graph_revision_used)
                    : "not reported"}
                </dd>
              </div>
            </dl>
          </div>
        ) : null}

        {isHermesGraphAgent ? (
          <details className="plan-agent-trace-tool-events" open>
            <summary>{toolActivityLabel} ({normalizedToolEvents.length})</summary>
            {normalizedToolEvents.length === 0 ? (
              <p className="plan-agent-muted plan-agent-trace-tool-empty" data-testid="plan-agent-trace-tools-none">
                No graph tools were called on this turn.
              </p>
            ) : (
              <ul>
                {normalizedToolEvents.map((event, index) => (
                  <li key={`${event.tool_name}-${index}`} className="plan-agent-trace-tool-event">
                    <div className="plan-agent-trace-tool-event-header">
                      <strong>{event.tool_name}</strong>
                      <span className="plan-agent-muted">
                        {event.state}
                        {event.duration_ms != null ? ` · ${event.duration_ms}ms` : ""}
                        {event.outcome ? ` · ${event.outcome}` : ""}
                      </span>
                    </div>
                    <dl className="plan-agent-trace-tool-event-grid">
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
              <p className="plan-agent-warning plan-agent-trace-tool-event-warning">
                Skipped {skippedToolEvents} malformed graph tool event{skippedToolEvents === 1 ? "" : "s"}.
              </p>
            ) : null}
          </details>
        ) : null}

        {!isHermesGraphAgent && steps.length ? (
          <details className="plan-agent-trace-steps">
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
          <div className="plan-agent-trace-artifacts">
            <h5>Artifact refs</h5>
            <ul>
              {trace.artifact_refs.map((ref, index) => {
                const record = ref && typeof ref === "object" ? ref as unknown as Record<string, unknown> : {};
                const kind = typeof record.kind === "string" ? record.kind : "ref";
                const path = typeof record.path === "string" ? record.path : "";
                const label = typeof record.label === "string" ? record.label : null;
                return (
                  <li key={`${kind}-${path}-${index}`}>
                    <div className="plan-agent-trace-artifact-meta">
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
          <div className="plan-agent-trace-warnings">
            <h5>Warnings</h5>
            <ul>
              {warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          </div>
        ) : null}

      </details>
    </section>
  );
}
