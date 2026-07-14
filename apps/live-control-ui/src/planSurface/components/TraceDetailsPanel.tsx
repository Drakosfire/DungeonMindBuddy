import type { AgentInteractionTrace, HermesGraphToolTraceEvent } from "../../api/types";

interface TraceDetailsPanelProps {
  trace: AgentInteractionTrace;
  answer?: string | null;
}

function formatTokens(usage: AgentInteractionTrace["usage"]): string {
  if (!usage.available) {
    return "not reported";
  }
  const parts: string[] = [];
  if (usage.input_tokens !== null) parts.push(`in ${usage.input_tokens}`);
  if (usage.output_tokens !== null) parts.push(`out ${usage.output_tokens}`);
  if (usage.total_tokens !== null) parts.push(`total ${usage.total_tokens}`);
  return parts.length ? parts.join(" · ") : "available (no counts)";
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
    bounded_ids: event.bounded_ids && typeof event.bounded_ids === "object"
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
  const context = trace.context_summary ?? {};
  const stepCount = trace.steps?.length ?? 0;
  const isHermesGraphAgent = trace.mode === "hermes_graph_agent";
  const normalizedToolEvents = (trace.tool_events ?? [])
    .map((event) => normalizeGraphToolEvent(event))
    .filter((event): event is HermesGraphToolTraceEvent => event != null);
  const skippedToolEvents = (trace.tool_events?.length ?? 0) - normalizedToolEvents.length;

  return (
    <section className="plan-agent-trace" aria-label="Agent interaction trace">
      <details className="plan-agent-trace-details">
        <summary>
          <span>Agent trace</span>
          <span className="plan-agent-muted">
            {trace.backend} · {trace.runtime} · {trace.status} · {trace.elapsed_ms}ms
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
            <dd>{trace.elapsed_ms} ms</dd>
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

        {isHermesGraphAgent && normalizedToolEvents.length ? (
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

        {!isHermesGraphAgent && trace.steps?.length ? (
          <details className="plan-agent-trace-steps">
            <summary>Tool / step trace ({trace.steps.length})</summary>
            <ul>
              {trace.steps.map((step, index) => (
                <li key={`${step.name}-${index}`}>
                  <strong>{step.name}</strong>
                  <span>{step.summary}</span>
                </li>
              ))}
            </ul>
          </details>
        ) : null}

        {!isHermesGraphAgent && trace.artifact_refs?.length ? (
          <div className="plan-agent-trace-artifacts">
            <h5>Artifact refs</h5>
            <ul>
              {trace.artifact_refs.map((ref) => (
                <li key={`${ref.kind}-${ref.path}`}>
                  <div className="plan-agent-trace-artifact-meta">
                    <strong>{ref.kind}</strong>
                    {ref.label ? <span>{ref.label}</span> : null}
                  </div>
                  <code>{ref.path}</code>
                </li>
              ))}
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
