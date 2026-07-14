import type { AgentInteractionTrace, HermesGraphToolTraceEvent } from "../../api/types";

interface TraceDetailsPanelProps {
  trace: AgentInteractionTrace;
  answer?: string | null;
}

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

export function TraceDetailsPanel({ trace, answer }: TraceDetailsPanelProps) {
  const context = isRecord(trace.context_summary) ? trace.context_summary : {};
  const steps = Array.isArray(trace.steps) ? trace.steps : [];
  const stepCount = steps.length;
  const isHermesGraphAgent = trace.mode === "hermes_graph_agent";
  const rawToolEvents = Array.isArray(trace.tool_events) ? trace.tool_events : [];
  const normalizedToolEvents = rawToolEvents
    .map((event) => normalizeGraphToolEvent(event))
    .filter((event): event is HermesGraphToolTraceEvent => event != null);
  const skippedToolEvents = !Array.isArray(trace.tool_events) && trace.tool_events != null
    ? 1
    : rawToolEvents.length - normalizedToolEvents.length;
  const elapsedMs = typeof trace.elapsed_ms === "number" ? trace.elapsed_ms : 0;

  return (
    <section className="plan-agent-trace" aria-label="Agent interaction trace">
      <details className="plan-agent-trace-details">
        <summary>
          <span>Agent trace</span>
          <span className="plan-agent-muted">
            {trace.backend} · {trace.runtime} · {trace.status} · {elapsedMs}ms
          </span>
        </summary>

        <dl className="plan-agent-trace-grid">
          <div>
            <dt>Mode</dt>
            <dd>{trace.mode}</dd>
          </div>
          <div>
            <dt>Provider / model</dt>
            <dd>
              {trace.provider ?? "n/a"} / {trace.model ?? "n/a"}
            </dd>
          </div>
          <div>
            <dt>Toolset</dt>
            <dd>{trace.toolset ?? "n/a"}</dd>
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
            <dd><code>{trace.trace_id}</code></dd>
          </div>
          <div>
            <dt>Started</dt>
            <dd>{trace.started_at}</dd>
          </div>
          {isHermesGraphAgent && trace.hermes_session_id ? (
            <div>
              <dt>Hermes session (observability)</dt>
              <dd><code>{trace.hermes_session_id}</code></dd>
            </div>
          ) : null}
        </dl>

        {!isHermesGraphAgent && trace.command_summary ? (
          <div className="plan-agent-trace-command">
            <h5>Command</h5>
            <code>{trace.command_summary}</code>
          </div>
        ) : null}

        {!isHermesGraphAgent && trace.prompt_preview ? (
          <details className="plan-agent-trace-prompt">
            <summary>Prompt sent to Hermes ({trace.prompt_char_count ?? trace.prompt_preview.length} chars)</summary>
            <pre>{trace.prompt_preview}</pre>
          </details>
        ) : null}

        {(context.admitted_count != null || context.rejected_count != null) ? (
          <div className="plan-agent-trace-context">
            <h5>Context summary</h5>
            <ul>
              {context.admitted_count != null ? (
                <li>Admitted evidence: {context.admitted_count}</li>
              ) : null}
              {context.rejected_count != null ? (
                <li>Rejected evidence: {context.rejected_count}</li>
              ) : null}
              {context.admitted_excerpt_char_count != null ? (
                <li>
                  Admitted excerpt payload: {context.admitted_excerpt_char_count} chars
                  {context.admitted_excerpt_token_estimate != null
                    ? ` (~${context.admitted_excerpt_token_estimate} tokens est.)`
                    : null}
                </li>
              ) : null}
              {context.total_excerpt_char_count != null ? (
                <li>
                  Total retrieved excerpt payload: {context.total_excerpt_char_count} chars
                  {context.total_excerpt_token_estimate != null
                    ? ` (~${context.total_excerpt_token_estimate} tokens est.)`
                    : null}
                </li>
              ) : null}
              {context.context_payload_kind ? (
                <li>Payload kind: {context.context_payload_kind}</li>
              ) : null}
              {!isHermesGraphAgent && context.manifest_path ? (
                <li>
                  Manifest: <code>{context.manifest_path}</code>
                </li>
              ) : null}
              {context.intent_class ? <li>Intent: {context.intent_class}</li> : null}
              {context.answerable_now != null ? (
                <li>Answerable now: {context.answerable_now ? "yes" : "no"}</li>
              ) : null}
              {context.verdict ? <li>Verdict: {context.verdict}</li> : null}
            </ul>
          </div>
        ) : null}

        {isHermesGraphAgent && (normalizedToolEvents.length > 0 || skippedToolEvents > 0) ? (
          <details className="plan-agent-trace-tool-events" open>
            <summary>Graph tool activity ({normalizedToolEvents.length})</summary>
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
                const record = step && typeof step === "object" ? step as Record<string, unknown> : {};
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
                const record = ref && typeof ref === "object" ? ref as Record<string, unknown> : {};
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

        {trace.warnings?.length ? (
          <div className="plan-agent-trace-warnings">
            <h5>Warnings</h5>
            <ul>
              {trace.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          </div>
        ) : null}

        {answer ? (
          <div className="plan-agent-trace-answer">
            <h5>Answer</h5>
            <p>{answer}</p>
          </div>
        ) : null}
      </details>
    </section>
  );
}
