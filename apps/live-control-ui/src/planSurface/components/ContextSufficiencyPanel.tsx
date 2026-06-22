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
  const { quality, verdict, weakItems, rejectedSummary, suggestedRoutes, sourceReviewWorklist } =
    review;

  return (
    <section className="plan-agent-packet-review" aria-label="Context packet review">
      <p className="plan-agent-quality-line">{quality.summaryLine}</p>

      {review.campaignTextExcerpts.length ? (
        <div className="plan-agent-campaign-text">
          <h4>Admitted campaign text</h4>
          <ul className="plan-agent-admitted-text">
            {review.campaignTextExcerpts.map((text, index) => (
              <li key={`${index}-${text.slice(0, 24)}`}>{text}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className={`plan-agent-verdict plan-agent-verdict-${verdict.status}`}>
        <h4>Preliminary verdict · {verdictLabel(verdict.status)}</h4>
        <p>{verdict.reason}</p>
        <p className="plan-agent-muted">
          Answerable now: {verdict.answerableNow ? "yes" : "no"}
        </p>
      </div>

      {suggestedRoutes.length ? (
        <div className="plan-agent-suggested-routes">
          <h4>Suggested source reads</h4>
          <ul>
            {suggestedRoutes.map((route) => (
              <li key={route}>
                <code>{route}</code>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {sourceReviewWorklist.length ? (
        <details className="plan-agent-source-review">
          <summary>Review selected source text ({sourceReviewWorklist.length})</summary>
          <ul>
            {sourceReviewWorklist.map((item) => (
              <li key={item.path} data-status={item.status} data-preferred={item.preferred}>
                <strong>{item.status === "excerpt_available" ? "Excerpt" : "Needs read"}</strong>
                <span>
                  {item.sourceRole} · {item.authority}
                </span>
                <code>{item.path}</code>
                {item.excerpt &&
                !review.campaignTextExcerpts.includes(item.excerpt) ? (
                  <p>{item.excerpt}</p>
                ) : null}
              </li>
            ))}
          </ul>
        </details>
      ) : null}

      {weakItems.length ? (
        <details className="plan-agent-weak-evidence">
          <summary>Weak or debug admitted items ({weakItems.length})</summary>
          <ul>
            {weakItems.map(({ evidence, label }) => (
              <li key={evidence.path + label}>
                <strong>{label}</strong>
                <code>{evidence.path}</code>
              </li>
            ))}
          </ul>
        </details>
      ) : null}

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
