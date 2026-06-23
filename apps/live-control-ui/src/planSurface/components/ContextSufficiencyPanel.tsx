import type { PacketReview } from "./contextSufficiencyLadder";

interface ContextSufficiencyPanelProps {
  review: PacketReview;
}

function verdictLabel(status: PacketReview["verdict"]["status"]): string {
  switch (status) {
    case "enough_context":
      return "Enough context";
    case "weak_context":
      return "Weak context";
    case "missing_context":
      return "Missing context";
    case "wrong_context":
      return "Wrong context";
    default:
      return status;
  }
}

export function ContextSufficiencyPanel({ review }: ContextSufficiencyPanelProps) {
  const { quality, verdict, rejectedSummary } = review;

  return (
    <section className="plan-agent-packet-review" aria-label="Context packet review">
      <p className="plan-agent-quality-line">{quality.summaryLine}</p>

      {review.admittedContextItems.length ? (
        <details className="plan-agent-full-context">
          <summary>Retrieved text ({review.admittedContextItems.length})</summary>
          <ul>
            {review.admittedContextItems.map((item, index) => (
              <li key={`${index}-${item.path ?? "context"}`}>
                <div className="plan-agent-context-meta">
                  <strong>{item.source_role ?? "unknown"}</strong>
                  <span>{item.authority ?? "unknown"}</span>
                  {item.line_start != null && item.line_end != null ? (
                    <span>lines {item.line_start}-{item.line_end}</span>
                  ) : null}
                </div>
                {item.path ? <code>{item.path}</code> : null}
                {item.text_excerpt ? (
                  <pre>{item.text_excerpt}</pre>
                ) : (
                  <p className="plan-agent-muted">No text excerpt returned for this admitted item.</p>
                )}
              </li>
            ))}
          </ul>
        </details>
      ) : null}

      <div className={`plan-agent-verdict plan-agent-verdict-${verdict.status}`}>
        <h4>Preliminary verdict · {verdictLabel(verdict.status)}</h4>
        <p>{verdict.reason}</p>
        <p className="plan-agent-muted">
          Answerable now: {verdict.answerableNow ? "yes" : "no"}
        </p>
      </div>

      {rejectedSummary.length ? (
        <div className="plan-agent-rejected-summary">
          <h4>Rejected evidence</h4>
          <ul>
            {rejectedSummary.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <dl className="plan-agent-proof-counts">
        <div>
          <dt>Admitted</dt>
          <dd>{quality.strong.length + quality.okay.length + quality.weak.length + quality.debug.length}</dd>
        </div>
        <div>
          <dt>Strong</dt>
          <dd>{quality.strong.length}</dd>
        </div>
        <div>
          <dt>Weak</dt>
          <dd>{quality.weak.length}</dd>
        </div>
        <div>
          <dt>Debug</dt>
          <dd>{quality.debug.length}</dd>
        </div>
      </dl>
    </section>
  );
}
