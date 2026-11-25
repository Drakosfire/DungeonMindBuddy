import {authenticatedApiFetch, LiveApiError} from './liveApi';
import type {ExtractionRunStatusResponse} from './types';

export interface BuildWorldbuildingLaunchRequest {
  request_id:string; document_id:string; managed_world_id:string; expected_revision:number;
  expected_content_sha256:string; profile_id:string; profile_version:string;
}
export const worldbuildingRecoveryKey=(worldId:string,documentId:string)=>'dmb.buildWorldbuildingLaunch.v1:'+JSON.stringify([worldId,documentId]);
export function validWorldbuildingRequest(value:unknown):value is BuildWorldbuildingLaunchRequest {
  if(!value||typeof value!=='object'||Array.isArray(value))return false;
  const r=value as BuildWorldbuildingLaunchRequest;
  const uuid=(s:unknown)=>typeof s==='string'&&/^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$/.test(s);
  return Object.keys(r).sort().join(',')==='document_id,expected_content_sha256,expected_revision,managed_world_id,profile_id,profile_version,request_id'
    &&uuid(r.request_id)&&uuid(r.document_id)&&typeof r.managed_world_id==='string'&&/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(r.managed_world_id)
    &&Number.isSafeInteger(r.expected_revision)&&r.expected_revision>0&&typeof r.expected_content_sha256==='string'&&/^[a-f0-9]{64}$/.test(r.expected_content_sha256)
    &&((r.profile_id==='worldbuilding_shepherds_flock_v0'&&r.profile_version==='0.1')||(r.profile_id==='worldbuilding_gazetteer_v1'&&r.profile_version==='1.10'));
}
export function assertWorldbuildingLaunchBinding(request:BuildWorldbuildingLaunchRequest,response:ExtractionRunStatusResponse){
  const launch=response.run.lineage?.build_launch as {schema?:string;request?:BuildWorldbuildingLaunchRequest}|undefined;
  if(response.run.source_domain!=='worldbuilding'||response.run.profile_id!==`${request.profile_id}@${request.profile_version}`
    ||launch?.schema!=='dmb_build_worldbuilding_launch_v1'||!validWorldbuildingRequest(launch.request)
    ||Object.keys(request).some(key=>request[key as keyof BuildWorldbuildingLaunchRequest]!==launch.request?.[key as keyof BuildWorldbuildingLaunchRequest]))
    throw new Error('The extraction does not match the saved Worldbuilding request and World.');
}
async function read(path:string,init?:RequestInit):Promise<ExtractionRunStatusResponse>{
  const {response}=await authenticatedApiFetch(path,{...init,cache:'no-store',headers:{'Content-Type':'application/json'}});
  const body=await response.json();
  if(!response.ok)throw new LiveApiError(typeof body.detail==='string'?body.detail:'Worldbuilding extraction unavailable',response.status);
  return body;
}
export const launchBuildWorldbuilding=(request:BuildWorldbuildingLaunchRequest)=>read('/api/live/graph-preview/build-worldbuilding-launches',{method:'POST',body:JSON.stringify(request)});
export const recoverBuildWorldbuilding=(request:BuildWorldbuildingLaunchRequest)=>read(`/api/live/graph-preview/build-worldbuilding-launches/${encodeURIComponent(request.request_id)}?`+new URLSearchParams({document_id:request.document_id,managed_world_id:request.managed_world_id}));
