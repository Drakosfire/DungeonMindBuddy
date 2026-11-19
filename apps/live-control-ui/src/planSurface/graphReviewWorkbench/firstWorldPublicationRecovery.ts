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
export const firstWorldScope=(review:Pick<ExactRunReviewPackage,'worldId'|'runId'|'sourceArtifactId'|'sourceRevisionId'>)=>JSON.stringify([review.worldId,review.runId,review.sourceArtifactId,review.sourceRevisionId]);
const selectionScope=(selection:FirstWorldSelection)=>JSON.stringify([selection.worldId,selection.runId]);
export const firstWorldRecoveryKey=(selection:FirstWorldSelection)=>'dmb.nativeFirstWorldPublication.v1:'+selectionScope(selection);

type RetainedCandidate={candidateId:string;kind:'node'|'edge';decision:string;row:Record<string,unknown>;value:Record<string,unknown>};
const record=(value:unknown):value is Record<string,unknown>=>value!==null&&typeof value==='object'&&!Array.isArray(value);

/** Validate only saved structural facts. No current review or invented evidence. */
function retainedCandidates(plan:FirstWorldRetainedPlan):RetainedCandidate[]{
  if(!plan||!['dmb_first_world_graph_plan_v3','dmb_native_first_world_plan_v1'].includes(plan.schema))
    throw new Error('This saved World creation plan is out of date and has been preserved.');
  if(!nonblank(plan.worldId)||!nonblank(plan.runId)||!nonblank(plan.sourceArtifactId)||!digest(plan.sourceRevisionId)
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
    ||!Array.isArray(plan.diagnostics)||!plan.diagnostics.every(value=>typeof value==='string'))
    throw new Error('The creation plan does not match its exact source, World and reviewed choices.');
  const fail=():never=>{throw new Error('The creation plan contains a foreign scope, source or materialized effect.');};
  const semanticFail=():never=>{throw new Error('The creation plan does not match the reviewed structured meaning.');};
  const effect=plan.reviewedEffect;
  if(!record(effect))return fail();
  const meta=effect.contribution_meta,map=effect.candidate_effect_map,snapshot=effect.decision_snapshot;
  if(plan.campaignScope!==plan.worldId||plan.sessionScope!==null||!record(meta)
    ||meta.source_kind!=='source_extraction'||meta.source_artifact_id!==plan.sourceArtifactId
    ||meta.source_revision_id!==plan.sourceRevisionId||meta.extraction_profile!==plan.extractionProfile||meta.campaign_scope!==plan.worldId
    ||!record(map)||!Array.isArray(snapshot)||Object.keys(map).length!==snapshot.length)return fail();
  const rows=new Map<string,Record<string,unknown>>();
  for(const [raw,ids,state] of [[effect.accepted_proposals,plan.acceptedAssertionIds,'accepted'],
    [effect.rejected_assertions,plan.rejectedAssertionIds,'rejected']] as const){
    if(!Array.isArray(raw)||raw.length!==ids.length)return fail();
    for(const row of raw){
      if(!record(row)||!nonblank(row.assertion_id)||!ids.includes(row.assertion_id)||rows.has(row.assertion_id)
        ||row.source_artifact_id!==plan.sourceArtifactId||row.source_revision_id!==plan.sourceRevisionId
        ||row.campaign_scope!==plan.worldId||row.acceptance_state!==state||!record(row.value))return fail();
      rows.set(row.assertion_id,row);
    }
  }
  const candidates:RetainedCandidate[]=[],seen=new Set<string>(),used=new Set<string>();
  for(const choice of snapshot){
    if(!record(choice)||!nonblank(choice.assertion_id)||seen.has(choice.assertion_id)||choice.target_node_id!=null
      ||(choice.candidate_kind!=='node'&&choice.candidate_kind!=='edge')||typeof choice.decision!=='string'
      ||!(choice.candidate_kind==='node'?['create_new','reject']:['accept','reject']).includes(choice.decision))return fail();
    const ids=map[choice.assertion_id];
    if(!strings(ids)||ids.length!==1||used.has(ids[0]))return fail();
    const row=rows.get(ids[0]),allowed=choice.decision==='reject'?plan.rejectedAssertionIds:plan.acceptedAssertionIds;
    if(!row||!allowed.includes(ids[0])||row.assertion_kind!==choice.candidate_kind||!record(row.value))return fail();
    const value=row.value;
    // Validate the actual retained evidence inventory, without substituting a
    // synthetic review or claiming current source admission.
    if(!strings(row.evidence_ref_ids)||(!row.evidence_ref_ids.length&&choice.decision!=='reject')||!Array.isArray(value.evidence)
      ||value.evidence.length!==row.evidence_ref_ids.length)return fail();
    const refs=new Set<string>();
    for(const evidence of value.evidence){
      if(!record(evidence)||!nonblank(evidence.evidence_ref_id)||refs.has(evidence.evidence_ref_id)
        ||!row.evidence_ref_ids.includes(evidence.evidence_ref_id)||evidence.source_artifact_id!==plan.sourceArtifactId
        ||!nonblank(evidence.source_span_ref_id))return fail();
      refs.add(evidence.evidence_ref_id);
    }
    if(choice.candidate_kind==='node'){
      if(row.subject_node_id!==choice.assertion_id||row.target_node_id!=null||row.predicate!=null||!nonblank(row.label)||!nonblank(value.kind)
        ||(value.role!==undefined&&value.role!==value.kind)||(value.label!==undefined&&value.label!==row.label))return semanticFail();
    }else if(!nonblank(row.subject_node_id)||!nonblank(row.target_node_id)||!nonblank(row.predicate)
      ||value.predicate!==row.predicate||value.direction!=='outbound')return semanticFail();
    candidates.push({candidateId:choice.assertion_id,kind:choice.candidate_kind,decision:choice.decision,row,value});
    seen.add(choice.assertion_id);used.add(ids[0]);
  }
  if(used.size!==rows.size||seen.size!==Object.keys(map).length)return fail();
  const nodes=new Map<string,RetainedCandidate>();
  for(const candidate of candidates)if(candidate.kind==='node')nodes.set(candidate.candidateId,candidate);
  for(const edge of candidates.filter(c=>c.kind==='edge')){
    const subject=edge.row.subject_node_id,target=edge.row.target_node_id;
    if(typeof subject!=='string'||typeof target!=='string'||!nodes.has(subject)||!nodes.has(target)
      ||(edge.decision==='accept'&&(nodes.get(subject)?.decision!=='create_new'||nodes.get(target)?.decision!=='create_new')))return semanticFail();
  }
  return candidates;
}

export function assertFirstWorldPlan(plan:FirstWorldRetainedPlan,review:ExactRunReviewPackage,decisions?:FirstWorldDisposition[]){
  const candidates=retainedCandidates(plan);
  if(review.sourceDomain!=='worldbuilding'||review.inspectionStatus!=='ready'||plan.worldId!==review.worldId||plan.runId!==review.runId
    ||plan.sourceArtifactId!==review.sourceArtifactId||plan.sourceRevisionId!==review.sourceRevisionId||candidates.length!==review.assertions.length
    ||(decisions&&(decisions.length!==candidates.length||new Set(decisions.map(row=>row.assertionId)).size!==candidates.length)))
    throw new Error('The creation plan does not match this exact source, World and reviewed choices.');
  for(const candidate of review.assertions){
    const saved=candidates.find(c=>c.candidateId===candidate.assertionId);
    if(!saved||saved.kind!==(candidate.kind==='object'?'node':'edge')
      ||(saved.decision!=='reject'&&!candidate.evidence.length)
      ||(decisions&&!decisions.some(d=>d.assertionId===candidate.assertionId&&d.decision===saved.decision)))
      throw new Error('The creation plan does not match this exact source, World and reviewed choices.');
    const endpoints=relationshipEndpoints(candidate),row=saved.row,value=saved.value;
    const matches=candidate.kind==='object'?row.label===candidate.label&&value.kind===candidate.contributionKind
      :!!endpoints&&row.predicate===candidate.relationshipType&&row.subject_node_id===endpoints[0]&&row.target_node_id===endpoints[1];
    if(!hasReviewSemantics(candidate,review.assertions)||!matches)
      throw new Error('The creation plan does not match the reviewed structured meaning.');
  }
  if(plan.schema==='dmb_native_first_world_plan_v1')assertNativeEnvelope(plan);
}
export function firstWorldDecisions(plan:FirstWorldRetainedPlan):FirstWorldDisposition[]{
  return retainedCandidates(plan).map<FirstWorldDisposition>(candidate=>({assertionId:candidate.candidateId,
    decision:candidate.decision==='create_new'?'create_new':candidate.decision==='accept'?'accept':'reject'}));
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
      ||!nonblank(b.introducedRevisionId)||!record(b.proof)||!record(b.sourceRevision)
      ||b.proof.schema_version!=='dm_native_utf8_span_v1'||b.sourceRevision.schema_version!=='dm_source_revision_v2'
      ||!nonblank(b.proof.evidence_ref_id)||!nonblank(b.proof.span_id)||!hex(b.proof.slice_sha256)
      ||!Number.isSafeInteger(b.proof.start_byte)||!Number.isSafeInteger(b.proof.end_byte)
      ||b.proof.start_byte<0||b.proof.end_byte<=b.proof.start_byte
      ||b.proof.source_revision_id!==stage.nativeSourceRevisionId||b.sourceRevision.source_revision_id!==b.proof.source_revision_id
      ||b.sourceRevision.source_artifact_id!==stage.nativeSourceArtifactId||b.sourceRevision.content_sha256!==stage.bodySha256
      ||b.sourceRevision.body_storage!=='dm_native_utf8_body_v1'||!Number.isFinite(Date.parse(b.sourceRevision.created_at))
      ||(b.sourceRevision.locator!==null&&typeof b.sourceRevision.locator!=='string')))
    throw new Error('The retained existing source bindings are inconsistent.');
  const source=[stage.admissionReceiptSha256,stage.nativeSourceArtifactId,stage.nativeSourceRevisionId,stage.wholeDocumentEvidenceRefId];
  if(stage.admissionState==='absent'?source.some(v=>v!==null):(!source.every(nonblank)||!hex(stage.admissionReceiptSha256)||!nonblank(stage.headRevisionId)))
    throw new Error('The creation source stage contains inconsistent admission identities.');
  const intent=JSON.parse(plan.compilerIntentJson);
  if(!same(intent.reviewed_effect,plan.reviewedEffect)||intent.world_id!==plan.worldId||intent.source_body_sha256!==stage.bodySha256)
    throw new Error('The compiler intent does not match the retained review.');
}

function assertOwnEnvelope(plan:FirstWorldRetainedPlan){
  retainedCandidates(plan);
  if(plan.schema==='dmb_native_first_world_plan_v1')assertNativeEnvelope(plan);
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
    const expectedScope=value.schema==='dmb_first_world_publication_recovery_v1'?firstWorldScope(value.plan):selectionScope(value.plan);
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
