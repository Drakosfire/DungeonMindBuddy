import {authenticatedApiFetch,getNativeGraphAccessGeneration,LiveApiError} from './liveApi';
import type {ManualSelector,ManualSource,ManualContext,ManualRequest,ManualPlan,ManualReceipt,ProfileRequest,ProfilePlan,ProfileReceipt,Witness} from './nativeManualKnowledgeTypes';

export const record=(v:unknown):v is Record<string,unknown>=>v!==null&&typeof v==='object'&&!Array.isArray(v);
export const text=(v:unknown):v is string=>typeof v==='string'&&v.trim().length>0;
export const digest=(v:unknown):v is string=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v);
export const nonnegative=(v:unknown):v is number=>Number.isSafeInteger(v)&&Number(v)>=0;
export const positive=(v:unknown):v is number=>Number.isSafeInteger(v)&&Number(v)>0;
export const uuid=(v:unknown):v is string=>typeof v==='string'&&/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/i.test(v);
export const instant=(v:unknown):v is string=>typeof v==='string'&&/(?:Z|[+-]\d\d:\d\d)$/.test(v)&&Number.isFinite(Date.parse(v));
export const clone=<T,>(v:T):T=>JSON.parse(JSON.stringify(v)) as T;
export const same=(a:unknown,b:unknown):boolean=>stable(a)===stable(b);
export function stable(v:unknown):string {
  if(Array.isArray(v))return '['+v.map(stable).join(',')+']';
  if(record(v))return '{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+stable(v[k])).join(',')+'}';
  return JSON.stringify(v);
}
export async function sha256(value:string|Uint8Array){
  const b=typeof value==='string'?new TextEncoder().encode(value):value;
  const owned=new Uint8Array(b.length);owned.set(b);
  return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',owned)),x=>x.toString(16).padStart(2,'0')).join('');
}
// Exact UTC normalization preserves all six fractional digits, never JS ms rounding.
export function exactInstant(value:string):string {
  const m=/^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.(\d{1,6}))?(Z|[+-]\d\d:\d\d)$/.exec(value);
  if(!m||!Number.isFinite(Date.parse(value)))invalid('Invalid original preparation time.');
  // The UI creates UTC. Server Pydantic emits Z or +00:00 for that same instant.
  if(m[3]!=='Z'&&m[3]!=='+00:00')invalid('Retained preparation time must be UTC.');
  return m[1]+'.'+(m[2]??'').padEnd(6,'0')+'Z';
}
export function sameRequest(a:ManualRequest,b:ManualRequest):boolean {
  return same({...a,createdAt:exactInstant(a.createdAt)},{...b,createdAt:exactInstant(b.createdAt)});
}

export class ManualApiError extends LiveApiError {
  readonly unknownOutcome:boolean;readonly verifiedZero:boolean;
  constructor(message:string,status:number,code:string|null=null,unknown=true,zero=false){
    super(message,status,{code});this.unknownOutcome=unknown;this.verifiedZero=zero;
  }
}
function invalid(message='Native manual response is unverified. Retain the original request.'):never{throw new ManualApiError(message,0);}
const zeroCodes=new Set(['manual_parent_stale','manual_source_authority_stale','manual_review_expired','manual_authority_changed',
  'manual_document_changed','manual_run_changed','manual_body_changed','manual_source_coordinates_changed','manual_profile_transition_required',
  'profile_transition_parent_stale','profile_transition_review_expired','profile_transition_already_adopted_without_receipt']);
async function post(path:string,body:unknown):Promise<Record<string,unknown>>{
  const result=await authenticatedApiFetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const generation=getNativeGraphAccessGeneration();
  if(result.requestEpoch!==generation)invalid('Graph authorization changed. The original request is retained.');
  let value:unknown;
  try{value=await result.response.json();}catch{invalid();}
  if(generation!==getNativeGraphAccessGeneration())invalid('Graph authorization changed during response decoding.');
  if(!result.response.ok){
    const d=record(value)&&record(value.detail)?value.detail:{};
    const code=typeof d.code==='string'?d.code:null;
    throw new ManualApiError(typeof d.message==='string'?d.message:'Native operation refused. Keep its original request.',
      result.response.status,code,d.outcome_unknown!==false,
      result.response.status===409&&d.outcome_unknown===false&&code!==null&&zeroCodes.has(code));
  }
  if(!record(value))invalid();return value;
}
export function assertSource(v:unknown):asserts v is ManualSource{
  if(!record(v)||!text(v.managedWorldId)||!text(v.nativeWorldId)||!positive(v.bindingVersion)||!uuid(v.documentId)
    ||!positive(v.documentRevision)||!digest(v.bodySha256)||!uuid(v.runId)||!positive(v.runRevision)
    ||!text(v.appSourceArtifactId)||!uuid(v.appSourceRevisionId)||!digest(v.spanIndexSha256))invalid('Saved source coordinates are invalid.');
}
export function assertWitness(v:unknown):asserts v is Witness{
  if(!record(v)||!text(v.sourceSpanRefId)||!Number.isSafeInteger(v.startByte)||Number(v.startByte)<0
    ||!Number.isSafeInteger(v.endByte)||Number(v.endByte)<=Number(v.startByte)||!digest(v.sliceSha256))invalid('Exact source witness is invalid.');
}
export function assertRequest(v:unknown):asserts v is ManualRequest{
  if(!record(v)||v.schema!=='dmb_native_manual_prepare_v1'||!uuid(v.operationId)||!instant(v.createdAt)
    ||!text(v.expectedParentRevisionId)||!nonnegative(v.expectedSourceAuthorityEpoch)||!record(v.operation))invalid();
  assertSource(v.source);assertWitness(v.witness);
  const o=v.operation;
  if(o.kind==='object'){
    if(!text(o.name)||!text(o.objectKind)||!(o.role===null||typeof o.role==='string')||!Array.isArray(o.aliases)
      ||o.aliases.some(x=>typeof x!=='string')||!(o.description===null||typeof o.description==='string'))invalid();
  }else if(o.kind==='relationship'){
    for(const e of [o.source,o.target])if(!record(e)||!text(e.entityId)||!text(e.name)||!text(e.objectKind))invalid();
    if(!record(o.source)||!record(o.target)||o.source.entityId===o.target.entityId||!text(o.predicate)
      ||!(o.label===null||typeof o.label==='string')||!(o.description===null||typeof o.description==='string'))invalid();
  }else invalid();
}
function refs(d:unknown,p:unknown){
  return record(d)&&text(d.domain_id)&&text(d.domain_revision)&&digest(d.descriptor_sha256)
    &&record(p)&&text(p.profile_id)&&text(p.profile_revision)&&digest(p.descriptor_sha256);
}
export function assertManualPlan(v:unknown,request?:ManualRequest):asserts v is ManualPlan{
  if(!record(v)||v.schema!=='dmb_native_manual_plan_v1'||!text(v.token)||!/^[\x00-\x7f]+$/.test(v.token)
    ||!text(v.preparedBy)||!instant(v.expiresAt)||typeof v.preparedChangeJson!=='string'
    ||!refs(v.domainContractRef,v.semanticProfileRef)||!record(v.publication))invalid();
  assertRequest(v.review);
  const r=v.review,p=v.publication;
  if(request&&!sameRequest(r,request))invalid('Preview changed the original request.');
  if(p.schema_version!=='dm_governed_native_source_publication_v1'||p.space_id!==r.source.nativeWorldId||p.publication_id!==r.operationId
    ||p.expected_parent_revision_id!==r.expectedParentRevisionId||!positive(p.expected_source_authority_epoch)||p.expected_source_authority_epoch!==r.expectedSourceAuthorityEpoch
    ||p.expected_body_sha256!==r.source.bodySha256||!text(p.original_admission_id)||!text(p.source_artifact_id)||!text(p.source_revision_id)
    ||(typeof p.created_at!=='string'||exactInstant(p.created_at)!==exactInstant(r.createdAt))||!record(p.contribution)||p.contribution.space_id!==p.space_id
    ||!Array.isArray(p.contribution.items)||!p.contribution.items.length||!Array.isArray(p.aliases)||!Array.isArray(p.dispositions)
    ||!record(p.evidence)||!['new_intervals','existing_support'].includes(String(p.evidence.mode))
    ||Date.parse(v.expiresAt)<=Date.parse(r.createdAt))invalid();
  try{if(!record(JSON.parse(v.preparedChangeJson)))invalid();}catch{invalid();}
  if(p.evidence.mode==='new_intervals'){
    if(!Array.isArray(p.evidence.spans)||p.evidence.spans.length!==1)invalid();
    const s=p.evidence.spans[0];
    if(!record(s)||s.evidence_role!=='support'||s.start_byte!==r.witness.startByte||s.end_byte!==r.witness.endByte||s.expected_slice_sha256!==r.witness.sliceSha256)invalid();
  }else{
    if(!Array.isArray(p.evidence.support)||p.evidence.support.length!==1)invalid();
    const s=p.evidence.support[0],q=record(s)?s.proof:null;
    if(!record(s)||!record(q)||!text(s.evidence_ref_id)||q.evidence_ref_id!==s.evidence_ref_id||q.span_id!==s.span_id
      ||q.source_revision_id!==p.source_revision_id||q.start_byte!==r.witness.startByte||q.end_byte!==r.witness.endByte
      ||q.slice_sha256!==r.witness.sliceSha256||!positive(s.proof_authority_epoch))invalid();
  }
}
export function assertProfilePlan(v:unknown,request?:ProfileRequest):asserts v is ProfilePlan{
  if(!record(v)||v.schema!=='dmb_native_profile_transition_plan_v1'||!text(v.managedWorldId)||!text(v.nativeWorldId)
    ||!positive(v.bindingVersion)||!digest(v.parentPayloadSha256)||!text(v.preparedBy)||!instant(v.expiresAt)
    ||!text(v.token)||!/^[\x00-\x7f]+$/.test(v.token)||!record(v.request))invalid();
  const r=v.request;
  if(r.schema_version!=='dm_knowledge_profile_transition_v1'||r.space_id!==v.nativeWorldId||!text(r.publication_id)
    ||!text(r.expected_parent_revision_id)||!instant(r.created_at)||!refs(r.domain_contract_ref,r.from_profile_ref)
    ||!record(r.to_profile_ref)||r.to_profile_ref.profile_revision!=='4'||!digest(r.to_profile_ref.descriptor_sha256)
    ||!record(r.from_profile_ref)||!['1','2','3'].includes(String(r.from_profile_ref.profile_revision))
    ||Date.parse(v.expiresAt)<=Date.parse(r.created_at))invalid();
  if(request&&(request.managedWorldId!==v.managedWorldId||request.expectedNativeWorldId!==v.nativeWorldId
    ||request.expectedBindingVersion!==v.bindingVersion||request.expectedParentRevisionId!==r.expected_parent_revision_id
    ||request.publicationId!==r.publication_id))invalid('Profile preview changed the retained operation.');
}
export function assertContext(v:unknown,selector:ManualSelector):asserts v is ManualContext{
  if(!record(v))invalid();assertSource(v.source);
  const s=v.source;
  if(v.schema!=='dmb_native_manual_context_result_v1'||s.managedWorldId!==selector.managedWorldId||s.documentId!==selector.documentId
    ||s.documentRevision!==selector.documentRevision||s.bodySha256!==selector.bodySha256||s.runId!==selector.runId||s.runRevision!==selector.runRevision
    ||!text(v.parentRevisionId)||!positive(v.sourceAuthorityEpoch)||typeof v.manualCapability!=='boolean'||v.transitionRequired!==!v.manualCapability
    ||!refs(v.domainContractRef,v.semanticProfileRef)||!record(v.nativeSource)||v.nativeSource.state!=='admitted'
    ||v.nativeSource.world_id!==s.managedWorldId||v.nativeSource.space_id!==s.nativeWorldId||v.nativeSource.body_sha256!==s.bodySha256
    ||!text(v.nativeSource.admission_id)||!text(v.nativeSource.source_artifact_id)||!text(v.nativeSource.source_revision_id)
    ||!Array.isArray(v.spans)||!v.spans.length||!record(v.kinds)||Object.keys(v.kinds).length!==13
    ||Object.values(v.kinds).some(x=>!text(x))||!record(v.predicates)||Object.keys(v.predicates).length!==45)invalid();
  for(const w of v.spans)assertWitness(w);
  for(const p of Object.values(v.predicates))if(!record(p)||!text(p.term)||typeof p.reverseEndpoints!=='boolean')invalid();
}
export async function readManualContext(selector:ManualSelector):Promise<ManualContext>{
  const v=await post('/api/live/graph-authoring/native-manual/context',selector);assertContext(v,selector);return clone(v);
}
export async function verifyManualPlan(plan:ManualPlan){
  assertManualPlan(plan);
  const c=plan.publication.contribution;
  if(!record(c)||!Array.isArray(c.diagnostics))invalid();
  const seals=c.diagnostics.filter(d=>record(d)&&record(d.payload)&&'manual_review_sha256' in d.payload);
  if(seals.length!==1||!record(seals[0])||!record(seals[0].payload))invalid();
  const seal=seals[0].payload;
  if(seal.prepared_by!==plan.preparedBy||seal.manual_review_sha256!==await sha256(stable(plan.review))
    ||seal.prepared_change_sha256!==await sha256(plan.preparedChangeJson))invalid('Saved original review commitments do not match.');
}
export async function prepareManual(request:ManualRequest):Promise<ManualPlan>{
  assertRequest(request);const v=await post('/api/live/graph-authoring/native-manual/prepare',request);
  assertManualPlan(v.plan,request);await verifyManualPlan(v.plan);return clone(v.plan);
}
export function assertManualReceipt(v:unknown,plan:ManualPlan):asserts v is ManualReceipt{
  assertManualPlan(plan);if(!record(v))invalid();const r=v.receipt,p=plan.publication;
  if(v.schema!=='dmb_native_manual_receipt_v1'||typeof v.recovered!=='boolean'||!record(r)
    ||r.schema_version!=='dm_governed_native_source_publication_receipt_v1'||r.space_id!==p.space_id||r.publication_id!==p.publication_id
    ||r.original_admission_id!==p.original_admission_id||r.source_artifact_id!==p.source_artifact_id||r.source_revision_id!==p.source_revision_id
    ||!digest(r.intent_sha256)||!digest(r.original_admission_sha256)||!record(p.evidence)||r.mode!==p.evidence.mode
    ||r.source_authority_epoch_before!==p.expected_source_authority_epoch
    ||r.source_authority_epoch_after!==Number(r.source_authority_epoch_before)+(r.mode==='new_intervals'?1:0)
    ||!record(r.publication_receipt)||r.publication_receipt.space_id!==p.space_id||r.publication_receipt.publication_id!==p.publication_id
    ||r.publication_receipt.expected_parent_revision_id!==p.expected_parent_revision_id||!text(r.publication_receipt.published_revision_id)
    ||!digest(r.publication_receipt.graph_payload_sha256)||!digest(r.publication_receipt.command_sha256)
    ||!Array.isArray(r.result_bindings)||!r.result_bindings.length)invalid();
  const contribution=p.contribution;
  if(!record(contribution)||!Array.isArray(contribution.items)||!Array.isArray(p.dispositions))invalid();
  const accepted=new Set<unknown>();
  for(const d of p.dispositions)if(record(d)&&d.disposition==='accepted')accepted.add(d.item_id);
  const expected=new Map<string,string>();
  for(const item of contribution.items){if(!record(item))invalid();if(!accepted.has(item.item_id))continue;
    if(!text(item.client_op_id))invalid();
    expected.set(item.client_op_id,item.kind==='create_entity'?'entity':'assertion');}
  if(expected.size!==r.result_bindings.length)invalid();
  const ids=new Set<string>();
  for(const b of r.result_bindings){if(!record(b)||!text(b.client_op_id)||ids.has(b.client_op_id)||!text(b.durable_id)
    ||expected.get(b.client_op_id)!==b.result_kind)invalid();ids.add(b.client_op_id);}
  if(!Array.isArray(r.proofs)||!Array.isArray(r.bindings)||!Array.isArray(r.reused_support))invalid();
  if(r.mode==='new_intervals'){
    if(r.proofs.length!==1||r.bindings.length!==1||r.reused_support.length!==0)invalid();
    const q=r.proofs[0],b=r.bindings[0],w=plan.review.witness;
    if(!record(q)||!record(b)||q.evidence_ref_id!==b.evidence_ref_id||q.span_id!==b.span_id||q.source_revision_id!==p.source_revision_id
      ||q.start_byte!==w.startByte||q.end_byte!==w.endByte||q.slice_sha256!==w.sliceSha256)invalid();
  }else if(r.proofs.length||r.bindings.length||!same(r.reused_support,p.evidence.support))invalid();
}
export async function confirmManual(plan:ManualPlan):Promise<ManualReceipt>{
  await verifyManualPlan(plan);const v=await post('/api/live/graph-authoring/native-manual/confirm',{schema:'dmb_native_manual_confirm_v1',plan});
  assertManualReceipt(v,plan);return clone(v);
}
export function assertProfileRequest(v:unknown):asserts v is ProfileRequest{
  if(!record(v)||v.schema!=='dmb_native_profile_transition_prepare_v1'||!text(v.managedWorldId)||!text(v.expectedNativeWorldId)
    ||!positive(v.expectedBindingVersion)||!text(v.expectedParentRevisionId)||!text(v.publicationId))invalid();
}
export async function prepareProfile(request:ProfileRequest):Promise<ProfilePlan>{
  const v=await post('/api/live/graph-authoring/native-profile-transition/prepare',request);assertProfilePlan(v.plan,request);return clone(v.plan);
}
export function assertProfileReceipt(v:unknown,plan:ProfilePlan):asserts v is ProfileReceipt{
  assertProfilePlan(plan);if(!record(v))invalid();const r=v.receipt,q=plan.request;
  if(v.schema!=='dmb_native_profile_transition_receipt_v1'||typeof v.recovered!=='boolean'||!record(r)||r.space_id!==plan.nativeWorldId
    ||r.publication_id!==q.publication_id||r.expected_parent_revision_id!==q.expected_parent_revision_id||!text(r.published_revision_id)
    ||r.graph_payload_sha256!==plan.parentPayloadSha256||!digest(r.command_sha256))invalid();
}
export async function confirmProfile(plan:ProfilePlan):Promise<ProfileReceipt>{
  assertProfilePlan(plan);const v=await post('/api/live/graph-authoring/native-profile-transition/confirm',{schema:'dmb_native_profile_transition_confirm_v1',plan});
  assertProfileReceipt(v,plan);return clone(v);
}
export function profileRequest(context:ManualContext):ProfileRequest{return {schema:'dmb_native_profile_transition_prepare_v1',
  managedWorldId:context.source.managedWorldId,expectedNativeWorldId:context.source.nativeWorldId,
  expectedBindingVersion:context.source.bindingVersion,expectedParentRevisionId:context.parentRevisionId,publicationId:crypto.randomUUID()};}
