import {hasReviewSemantics, relationshipEndpoints} from './candidateReviewSemantics';
import {ExtractPromoteApiError} from '../../api/extractPromoteApi';
import type {NativeFirstWorldPlan, FirstWorldRetainedPlan, FirstWorldPublicationRequest, FirstWorldPublicationReceipt} from '../../api/nativeFirstWorldPublicationTypes';
import type {ExactRunReviewPackage,FirstWorldDisposition,FirstWorldGraphPlan,FirstWorldGraphConfirmReceipt,FirstWorldConfirmNonapplication} from '../../api/types';

export type FirstWorldRecovery={schema:'dmb_first_world_publication_recovery_v1'|'dmb_native_first_world_recovery_v1';scope:string;plan:FirstWorldRetainedPlan;submitted:boolean;request?:FirstWorldPublicationRequest};
export type FirstWorldSelection={worldId?:string|null;runId:string};
const nonblank=(value:unknown):value is string=>typeof value==='string'&&!!value.trim();
const digest=(value:unknown)=>typeof value==='string'&&/^sha256:[a-f0-9]{64}$/.test(value);
const strings=(value:unknown):value is string[]=>Array.isArray(value)&&value.every(nonblank)&&new Set(value).size===value.length;
const stable=(value:unknown)=>JSON.stringify(value,(_key,item)=>item&&typeof item==='object'&&!Array.isArray(item)?Object.fromEntries(Object.keys(item).sort().map(key=>[key,item[key]])):item);
const same=(a:unknown,b:unknown)=>stable(a)===stable(b);
export const firstWorldScope=(review:ExactRunReviewPackage)=>JSON.stringify([review.worldId,review.runId,review.sourceArtifactId,review.sourceRevisionId]);
const selectionScope=(selection:FirstWorldSelection)=>JSON.stringify([selection.worldId,selection.runId]);
export const firstWorldRecoveryKey=(selection:FirstWorldSelection)=>'dmb.nativeFirstWorldPublication.v1:'+selectionScope(selection);

function assertFirstWorldEffect(plan:FirstWorldRetainedPlan,review:ExactRunReviewPackage){
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
  const proposals = [...accepted as Record<string,unknown>[], ...rejected as Record<string,unknown>[]];
  for (const candidate of review.assertions) {
    const ids = (map as Record<string,string[]>)[candidate.assertionId];
    const rows = proposals.filter(row => ids.includes(row.assertion_id as string));
    if (!hasReviewSemantics(candidate, review.assertions) || rows.length !== 1 || ids.length !== 1)
      throw new Error('The creation plan does not match the reviewed structured meaning.');
    const row = rows[0], value = row.value as Record<string,unknown> | undefined;
    const endpoints = relationshipEndpoints(candidate);
    const matches = candidate.kind === 'object'
      ? row.assertion_kind === 'node' && row.subject_node_id === candidate.assertionId
        && row.label === candidate.label && value?.kind === candidate.contributionKind
      : row.assertion_kind === 'edge' && !!endpoints
        && row.predicate === candidate.relationshipType && value?.predicate === candidate.relationshipType
        && row.subject_node_id === endpoints[0] && row.target_node_id === endpoints[1]
        && value?.direction === 'outbound';
    if (!matches) throw new Error('The creation plan does not match the reviewed structured meaning.');
  }
}

export function assertFirstWorldPlan(plan:FirstWorldRetainedPlan,review:ExactRunReviewPackage,decisions?:FirstWorldDisposition[]){
  if(plan && !['dmb_first_world_graph_plan_v3','dmb_native_first_world_plan_v1'].includes(plan.schema)) throw new Error('This saved World creation plan is out of date and has been preserved. Inspect World status, then prepare and review again.');
  const snapshot=plan?.reviewedEffect?.decision_snapshot;
  if(!plan||!['dmb_first_world_graph_plan_v3','dmb_native_first_world_plan_v1'].includes(plan.schema)||review.sourceDomain!=='worldbuilding'||review.inspectionStatus!=='ready'
    ||!nonblank(review.worldId)||plan.worldId!==review.worldId||plan.runId!==review.runId
    ||plan.sourceArtifactId!==review.sourceArtifactId||plan.sourceRevisionId!==review.sourceRevisionId||!digest(review.sourceRevisionId)
    ||!plan.nativeTarget||!/^world:[a-f0-9]{32}$/.test(plan.nativeTarget.nativeWorldId)
    ||!/^provision:[a-f0-9]{32}$/.test(plan.nativeTarget.provisioningId)||plan.nativeTarget.bindingVersion!==1
    ||!digest(plan.sourceEvidenceSha256)||!nonblank(plan.planId)||!digest(plan.planDigest)||!digest(plan.decisionDigest)||!nonblank(plan.contributionId)
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
  if(plan.schema==='dmb_native_first_world_plan_v1')assertNativeEnvelope(plan);
}
export function firstWorldDecisions(plan:FirstWorldRetainedPlan):FirstWorldDisposition[]{
  return (plan.reviewedEffect.decision_snapshot as {assertion_id:string;decision:FirstWorldDisposition['decision']}[])
    .map(row=>({assertionId:row.assertion_id,decision:row.decision}));
}
/** Browser checks correlations only. The server verifies signature/current owner. */
function assertNativeEnvelope(plan:NativeFirstWorldPlan){
  const hex=(v:unknown)=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v);
  const stage=plan.sourceStage,domain=plan.domainContractRef,profile=plan.targetProfileRef;
  if(!nonblank(plan.compilerIntentJson)||plan.compilerIntentJson.length>8*1024*1024||!hex(plan.compilerIntentSha256)
    ||!domain||!nonblank(domain.domain_id)||!nonblank(domain.domain_revision)||!hex(domain.descriptor_sha256)
    ||!profile||!nonblank(profile.profile_id)||!nonblank(profile.profile_revision)||!hex(profile.descriptor_sha256)
    ||!nonblank(plan.token)||plan.token.length>16*1024*1024||!nonblank(plan.publicationId)||!nonblank(plan.preparedBy)
    ||plan.policy!=='dmb_native_first_world_compiler_v1'||!Number.isSafeInteger(plan.runRevision)||plan.runRevision<0
    ||!Number.isFinite(Date.parse(plan.createdAt))||!Number.isFinite(Date.parse(plan.expiresAt))
    ||Date.parse(plan.expiresAt)<=Date.parse(plan.createdAt)||!stage
    ||!['absent','admitted'].includes(stage.admissionState)||!nonblank(stage.admissionId)
    ||stage.documentId!==plan.workspaceDocumentId||String(stage.documentRevision)!==plan.workspaceDocumentRevision
    ||!Number.isSafeInteger(stage.documentRevision)||stage.documentRevision<1||!nonblank(stage.sourceRootRelpath)
    ||!hex(stage.bodySha256)||plan.sourceRevisionId!=='sha256:'+stage.bodySha256
    ||!stage.origin||stage.origin.object_id!==stage.documentId||stage.origin.revision_id!==`registry-revision:${stage.documentRevision}`
    ||!nonblank(stage.origin.namespace)||!nonblank(stage.genesisInitializationId)||!nonblank(stage.extensionId)||!nonblank(stage.profileTransitionId)
    ||!Number.isFinite(Date.parse(stage.documentUpdatedAt))||!Number.isFinite(Date.parse(stage.genesisCreatedAt))
    ||!Number.isSafeInteger(stage.sourceAuthorityEpoch)||stage.sourceAuthorityEpoch<0
    ||((stage.headRevisionId===null)!==(stage.headProfileRef===null)))throw new Error('The signed native creation envelope is incomplete or inconsistent.');
  if(!Array.isArray(stage.existingBindings)||new Set(stage.existingBindings.map(b=>b?.reviewedEvidenceRefId)).size!==stage.existingBindings.length
    ||(stage.admissionState==='absent'&&stage.existingBindings.length!==0)
    ||stage.existingBindings.some(b=>!b||!nonblank(b.reviewedEvidenceRefId)||!['support','context'].includes(b.evidenceRole)
      ||!Number.isSafeInteger(b.proofAuthorityEpoch)||b.proofAuthorityEpoch<1||b.proofAuthorityEpoch>stage.sourceAuthorityEpoch
      ||!['admission','extension'].includes(b.originKind)||!nonblank(b.originOperationId)||!hex(b.originReceiptSha256)
      ||!nonblank(b.introducedRevisionId)||!b.proof||!b.sourceRevision))
    throw new Error('The retained existing source bindings are inconsistent.');
  const source=[stage.admissionReceiptSha256,stage.nativeSourceArtifactId,stage.nativeSourceRevisionId,stage.wholeDocumentEvidenceRefId];
  if(stage.admissionState==='absent'?source.some(v=>v!==null):(!source.every(nonblank)||!hex(stage.admissionReceiptSha256)||!nonblank(stage.headRevisionId)))
    throw new Error('The creation source stage contains inconsistent admission identities.');
  const intent=JSON.parse(plan.compilerIntentJson);
  if(!same(intent.reviewed_effect,plan.reviewedEffect)||intent.world_id!==plan.worldId||intent.source_body_sha256!==stage.bodySha256)
    throw new Error('The compiler intent does not match the retained review.');
}

function assertOwnEnvelope(plan:FirstWorldRetainedPlan){
  if(!plan||!['dmb_first_world_graph_plan_v3','dmb_native_first_world_plan_v1'].includes(plan.schema))
    throw new Error('This saved World creation plan is out of date and has been preserved.');
  const map=plan.reviewedEffect?.candidate_effect_map as Record<string,string[]>|undefined;
  const snapshot=plan.reviewedEffect?.decision_snapshot as {assertion_id:string;candidate_kind:string}[]|undefined;
  const rows=[...(plan.reviewedEffect?.accepted_proposals as Record<string,unknown>[]??[]),
    ...(plan.reviewedEffect?.rejected_assertions as Record<string,unknown>[]??[])];
  if(!map||!Array.isArray(snapshot))throw new Error('The retained creation envelope is incomplete.');
  // Derive structural correlations from the saved envelope, never today's candidates.
  const assertions=snapshot.map(choice=>{
    const row=rows.find(r=>map[choice.assertion_id]?.includes(String(r.assertion_id)));
    if(!row)throw new Error('The retained creation envelope is incomplete.');
    return {assertionId:choice.assertion_id,kind:choice.candidate_kind==='node'?'object':'relationship',
      label:row.label,summary:'',nodeType:(row.value as Record<string,unknown>)?.kind,
      contributionKind:(row.value as Record<string,unknown>)?.kind,relationshipType:row.predicate,
      fromCandidateNodeId:row.subject_node_id,toCandidateNodeId:row.target_node_id,evidence:[{}]};
  });
  assertFirstWorldPlan(plan,{schema:'dmb_extract_promote_exact_run_review_v1',sourceDomain:'worldbuilding',inspectionStatus:'ready',
    worldId:plan.worldId,runId:plan.runId,sourceArtifactId:plan.sourceArtifactId,sourceRevisionId:plan.sourceRevisionId,
    sourceProse:'',assertions,diagnostics:[]} as ExactRunReviewPackage);
}
export function firstWorldRequest(plan:FirstWorldRetainedPlan):FirstWorldPublicationRequest{
  return plan.schema==='dmb_native_first_world_plan_v1'?{schema:'dmb_native_first_world_confirm_request_v1',plan}
    :{schema:'dmb_first_world_graph_confirm_request_v1',plan};
}

/** Bounded discovery by selected managed World/run, independent of source readiness. */
export function readFirstWorldRecovery(selection:FirstWorldSelection):FirstWorldRecovery|null{
  if(!nonblank(selection.worldId)||!nonblank(selection.runId))return null;
  localStorage.getItem(firstWorldRecoveryKey(selection)); // Probe storage access even with no retained entries.
  if(localStorage.length>2048)throw new Error('Too many saved requests to inspect safely. Recovery is preserved.');
  let found:FirstWorldRecovery|null=null;
  for(let i=0;i<localStorage.length;i++){
    const key=localStorage.key(i)!;
    if(!key.startsWith('dmb.firstWorldPublication.v1:')&&!key.startsWith('dmb.nativeFirstWorldPublication.v1:'))continue;
    // Keys themselves select scope before parsing possibly unrelated stored content.
    let scope:unknown;
    try{scope=JSON.parse(key.slice(key.indexOf(':')+1));}catch{continue;}
    if(!Array.isArray(scope)||scope[0]!==selection.worldId||scope[1]!==selection.runId)continue;
    const raw=localStorage.getItem(key)!;
    if(raw.length>24*1024*1024)throw new Error('The saved creation request exceeds the inspection bound. It is preserved.');
    const value=JSON.parse(raw) as FirstWorldRecovery;
    if(!value||!['dmb_first_world_publication_recovery_v1','dmb_native_first_world_recovery_v1'].includes(value.schema)
      ||typeof value.submitted!=='boolean'||!value.plan||value.plan.worldId!==selection.worldId||value.plan.runId!==selection.runId
      ||Object.keys(value).some(k=>!['schema','scope','plan','submitted','request'].includes(k)))throw new Error('Saved World creation recovery does not match its own envelope.');
    if((value.schema==='dmb_first_world_publication_recovery_v1'&&value.plan.schema!=='dmb_first_world_graph_plan_v3')
      ||(value.schema==='dmb_native_first_world_recovery_v1'&&value.plan.schema!=='dmb_native_first_world_plan_v1'))
      throw new Error('This saved World creation plan is out of date and has been preserved.');
    assertOwnEnvelope(value.plan);
    const expectedScope=value.schema==='dmb_first_world_publication_recovery_v1'?firstWorldScope(value.plan as unknown as ExactRunReviewPackage):selectionScope(value.plan);
    if(value.scope!==expectedScope||!(key===firstWorldRecoveryKey(value.plan)||key==='dmb.firstWorldPublication.v1:'+expectedScope)
      ||(value.schema==='dmb_native_first_world_recovery_v1'&&(!value.request||!same(value.request,firstWorldRequest(value.plan)))))
      throw new Error('Saved World creation request does not match its retained plan.');
    if(found)throw new Error('Multiple creation requests are retained for this World/run. They have been preserved.');
    found=value;
  }
  return found;
}
export async function saveFirstWorldRecovery(review:ExactRunReviewPackage,plan:FirstWorldRetainedPlan,submitted:boolean,isCurrent:()=>boolean){
  assertFirstWorldPlan(plan,review);
  if(!navigator.locks)throw new Error('This browser cannot safely retain World creation across tabs.');
  return navigator.locks.request(firstWorldRecoveryKey(review),()=>{
    if(!isCurrent())throw new Error('The selected source or World changed. No creation request was sent.');
    const current=readFirstWorldRecovery(review);
    if((current&&!same(current.plan,plan))||(current?.submitted&&!submitted)||(submitted&&!current))
      throw new Error('Another creation request is retained. Reopen this review to recover it.');
    const native=plan.schema==='dmb_native_first_world_plan_v1';
    const value:FirstWorldRecovery=native?{schema:'dmb_native_first_world_recovery_v1',scope:selectionScope(plan),plan,submitted,request:firstWorldRequest(plan)}
      :{schema:'dmb_first_world_publication_recovery_v1',scope:firstWorldScope(review),plan,submitted};
    localStorage.setItem(firstWorldRecoveryKey(review),JSON.stringify(value));
    if(localStorage.getItem(firstWorldRecoveryKey(review))!==JSON.stringify(value))throw new Error('Creation request was not retained. No request was sent.');
  });
}
/** Mark and retrieve an exact saved request without consulting current source data. */
export async function retainFirstWorldRetry(selection:FirstWorldSelection,plan:FirstWorldRetainedPlan,isCurrent:()=>boolean):Promise<FirstWorldPublicationRequest>{
  if(!navigator.locks)throw new Error('This browser cannot safely retain World creation across tabs.');
  return navigator.locks.request(firstWorldRecoveryKey(selection),()=>{
    if(!isCurrent())throw new Error('The selected source or World changed. Recovery is retained.');
    const saved=readFirstWorldRecovery(selection);
    if(!saved||!same(saved.plan,plan))throw new Error('Another creation request owns recovery.');
    const request=saved.request??firstWorldRequest(saved.plan);
    // Retain the submitted marker at its original key; never migrate/replace its plan.
    const key=saved.schema==='dmb_first_world_publication_recovery_v1'&&localStorage.getItem('dmb.firstWorldPublication.v1:'+saved.scope)!==null
      ?'dmb.firstWorldPublication.v1:'+saved.scope:firstWorldRecoveryKey(selection);
    localStorage.setItem(key,JSON.stringify({...saved,submitted:true}));
    const checked=readFirstWorldRecovery(selection);
    if(!checked?.submitted||!same(checked.plan,plan))throw new Error('Recovery submission could not be retained.');
    return request;
  });
}
export function assertNativeFirstWorldReceipt(receipt:FirstWorldPublicationReceipt,plan:FirstWorldRetainedPlan){
  if(!receipt||receipt.worldId!==plan.worldId||receipt.planId!==plan.planId||receipt.planDigest!==plan.planDigest
    ||receipt.nativeWorldId!==plan.nativeTarget.nativeWorldId)throw new Error('The creation receipt does not match the retained request.');
  if(plan.schema==='dmb_first_world_graph_plan_v3'){
    if(receipt.schema!=='dmb_historical_first_world_receipt_v1'||receipt.activationStatus!=='historical_only'
      ||receipt.historicalReceipt?.world_id!==plan.nativeTarget.nativeWorldId||receipt.historicalReceipt.source_plan_id!==plan.planId
      ||'sha256:'+receipt.historicalReceipt.source_plan_sha256!==plan.planDigest)throw new Error('The historical receipt does not match the saved classic request.');
    return;
  }
  if(receipt.schema!=='dmb_native_first_world_confirm_v1'||!['initialized','already_initialized','activation_pending'].includes(receipt.outcome)
    ||receipt.decisionDigest!==plan.decisionDigest||receipt.sourceArtifactId!==plan.sourceArtifactId||receipt.sourceRevisionId!==plan.sourceRevisionId
    ||receipt.contributionId!==plan.contributionId||!nonblank(receipt.nativeContributionId)||receipt.publicationId!==plan.publicationId
    ||!nonblank(receipt.committedRevisionId)||receipt.appliedAssertionCount!==plan.acceptedAssertionIds.length
    ||!same(receipt.acceptedAssertionIds,plan.acceptedAssertionIds)||!same(receipt.rejectedAssertionIds,plan.rejectedAssertionIds)
    ||!['active','pending'].includes(receipt.activationStatus)||((receipt.outcome==='activation_pending')!==(receipt.activationStatus==='pending'))
    ||!['available','unavailable','unknown'].includes(receipt.sourceStatus)||typeof receipt.recovered!=='boolean'
    ||!Array.isArray(receipt.warnings)||!receipt.warnings.every(v=>typeof v==='string'))throw new Error('The native receipt does not match the saved creation request.');
  for(const core of [receipt.nativePublication?.publication_receipt,receipt.nativePublication?.prospective_result]){
    if(!core||core.space_id!==receipt.nativeWorldId||core.publication_id!==receipt.publicationId||core.published_revision_id!==receipt.committedRevisionId)
      throw new Error('The native publication proof does not match its receipt.');
  }
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


export function firstWorldNonapplication(error: unknown, plan: FirstWorldGraphPlan): FirstWorldConfirmNonapplication | null {
  if (!(error instanceof ExtractPromoteApiError) || error.code !== 'first_world_confirm_not_invoked'
    || error.body?.schema !== 'dmb_extract_promote_error_v1') return null;
  const proof = error.body.failureResult;
  if (!proof || proof.schema !== 'dmb_first_world_confirm_not_invoked_v1'
    || proof.worldId !== plan.worldId || proof.nativeWorldId !== plan.nativeTarget.nativeWorldId
    || proof.initializationId !== plan.nativeTarget.provisioningId || proof.planId !== plan.planId
    || proof.planDigest !== plan.planDigest || proof.initializationInvoked !== false
    || !nonblank(proof.validationMessage) || !proof.failure || typeof proof.failure !== 'object' || Array.isArray(proof.failure)
    || Object.keys(proof).some(key => !['schema','worldId','nativeWorldId','initializationId','planId','planDigest','initializationInvoked','validationMessage','failure'].includes(key))) return null;
  return proof as unknown as FirstWorldConfirmNonapplication;
}

export async function releaseFirstWorldRecovery(_review: ExactRunReviewPackage, _plan: FirstWorldGraphPlan,
  _proof: FirstWorldConfirmNonapplication, _isCurrent: () => boolean) {
  throw new Error('Submitted creation requests are retained. A request-local nonapplication result cannot release recovery.');
}

/** Inspect only the obsolete envelope, never make its plan executable. */
export function obsoleteUnsubmittedRecovery(review: ExactRunReviewPackage): string | null {
  try {
    const raw = localStorage.getItem(firstWorldRecoveryKey(review));
    if (raw === null) return null;
    const value = JSON.parse(raw), plan = value?.plan;
    return value?.schema === 'dmb_first_world_publication_recovery_v1'
      && value.scope === firstWorldScope(review) && value.submitted === false
      && Object.keys(value).every(key => ['schema','scope','plan','submitted'].includes(key))
      && plan?.schema === 'dmb_first_world_graph_plan_v2'
      && plan.worldId === review.worldId && plan.runId === review.runId
      && plan.sourceArtifactId === review.sourceArtifactId && plan.sourceRevisionId === review.sourceRevisionId
      && nonblank(plan.planId) && digest(plan.planDigest) ? raw : null;
  } catch { return null; }
}

export async function archiveObsoleteUnsubmittedRecovery(review: ExactRunReviewPackage, expectedRaw: string,
  isCurrent: () => boolean) {
  if (!navigator.locks) throw new Error('This browser cannot safely archive World creation recovery.');
  return navigator.locks.request(firstWorldRecoveryKey(review), () => {
    if (!isCurrent()) throw new Error('The selected source or World changed. Recovery is retained.');
    if (obsoleteUnsubmittedRecovery(review) !== expectedRaw)
      throw new Error('Another creation request owns recovery. Reopen this review.');
    const key = firstWorldRecoveryKey(review), archiveKey = key + ':obsolete:' + crypto.randomUUID();
    // Persist and verify the exact old bytes before releasing the active slot.
    localStorage.setItem(archiveKey, expectedRaw);
    if (localStorage.getItem(archiveKey) !== expectedRaw || localStorage.getItem(key) !== expectedRaw)
      throw new Error('Recovery could not be archived safely. The request is retained.');
    localStorage.removeItem(key);
    if (localStorage.getItem(key) !== null) throw new Error('Recovery could not be released. Reopen this review.');
  });
}
