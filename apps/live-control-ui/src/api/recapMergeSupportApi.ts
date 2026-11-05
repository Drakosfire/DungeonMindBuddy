import {authenticatedApiFetch,LiveApiError} from './liveApi';
import type {ExactRunCandidateProjection} from './exactRunCandidateProjectionApi';
import type {RecapNativeReview} from './recapNativeReviewApi';
import {supportEvidenceIds,witnessByteRange} from '../ingestion/recapMergeSelections';
export interface RecapSupportRequest {
 managed_world_id:string;extension_id:string;original_admission_id:string;source_artifact_id:string;source_revision_id:string;expected_body_sha256:string;expected_parent_revision_id:string;expected_source_authority_epoch:number;created_at:string;
 spans:Array<{client_ref:string;evidence_role:'support';start_byte:number;end_byte:number;expected_slice_sha256:string}>;
}
const hash=async(text:string)=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text)))].map(n=>n.toString(16).padStart(2,'0')).join('');
export async function buildRecapSupportRequest(p:ExactRunCandidateProjection,r:RecapNativeReview):Promise<RecapSupportRequest|null> {
 const admission=r.native_context.source_admission;
 if(admission.state!=='admitted'||admission.opening_state!=='verified')throw new Error('Source evidence is not verified.');
 const ranges=new Map<string,ReturnType<typeof witnessByteRange>>();
 for(const record of [...p.nodes,...p.edges]) {
  if(!record.evidence.length)throw new Error('A displayed claim has no verified source witness. Nothing was published.');
  for(const w of record.evidence)if(!supportEvidenceIds(p,r,[w]).length){const span=witnessByteRange(p,w);if(!span.text.trim())throw new Error('A candidate support passage is empty.');ranges.set(`${span.start}:${span.end}`,span);}
 }
 if(!ranges.size)return null;
 if(!admission.admission_id||!admission.source_artifact_id||!admission.source_revision_id)throw new Error('The native source receipt is incomplete. Reload before merging.');
 const spans=await Promise.all([...ranges.values()].sort((a,b)=>a.start-b.start||a.end-b.end).map(async s=>({client_ref:`recap:${s.start}:${s.end}`,evidence_role:'support' as const,start_byte:s.start,end_byte:s.end,expected_slice_sha256:await hash(s.text)})));
 const identity=await hash(JSON.stringify([p.nativeWorldId,admission.admission_id,p.runId,p.runRevision,p.candidateSha256,p.spanIndexSha256,spans]));
 return {managed_world_id:p.managedWorldId,extension_id:'dungeonbuddy:recap-support:v1:'+identity,original_admission_id:admission.admission_id,source_artifact_id:admission.source_artifact_id,source_revision_id:admission.source_revision_id,expected_body_sha256:p.sourceSha256.slice(7),expected_parent_revision_id:r.native_context.revision_id,expected_source_authority_epoch:r.native_context.source_authority_epoch,created_at:new Date().toISOString(),spans};
}
export async function validateRecapSupportRequest(p:ExactRunCandidateProjection,r:RecapNativeReview,value:unknown):Promise<RecapSupportRequest> {
 const object=(v:unknown):v is Record<string,unknown>=>!!v&&typeof v==='object'&&!Array.isArray(v);
 const a=r.native_context.source_admission;
 const keys=new Set(['managed_world_id','extension_id','original_admission_id','source_artifact_id','source_revision_id','expected_body_sha256','expected_parent_revision_id','expected_source_authority_epoch','created_at','spans']);
 if(!object(value)||Object.keys(value).some(k=>!keys.has(k))||a.state!=='admitted'||a.opening_state!=='verified'||![a.admission_id,a.source_artifact_id,a.source_revision_id].every(v=>typeof v==='string'&&!!v)||value.managed_world_id!==p.managedWorldId||value.original_admission_id!==a.admission_id||value.source_artifact_id!==a.source_artifact_id||value.source_revision_id!==a.source_revision_id||value.expected_body_sha256!==p.sourceSha256.slice(7)||typeof value.expected_parent_revision_id!=='string'||!value.expected_parent_revision_id||!Number.isInteger(value.expected_source_authority_epoch)||Number(value.expected_source_authority_epoch)<1||typeof value.created_at!=='string'||!value.created_at.endsWith('Z')||!Number.isFinite(Date.parse(value.created_at))||!Array.isArray(value.spans)||!value.spans.length)throw new Error('The saved support request is invalid. It remains preserved; no write was sent.');
 const eligible=new Map<string,ReturnType<typeof witnessByteRange>>();
 for(const record of [...p.nodes,...p.edges])for(const w of record.evidence){const span=witnessByteRange(p,w);eligible.set(`${span.start}:${span.end}`,span);}
 const seen=new Set<string>();
 for(const s of value.spans) {
  if(!object(s)||Object.keys(s).length!==5||s.evidence_role!=='support'||!Number.isInteger(s.start_byte)||!Number.isInteger(s.end_byte)||typeof s.expected_slice_sha256!=='string')throw new Error('The saved support span is invalid. No write was sent.');
  const key=`${s.start_byte}:${s.end_byte}`,span=eligible.get(key);
  if(!span||seen.has(key)||s.client_ref!==`recap:${key}`||await hash(span.text)!==s.expected_slice_sha256)throw new Error('The saved support span is outside the reviewed candidate or its bytes changed. No write was sent.');
  seen.add(key);
 }
 const identity=await hash(JSON.stringify([p.nativeWorldId,a.admission_id,p.runId,p.runRevision,p.candidateSha256,p.spanIndexSha256,value.spans]));
 if(value.extension_id!=='dungeonbuddy:recap-support:v1:'+identity)throw new Error('The saved support identity changed. No write was sent.');
 return value as unknown as RecapSupportRequest;
}
export async function extendRecapSupport(p:ExactRunCandidateProjection,request:RecapSupportRequest) {
 const {response}=await authenticatedApiFetch('/api/live/source-statements/extend-evidence',{method:'POST',cache:'no-store',headers:{'Content-Type':'application/json'},body:JSON.stringify(request)});
 const value=await response.json();
 if(!response.ok)throw new LiveApiError(value?.detail?.message??'Source support could not be verified. Recover the exact request.',response.status,{code:value?.detail?.code});
 const r=value?.receipt;
 if(value?.status!=='committed'||r?.space_id!==p.nativeWorldId||r?.extension_id!==request.extension_id||r?.original_admission_id!==request.original_admission_id||r?.source_artifact_id!==request.source_artifact_id||r?.source_revision_id!==request.source_revision_id||!r?.publication_receipt?.published_revision_id||!Array.isArray(r.bindings)||r.bindings.length!==request.spans.length||!request.spans.every(s=>r.bindings.filter((b:{client_ref?:string;evidence_role?:string;evidence_ref_id?:string})=>b.client_ref===s.client_ref&&b.evidence_role==='support'&&typeof b.evidence_ref_id==='string'&&b.evidence_ref_id).length===1))throw new Error('Source support receipt is unverified. Recover the exact request before publication.');
 return value;
}
