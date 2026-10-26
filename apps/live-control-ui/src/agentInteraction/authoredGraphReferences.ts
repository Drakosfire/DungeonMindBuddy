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

export type ComposerReferenceDraft={serialized:string|null;references:AuthoredGraphReferenceV1[]};
export const composerReferenceKey=(world:string,page:string)=>`dmb:authored-graph-composer:v1:${JSON.stringify([world,page])}`;
export function readComposerReferences(storage:Pick<Storage,'getItem'>,world:string,page:string):ComposerReferenceDraft {
 const serialized=storage.getItem(composerReferenceKey(world,page));
 if(serialized===null)return {serialized,references:[]};
 const value:unknown=JSON.parse(serialized);
 if(!exact(value,['schema','world_id','document_id','references'])||value.schema!=='dmb_authored_graph_composer_v1'||value.world_id!==world||value.document_id!==page||!isAuthoredGraphReferenceList(value.references,world))throw new Error('The local Graph reference draft could not be read. Its bytes were retained.');
 return {serialized,references:value.references};
}
export function writeComposerReferences(storage:Pick<Storage,'getItem'|'setItem'>,world:string,page:string,expected:string|null,references:AuthoredGraphReferenceV1[]):ComposerReferenceDraft {
 if(!isAuthoredGraphReferenceList(references,world))throw new Error('Graph references belong to a different World or selection snapshot.');
 const key=composerReferenceKey(world,page);
 if(storage.getItem(key)!==expected)throw new Error('The Graph reference draft changed. Reopen the composer before changing it.');
 const serialized=JSON.stringify({schema:'dmb_authored_graph_composer_v1',world_id:world,document_id:page,references});
 storage.setItem(key,serialized);
 if(storage.getItem(key)!==serialized)throw new Error('The exact Graph references could not be retained. Nothing was sent.');
 return {serialized,references};
}
