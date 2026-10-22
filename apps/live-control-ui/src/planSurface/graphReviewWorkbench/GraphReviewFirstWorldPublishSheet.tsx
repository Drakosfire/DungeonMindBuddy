import {CandidateReviewSemantics} from './CandidateReviewSemantics';
import {relationshipEndpoints, hasReviewSemantics, candidateSemanticDescription} from './candidateReviewSemantics';
import { useEffect, useMemo, useRef, useState } from "react";

import {
  ExtractPromoteApiError,
  confirmFirstWorldGraph,
  prepareFirstWorldGraph,
} from "../../api/extractPromoteApi";
import type {
  ExactRunReviewAssertion,
  ExactRunReviewPackage,
  FirstWorldDecision,
  FirstWorldDisposition,
  FirstWorldGraphConfirmReceipt,
  FirstWorldGraphPlan,
  FirstWorldConfirmNonapplication,
} from "../../api/types";

import {assertFirstWorldPlan,assertFirstWorldReceipt,firstWorldDecisions,firstWorldScope,
  obsoleteUnsubmittedRecovery,archiveObsoleteUnsubmittedRecovery,readFirstWorldRecovery,saveFirstWorldRecovery,firstWorldNonapplication,releaseFirstWorldRecovery,type FirstWorldRecovery} from './firstWorldPublicationRecovery';

export interface GraphReviewFirstWorldPublishSheetProps {
  review: ExactRunReviewPackage;
  onConfirmInFlightChange?: (inFlight: boolean) => void;
  isCurrent?: () => boolean;
}

type PublishPhase =
  | "idle"
  | "publishing"
  | "receipt"
  | "pre_commit_error"
  | "unknown_result";

function formatWorldDisplayName(worldId: string): string {
  return worldId
    .split("-")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function isEvidenceBacked(assertion: ExactRunReviewAssertion): boolean {
  return assertion.evidence.length > 0;
}

function buildInitialKeepState(assertions: ExactRunReviewAssertion[]): Map<string, boolean> {
  const objectKeep = new Map<string, boolean>();
  for (const assertion of assertions) {
    if (assertion.kind === "object") {
      objectKeep.set(assertion.assertionId, isEvidenceBacked(assertion) && hasReviewSemantics(assertion, assertions));
    }
  }

  const keep = new Map<string, boolean>();
  for (const assertion of assertions) {
    if (assertion.kind === "object") {
      keep.set(assertion.assertionId, objectKeep.get(assertion.assertionId) ?? false);
      continue;
    }
    const endpoints = relationshipEndpoints(assertion);
    const endpointsKept =
      endpoints != null
      && (objectKeep.get(endpoints[0]) ?? false)
      && (objectKeep.get(endpoints[1]) ?? false);
    keep.set(
      assertion.assertionId,
      isEvidenceBacked(assertion) && hasReviewSemantics(assertion, assertions) && endpointsKept,
    );
  }
  return keep;
}

function relationshipEndpointIds(
  assertion: ExactRunReviewAssertion,
): [string, string] | null {
  if (assertion.kind !== "relationship") return null;
  return relationshipEndpoints(assertion);
}

function isRelationshipBlocked(
  assertion: ExactRunReviewAssertion,
  keepByAssertionId: Map<string, boolean>,
): boolean {
  const endpoints = relationshipEndpointIds(assertion);
  if (!endpoints) return false;
  return !keepByAssertionId.get(endpoints[0]) || !keepByAssertionId.get(endpoints[1]);
}

export function buildFirstWorldDecisions(
  assertions: ExactRunReviewAssertion[],
  keepByAssertionId: Map<string, boolean>,
): FirstWorldDisposition[] {
  return assertions.map((assertion) => {
    const keep = keepByAssertionId.get(assertion.assertionId) ?? false;
    let decision: FirstWorldDecision = "reject";
    if (keep) {
      decision = assertion.kind === "object" ? "create_new" : "accept";
    }
    return {
      assertionId: assertion.assertionId,
      decision,
    };
  });
}

function countKeptDecisions(
  assertions: ExactRunReviewAssertion[],
  keepByAssertionId: Map<string, boolean>,
): number {
  return assertions.filter((assertion) => keepByAssertionId.get(assertion.assertionId)).length;
}

function outcomeLabel(outcome: FirstWorldGraphConfirmReceipt["outcome"]): string {
  switch (outcome) {
    case "initialized":
      return "World Graph created";
    case "already_initialized":
      return "World Graph already exists";
    case "published_audit_degraded":
      return "World Graph created with degraded audit";
    default:
      return outcome;
  }
}

function publishErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return "Failed to create World Graph.";
}

/**
 * First-world keep/reject review for exact worldbuilding runs (CR02A).
 */
export function GraphReviewFirstWorldPublishSheet(props:GraphReviewFirstWorldPublishSheetProps){
  const scope=firstWorldScope(props.review),currentScope=useRef(scope);currentScope.current=scope;
  const [epoch,setEpoch]=useState(0);
  const isCurrent=()=>currentScope.current===scope&&(props.isCurrent?.()??true);
  let saved:FirstWorldRecovery|null;
  try {saved=readFirstWorldRecovery(props.review);}
  catch(reason){return <ObsoleteCreationRecovery key={`${scope}:${epoch}`} review={props.review}
    message={publishErrorMessage(reason)} isCurrent={isCurrent} onArchived={()=>setEpoch(n=>n+1)}/>;}
  if(props.review.firstWorldPublishEligible!==true&&!saved)return null;
  return <FirstWorldPublish key={`${scope}:${epoch}`} {...props} saved={saved}
    isScopeCurrent={()=>currentScope.current===scope&&(props.isCurrent?.()??true)}/>;
}
function ObsoleteCreationRecovery({review,message,isCurrent,onArchived}: {
  review:ExactRunReviewPackage;message:string;isCurrent:()=>boolean;onArchived:()=>void;
}) {
  const [raw]=useState(()=>obsoleteUnsubmittedRecovery(review));
  const [error,setError]=useState<string|null>(null),[busy,setBusy]=useState(false);
  const alive=useRef(true),locked=useRef(false);
  useEffect(()=>{alive.current=true;return()=>{alive.current=false;};},[]);
  const archive=async()=>{
    if(!raw||locked.current)return;
    locked.current=true;setBusy(true);
    try {await archiveObsoleteUnsubmittedRecovery(review,raw,()=>alive.current&&isCurrent());
      if(alive.current&&isCurrent())onArchived();
    } catch(reason){if(alive.current)setError(publishErrorMessage(reason));}
    finally{locked.current=false;if(alive.current)setBusy(false);}
  };
  return <section><p role="alert">{error??message}</p>{raw?<>
    <p>This plan was never submitted. Archive it to review the source again. No publication will be sent.</p>
    <button disabled={busy} onClick={()=>void archive()}>Archive old plan and review again</button>
  </>:null}</section>;
}
function FirstWorldPublish({review,onConfirmInFlightChange,saved,isScopeCurrent}:GraphReviewFirstWorldPublishSheetProps&{
  saved:FirstWorldRecovery|null;isScopeCurrent:()=>boolean;
}){
  const worldId = review.worldId?.trim() ?? "";
  const worldDisplayName = worldId ? formatWorldDisplayName(worldId) : "this world";

  const [keepByAssertionId, setKeepByAssertionId] = useState<Map<string, boolean>>(() =>
    saved?new Map(firstWorldDecisions(saved.plan).map(row=>[row.assertionId,row.decision!=='reject'])):buildInitialKeepState(review.assertions),
  );
  const [publishPhase, setPublishPhase] = useState<PublishPhase>(saved?"unknown_result":"idle");
  const [sealedPlan, setSealedPlan] = useState<FirstWorldGraphPlan | null>(saved?.plan??null);
  const [receipt, setReceipt] = useState<FirstWorldGraphConfirmReceipt | null>(null);
  const [publishError, setPublishError] = useState<string | null>(null);
  const [nonapplication, setNonapplication] = useState<FirstWorldConfirmNonapplication | null>(null);
  const [failure, setFailure] = useState<Record<string, unknown> | null>(null);
  const rememberFailure = (error: unknown, plan?: FirstWorldGraphPlan) => {
    if (error instanceof ExtractPromoteApiError) {
      const payload=error.body?.failureResult;
      if (payload && ['dmb_first_world_preflight_failure_v1','dmb_first_world_confirm_not_invoked_v1'].includes(String(payload.schema))
        && payload.failure && typeof payload.failure==='object' && !Array.isArray(payload.failure))
        setFailure(payload.failure as Record<string,unknown>);
    }
    if (plan) setNonapplication(firstWorldNonapplication(error,plan));
  };
  const returnToReview = async () => {
    if (!sealedPlan || !nonapplication || lock.current || !current()) return;
    lock.current=true;
    try {
      await releaseFirstWorldRecovery(review,sealedPlan,nonapplication,current);
      if (!current()) return;
      setSealedPlan(null);setNonapplication(null);setPublishPhase('pre_commit_error');
      setPublishError('This confirm did not call initialization. Your choices are retained; explicitly review the invalid relationships before retrying.');
    } catch(error) {if(current())setPublishError(publishErrorMessage(error));}
    finally {lock.current=false;}
  };

  const alive=useRef(true),lock=useRef(false);
  useEffect(()=>{alive.current=true;return()=>{alive.current=false;};},[]);
  const current=()=>alive.current&&isScopeCurrent();
  const publishing = publishPhase === "publishing";
  const hasTerminalReceipt = receipt != null;
  const selectionLocked = publishing || hasTerminalReceipt || sealedPlan!==null;
  const keptCount = useMemo(
    () => countKeptDecisions(review.assertions, keepByAssertionId),
    [keepByAssertionId, review.assertions],
  );

  useEffect(() => {
    onConfirmInFlightChange?.(publishing);
    return () => {
      onConfirmInFlightChange?.(false);
    };
  }, [onConfirmInFlightChange, publishing]);

  const toggleKeep = (assertion: ExactRunReviewAssertion) => {
    if (selectionLocked) return;
    setKeepByAssertionId((prev) => {
      const next = new Map(prev);
      const nextKeep = !(next.get(assertion.assertionId) ?? false);
      next.set(assertion.assertionId, nextKeep);

      if (assertion.kind === "object" && !nextKeep) {
        for (const candidate of review.assertions) {
          if (candidate.kind !== "relationship") continue;
          const endpoints = relationshipEndpointIds(candidate);
          if (!endpoints) continue;
          if (endpoints[0] === assertion.assertionId || endpoints[1] === assertion.assertionId) {
            next.set(candidate.assertionId, false);
          }
        }
      }
      return next;
    });
  };

  async function confirmRetained(plan:FirstWorldGraphPlan){
    await saveFirstWorldRecovery(review,plan,true,current);
    if(!current())return;
    const nextReceipt=await confirmFirstWorldGraph({plan});
    if(!current())return;
    assertFirstWorldReceipt(nextReceipt,plan);
    setReceipt(nextReceipt);setPublishPhase('receipt');
  }
  async function runConfirmWithPlan(plan:FirstWorldGraphPlan){
    if(lock.current||hasTerminalReceipt||!current())return;
    lock.current=true;setPublishPhase('publishing');setPublishError(null);
    try {await confirmRetained(plan);}
    catch(error){if(current()){rememberFailure(error,plan);setPublishPhase('unknown_result');setPublishError(publishErrorMessage(error));}}
    finally {lock.current=false;}
  }
  async function runPrepareAndConfirm(){
    if(lock.current||sealedPlan||hasTerminalReceipt||keptCount===0||!current())return;
    lock.current=true;setPublishPhase('publishing');setPublishError(null);
    let prepared=false;
    let attemptedPlan: FirstWorldGraphPlan | undefined;
    try {
      const decisions=buildFirstWorldDecisions(review.assertions,keepByAssertionId);
      const plan=await prepareFirstWorldGraph({runId:review.runId,decisions});
      if(!current())return;
      assertFirstWorldPlan(plan,review,decisions);
      await saveFirstWorldRecovery(review,plan,false,current);
      if(!current())return;
      prepared=true;attemptedPlan=plan;setSealedPlan(plan);
      await confirmRetained(plan);
    } catch(error){if(current()){rememberFailure(error,attemptedPlan);setPublishPhase(prepared?'unknown_result':'pre_commit_error');setPublishError(publishErrorMessage(error));}}
    finally {lock.current=false;}
  }

  const onRetryExactConfirm = () => {
    if (!sealedPlan) return;
    void runConfirmWithPlan(sealedPlan);
  };

  const showCreateCta =
    !hasTerminalReceipt
    && publishPhase !== "unknown_result"
    && publishPhase !== "pre_commit_error";

  return (
    <section
      className="graph-review-extract-promote-sheet graph-review-first-world-publish-sheet"
      data-testid="graph-review-first-world-publish-sheet"
      data-world-id={worldId || undefined}
      aria-label={`Review first-world changes for ${worldDisplayName}`}
    >
      <header className="graph-review-extract-promote-sheet-header">
        <div>
          <h4>Review what DungeonBuddy found</h4>
          <p className="graph-review-extract-promote-sheet-meta">
            {worldDisplayName}
            {worldId ? (
              <>
                {" "}
                · <code>{worldId}</code>
              </>
            ) : null}
          </p>
        </div>
      </header>

      {receipt ? (
        <div
          className="graph-review-extract-promote-receipt"
          data-testid="graph-review-first-world-receipt"
          data-outcome={receipt.outcome}
        >
          <p className="graph-review-extract-promote-receipt-outcome">
            {outcomeLabel(receipt.outcome)}
          </p>
          <p className="graph-review-extract-promote-receipt-applied">
            {receipt.appliedAssertionCount} source-backed change
            {receipt.appliedAssertionCount === 1 ? "" : "s"} added to {worldDisplayName}.
          </p>
          {receipt.committedRevisionId ? (
            <p className="graph-review-extract-promote-receipt-revision">
              Committed revision <code>{receipt.committedRevisionId}</code>
            </p>
          ) : null}
          {receipt.warnings.length ? (
            <ul className="graph-review-extract-promote-receipt-warnings">
              {receipt.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      {publishError ? (
        <p
          className="graph-review-extract-promote-error"
          data-testid="graph-review-first-world-publish-error"
          role="alert"
        >
          {publishError}
        </p>
      ) : null}

      {failure ? <p role="status">
        {review.assertions.filter(a => Array.isArray(failure.candidate_assertion_ids) && failure.candidate_assertion_ids.includes(a.assertionId))
          .map(a => `${a.label}: ${candidateSemanticDescription(a, review.assertions)}`).join('; ') || 'Review the rejected relationship'}.
        Proposed predicate {String(failure.buddy_predicate ?? '')}
        {failure.subject_dm_kind || failure.object_dm_kind ? ` (${String(failure.subject_dm_kind ?? '?')} → ${String(failure.object_dm_kind ?? '?')})` : ''}.
        {String(failure.reason ?? 'Native validation rejected this choice.')}.
      </p> : null}

      {!hasTerminalReceipt ? (
        <ul className="graph-review-extract-promote-items">
          {review.assertions.map((assertion) => {
            const kept = keepByAssertionId.get(assertion.assertionId) ?? false;
            const blocked =
              assertion.kind === "relationship"
              && isRelationshipBlocked(assertion, keepByAssertionId);
            const semanticReady = hasReviewSemantics(assertion, review.assertions);
            const disabled = selectionLocked || blocked || !semanticReady;
            const invalid = Array.isArray(failure?.candidate_assertion_ids)
              && failure.candidate_assertion_ids.includes(assertion.assertionId);
            return (
              <li
                key={assertion.assertionId}
                aria-invalid={invalid || undefined}
                className={
                  blocked
                    ? "graph-review-extract-promote-item is-blocked"
                    : "graph-review-extract-promote-item"
                }
              >
                {invalid ? <p role="status">Review this choice: {String(failure?.reason ?? 'Native validation rejected this relationship.')}</p> : null}
                <label>
                  <input
                    type="checkbox"
                    checked={kept}
                    disabled={disabled}
                    onChange={() => toggleKeep(assertion)}
                    aria-label={`Keep ${assertion.label}`}
                  />
                  <span className="graph-review-extract-promote-item-body">
                    <span className="graph-review-extract-promote-item-title">
                      {assertion.label}
                      <span className="graph-review-extract-promote-item-badge">
                        {assertion.kind}
                      </span>
                    </span>
                    <CandidateReviewSemantics assertion={assertion} assertions={review.assertions}/>
                    <span>Candidate wording: {assertion.label}</span>
                    {assertion.kind === 'object' ? <span className="graph-review-extract-promote-item-summary">{assertion.summary}</span> : null}
                    {assertion.evidence[0]?.paragraphText ? (
                      <span className="graph-review-extract-promote-item-evidence">
                        {assertion.evidence[0].paragraphText}
                      </span>
                    ) : null}
                    {blocked ? (
                      <span
                        className="graph-review-extract-promote-item-warnings"
                        data-testid={`graph-review-first-world-relationship-blocked-${assertion.assertionId}`}
                      >
                        Ignored because a required endpoint object is ignored.
                      </span>
                    ) : null}
                  </span>
                </label>
              </li>
            );
          })}
        </ul>
      ) : null}

      <footer className="graph-review-extract-promote-sheet-footer">
        <p
          className="graph-review-extract-promote-confirm-note"
          data-testid="graph-review-first-world-selection-status"
          data-selected-count={keptCount}
        >
          {hasTerminalReceipt
            ? `World Graph is initialized for ${worldDisplayName}.`
            : keptCount === 0
              ? "Keep at least one object or relationship to create the World Graph."
              : `${keptCount} change${keptCount === 1 ? "" : "s"} kept.`}
        </p>

        {showCreateCta ? (
          <button
            type="button"
            className="primary"
            data-testid="graph-review-first-world-create-cta"
            disabled={keptCount === 0 || publishing}
            onClick={() => {
              void runPrepareAndConfirm();
            }}
          >
            {publishing
              ? "Creating World Graph…"
              : `Create World Graph with ${keptCount} change${keptCount === 1 ? "" : "s"}`}
          </button>
        ) : null}

        {publishPhase === "pre_commit_error" && !hasTerminalReceipt ? (
          <button
            type="button"
            className="primary"
            data-testid="graph-review-first-world-retry-prepare"
            disabled={publishing || keptCount === 0}
            onClick={() => {
              void runPrepareAndConfirm();
            }}
          >
            Retry create
          </button>
        ) : null}

        {nonapplication && sealedPlan && !hasTerminalReceipt ? <button type="button"
          disabled={publishing} onClick={() => {void returnToReview();}}>Return to review</button> : null}
        {publishPhase === "unknown_result" && !hasTerminalReceipt && !nonapplication ? (
          <button
            type="button"
            className="primary"
            data-testid="graph-review-first-world-retry-exact-confirm"
            disabled={publishing || !sealedPlan}
            onClick={onRetryExactConfirm}
          >
            Recover saved creation result
          </button>
        ) : null}
      </footer>
    </section>
  );
}
