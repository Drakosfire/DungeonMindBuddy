import {authenticatedApiFetch, LiveApiError} from './liveApi';
import {getSavedRecapRuns,getSavedRecapSource, type SavedRecapSource} from './savedRecapRunsApi';
import {getExactRunCandidateProjection,type ExactRunCandidateProjection} from './exactRunCandidateProjectionApi';
import {recapSourceTarget,type RecapSourceTarget} from './nativeRecapSourceApi';

export type Json = null | boolean | number | string | Json[] | {[key:string]:Json};
export type Packet = {[key:string]:Json};
export const record=(v:unknown):v is Record<string,unknown>=>v!==null&&typeof v==='object'&&!Array.isArray(v);
export const text=(v:unknown):v is string=>typeof v==='string'&&!!v&&v===v.trim();
export const digest=(v:unknown):v is string=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v);
export const positive=(v:unknown):v is number=>typeof v==='number'&&Number.isSafeInteger(v)&&v>0;
export const bare=(s:string)=>s.replace(/^sha256:/,'');
export const clone=<T,>(value:T):T=>JSON.parse(JSON.stringify(value)) as T;
export async function sha256(textOrBytes:string|Uint8Array):Promise<string>{
  const bytes=typeof textOrBytes==='string'?new TextEncoder().encode(textOrBytes):textOrBytes;
  const owned=new Uint8Array(bytes.length);owned.set(bytes);
  return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',owned)),x=>x.toString(16).padStart(2,'0')).join('');
}
function invalid(message='Native Recap response does not match the exact selected source, run and World.'):never{throw new LiveApiError(message,0);}
export interface Snapshot {
  worldId:string;nativeWorldId:string;bindingVersion:number;runId:string;runRevision:number;
  campaignId:string;sessionId:string;artifactId:string;sourceRevisionId:string;sourceSha256:string;
  candidateSha256:string;spanIndexSha256:string;sourceMarkdown:string;
}
export interface ReviewField {field:string;index?:number;value:Json}
export interface ReviewRecord {kind:'node'|'beat'|'edge'|'placement';record_id:string;fields?:Packet;
  selectable_facts?:ReviewField[];candidate:Packet;from_record_id?:string;to_record_id?:string;
  relationship_type?:string;held_reason?:string|null;required_claim_mode?:string}
export interface Metadata {evidence_ref_ids:string[];visibility:{kind:string;labels:string[]};
  epistemic_basis:string;claim_mode:string;standing:string;temporal_scope:Packet}
export interface Selection {kind:ReviewRecord['kind'];record_id:string;action:'create'|'use_existing'|'defer'|'reject';
  entity_id?:string;facts?:Array<{field:string;index?:number;metadata:Metadata}>;metadata?:Metadata}
export interface Coordinates {managed_world_id:string;campaign_id:string;run_id:string;expected_run_revision:number;
  candidate_sha256:string;source_admission_run_id:string;expected_parent_revision_id:string;expected_source_authority_epoch:number}
export interface Context {schema:'dmb_native_recap_review_context_v1';publication:'not_performed';binding:Record<string,unknown>;
  campaign_id:string;session_id:string;source_artifact_id:string;source_revision_id:string;source_sha256:string;
  native_source:{admission_id:string;source_artifact_id:string;source_revision_id:string;body_sha256:string};
  source_support:Array<{evidence_ref_id:string;start_byte:number;end_byte:number;text:string}>;
  records:ReviewRecord[];held_records:Json[];candidate_inventory:Packet;source_order:Packet;prepare_coordinates:Coordinates}
export interface Confirmation {envelope:Packet;prepared:Packet;token:string}
export interface Extension {managed_world_id:string;extension_id:string;original_admission_id:string;source_artifact_id:string;
  source_revision_id:string;expected_body_sha256:string;expected_parent_revision_id:string;expected_source_authority_epoch:number;
  created_at:string;spans:Array<{client_ref:string;evidence_role:'support';start_byte:number;end_byte:number;expected_slice_sha256:string}>}
export interface Witness {startByte:number;endByte:number;text:string;sha256:string}
export function targetFor(snapshot:Snapshot):RecapSourceTarget{
  return {managedWorldId:snapshot.worldId,nativeWorldId:snapshot.nativeWorldId,bindingVersion:snapshot.bindingVersion,
    campaignId:snapshot.campaignId,session:Number(snapshot.sessionId.slice(8)),sourceArtifactId:snapshot.artifactId,
    sourceRevisionId:snapshot.sourceRevisionId,contentSha256:snapshot.sourceSha256};
}
export async function loadRecapSnapshot(worldId:string,campaignId:string,runId:string,runRevision:number,candidateHash:string,artifactId:string,sourceHash:string):Promise<{snapshot:Snapshot;projection:ExactRunCandidateProjection;source:SavedRecapSource}>{
  const catalog=await getSavedRecapRuns(worldId,campaignId);
  const rows=catalog.runs.filter(r=>r.runId===runId);
  if(rows.length!==1||rows[0].runRevision!==runRevision||rows[0].sourceArtifactId!==artifactId||rows[0].sourceSha256!==bare(sourceHash))invalid();
  const source=await getSavedRecapSource(catalog,rows[0]);
  const target=recapSourceTarget(source);if(!target)invalid();
  const p=await getExactRunCandidateProjection(runId,worldId);
  if(p.runRevision!==runRevision||p.sourceArtifactId!==artifactId||bare(p.sourceSha256)!==target.contentSha256
    ||p.sourceRevisionId!==p.sourceSha256||bare(p.candidateSha256)!==bare(candidateHash)
    ||p.campaignId!==campaignId||p.sessionId!==source.run.sessionId||p.nativeWorldId!==target.nativeWorldId
    ||p.bindingVersion!==target.bindingVersion||p.sourceMarkdown!==source.sourceProse
    ||await sha256(p.sourceMarkdown)!==target.contentSha256)invalid();
  const snapshot:Snapshot={worldId,nativeWorldId:target.nativeWorldId,bindingVersion:target.bindingVersion,runId,runRevision,
    campaignId,sessionId:p.sessionId,artifactId,sourceRevisionId:target.sourceRevisionId,sourceSha256:target.contentSha256,
    candidateSha256:bare(p.candidateSha256),spanIndexSha256:bare(p.spanIndexSha256),sourceMarkdown:p.sourceMarkdown};
  return {snapshot,projection:p,source};
}
async function post(path:string,body:unknown):Promise<Record<string,unknown>>{
  const {response}=await authenticatedApiFetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  let value:unknown;try{value=await response.json();}catch{throw new LiveApiError('Native Recap outcome is unknown: invalid response. Retain and retry the exact request.',response.status);}
  if(!response.ok){const d=record(value)&&record(value.detail)?value.detail:{};throw new LiveApiError(typeof d.message==='string'?d.message:'Native Recap operation refused. Retain its exact request.',response.status,{code:typeof d.code==='string'?d.code:null});}
  if(!record(value))invalid();return value;
}
export async function readContext(s:Snapshot):Promise<Context>{
  const v=await post('/api/live/extract-promote/native-recap-context',{managed_world_id:s.worldId,campaign_id:s.campaignId,
    session_id:s.sessionId,run_id:s.runId,expected_run_revision:s.runRevision,candidate_sha256:s.candidateSha256,
    source_artifact_id:s.artifactId,source_revision_id:s.sourceRevisionId,source_sha256:s.sourceSha256});
  const c=v.prepare_coordinates,n=v.native_source,b=v.binding;
  if(v.schema!=='dmb_native_recap_review_context_v1'||v.publication!=='not_performed'||!record(c)||!record(n)||!record(b)
    ||b.managed_world_id!==s.worldId||b.native_world_id!==s.nativeWorldId||b.binding_version!==s.bindingVersion
    ||v.campaign_id!==s.campaignId||v.session_id!==s.sessionId||v.source_artifact_id!==s.artifactId
    ||v.source_revision_id!==s.sourceRevisionId||v.source_sha256!==s.sourceSha256
    ||c.managed_world_id!==s.worldId||c.campaign_id!==s.campaignId||c.run_id!==s.runId||c.expected_run_revision!==s.runRevision
    ||c.candidate_sha256!==s.candidateSha256||!text(c.source_admission_run_id)||!text(c.expected_parent_revision_id)||!positive(c.expected_source_authority_epoch)
    ||!text(n.admission_id)||!text(n.source_artifact_id)||!text(n.source_revision_id)||n.body_sha256!==s.sourceSha256
    ||!Array.isArray(v.records)||!Array.isArray(v.held_records)||!Array.isArray(v.source_support)||!record(v.candidate_inventory)||!record(v.source_order))invalid();
  const ids=new Set<string>();
  for(const r of v.records){if(!record(r)||!['node','beat','edge','placement'].includes(String(r.kind))||!text(r.record_id)||!record(r.candidate)||ids.has(r.kind+':'+r.record_id))invalid();ids.add(r.kind+':'+r.record_id);
    if(['node','beat'].includes(String(r.kind))&&(!Array.isArray(r.selectable_facts)||r.selectable_facts.some(f=>!record(f)||!text(f.field)||!('value' in f)||(f.field==='session_actions'?!Number.isSafeInteger(f.index)||Number(f.index)<0:f.index!==undefined))))invalid();}
  const bytes=new TextEncoder().encode(s.sourceMarkdown);
  const evidence=new Set<string>();
  for(const r of v.source_support){if(!record(r)||!text(r.evidence_ref_id)||evidence.has(r.evidence_ref_id)||!Number.isSafeInteger(r.start_byte)||!Number.isSafeInteger(r.end_byte)||Number(r.start_byte)<0||Number(r.end_byte)<=Number(r.start_byte)||Number(r.end_byte)>bytes.length||typeof r.text!=='string'||new TextDecoder('utf-8',{fatal:true}).decode(bytes.slice(Number(r.start_byte),Number(r.end_byte)))!==r.text)invalid();evidence.add(r.evidence_ref_id);}
  return clone(v) as unknown as Context;
}
export async function witnessFromLines(s:Pick<Snapshot,"sourceMarkdown"|"sourceSha256">,startLine:number,endLine:number,quote:string):Promise<Witness>{
  if(await sha256(s.sourceMarkdown)!==s.sourceSha256||!positive(startLine)||!positive(endLine)||endLine<startLine||!quote)invalid('Select exact nonempty evidence from the frozen source.');
  const lines=s.sourceMarkdown.match(/[^\r\n\v\f\u0085\u2028\u2029]*(?:\r\n|[\r\n\v\f\u0085\u2028\u2029]|$)/gu)?.filter(x=>x!=='')??[];
  if(endLine>lines.length||lines.join('')!==s.sourceMarkdown)invalid('Frozen source line bounds are invalid.');
  const paragraph=lines.slice(startLine-1,endLine).join(''),index=paragraph.indexOf(quote);
  if(index<0||paragraph.lastIndexOf(quote)!==index)invalid('Witness must occur exactly once within its frozen paragraph.');
  const prefix=lines.slice(0,startLine-1).join('')+paragraph.slice(0,index);
  const startByte=new TextEncoder().encode(prefix).length,raw=new TextEncoder().encode(quote),endByte=startByte+raw.length;
  if(new TextDecoder('utf-8',{fatal:true}).decode(new TextEncoder().encode(s.sourceMarkdown).slice(startByte,endByte))!==quote)invalid('Witness must end on exact UTF-8 character boundaries.');
  if(startByte===0&&endByte===new TextEncoder().encode(s.sourceMarkdown).length)invalid('The whole-body interval is context evidence. Explicitly choose a proper source subrange for support; it will not be trimmed or relabeled.');
  return {startByte,endByte,text:quote,sha256:await sha256(raw)};
}
export function buildExtension(s:Pick<Snapshot,"worldId"|"sourceSha256">,c:Pick<Context,"source_support"|"native_source"> & {prepare_coordinates:Pick<Coordinates,"expected_parent_revision_id"|"expected_source_authority_epoch">},w:Witness,id:string,createdAt:string):Extension{
  if(!text(id)||!Number.isFinite(Date.parse(createdAt))||!/(?:Z|[+-]\d\d:\d\d)$/.test(createdAt)||!digest(w.sha256)||w.startByte<0||w.endByte<=w.startByte)invalid();
  if(c.source_support.some(row=>row.start_byte===w.startByte&&row.end_byte===w.endByte))invalid('This exact support already exists. Select its actual evidence ID instead.');
  return {managed_world_id:s.worldId,extension_id:id,original_admission_id:c.native_source.admission_id,
    source_artifact_id:c.native_source.source_artifact_id,source_revision_id:c.native_source.source_revision_id,
    expected_body_sha256:s.sourceSha256,expected_parent_revision_id:c.prepare_coordinates.expected_parent_revision_id,
    expected_source_authority_epoch:c.prepare_coordinates.expected_source_authority_epoch,created_at:createdAt,
    spans:[{client_ref:'operator-selected-witness',evidence_role:'support',start_byte:w.startByte,end_byte:w.endByte,expected_slice_sha256:w.sha256}]};
}
export async function extendEvidence(s:Pick<Snapshot,"nativeWorldId">,request:Extension){
  const v=await post('/api/live/source-statements/extend-evidence',request),r=v.receipt;
  if(v.status!=='committed'||!record(r)||r.schema_version!=='dm_native_source_evidence_extension_receipt_v1'
    ||r.extension_id!==request.extension_id||r.original_admission_id!==request.original_admission_id
    ||r.source_artifact_id!==request.source_artifact_id||r.source_revision_id!==request.source_revision_id||r.space_id!==s.nativeWorldId
    ||!digest(r.original_admission_sha256)||!digest(r.intent_sha256)||!positive(r.source_authority_epoch)||r.source_authority_epoch<request.expected_source_authority_epoch
    ||!Array.isArray(r.bindings)||!Array.isArray(r.proofs)||r.bindings.length!==request.spans.length||r.proofs.length!==request.spans.length
    ||!record(r.publication_receipt)||r.publication_receipt.space_id!==s.nativeWorldId||r.publication_receipt.publication_id!==request.extension_id
    ||r.publication_receipt.expected_parent_revision_id!==request.expected_parent_revision_id||!text(r.publication_receipt.published_revision_id))invalid('Evidence extension response is unverified. Retain and retry the exact request.');
  const seen=new Set<string>(),evidence=new Set<string>();
  for(let i=0;i<request.spans.length;i++){
    const b=r.bindings[i],p=r.proofs[i],wanted=request.spans.find(span=>record(b)&&span.client_ref===b.client_ref);
    if(!record(b)||!record(p)||!wanted||seen.has(String(b.client_ref))||!text(b.span_id)||!text(b.evidence_ref_id)
      ||evidence.has(b.evidence_ref_id)||p.schema_version!=='dm_native_utf8_span_v1'||p.source_revision_id!==request.source_revision_id
      ||p.span_id!==b.span_id||p.evidence_ref_id!==b.evidence_ref_id||p.start_byte!==wanted.start_byte||p.end_byte!==wanted.end_byte
      ||p.slice_sha256!==wanted.expected_slice_sha256)invalid('Evidence extension span proof does not match the retained request.');
    seen.add(String(b.client_ref));evidence.add(b.evidence_ref_id);
  }
  return v;
}
export function assertConfirmation(packet:unknown,s:Snapshot):asserts packet is Confirmation{
  if(!record(packet)||!record(packet.envelope)||!record(packet.prepared)||!text(packet.token))invalid();
  const e=packet.envelope,r=e.review,b=e.binding,p=e.parent_context;
  if(e.purpose!=='dmb_native_recap_confirm_v1'||e.producer!=='dungeonbuddy:reviewed-recap'||!text(e.prepared_change_id)||!digest(e.prepared_digest)||!text(e.expires_at)
    ||!record(r)||!record(b)||!record(p)||r.managed_world_id!==s.worldId||r.run_id!==s.runId||r.expected_run_revision!==s.runRevision
    ||r.campaign_id!==s.campaignId||r.candidate_sha256!==s.candidateSha256||!text(r.source_admission_run_id)||!text(r.expected_parent_revision_id)||!positive(r.expected_source_authority_epoch)||!Array.isArray(r.selections)
    ||b.native_world_id!==s.nativeWorldId||b.binding_version!==s.bindingVersion||p.revision_id!==r.expected_parent_revision_id||p.source_epoch!==r.expected_source_authority_epoch)invalid('Saved confirmation does not match its retained Recap snapshot.');
}
function contains(actual:unknown,submitted:unknown):boolean{
  if(Array.isArray(submitted))return Array.isArray(actual)&&actual.length===submitted.length&&submitted.every((v,i)=>contains(actual[i],v));
  if(record(submitted))return record(actual)&&Object.entries(submitted).every(([k,v])=>contains(actual[k],v));
  return actual===submitted;
}
export async function prepareRecap(s:Snapshot,c:Context,selections:Selection[]){
  const request={...c.prepare_coordinates,selections};
  const v=await post('/api/live/extract-promote/native-prepare',request);
  if(v.publication!=='not_performed'||v.run_id!==s.runId||v.run_revision!==s.runRevision||v.candidate_sha256!==s.candidateSha256||v.source_revision_id!==s.sourceRevisionId||v.native_source_admission_id!==c.native_source.admission_id||v.expected_parent_revision_id!==request.expected_parent_revision_id||v.expected_source_authority_epoch!==request.expected_source_authority_epoch||!Array.isArray(v.records))invalid();
  if(v.status==='held'&&v.envelope===null&&v.prepared===null&&v.token===null)return {status:'held' as const,records:v.records};
  const packet={envelope:v.envelope,prepared:v.prepared,token:v.token};assertConfirmation(packet,s);
  if(v.status!=='prepared'||!contains(packet.envelope.review,request))invalid();
  return {status:'prepared' as const,packet:clone(packet),records:v.records};
}
export async function confirmRecap(s:Snapshot,packet:Confirmation){
  assertConfirmation(packet,s);const v=await post('/api/live/extract-promote/native-confirm',packet),r=v.result,e=packet.envelope;
  const review=e.review as Packet;
  if(v.status!=='committed'||typeof v.recovered!=='boolean'||!record(r)||!text(r.child_revision_id)||r.prepared_change_id!==e.prepared_change_id
    ||r.dungeonmind_publication_id!==e.prepared_change_id||r.expected_parent_revision_id!==review.expected_parent_revision_id)invalid('Confirmation outcome is unverified. Retain and retry the exact packet.');
  return v;
}
