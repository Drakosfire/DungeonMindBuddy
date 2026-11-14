import {getNativeWorldbuildingContext, prepareNativeWorldbuilding, type NativeWorldbuildingConfirmation} from "../../api/nativeWorldbuildingPublicationApi";
import {submitNativeWorldbuildingConfirmation} from "./worldbuildingPublicationRecovery";
import {CandidateReviewSemantics} from './CandidateReviewSemantics';
import { useEffect, useRef, useState } from "react";
import { ExtractPromoteApiError } from "../../api/extractPromoteApi";
import { LiveApiError, postManagedWorldGraphProjection } from "../../api/liveApi";
import type { ExactRunReviewPackage, ManagedWorldGraphProjectionResponse } from "../../api/types";
import { confirmWorldbuilding, getWorldbuildingCapabilities, prepareWorldbuilding,
  type WorldbuildingDecision, type WorldbuildingPlan, type WorldbuildingReceipt } from "../../api/worldbuildingPublicationApi";
import { useSelectedWorld } from "../../selectedWorld/SelectedWorldContext";
import { GraphReviewFirstWorldPublishSheet } from "./GraphReviewFirstWorldPublishSheet";

import {assertWorldbuildingPlan, clearUnsubmittedWorldbuildingPublication, readWorldbuildingPublicationRecovery,
  readNativeWorldbuildingPublicationRecovery, retryNativeWorldbuildingConfirmation,
  saveWorldbuildingPublicationRecovery, setAsideRejectedWorldbuildingPublication} from "./worldbuildingPublicationRecovery";

import {obsoleteUnsubmittedRecovery,readFirstWorldRecovery} from './firstWorldPublicationRecovery';

type Props = {review: ExactRunReviewPackage; onConfirmInFlightChange?: (busy: boolean) => void; isCurrent?:()=>boolean};

const message = (error: unknown) => error instanceof Error ? error.message : "World publication is unavailable.";

/** Exact-source remount restores only a locally retained request, never a receipt. */
export function GraphReviewWorldbuildingPublication(props: Props) {
  const world = useSelectedWorld();
  const [epoch, setEpoch] = useState(0);
  const scope=JSON.stringify([world.kind,world.kind==='managed'?world.worldId:null,props.review.runId,props.review.sourceArtifactId,props.review.sourceRevisionId]);
  const currentScope=useRef(scope);currentScope.current=scope;
  const isCurrent=()=>currentScope.current===scope&&(props.isCurrent?.()??true);
  if (world.kind !== "managed" || props.review.worldId !== world.worldId) {
    return <p role="status">Select the verified World belonging to this exact source to review publication.</p>;
  }
  if (props.review.inspectionStatus !== "ready" || props.review.sourceDomain !== "worldbuilding") return null;
  return <PublicationEntry key={`${scope}:${epoch}`} {...props} isCurrent={isCurrent}
    managedWorldId={world.worldId} onReset={() => setEpoch(n => n + 1)} />;
}
function PublicationEntry(props: Props & {managedWorldId: string; onReset: () => void}) {
  // Choose the route once on entry to this exact source scope. A newly saved
  // creation request must not reparent an in-flight sheet on a busy/status
  // update and discard its actual receipt. True remounts still recover explicitly.
  const [entry] = useState(() => {
    try { return {creation: readFirstWorldRecovery(props.review) !== null, error: null}; }
    catch (reason) { return {creation: obsoleteUnsubmittedRecovery(props.review)!==null, error: message(reason)}; }
  });
  if (entry.creation) return <GraphReviewFirstWorldPublishSheet {...props}/>;
  if (entry.error) return <p role="alert">{entry.error}</p>;
  return <ExistingWorldPublication {...props}/>;
}

function ExistingWorldPublication(props: Props & {managedWorldId: string; onReset: () => void}) {
  const [saved] = useState(() => {
    try {
      return {packet: readNativeWorldbuildingPublicationRecovery(props.review, props.managedWorldId, {allowClassic: true}), error: null};
    } catch (reason) {
      return {packet: null, error: message(reason)};
    }
  });
  if (saved.error) return <p role="alert">{saved.error}</p>;
  if (saved.packet) return <NativePublicationRecovery {...props}/>;
  if (import.meta.env.VITE_NATIVE_WORLDBUILDING_WORLD === props.managedWorldId &&
      !readWorldbuildingPublicationRecovery(props.review, props.managedWorldId)) {
    return <NativePublication {...props}/>;
  }
  return <Publication {...props}/>;
}

function NativePublicationRecovery({review, managedWorldId, isCurrent, onConfirmInFlightChange}: Props & {managedWorldId: string}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [committed, setCommitted] = useState(false);
  const lock = useRef(false);
  async function retry() {
    if (lock.current || committed || isCurrent?.() === false) return;
    lock.current = true;
    setBusy(true);
    setError(null);
    onConfirmInFlightChange?.(true);
    try {
      await retryNativeWorldbuildingConfirmation(review, managedWorldId);
      if (isCurrent?.() !== false) setCommitted(true);
    } catch (reason) {
      if (isCurrent?.() !== false) setError(message(reason));
    } finally {
      lock.current = false;
      if (isCurrent?.() !== false) setBusy(false);
      onConfirmInFlightChange?.(false);
    }
  }
  return <section aria-label="Native Worldbuilding publication recovery">
    {committed ? <p role="status">Worldbuilding publication confirmed.</p> :
      <button type="button" disabled={busy} onClick={() => void retry()}>
        Retry saved publication
      </button>}
    {error && <p role="alert">{error}</p>}
  </section>;
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
          <p><CandidateReviewSemantics assertion={a} assertions={review.assertions}/></p>
          {a.kind === 'object' ? <p>{a.summary}</p> : null}
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


function NativePublication({review, managedWorldId, isCurrent, onConfirmInFlightChange}: Props & {managedWorldId: string}) {
  const [context, setContext] = useState<Awaited<ReturnType<typeof getNativeWorldbuildingContext>>>();
  const [selection, setSelection] = useState({record: "", fields: [] as string[], support: ""});
  const [existingId, setExistingId] = useState("");
  const [bindExisting, setBindExisting] = useState(false);
  const [packet, setPacket] = useState<NativeWorldbuildingConfirmation>();
  const [error, setError] = useState<string>();
  const [committed, setCommitted] = useState(false);
  const [busy, setBusy] = useState(false);
  const lock = useRef(false);
  useEffect(() => {
    let active = true;
    void getNativeWorldbuildingContext({
      managed_world_id: managedWorldId, run_id: review.runId,
      source_artifact_id: review.sourceArtifactId, source_sha256: review.sourceRevisionId.slice(7),
    }).then(value => { if (active) setContext(value); })
      .catch(reason => { if (active) setError(message(reason)); });
    return () => { active = false; };
  }, [managedWorldId, review.runId, review.sourceArtifactId, review.sourceRevisionId]);
  const records = context?.records.filter(row => row && typeof row === "object" && !Array.isArray(row) && row.kind === "node") ?? [];
  const record = records.find(row => row && typeof row === "object" && !Array.isArray(row) && row.record_id === selection.record);
  async function run(confirm: boolean) {
    if (!context || lock.current || isCurrent?.() === false) return;
    lock.current = true;
    setBusy(true);
    setError(undefined);
    if (confirm) onConfirmInFlightChange?.(true);
    try {
      if (confirm && packet) {
        await submitNativeWorldbuildingConfirmation(review, managedWorldId, packet);
        if (isCurrent?.() !== false) setCommitted(true);
      } else if (!confirm && selection.record && selection.fields.length && selection.support && (!bindExisting || existingId.trim())) {
        const result = await prepareNativeWorldbuilding({
          ...context.prepareCoordinates,
          selections: [{
            kind: "node", record_id: selection.record, action: bindExisting ? "use_existing" : "create",
            ...(bindExisting ? {entity_id: existingId.trim()} : {}),
            facts: selection.fields.map(field => ({ field, metadata: {
              evidence_ref_ids: [selection.support],
              visibility: { kind: "labels_any", labels: ["dungeonbuddy.visibility:gm"] },
              epistemic_basis: "asserted", claim_mode: "dungeonbuddy.claim:fact",
              standing: "provisional", temporal_scope: { kind: "timeless" },
            }})),
          }],
        });
        if (isCurrent?.() !== false) {
          if (result.status === "prepared") setPacket(result.confirmation);
          else setError("The selected fact was held. Nothing was published.");
        }
      }
    } catch (reason) {
      if (isCurrent?.() !== false) setError(message(reason));
    } finally {
      lock.current = false;
      setBusy(false);
      if (confirm) onConfirmInFlightChange?.(false);
    }
  }
  const fields = record && typeof record === "object" && !Array.isArray(record) ? record.fields : null;
  return <section aria-label="Native Worldbuilding review">
    {error && <p role="alert">{error}</p>}
    {committed ? <p role="status">Worldbuilding publication confirmed.</p> :
      packet ? <button type="button" disabled={busy} onClick={() => void run(true)}>Confirm native publication</button> :
      context ? <fieldset disabled={busy}>
        <legend>Review provisional GM facts</legend>
        <label>Candidate object<select value={selection.record} onChange={event =>
          setSelection({record: event.target.value, fields: [] as string[], support: ""})}>
          <option value="">Choose an object</option>
          {records.map(row => row && typeof row === "object" && !Array.isArray(row) &&
            <option key={String(row.record_id)} value={String(row.record_id)}>{String(row.label ?? row.record_id)}</option>)}
        </select></label>
        <label>Object action<select value={bindExisting ? "existing" : "new"} onChange={event =>
          setBindExisting(event.target.value === "existing")}>
          <option value="new">Create object</option>
          <option value="existing">Bind existing object</option>
        </select></label>
        {bindExisting && <label>Existing object ID<input value={existingId}
          onChange={event => setExistingId(event.target.value)} /></label>}
        <label>Facts<select multiple value={selection.fields} onChange={event =>
          setSelection({...selection, fields: Array.from(event.target.selectedOptions, option => option.value)})}>
          {fields && Object.entries(fields).filter(([field]) => ["label", "node_type", "description"].includes(field))
            .map(([field, value]) => <option key={field} value={field}>{field}: {String(value)}</option>)}
        </select></label>
        <label>Supporting excerpt<select value={selection.support} onChange={event =>
          setSelection({...selection, support: event.target.value})}>
          <option value="">Choose exact source evidence</option>
          {context.sourceSupport.map(row => row && typeof row === "object" && !Array.isArray(row) &&
            <option key={String(row.evidence_ref_id)} value={String(row.evidence_ref_id)}>{String(row.text)}</option>)}
        </select></label>
        <button type="button" disabled={!selection.record || !selection.fields.length || !selection.support || (bindExisting && !existingId.trim())}
          onClick={() => void run(false)}>Prepare selected facts</button>
      </fieldset> : !error && <p role="status">Loading saved Worldbuilding review…</p>}
  </section>;
}
