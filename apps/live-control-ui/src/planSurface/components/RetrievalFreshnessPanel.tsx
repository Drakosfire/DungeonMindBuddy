import type { RetrievalFreshnessDecision } from "../../api/types";

const DECISION_COPY: Record<RetrievalFreshnessDecision["decision"], { label: string; summary: string }> = {
  fresh_retrieval: {
    label: "Fresh retrieval",
    summary: "Used current corpus retrieval for this answer.",
  },
  blended: {
    label: "Blended",
    summary: "Used current corpus retrieval and the active thread/session context.",
  },
  thread_context: {
    label: "Thread context",
    summary: "Used the active thread/session context. No fresh corpus evidence was admitted for this turn.",
  },
  insufficient_grounding: {
    label: "Insufficient grounding",
    summary: "No admitted corpus evidence and no reliable thread basis were available.",
  },
};

export function RetrievalFreshnessPanel({ decision }: { decision: RetrievalFreshnessDecision | null | undefined }) {
  if (!decision) return null;
  const copy = DECISION_COPY[decision.decision] ?? DECISION_COPY.insufficient_grounding;
  return (
    <section className="plan-agent-retrieval-freshness" data-decision={decision.decision} aria-label="Retrieval freshness">
      <div>
        <p className="plan-surface-kicker">Grounding</p>
        <h4>{copy.label}</h4>
        <p>{copy.summary}</p>
      </div>
      <p>{decision.reason}</p>
      <dl>
        <div>
          <dt>Fresh retrieval</dt>
          <dd>{decision.used_fresh_retrieval ? "yes" : "no"}</dd>
        </div>
        <div>
          <dt>Thread context</dt>
          <dd>{decision.used_thread_context ? "yes" : "no"}</dd>
        </div>
        <div>
          <dt>Admitted / rejected</dt>
          <dd>{decision.admitted_evidence_count} / {decision.rejected_evidence_count}</dd>
        </div>
        <div>
          <dt>Prior turns</dt>
          <dd>{decision.prior_turn_count}</dd>
        </div>
      </dl>
      {decision.warnings.length ? (
        <ul>
          {decision.warnings.map((warning) => <li key={warning}>{warning}</li>)}
        </ul>
      ) : null}
    </section>
  );
}
