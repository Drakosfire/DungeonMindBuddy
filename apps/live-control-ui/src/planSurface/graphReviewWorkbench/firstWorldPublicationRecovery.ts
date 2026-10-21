import type {ExactRunReviewPackage,FirstWorldDisposition,FirstWorldGraphPlan,FirstWorldGraphConfirmReceipt} from '../../api/types';

export type FirstWorldRecovery={schema:'dmb_first_world_publication_recovery_v1';scope:string;plan:FirstWorldGraphPlan;submitted:boolean};
const nonblank=(value:unknown):value is string=>typeof value==='string'&&!!value.trim();
const digest=(value:unknown)=>typeof value==='string'&&/^sha256:[a-f0-9]{64}$/.test(value);
const strings=(value:unknown):value is string[]=>Array.isArray(value)&&value.every(nonblank)&&new Set(value).size===value.length;
const same=(a:unknown,b:unknown)=>JSON.stringify(a)===JSON.stringify(b);
export const firstWorldScope=(review:ExactRunReviewPackage)=>JSON.stringify([review.worldId,review.runId,review.sourceArtifactId,review.sourceRevisionId]);
export const firstWorldRecoveryKey=(review:ExactRunReviewPackage)=>'dmb.firstWorldPublication.v1:'+firstWorldScope(review);

function assertFirstWorldEffect(plan:FirstWorldGraphPlan,review:ExactRunReviewPackage){
  const effect=plan.reviewedEffect,meta=effect?.contribution_meta as Record<string,unknown>|undefined;
  const accepted=effect?.accepted_proposals,rejected=effect?.rejected_assertions,map=effect?.candidate_effect_map;
  const check=(rows:unknown,ids:string[],state:string)=>Array.isArray(rows)&&rows.length===ids.length
    &&new Set(rows.map(row=>row?.assertion_id)).size===ids.length&&rows.every(row=>row&&ids.includes(row.assertion_id)
      &&row.source_artifact_id===plan.sourceArtifactId&&row.source_revision_id===plan.sourceRevisionId
      &&row.campaign_scope===plan.worldId&&row.acceptance_state===state);
  if(plan.campaignScope!==plan.worldId||plan.sessionScope!==null
    ||!meta||meta.source_kind!=='source_extraction'||meta.source_artifact_id!==plan.sourceArtifactId
    ||meta.source_revision_id!==plan.sourceRevisionId||meta.extraction_profile!==plan.extractionProfile||meta.campaign_scope!==plan.worldId
    ||!check(accepted,plan.acceptedAssertionIds,'accepted')||!check(rejected,plan.rejectedAssertionIds,'rejected')
    ||!map||typeof map!=='object'||Array.isArray(map)||Object.keys(map).length!==review.assertions.length
    ||Object.entries(map).some(([candidate,ids])=>{
      const decision=(effect.decision_snapshot as {assertion_id:string;decision:string}[]).find(row=>row.assertion_id===candidate);
      const allowed=decision?.decision==='reject'?plan.rejectedAssertionIds:plan.acceptedAssertionIds;
      return !decision||!strings(ids)||ids.length===0||ids.some(id=>!allowed.includes(id));
    })||new Set(Object.values(map).flat()).size!==plan.acceptedAssertionIds.length+plan.rejectedAssertionIds.length){
    throw new Error('The creation plan contains a foreign scope, source or materialized effect.');
  }
}

export function assertFirstWorldPlan(plan:FirstWorldGraphPlan,review:ExactRunReviewPackage,decisions?:FirstWorldDisposition[]){
  const snapshot=plan?.reviewedEffect?.decision_snapshot;
  if(!plan||plan.schema!=='dmb_first_world_graph_plan_v1'||review.sourceDomain!=='worldbuilding'||review.inspectionStatus!=='ready'
    ||!nonblank(review.worldId)||plan.worldId!==review.worldId||plan.runId!==review.runId
    ||plan.sourceArtifactId!==review.sourceArtifactId||plan.sourceRevisionId!==review.sourceRevisionId||!digest(review.sourceRevisionId)
    ||!nonblank(plan.planId)||!digest(plan.planDigest)||!digest(plan.decisionDigest)||!nonblank(plan.contributionId)
    ||!/^[a-f0-9]{64}$/.test(plan.contributionPayloadSha256)||!nonblank(plan.workspaceDocumentId)
    ||typeof plan.workspaceDocumentRevision!=='string'||!/^\d+$/.test(plan.workspaceDocumentRevision)||Number(plan.workspaceDocumentRevision)<1
    ||plan.extractionProfile!=='worldbuilding_shepherds_flock_v0@0.1'||plan.confirmable!==true
    ||!strings(plan.acceptedAssertionIds)||!plan.acceptedAssertionIds.length||!strings(plan.rejectedAssertionIds)
    ||plan.acceptedAssertionIds.some(id=>plan.rejectedAssertionIds.includes(id))
    ||!plan.summary||!['createNewNodeCount','acceptedEdgeCount','rejectedCandidateCount','acceptedAssertionCount'].every(key=>{
      const value=plan.summary[key as keyof typeof plan.summary];return Number.isSafeInteger(value)&&value>=0;})
    ||plan.summary.acceptedAssertionCount!==plan.acceptedAssertionIds.length
    ||!Array.isArray(plan.diagnostics)||!plan.diagnostics.every(value=>typeof value==='string')
    ||!Array.isArray(snapshot)||snapshot.length!==review.assertions.length
    ||new Set(snapshot.map(row=>row?.assertion_id)).size!==snapshot.length
    ||snapshot.some(row=>{
      const candidate=review.assertions.find(item=>item.assertionId===row?.assertion_id);
      return !candidate||row.target_node_id!=null||row.candidate_kind!==(candidate.kind==='object'?'node':'edge')
        ||!(candidate.kind==='object'?['create_new','reject']:['accept','reject']).includes(row.decision)
        ||(row.decision!=='reject'&&!candidate.evidence.length)
        ||(decisions&&!decisions.some(choice=>choice.assertionId===row.assertion_id&&choice.decision===row.decision));
    })|| (decisions&&(decisions.length!==snapshot.length||new Set(decisions.map(row=>row.assertionId)).size!==snapshot.length))){
    throw new Error('The creation plan does not match this exact source, World and reviewed choices.');
  }
  assertFirstWorldEffect(plan,review);
}
export function firstWorldDecisions(plan:FirstWorldGraphPlan):FirstWorldDisposition[]{
  return (plan.reviewedEffect.decision_snapshot as {assertion_id:string;decision:FirstWorldDisposition['decision']}[])
    .map(row=>({assertionId:row.assertion_id,decision:row.decision}));
}
export function readFirstWorldRecovery(review:ExactRunReviewPackage):FirstWorldRecovery|null{
  const raw=localStorage.getItem(firstWorldRecoveryKey(review));if(raw===null)return null;
  const value=JSON.parse(raw) as FirstWorldRecovery;
  if(value?.schema!=='dmb_first_world_publication_recovery_v1'||value.scope!==firstWorldScope(review)||typeof value.submitted!=='boolean'
    ||Object.keys(value).some(key=>!['schema','scope','plan','submitted'].includes(key)))throw new Error('Saved World creation recovery does not match this source.');
  assertFirstWorldPlan(value.plan,review);return value;
}
export async function saveFirstWorldRecovery(review:ExactRunReviewPackage,plan:FirstWorldGraphPlan,submitted:boolean,isCurrent:()=>boolean){
  assertFirstWorldPlan(plan,review);
  if(!navigator.locks)throw new Error('This browser cannot safely retain World creation across tabs.');
  return navigator.locks.request(firstWorldRecoveryKey(review),()=>{
    if(!isCurrent())throw new Error('The selected source or World changed. No creation request was sent.');
    const current=readFirstWorldRecovery(review);
    if((current&&!same(current.plan,plan))||(current?.submitted&&!submitted)||(submitted&&!current))
      throw new Error('Another creation request is retained. Reopen this review to recover it.');
    const value:FirstWorldRecovery={schema:'dmb_first_world_publication_recovery_v1',scope:firstWorldScope(review),plan,submitted};
    localStorage.setItem(firstWorldRecoveryKey(review),JSON.stringify(value));
  });
}
export function assertFirstWorldReceipt(receipt:FirstWorldGraphConfirmReceipt,plan:FirstWorldGraphPlan){
  if(!receipt||receipt.schema!=='dmb_first_world_graph_confirm_v1'||!['initialized','already_initialized','published_audit_degraded'].includes(receipt.outcome)
    ||receipt.worldId!==plan.worldId||receipt.planId!==plan.planId||receipt.planDigest!==plan.planDigest||receipt.decisionDigest!==plan.decisionDigest
    ||receipt.sourceArtifactId!==plan.sourceArtifactId||receipt.sourceRevisionId!==plan.sourceRevisionId||receipt.contributionId!==plan.contributionId
    ||!nonblank(receipt.committedRevisionId)||receipt.appliedAssertionCount!==plan.acceptedAssertionIds.length
    ||!same(receipt.acceptedAssertionIds,plan.acceptedAssertionIds)||!same(receipt.rejectedAssertionIds,plan.rejectedAssertionIds)
    ||!['ok','degraded'].includes(receipt.auditStatus)||!Array.isArray(receipt.warnings)||!receipt.warnings.every(value=>typeof value==='string'))
    throw new Error('The creation receipt does not match the retained request. Recover its exact result.');
}
