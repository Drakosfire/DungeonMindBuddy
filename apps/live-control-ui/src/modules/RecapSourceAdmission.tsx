import { useEffect, useRef, useState } from "react";
import type { SavedRecapSource } from "../api/savedRecapRunsApi";
import { admitRecapSource, inspectRecapSource, recapSourceTarget, resumeRecapSource } from "../api/nativeRecapSourceApi";
import type { NativeRecapSourceStatus, RecapSourceTarget } from "../api/nativeRecapSourceApi";

/** Native APP intent/receipt owns recovery; this component retains no second ledger. */
export function RecapSourceAdmission({ source }: { source: SavedRecapSource }) {
  const target = recapSourceTarget(source);
  if (!target) return <section aria-label="Source availability"><p>Source admission is unavailable: this saved source needs an exact revision and matching scope.</p></section>;
  // Remount on any selected source/run/binding change, including A→B→A.
  return <Admission key={JSON.stringify([target, source.run.runId, source.run.runRevision])} target={target} />;
}
function Admission({ target }: { target: RecapSourceTarget }) {
  const [status, setStatus] = useState<NativeRecapSourceStatus | null>(null);
  const [busy, setBusy] = useState(false), [error, setError] = useState<string | null>(null);
  const [uncertain, setUncertain] = useState(false);
  const alive = useRef(true), lock = useRef(false);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  async function run(operation: "admit" | "inspect" | "resume") {
    if (lock.current) return;
    lock.current = true; setBusy(true); setError(null);
    try {
      const result = operation === "admit" ? await admitRecapSource(target)
        : operation === "inspect" ? await inspectRecapSource(target, status!) : await resumeRecapSource(target, status!);
      if (alive.current) { setStatus(result); setUncertain(false); }
    } catch (reason) {
      if (alive.current) {
        setUncertain(true);
        setError(reason instanceof Error ? reason.message : "Source admission could not be checked.");
      }
    } finally { lock.current = false; if (alive.current) setBusy(false); }
  }
  const verified = !uncertain && status?.state === "admitted" && status.admission_committed && status.opening.state === "verified";
  const resumable = !uncertain && status && !status.admission_committed && ["reserved", "conflict", "unknown"].includes(status.state);
  return <section className="module-card" aria-label="Source availability">
    <h3>Source availability</h3>
    <p>Make this exact saved source available as evidence. Extracted facts still need separate review and publication.</p>
    {verified ? <p role="status">Source available as evidence.</p>
      : uncertain ? <p role="status">The latest outcome is unverified here. The request may have completed. Recover this same source request; changing pages does not cancel it.</p>
      : status?.admission_committed ? <p role="status">Source admission committed; its opening is not verified. Refresh the saved operation.</p>
      : status ? <p role="status">{status.state === "unknown" ? "Admission outcome unknown. Refresh its status or deliberately resume this exact saved request."
        : status.state === "conflict" ? "Admission needs a deliberate resume after a conflict."
        : status.state === "dispatching" ? "Admission is in progress. Refresh its saved status."
        : status.state === "reserved" ? "Source admission is saved and waiting to run."
        : "Source admission is unavailable. Refresh its saved status for recovery."}</p>
      : <p>Admission has not been checked here. An existing request for this exact source will be recovered.</p>}
    {error && <p role="alert">{error}</p>}
    {!status && <button type="button" disabled={busy} onClick={() => void run("admit")}>{busy ? "Checking source…" : uncertain ? "Recover source admission" : "Admit source"}</button>}
    {status && <button type="button" disabled={busy} onClick={() => void run("inspect")}>{busy ? "Checking source…" : "Refresh source admission"}</button>}
    {resumable && <button type="button" disabled={busy} onClick={() => void run("resume")}>Resume exact source admission</button>}
    {status?.failure_code && <p>Recorded diagnostic: {status.failure_code}</p>}
    <details><summary>Source details</summary><dl>
      <dt>World / campaign / session</dt><dd>{target.managedWorldId} / {target.campaignId} / {target.session}</dd>
      <dt>Saved source</dt><dd>{target.sourceArtifactId}</dd>
      <dt>Saved revision</dt><dd>{target.sourceRevisionId}</dd>
      {status && <><dt>Admission operation</dt><dd>{status.run_id} · revision {status.run_revision}</dd>
        <dt>Receipt</dt><dd>{status.admission_committed ? "Committed" : "Not confirmed"}</dd>
        <dt>Source opening</dt><dd>{status.opening.state}</dd></>}
    </dl></details>
  </section>;
}
