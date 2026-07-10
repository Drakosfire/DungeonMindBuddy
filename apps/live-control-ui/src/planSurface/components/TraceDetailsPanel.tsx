// PR003_LEGACY_GRAPH_PREVIEW_EXEMPTION:
// Retained until PR007/PR008 removes preview/latest-ingest selectors from surface APIs.
import type { AgentInteractionTrace } from "../../api/types";

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

export function TraceDetailsPanel({ trace, answer }: TraceDetailsPanelProps) {
  const context = trace.context_summary ?? {};
  const stepCount = trace.steps?.length ?? 0;

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
          {trace.prompt_char_count != null ? (
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
        </dl>

        {trace.command_summary ? (
          <div className="plan-agent-trace-command">
            <h5>Command</h5>
            <code>{trace.command_summary}</code>
          </div>
        ) : null}

        {trace.prompt_preview ? (
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
              {context.manifest_path ? (
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

        {trace.steps?.length ? (
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

        {trace.artifact_refs?.length ? (
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
