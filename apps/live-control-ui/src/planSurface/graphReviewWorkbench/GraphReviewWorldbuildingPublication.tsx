import { useEffect, useRef, useState } from "react";
import { ExtractPromoteApiError } from "../../api/extractPromoteApi";
import { LiveApiError, postManagedWorldGraphProjection } from "../../api/liveApi";
import type { ExactRunReviewPackage, ManagedWorldGraphProjectionResponse } from "../../api/types";
import { confirmWorldbuilding, getWorldbuildingCapabilities, prepareWorldbuilding,
  type WorldbuildingDecision, type WorldbuildingPlan, type WorldbuildingReceipt } from "../../api/worldbuildingPublicationApi";
import { useSelectedWorld } from "../../selectedWorld/SelectedWorldContext";
import { GraphReviewFirstWorldPublishSheet } from "./GraphReviewFirstWorldPublishSheet";

import {assertWorldbuildingPlan, clearUnsubmittedWorldbuildingPublication, readWorldbuildingPublicationRecovery,
  saveWorldbuildingPublicationRecovery, setAsideRejectedWorldbuildingPublication} from "./worldbuildingPublicationRecovery";

import {readFirstWorldRecovery} from './firstWorldPublicationRecovery';

type Props = {review: ExactRunReviewPackage; onConfirmInFlightChange?: (busy: boolean) => void; isCurrent?:()=>boolean};

const message = (error: unknown) => error instanceof Error ? error.message : "World publication is unavailable.";

/** Exact-source remount restores only a locally retained request, never a receipt. */
export function GraphReviewWorldbuildingPublication(props: Props) {
  const world = useSelectedWorld();
  const [epoch, setEpoch] = useState(0);
  const scope=JSON.stringify([world.kind,world.kind==='managed'?world.worldId:null,props.review.runId,props.review.sourceRevisionId]);
  const currentScope=useRef(scope);currentScope.current=scope;
  const isCurrent=()=>currentScope.current===scope;
  if (world.kind !== "managed" || props.review.worldId !== world.worldId) {
    return <p role="status">Select the verified World belonging to this exact source to review publication.</p>;
  }
  if (props.review.inspectionStatus !== "ready" || props.review.sourceDomain !== "worldbuilding") return null;
  // Initialization changes eligibility and creates the binding. Recover the
  // original creation request before considering a different publication mode.
  try {
    if(readFirstWorldRecovery(props.review))return <GraphReviewFirstWorldPublishSheet {...props} isCurrent={isCurrent}/>;
  }catch(reason){return <p role="alert">{message(reason)}</p>;}
  return <Publication key={`${world.worldId}:${props.review.runId}:${props.review.sourceArtifactId}:${props.review.sourceRevisionId}:${epoch}`}
    {...props} isCurrent={isCurrent} managedWorldId={world.worldId} onReset={() => setEpoch(n => n + 1)} />;
}
function Publication({review, managedWorldId, onConfirmInFlightChange, onReset, isCurrent}: Props & {managedWorldId: string; onReset: () => void}) {
  const [saved] = useState(() => {
    try { return {recovery: readWorldbuildingPublicationRecovery(review, managedWorldId), error: null}; }
    catch (reason) { return {recovery: null, error: message(reason)}; }
  });
  const [staleParent, setStaleParent] = useState(saved.recovery?.staleParent ?? false);
  const [submitted, setSubmitted] = useState(saved.recovery?.submitted ?? false);
  const [projection, setProjection] = useState<ManagedWorldGraphProjectionResponse | null>(null);
  const [firstWorld, setFirstWorld] = useState(false);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(saved.error);
  const [decisions, setDecisions] = useState<Record<string, WorldbuildingDecision>>(() => Object.fromEntries(
    saved.recovery ? saved.recovery.plan.effect.decisionSnapshot.map(({assertionId, decision, targetNodeId}) =>
      [assertionId, {assertionId, decision, ...(targetNodeId ? {targetNodeId} : {})}]) :
      review.assertions.map(a => [a.assertionId, {assertionId: a.assertionId, decision: "defer"}])));
  const [plan, setPlan] = useState<WorldbuildingPlan | null>(saved.recovery?.plan ?? null);
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
        if (saved.error) throw new Error(saved.error);
        if (saved.recovery) assertWorldbuildingPlan(saved.recovery.plan, review, managedWorldId, p);
        setProjection(p);
        const capability = await getWorldbuildingCapabilities();
        if (cancelled) return;
        if (capability.schema !== "dmb_worldbuilding_publication_capabilities_v1" || !capability.configured
          || capability.confirmationSupported !== true) throw new Error("World publication is not configured.");
        setReady(true);
      } catch (e) {
        if (cancelled) return;
        if (e instanceof LiveApiError && e.code === "native_graph_provisioning_pending"
          && !saved.recovery && !saved.error && review.worldState === "uninitialized" && review.firstWorldPublishEligible === true) setFirstWorld(true);
        else setError(message(e));
      }
    })();
    return () => {cancelled = true; alive.current = false; onConfirmInFlightChange?.(false);};
  }, [managedWorldId, review.worldState, review.firstWorldPublishEligible]);

  if (firstWorld) return <GraphReviewFirstWorldPublishSheet review={review}
    onConfirmInFlightChange={onConfirmInFlightChange} isCurrent={isCurrent} />;
  const busy = phase === "preparing" || phase === "confirming";
  const selected = Object.values(decisions).some(d => ["create_new", "bind_existing", "accept"].includes(d.decision));
  const update = async (id: string, decision: WorldbuildingDecision["decision"], targetNodeId?: string) => {
    if (lock.current || submitted || receipt || saved.error) return;
    if (plan) {
      lock.current = true;
      try { await clearUnsubmittedWorldbuildingPublication(review, managedWorldId, plan); }
      catch (reason) { if (alive.current) setError(message(reason)); return; }
      finally { lock.current = false; }
      if (!alive.current) return;
    }
    setPlan(null); setError(null);
    setDecisions(d => ({...d, [id]: {assertionId: id, decision, ...(targetNodeId ? {targetNodeId} : {})}}));
  };
  async function prepare() {
    if (!ready || !projection || lock.current || !selected || receipt || submitted || saved.error) return;
    lock.current = true; setPhase("preparing"); setError(null); setPlan(null);
    try {
      const result = await prepareWorldbuilding({runId: review.runId,
        expectedParentRevisionId: projection.projection.snapshot.revisionId, dispositions: Object.values(decisions)});
      if (!alive.current) return;
      assertWorldbuildingPlan(result, review, managedWorldId, projection, decisions);
      await saveWorldbuildingPublicationRecovery(review, managedWorldId, result, false);
      if (!alive.current) return;
      setPlan(result);
    } catch (e) { if (alive.current) setError(`${message(e)} No graph publication was confirmed. Review the source and reload this review before preparing again.`); }
    finally {lock.current = false; if (alive.current) setPhase("idle");}
  }
  async function confirm() {
    if (!plan || !ready || !projection || lock.current || receipt || saved.error) return;
    lock.current = true;
    try {
      assertWorldbuildingPlan(plan, review, managedWorldId, projection);
      await saveWorldbuildingPublicationRecovery(review, managedWorldId, plan, true);
    } catch (reason) { lock.current = false; if (alive.current) setError(`${message(reason)} The publication request could not be retained. No request was sent.`); return; }
    if (!alive.current) {lock.current = false; return;}
    setSubmitted(true);
    setPhase("confirming"); setError(null); onConfirmInFlightChange?.(true);
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

    } catch (e) {
      if (alive.current) {
        setPhase("uncertain");
        if (e instanceof ExtractPromoteApiError && e.code === "stale_parent_revision") {
          try {
            await saveWorldbuildingPublicationRecovery(review, managedWorldId, plan, true, true);
            if (!alive.current) return;
            setStaleParent(true);
            setError(`${message(e)} The server rejected the outdated parent. Retain this request before preparing a replacement.`);
          } catch (reason) { setError(`${message(reason)} The rejection could not be saved; retain the original request and retry recovery.`); }
        } else setError(`${message(e)} The publication outcome is unverified. Recover its result by retrying the saved exact confirmation.`);
      }
    }
    finally {lock.current = false; onConfirmInFlightChange?.(false);}
  }
  return <section aria-label="Publish authored material into World" className="graph-review-exact-run-promote">
    <h3>Review for your World</h3>
    <p>Review what to add, connect to existing identities, or leave out. Keep the source’s proposals and historical facts distinct.</p>
    {error ? <p role="alert">{error}</p> : null}
    {staleParent && !receipt ? <button disabled={busy || !ready} onClick={async () => {
      try { await setAsideRejectedWorldbuildingPublication(review, managedWorldId, plan!); if (alive.current) onReset(); }
      catch (reason) { setError(message(reason)); }
    }}>Set aside rejected plan and refresh World</button> : null}
    {submitted && !receipt ? <p>The original publication request is saved. Recover its result without preparing another plan or changing its choices.</p> : null}
    {!projection && !error ? <p role="status">Reading the World’s existing identities…</p> : null}
    {projection ? <>
      <p>Existing World: {managedWorldId}. Review each identity and relationship. Unreviewed items stay deferred.</p>
      <fieldset disabled={!ready || busy || !!receipt || submitted || !!saved.error}>
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
        <button disabled={!ready || busy || !selected || submitted || !!saved.error
          || Object.values(decisions).some(d => d.decision === "bind_existing" && !d.targetNodeId)} onClick={() => void prepare()}>
          {phase === "preparing" ? "Preparing…" : "Prepare proposed changes"}</button>
      </> : null}
    </> : null}
    {plan && !receipt ? <>
      <h4>Proposed graph change</h4>
      <p>{plan.summary.createNewNodeCount} new identities; {plan.summary.bindExistingNodeCount} existing identities; {plan.summary.acceptedEdgeCount} relationships; {plan.summary.deferredCandidateCount} deferred.</p>
      <details><summary>Inspect the exact plan</summary><pre style={{whiteSpace: "pre-wrap", overflowWrap: "anywhere"}}>{JSON.stringify(plan, null, 2)}</pre></details>
      <button disabled={!ready || busy || !!saved.error || plan.summary.acceptedAssertionCount === 0} onClick={() => void confirm()}>{phase === "confirming" ? "Publishing…" : submitted ? "Recover publication result" : "Confirm publication"}</button>
    </> : null}
    {receipt ? <p role="status">{receipt.outcome === "published_audit_degraded" ? "Published with an audit warning" : "Publication recorded"}: {receipt.appliedAssertionCount} assertions · revision {receipt.committedRevisionId}. {receipt.warnings.join(" ")}</p> : null}
  </section>;
}
