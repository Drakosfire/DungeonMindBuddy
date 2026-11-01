import { useEffect, useRef, useState } from "react";
import type { ExactRunCandidateProjection } from "../../api/exactRunCandidateProjectionApi";
import { getRecapNativeReview, type RecapNativeReview } from "../../api/recapNativeReviewApi";

export function CandidateNativeReview({ projection: p, nodeId }: { projection: ExactRunCandidateProjection; nodeId: string }) {
  if (p.runStatus !== "reviewable") return <p>World comparison is available for reviewable extractions. This saved extraction is {p.runStatus}.</p>;
  const key = JSON.stringify([p.runId, p.runRevision, p.sourceArtifactId, p.sourceSha256, p.candidateSha256, p.spanIndexSha256,
    p.managedWorldId, p.nativeWorldId, p.bindingVersion, p.campaignId, p.sessionId, nodeId]);
  return <Comparison key={key} projection={p} nodeId={nodeId} />;
}
function Comparison({ projection, nodeId }: { projection: ExactRunCandidateProjection; nodeId: string }) {
  const [review, setReview] = useState<RecapNativeReview | null>(null), [error, setError] = useState<string | null>(null), [busy, setBusy] = useState(false);
  const alive = useRef(true), pending = useRef<AbortController | null>(null);
  useEffect(() => { alive.current = true; return () => { alive.current = false; pending.current?.abort(); }; }, []);
  async function inspect() {
    if (pending.current) return;
    const controller = new AbortController(); pending.current = controller;
    setBusy(true); setError(null); setReview(null);
    try {
      const next = await getRecapNativeReview(projection, nodeId, controller.signal);
      if (alive.current) setReview(next);
    } catch (reason) {
      if (alive.current) setError(reason instanceof Error ? reason.message : "World comparison could not be opened.");
    } finally {
      if (pending.current === controller) pending.current = null;
      if (alive.current) setBusy(false);
    }
  }
  const native = review?.native_context;
  const admission = native?.source_admission;
  const verified = admission?.state === "admitted" && admission.opening_state === "verified";
  const identities = native?.selections.find(s => s.candidate_node_id === nodeId)?.alternatives ?? [];
  return <section aria-label="World comparison">
    <h4>Compare with World</h4>
    <p>Compare available source passages with the candidate’s pinned evidence before accepting it.</p>
    <button type="button" disabled={busy} onClick={() => void inspect()}>{busy ? "Comparing…" : review ? "Refresh comparison" : "Compare with World"}</button>
    {busy && <p role="status">Opening the current World comparison…</p>}
    {error && <p role="alert">{error}</p>}
    {native && <>
      {!verified ? <p role="status">{admission?.state === "not_found" ? "This saved source is not available for comparison yet. Use View saved source to check its availability."
        : "Source availability is not verified. Use View saved source to check it."}</p>
        : <p role="status">{native.source_evidence.length ? `${native.source_evidence.length} source passages listed for review.` : "No support passages are available for this saved source."}</p>}
      <p>This comparison does not approve claims or choose an existing identity.</p>
      {native.source_evidence.map((row, index) => <details key={row.evidence_ref_id}>
        <summary>Passage {index + 1}{row.opening.status === "unavailable" ? " · unavailable" : ""}</summary>
        {row.opening.status === "available" ? <blockquote style={{ whiteSpace: "pre-wrap" }}>{row.opening.span_text}</blockquote>
          : <p>This passage could not be opened.</p>}
      </details>)}
      <details><summary>Possible existing identities ({identities.length})</summary>
        <p>These are advisory matches. Their other sources are not support for this candidate.</p>
        {identities.length ? <ul>{identities.map(a => <li key={a.entity_id}>{a.entity_id} · needs review</li>)}</ul>
          : <p>No existing identity matches were found.</p>}
      </details>
      <details><summary>Comparison details</summary><dl>
        <dt>Saved source revision</dt><dd>{review.source_revision_id}</dd>
        <dt>World revision</dt><dd>{native.revision_id}</dd>
        <dt>Source authority version</dt><dd>{native.source_authority_epoch}</dd>
        <dt>Domain</dt><dd>{native.domain_contract_ref.domain_id} · {native.domain_contract_ref.domain_revision}</dd>
        <dt>Profile</dt><dd>{native.semantic_profile_ref.profile_id} · {native.semantic_profile_ref.profile_revision}</dd>
      </dl></details>
    </>}
  </section>;
}
