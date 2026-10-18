import { useEffect, useRef, useState } from "react";
import { LiveApiError, postManagedWorldGraphProjection } from "../../api/liveApi";
import type { ExactRunReviewPackage, ManagedWorldGraphProjectionResponse } from "../../api/types";
import { confirmWorldbuilding, getWorldbuildingCapabilities, prepareWorldbuilding,
  type WorldbuildingDecision, type WorldbuildingPlan, type WorldbuildingReceipt } from "../../api/worldbuildingPublicationApi";
import { useSelectedWorld } from "../../selectedWorld/SelectedWorldContext";
import { GraphReviewFirstWorldPublishSheet } from "./GraphReviewFirstWorldPublishSheet";

type Props = {review: ExactRunReviewPackage; onConfirmInFlightChange?: (busy: boolean) => void;
  onCatalogRefresh?: () => void | Promise<void>};
const digest = (value: unknown) => typeof value === "string" && /^sha256:[a-f0-9]{64}$/.test(value);
const message = (error: unknown) => error instanceof Error ? error.message : "World publication is unavailable.";

/** Changing exact source or selected World destroys all transient decisions and plans. */
export function GraphReviewWorldbuildingPublication(props: Props) {
  const world = useSelectedWorld();
  if (world.kind !== "managed" || props.review.worldId !== world.worldId) {
    return <p role="status">Select the verified World belonging to this exact source to review publication.</p>;
  }
  if (props.review.inspectionStatus !== "ready" || props.review.sourceDomain !== "worldbuilding") return null;
  return <Publication key={`${world.worldId}:${props.review.runId}:${props.review.sourceArtifactId}:${props.review.sourceRevisionId}`}
    {...props} managedWorldId={world.worldId} />;
}
function Publication({review, managedWorldId, onConfirmInFlightChange, onCatalogRefresh}: Props & {managedWorldId: string}) {
  const [projection, setProjection] = useState<ManagedWorldGraphProjectionResponse | null>(null);
  const [firstWorld, setFirstWorld] = useState(false);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [decisions, setDecisions] = useState<Record<string, WorldbuildingDecision>>(() => Object.fromEntries(
    review.assertions.map(a => [a.assertionId, {assertionId: a.assertionId, decision: "defer"}])));
  const [plan, setPlan] = useState<WorldbuildingPlan | null>(null);
  const [receipt, setReceipt] = useState<WorldbuildingReceipt | null>(null);
  const [phase, setPhase] = useState<"idle" | "preparing" | "confirming" | "uncertain">("idle");
  const alive = useRef(true);
  const lock = useRef(false);
  useEffect(() => {
    alive.current = true;
    let cancelled = false;
    void (async () => {
      try {
        const p = await postManagedWorldGraphProjection({schema: "dmb_managed_world_graph_projection_request_v1", managedWorldId});
        if (cancelled) return;
        if (p.managedWorldId !== managedWorldId || p.nativeWorldId !== p.projection.snapshot.worldId
          || !p.projection.snapshot.isHead || p.projection.snapshot.revisionId !== p.projection.snapshot.headRevisionId) {
          throw new Error("The World projection binding could not be verified.");
        }
        setProjection(p);
        const capability = await getWorldbuildingCapabilities();
        if (cancelled) return;
        if (capability.schema !== "dmb_worldbuilding_publication_capabilities_v1" || !capability.configured
          || capability.confirmationSupported !== true) throw new Error("World publication is not configured.");
        setReady(true);
      } catch (e) {
        if (cancelled) return;
        if (e instanceof LiveApiError && e.code === "native_graph_binding_missing"
          && review.worldState === "uninitialized" && review.firstWorldPublishEligible === true) setFirstWorld(true);
        else setError(message(e));
      }
    })();
    return () => {cancelled = true; alive.current = false;};
  }, [managedWorldId, review.worldState, review.firstWorldPublishEligible]);

  if (firstWorld) return <GraphReviewFirstWorldPublishSheet review={review}
    onConfirmInFlightChange={onConfirmInFlightChange} onCatalogRefresh={onCatalogRefresh} />;
  const busy = phase === "preparing" || phase === "confirming";
  const selected = Object.values(decisions).some(d => ["create_new", "bind_existing", "accept"].includes(d.decision));
  const update = (id: string, decision: WorldbuildingDecision["decision"], targetNodeId?: string) => {
    if (lock.current || phase === "uncertain" || receipt) return;
    setPlan(null); setError(null);
    setDecisions(d => ({...d, [id]: {assertionId: id, decision, ...(targetNodeId ? {targetNodeId} : {})}}));
  };
  async function prepare() {
    if (!ready || !projection || lock.current || !selected || receipt || phase === "uncertain") return;
    lock.current = true; setPhase("preparing"); setError(null); setPlan(null);
    try {
      const result = await prepareWorldbuilding({runId: review.runId,
        expectedParentRevisionId: projection.projection.snapshot.revisionId, dispositions: Object.values(decisions)});
      if (!alive.current) return;
      const binding = result.publicationBinding;
      const snapshot = result.effect?.decisionSnapshot;
      if (result.schema !== "dmb_worldbuilding_write_plan_v2" || result.version !== 2
        || !result.planId || !digest(result.planDigest) || !digest(result.decisionDigest)
        || !result.summary || !Object.values(result.summary).every(n => Number.isInteger(n) && n >= 0)
        || !Array.isArray(result.effect?.acceptedProposals) || !Array.isArray(result.diagnostics)
        || result.runId !== review.runId || result.sourceArtifactId !== review.sourceArtifactId
        || result.sourceRevisionId !== review.sourceRevisionId || result.worldId !== projection.nativeWorldId
        || result.parentRevisionId !== projection.projection.snapshot.revisionId || !result.prepareBinding
        || binding?.managedWorldId !== managedWorldId || binding.nativeWorldId !== projection.nativeWorldId
        || binding.bindingVersion !== projection.bindingVersion || binding.sourceArtifactId !== review.sourceArtifactId
        || !digest(review.sourceRevisionId) || binding.sourceSha256 !== review.sourceRevisionId.slice(7)
        || typeof binding.documentId !== "string" || !binding.documentId.trim()
        || !Number.isSafeInteger(binding.documentRevision) || binding.documentRevision <= 0
        || !Array.isArray(snapshot) || snapshot.length !== review.assertions.length
        || snapshot.some(d => { const expected = decisions[d.assertionId]; return !expected
          || d.decision !== expected.decision || (d.targetNodeId ?? undefined) !== expected.targetNodeId; })
        || new Set(snapshot.map(d => d.assertionId)).size !== snapshot.length) {
        throw new Error("The prepared plan does not match this exact source, World or reviewed choices.");
      }
      setPlan(result);
    } catch (e) { if (alive.current) setError(`${message(e)} No graph publication was confirmed. Review the source and reload this review before preparing again.`); }
    finally {lock.current = false; if (alive.current) setPhase("idle");}
  }
  async function confirm() {
    if (!plan || lock.current || receipt || phase === "uncertain") return;
    lock.current = true; setPhase("confirming"); setError(null); onConfirmInFlightChange?.(true);
    try {
      const result = await confirmWorldbuilding(plan);
      if (!alive.current) return;
      if (result.schema !== "dmb_worldbuilding_write_plan_confirm_v1" || result.planId !== plan.planId
        || result.planDigest !== plan.planDigest || result.decisionDigest !== plan.decisionDigest
        || result.worldId !== plan.worldId || result.parentRevisionId !== plan.parentRevisionId
        || !result.committedRevisionId || !Array.isArray(result.warnings)
        || !Number.isInteger(result.appliedAssertionCount) || result.appliedAssertionCount < 0
        || !["ok", "degraded"].includes(result.auditStatus) || !["committed", "already_applied", "published_audit_degraded"].includes(result.outcome)) {
        throw new Error("The publication receipt could not be verified.");
      }
      setReceipt(result); setPhase("idle");
      void Promise.resolve().then(() => onCatalogRefresh?.()).catch(() => {
        if (alive.current) setError("Publication is recorded, but the run list could not refresh.");
      });
    } catch (e) {if (alive.current) {setPhase("uncertain"); setError(`${message(e)} The publication outcome is unverified. Check World history before sending another publication.`);}}
    finally {lock.current = false; onConfirmInFlightChange?.(false);}
  }
  return <section aria-label="Publish authored material into World" className="graph-review-exact-run-promote">
    <h3>Review for your World</h3>
    <p>Review what to add, connect to existing identities, or leave out. Keep the source’s proposals and historical facts distinct.</p>
    {error ? <p role="alert">{error}</p> : null}
    {!projection && !error ? <p role="status">Reading the World’s existing identities…</p> : null}
    {projection ? <>
      <p>Existing World: {managedWorldId}. Review each identity and relationship. Unreviewed items stay deferred.</p>
      <fieldset disabled={!ready || busy || !!receipt || phase === "uncertain"}>
        <legend>Publication choices</legend>
        {review.assertions.map(a => <details key={a.assertionId}>
          <summary>{a.label} · {decisions[a.assertionId].decision}</summary>
          <p>{a.summary}</p>
          {a.evidence.map((e, i) => <blockquote key={i}>{e.anchorQuotes.join("\n")}</blockquote>)}
          <label>Decision for {a.label}<select value={decisions[a.assertionId].decision}
            onChange={e => update(a.assertionId, e.target.value as WorldbuildingDecision["decision"])}>
            <option value="defer">Defer</option><option value="reject">Omit</option>
            {a.kind === "object" ? <><option value="create_new">Create a new identity</option><option value="bind_existing">Use an existing identity</option></>
              : <option value="accept">Accept relationship</option>}
          </select></label>
          {decisions[a.assertionId].decision === "bind_existing" ? <label>Existing identity for {a.label}
            <select value={decisions[a.assertionId].targetNodeId ?? ""}
              onChange={e => update(a.assertionId, "bind_existing", e.target.value)}>
              <option value="">Choose an identity</option>
              {projection.projection.nodes.map(n => <option key={n.nodeId} value={n.nodeId}>{n.label} · {n.kind} · {n.nodeId}</option>)}
            </select></label> : null}
        </details>)}
      </fieldset>
      {!receipt && !plan ? <>
        <p>Preparing records exact source provenance and seals these choices. It does not publish graph facts.</p>
        <button disabled={!ready || busy || !selected || phase === "uncertain"
          || Object.values(decisions).some(d => d.decision === "bind_existing" && !d.targetNodeId)} onClick={() => void prepare()}>
          {phase === "preparing" ? "Preparing…" : "Prepare proposed changes"}</button>
      </> : null}
    </> : null}
    {plan && !receipt ? <>
      <h4>Proposed graph change</h4>
      <p>{plan.summary.createNewNodeCount} new identities; {plan.summary.bindExistingNodeCount} existing identities; {plan.summary.acceptedEdgeCount} relationships; {plan.summary.deferredCandidateCount} deferred.</p>
      <details><summary>Inspect the exact plan</summary><pre style={{whiteSpace: "pre-wrap", overflowWrap: "anywhere"}}>{JSON.stringify(plan, null, 2)}</pre></details>
      <button disabled={busy || phase === "uncertain" || plan.summary.acceptedAssertionCount === 0} onClick={() => void confirm()}>{phase === "confirming" ? "Publishing…" : "Confirm publication"}</button>
    </> : null}
    {receipt ? <p role="status">{receipt.outcome === "published_audit_degraded" ? "Published with an audit warning" : "Publication recorded"}: {receipt.appliedAssertionCount} assertions · revision {receipt.committedRevisionId}. {receipt.warnings.join(" ")}</p> : null}
  </section>;
}
