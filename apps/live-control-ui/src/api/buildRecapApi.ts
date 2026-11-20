import {authenticatedApiFetch, LiveApiError} from './liveApi';
import type {ExtractionRunStatusResponse} from './types';
import type {SessionEvidenceRef} from '../playSurface/review/sessionEvidenceApi';

export interface BuildRecapLaunchRequest {
  request_id: string; document_id: string; expected_revision: number; expected_content_sha256: string;
  managed_world_id: string; campaign_id: string; session: number; session_evidence: SessionEvidenceRef[];
}
export interface BuildRecapSettings {worldId: string; campaignId: string; session: number; evidence: SessionEvidenceRef[]}
export const recapRecoveryKey = (worldId: string, documentId: string) => 'dmb.buildRecapLaunch.v1:'+JSON.stringify([worldId,documentId]);
export const recapHistoryKey = (worldId: string, documentId: string) => 'dmb.buildRecapHistory.v1:'+JSON.stringify([worldId,documentId]);
export function validRecapRequest(value: unknown): value is BuildRecapLaunchRequest {
  if (!value || typeof value !== 'object') return false;
  const r=value as BuildRecapLaunchRequest;
  const uuid=(s:unknown)=>typeof s==='string' && /^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$/.test(s);
  const name=(s:unknown)=>typeof s==='string' && /^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(s);
  if(Object.keys(r).some(key=>!['request_id','document_id','expected_revision','expected_content_sha256','managed_world_id','campaign_id','session','session_evidence'].includes(key)))return false;
  return uuid(r.request_id)&&uuid(r.document_id)&&Number.isInteger(r.expected_revision)&&r.expected_revision>0
    &&typeof r.expected_content_sha256==='string'&&/^[a-f0-9]{64}$/.test(r.expected_content_sha256)
    &&name(r.managed_world_id)&&name(r.campaign_id)&&Number.isInteger(r.session)&&r.session>0
    &&Array.isArray(r.session_evidence)&&r.session_evidence.length<=3&&r.session_evidence.every(p=>p!==null&&typeof p==='object'&&!Array.isArray(p)
      &&Object.keys(p).every(key=>['run_id','review_revision','sha256'].includes(key))&&uuid(p.run_id)&&Number.isInteger(p.review_revision)
      &&p.review_revision>0&&typeof p.sha256==='string'&&/^[a-f0-9]{64}$/.test(p.sha256));
}
const canonical=(value: unknown): string=>JSON.stringify(value,(_key,item)=>item&&typeof item==='object'&&!Array.isArray(item)
  ?Object.fromEntries(Object.keys(item).sort().map(key=>[key,item[key]])):item);
export function assertRecapLaunchBinding(request:BuildRecapLaunchRequest,response:ExtractionRunStatusResponse) {
  const lineage=response.run.lineage as Record<string,any>|undefined;
  if(response.run.source_domain!=='recap'||response.run.campaign_id!==request.campaign_id
    ||response.run.session_id!==`session-${request.session}`||!['recap_category_v1@1.0','recap_category_v2@2.0','recap_category_encounter_job_preview@2.0'].includes(response.run.profile_id ?? '')
    ||lineage?.build_launch?.schema!=='dmb_build_recap_launch_v1'
    ||response.run.profile_id!==`${lineage?.build_launch?.server_configuration?.profile_id}@${lineage?.build_launch?.server_configuration?.profile_version}`
    ||canonical(lineage?.build_launch?.request)!==canonical(request)
    ||lineage?.world_campaign_ingest_context?.managed_world_id!==request.managed_world_id) {
    throw new Error('The extraction does not match the saved Recap request and World.');
  }
}
async function read(path:string,init?:RequestInit):Promise<ExtractionRunStatusResponse>{
  const {response}=await authenticatedApiFetch(path,{...init,cache:'no-store',headers:{'Content-Type':'application/json'}});
  const body=await response.json();
  if(!response.ok)throw new LiveApiError(typeof body.detail==='string'?body.detail:'Recap extraction unavailable',response.status);
  return body;
}
export const launchBuildRecap=(request:BuildRecapLaunchRequest)=>read('/api/live/graph-preview/build-recap-launches',{
  method:'POST',body:JSON.stringify(request)});
export const recoverBuildRecap=(request:BuildRecapLaunchRequest)=>read(`/api/live/graph-preview/build-recap-launches/${encodeURIComponent(request.request_id)}?`+
  new URLSearchParams({document_id:request.document_id,managed_world_id:request.managed_world_id}));
