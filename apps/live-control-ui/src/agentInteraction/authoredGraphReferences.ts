import type {AuthoredGraphReferenceV1, AuthoredGraphReferencesV1} from '../api/types';
import {exact, canonical} from '../shared/sourcePassageProtocol';

const fields=['schema','managed_world_id','native_world_id','binding_version','graph_revision','node_id','label'];
export function isAuthoredGraphReference(v:unknown, worldId?:string):v is AuthoredGraphReferenceV1 {
  return exact(v,fields)&&v.schema==='dmb_authored_graph_reference_v1'
    &&['managed_world_id','native_world_id','graph_revision','node_id','label'].every(k=>typeof v[k]==='string'&&(v[k] as string).trim())
    &&Number.isSafeInteger(v.binding_version)&&(v.binding_version as number)>0
    &&(worldId===undefined||v.managed_world_id===worldId);
}
export function referenceIdentity(ref:AuthoredGraphReferenceV1) {
  return canonical([ref.managed_world_id,ref.native_world_id,ref.node_id]);
}
function basis(ref:AuthoredGraphReferenceV1) {const {label:_,...identity}=ref;return canonical(identity);}
export function mergeAuthoredReferences(...groups:(readonly AuthoredGraphReferenceV1[])[]):AuthoredGraphReferenceV1[] {
  const found=new Map<string,AuthoredGraphReferenceV1>();
  for(const group of groups)for(const ref of group){
    if(!isAuthoredGraphReference(ref))throw new Error('Invalid Graph reference. Your selection was retained.');
    const key=referenceIdentity(ref),old=found.get(key);
    if(old&&basis(old)!==basis(ref))throw new Error('The same Graph object has conflicting selection snapshots. Choose it again.');
    if(!old)found.set(key,ref);
  }
  return [...found.values()];
}
export function isAuthoredGraphReferenceList(v:unknown,worldId?:string):v is AuthoredGraphReferenceV1[] {
  if(!Array.isArray(v)||!v.every(ref=>isAuthoredGraphReference(ref,worldId)))return false;
  try{return mergeAuthoredReferences(v).length===v.length;}catch{return false;}
}
export function isAuthoredGraphReferences(v:unknown,worldId?:string):v is AuthoredGraphReferencesV1 {
  return exact(v,['schema','references'])&&v.schema==='dmb_authored_graph_references_v1'&&isAuthoredGraphReferenceList(v.references,worldId);
}
export function authoredGraphReferences(references:AuthoredGraphReferenceV1[]):AuthoredGraphReferencesV1 {
  return {schema:'dmb_authored_graph_references_v1',references:mergeAuthoredReferences(references)};
}

export type ComposerReferenceDraft={serialized:string|null;references:AuthoredGraphReferenceV1[];submittedTurnId:string|null};
export const composerReferenceKey=(world:string,page:string)=>`dmb:authored-graph-composer:v1:${JSON.stringify([world,page])}`;
export function readComposerReferences(storage:Pick<Storage,'getItem'>,world:string,page:string):ComposerReferenceDraft {
 const serialized=storage.getItem(composerReferenceKey(world,page));
 if(serialized===null)return {serialized,references:[],submittedTurnId:null};
 const value:unknown=JSON.parse(serialized);
 if(!exact(value,['schema','world_id','document_id','references',...(value&&typeof value==='object'&&'schema' in value&&value.schema==='dmb_authored_graph_composer_v2'?['submitted_turn_id']:[])])||!['dmb_authored_graph_composer_v1','dmb_authored_graph_composer_v2'].includes(String(value.schema))||value.world_id!==world||value.document_id!==page||!isAuthoredGraphReferenceList(value.references,world)||value.schema==='dmb_authored_graph_composer_v2'&&!(value.submitted_turn_id===null||typeof value.submitted_turn_id==='string'&&/^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$/i.test(value.submitted_turn_id)))throw new Error('The local Graph reference draft could not be read. Its bytes were retained.');
 return {serialized,references:value.references,submittedTurnId:value.schema==='dmb_authored_graph_composer_v2'?value.submitted_turn_id as string|null:null};
}
export function writeComposerReferences(storage:Pick<Storage,'getItem'|'setItem'>,world:string,page:string,expected:string|null,references:AuthoredGraphReferenceV1[],submittedTurnId:string|null=null):ComposerReferenceDraft {
 if(submittedTurnId!==null&&!/^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$/i.test(submittedTurnId))throw new Error('Invalid composer submission identity.');
 if(!isAuthoredGraphReferenceList(references,world))throw new Error('Graph references belong to a different World or selection snapshot.');
 const key=composerReferenceKey(world,page);
 if(storage.getItem(key)!==expected)throw new Error('The Graph reference draft changed. Reopen the composer before changing it.');
 const serialized=JSON.stringify({schema:'dmb_authored_graph_composer_v2',world_id:world,document_id:page,references,submitted_turn_id:submittedTurnId});
 storage.setItem(key,serialized);
 if(storage.getItem(key)!==serialized)throw new Error('The exact Graph references could not be retained. Nothing was sent.');
 return {serialized,references,submittedTurnId};
}

const COMPOSER_RECOVERY_PREFIX='dmb:authored-graph-composer-recovery:v1:';
const composerRecoveryPrefix=(world:string,page:string)=>`${COMPOSER_RECOVERY_PREFIX}${JSON.stringify([world,page])}:`;
export function readComposerReferenceRecoveries(storage:Pick<Storage,'length'|'key'|'getItem'>,world:string,page:string):{key:string;raw:string}[]{
 const prefix=composerRecoveryPrefix(world,page),copies:{key:string;raw:string}[]=[];
 for(let i=0;i<storage.length;i++){
  const key=storage.key(i);if(!key?.startsWith(prefix))continue;
  const bytes=storage.getItem(key);if(bytes===null)continue;const value:unknown=JSON.parse(bytes);
  if(!/^[a-f0-9]{64}$/.test(key.slice(prefix.length))||!exact(value,['schema','world_id','document_id','original_bytes'])||value.schema!=='dmb_authored_graph_composer_recovery_v1'||value.world_id!==world||value.document_id!==page||typeof value.original_bytes!=='string')throw new Error('A retained reference draft needs inspection. Its bytes were preserved.');
  copies.push({key,raw:value.original_bytes});
 }
 return copies.sort((a,b)=>a.key.localeCompare(b.key));
}
/** Explicit author recovery only: preserve exact raw bytes before replacing that unchanged copy. */
export async function recoverComposerReferences(storage:Pick<Storage,'getItem'|'setItem'>,world:string,page:string,expectedRaw:string):Promise<ComposerReferenceDraft>{
 // A readable newer selection must be edited through the ordinary picker instead.
 if(storage.getItem(composerReferenceKey(world,page))!==expectedRaw)throw new Error('The reference draft changed. No recovery copy was replaced.');
 try{readComposerReferences(storage,world,page);}catch{ // Only an unreadable snapshot can enter this path.
  const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(expectedRaw))),b=>b.toString(16).padStart(2,'0')).join('');
  const key=composerRecoveryPrefix(world,page)+digest;
  const bytes=JSON.stringify({schema:'dmb_authored_graph_composer_recovery_v1',world_id:world,document_id:page,original_bytes:expectedRaw});
  const previous=storage.getItem(key);if(previous!==null&&previous!==bytes)throw new Error('The retained reference draft differs. Both copies were preserved.');
  storage.setItem(key,bytes);if(storage.getItem(key)!==bytes)throw new Error('The unreadable reference draft could not be retained. Nothing was replaced.');
  return writeComposerReferences(storage,world,page,expectedRaw,[]);
 }
 throw new Error('This reference draft is readable. Choose references normally.');
}
