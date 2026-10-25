import {authenticatedApiFetch,LiveApiError} from './liveApi';
import type {WorkspaceDocumentRecord} from './types';
import type {SurfaceTextCapture} from '../surfaceInteraction/SurfaceSelectionActions';
export interface SavedExcerptOrigin {kind:"saved_page_excerpt";document_id:string;revision:number;content_sha256:string;line_start:number;line_end:number;selected_text:string}
export interface ConnectedPageIntent{
  operation_id:string;world_id:string;title:string;
  origin:(SurfaceTextCapture&{document_id:string;revision:number;content_sha256:string})|SavedExcerptOrigin;
  place:{node_id:string|null;label:string;kind:'location'};
  person:{node_id:string|null;label:string;kind:'npc'}|null;
  relationships:('owns'|'operates')[];mode:'scaffold'|'build_out';instructions:string;
}
export interface ConnectedPageOperation{
  schema:'dmb_connected_page_operation_v1'|'dmb_connected_page_operation_v2';operation_id:string;phase:'reserved'|'created'|'saved'|'prepared'|'complete';
  intent:ConnectedPageIntent;page:WorkspaceDocumentRecord|null;
  initial_source:{documentId:string;revision:number;contentSha256:string}|null;
  prepared:{confirm_token:string;assertions_preview:{summary:string}[]}|null;
  receipt:{committed:boolean;created_node_ids:Record<string,string>}|null;
  connections:{place_node_id:string;person_node_id:string|null;relationships:('owns'|'operates')[]}|null;
}
const uuid=(value:unknown)=>typeof value==='string'&&/^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$/i.test(value);
const hash=(value:unknown)=>typeof value==='string'&&/^[a-f0-9]{64}$/.test(value);
export const canonicalConnectedIntent=(value:unknown):string=>JSON.stringify(value,(_key,item)=>item&&typeof item==='object'&&!Array.isArray(item)
  ?Object.fromEntries(Object.keys(item).sort().map(key=>[key,item[key]])):item);
export function validConnectedPageIntent(value:unknown):value is ConnectedPageIntent{
  if(!value||typeof value!=='object'||Array.isArray(value))return false;
  const r=value as ConnectedPageIntent;
  const keys=(object:object,allowed:string[])=>Object.keys(object).every(key=>allowed.includes(key));
  const obj=(item:unknown,kind:string)=>!!item&&typeof item==='object'&&!Array.isArray(item)
    &&keys(item,['node_id','label','kind'])&&typeof (item as any).label==='string'&&!!(item as any).label.trim()
    &&(item as any).kind===kind&&((item as any).node_id==null||typeof (item as any).node_id==='string'&&!!(item as any).node_id);
  return keys(r,['operation_id','world_id','title','origin','place','person','relationships','mode','instructions'])
    &&uuid(r.operation_id)&&typeof r.world_id==='string'&&/^[a-z0-9][a-z0-9_-]{0,62}$/.test(r.world_id)
    &&typeof r.title==='string'&&!!r.title.trim()&&r.title.length<=200&&typeof r.instructions==='string'
    &&['scaffold','build_out'].includes(r.mode)&&obj(r.place,'location')&&(r.person===null||obj(r.person,'npc'))
    &&Array.isArray(r.relationships)&&r.relationships.length<=2&&r.relationships.every(p=>['owns','operates'].includes(p))
    &&new Set(r.relationships).size===r.relationships.length&&!!r.person===(r.relationships.length>0)
    &&!!r.origin&&typeof r.origin==='object'
    &&('kind' in r.origin? r.origin.kind==='saved_page_excerpt'&&keys(r.origin,['kind','document_id','revision','content_sha256','line_start','line_end','selected_text'])&&Number.isSafeInteger(r.origin.line_start)&&r.origin.line_start>0&&Number.isSafeInteger(r.origin.line_end)&&r.origin.line_end>=r.origin.line_start:keys(r.origin,['document_id','revision','content_sha256','editor_json','editor_sha256','selection_from','selection_to','selected_text']))
    &&uuid(r.origin.document_id)&&Number.isInteger(r.origin.revision)&&r.origin.revision>0&&hash(r.origin.content_sha256)
    &&('kind' in r.origin||typeof r.origin.editor_json==='string'&&r.origin.editor_json.length<=2_000_000&&hash(r.origin.editor_sha256)
    &&Number.isInteger(r.origin.selection_from)&&Number.isInteger(r.origin.selection_to)&&r.origin.selection_from>=0
    &&r.origin.selection_to>r.origin.selection_from)&&typeof r.origin.selected_text==='string'&&!!r.origin.selected_text.trim();
}
export function assertConnectedPageOperation(value:unknown,request:ConnectedPageIntent):ConnectedPageOperation{
  const r=value as ConnectedPageOperation;
  if(!r||r.schema!==('kind' in request.origin?'dmb_connected_page_operation_v2':'dmb_connected_page_operation_v1')||r.operation_id!==request.operation_id
    ||!validConnectedPageIntent(r.intent)||canonicalConnectedIntent(r.intent)!==canonicalConnectedIntent(request)
    ||!['reserved','created','saved','prepared','complete'].includes(r.phase))throw new Error('The returned page operation does not match this request. The original request is retained.');
  if(r.page&&(!uuid(r.page.document_id)||r.page.world_id!==request.world_id||r.page.campaign_id!==request.world_id
    ||r.page.kind!=='worldbuilding_source'||r.page.status!=='active'||r.page.connected_page_operation_id!==request.operation_id))throw new Error('The created page has a different owner.');
  if(r.phase!=='reserved'&&!r.page)throw new Error('The created page is missing.');
  if(['saved','prepared','complete'].includes(r.phase)&&(!r.initial_source||r.initial_source.documentId!==r.page?.document_id
    ||!hash(r.initial_source.contentSha256)||!Number.isInteger(r.initial_source.revision)||r.initial_source.revision<1))throw new Error('The initial page source is missing.');
  if(['prepared','complete'].includes(r.phase)&&(!r.prepared||typeof r.prepared.confirm_token!=='string'||!r.prepared.confirm_token
    ||!Array.isArray(r.prepared.assertions_preview)))throw new Error('The exact connection review is missing.');
  if(r.phase==='complete'){
    const ids=r.receipt?.created_node_ids;
    if(!r.receipt?.committed||!r.connections||r.connections.place_node_id!==(request.place.node_id||ids?.place)
      ||r.connections.person_node_id!==(request.person?(request.person.node_id||ids?.person):null)
      ||JSON.stringify(r.connections.relationships)!==JSON.stringify(request.relationships))throw new Error('The native connections were not acknowledged for this page.');
  }
  return r;
}
async function read(path:string,request:ConnectedPageIntent,init?:RequestInit){
  const {response}=await authenticatedApiFetch(path,{...init,cache:'no-store',headers:{'Content-Type':'application/json'}});
  const body=await response.json();
  if(!response.ok)throw new LiveApiError(typeof body.detail==='string'?body.detail:body.detail?.message||'The page operation is unavailable.',response.status);
  return assertConnectedPageOperation(body,request);
}
export const prepareConnectedPage=(request:ConnectedPageIntent)=>read('/api/live/connected-pages/prepare',request,{method:'POST',body:JSON.stringify(request)});
export const recoverConnectedPage=(request:ConnectedPageIntent)=>read('/api/live/connected-pages/'+encodeURIComponent(request.operation_id)+'?'+new URLSearchParams({world_id:request.world_id}),request);
export const confirmConnectedPage=(operation:ConnectedPageOperation)=>read('/api/live/connected-pages/confirm',operation.intent,{method:'POST',body:JSON.stringify({operation_id:operation.operation_id,world_id:operation.intent.world_id,confirm_token:operation.prepared!.confirm_token})});
/** Reopen a page's immutable association without replaying creation or generation. */
export async function readConnectedPageForPage(operationId:string,worldId:string,documentId:string){
  const {response}=await authenticatedApiFetch('/api/live/connected-pages/'+encodeURIComponent(operationId)+'?'+new URLSearchParams({world_id:worldId}),{cache:'no-store'});
  const body=await response.json();
  if(!response.ok)throw new LiveApiError(typeof body.detail==='string'?body.detail:'Page connections are unavailable.',response.status);
  if(!validConnectedPageIntent(body.intent)||body.operation_id!==operationId||body.intent.world_id!==worldId
    ||body.page?.document_id!==documentId)throw new Error('These connections belong to a different page.');
  return assertConnectedPageOperation(body,body.intent);
}
