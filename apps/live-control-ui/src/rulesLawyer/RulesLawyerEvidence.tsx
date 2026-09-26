import { useEffect, useState, type FormEvent } from "react";

import { queryRules, type RulesEvidenceItem, type RulesQueryPacket } from "../api/rulesQuery";

function Citation({ item }: { item: RulesEvidenceItem }) {
  return (
    <li>
      <button type="button" aria-label={`Inspect citation ${item.rank}`} onClick={(event) => {
        const details = event.currentTarget.nextElementSibling as HTMLDivElement | null;
        if (details) details.hidden = !details.hidden;
      }}>
        {item.source_locator || item.locator || `Source ${item.rank}`}
      </button>
      <div hidden data-testid={`citation-${item.rank}-details`}>
        <p>{item.excerpt || "No source excerpt available."}</p>
        <dl>
          <dt>Evidence unit</dt><dd>{item.evidence_unit_id}</dd>
          <dt>Evidence reference</dt><dd>{item.evidence_ref_id}</dd>
          <dt>Assertion</dt><dd>{item.assertion_id}</dd>
          <dt>Source artifact</dt><dd>{item.source_artifact_id}</dd>
          <dt>Source revision</dt><dd>{item.source_revision_id || "Unknown"}</dd>
          <dt>Source anchor</dt><dd>{item.source_anchor_id || "Unknown"}</dd>
        </dl>
        {item.source_uri?.startsWith("https://") ? (
          <a href={item.source_uri} target="_blank" rel="noopener noreferrer">Open source</a>
        ) : null}
      </div>
    </li>
  );
}

export function RulesLawyerEvidence() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [packet, setPacket] = useState<RulesQueryPacket | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [controller, setController] = useState<AbortController | null>(null);

  useEffect(() => () => controller?.abort(), [controller]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const submitted = question.trim();
    if (!submitted) return;
    controller?.abort();
    const next = new AbortController();
    setController(next);
    setLoading(true);
    setError(null);
    setPacket(null);
    try {
      setPacket(await queryRules(submitted, next.signal));
    } catch (caught) {
      if (!next.signal.aborted) setError(caught instanceof Error ? caught.message : "Rules service unavailable");
    } finally {
      if (!next.signal.aborted) setLoading(false);
    }
  }

  return (
    <section aria-label="Rules Lawyer evidence">
      <h2>Rules Lawyer</h2>
      <form onSubmit={(event) => void submit(event)}>
        <label htmlFor="rules-question">Ask a rules question</label>
        <input id="rules-question" value={question} onChange={(event) => setQuestion(event.target.value)} maxLength={2000} required />
        <button type="submit" disabled={loading}>Find evidence</button>
      </form>
      {loading ? <p role="status">Finding cited rules evidence…</p> : null}
      {error ? <p role="alert">Rules service unavailable: {error}</p> : null}
      {packet?.status === "no_evidence" ? <p role="status">No evidence found for this question.</p> : null}
      {packet?.status === "insufficient_evidence" ? <p role="status">Only partial evidence is available; it may not answer the question.</p> : null}
      {packet?.status === "rules_space_unavailable" || packet?.status === "downstream_failure" ? (
        <p role="alert">Rules evidence service unavailable. {packet.trace.reason}</p>
      ) : null}
      {packet && packet.evidence.length > 0 ? (
        <div>
          <p>{packet.status === "success" ? "Cited rules evidence" : "Available evidence"}</p>
          <ol>{packet.evidence.map((item) => <Citation key={`${item.evidence_ref_id}:${item.evidence_unit_id}`} item={item} />)}</ol>
        </div>
      ) : null}
    </section>
  );
}
