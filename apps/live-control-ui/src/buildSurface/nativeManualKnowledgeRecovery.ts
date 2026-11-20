/** Browser state is an untrusted journal, not a receipt or source authority. */
import {assertManualPlan,assertProfilePlan,assertRequest,assertManualReceipt,assertProfileReceipt,assertProfileRequest,verifyManualPlan,clone,digest,record,sameRequest,same,sha256,text,uuid} from '../api/nativeManualKnowledgeApi';
import type {NativeWorldSourceAdmissionStatus} from '../api/types';
import type {ManualReceipt,ProfileReceipt} from '../api/nativeManualKnowledgeTypes';
import type {AdmissionTarget,ManualRequest,ManualPlan,ProfileRequest,ProfilePlan} from '../api/nativeManualKnowledgeTypes';
import {readKnowledgeRecovery,type ManualKnowledgeRecovery,type ManualKnowledgeScope} from './buildManualKnowledge';

export type Scope={worldId:string;documentId:string};
export type Operation=
  | {stage:'manual';request:ManualRequest;plan:ManualPlan|null;witnessText:string}
  | {stage:'profile';request:ProfileRequest;plan:ProfilePlan|null}
  | {stage:'admission';target:AdmissionTarget};
export interface Recovery {schema:'dmb_native_manual_recovery_v1';scope:Scope;operation:Operation;
  submitted:boolean;everUnknown:boolean;attempts:number;zeroConfirmed:boolean;receipt:ManualReceipt|ProfileReceipt|NativeWorldSourceAdmissionStatus|null}
export interface Located {key:string;raw:string;value:Recovery}
export interface LegacyLocated {key:string;raw:string;value:ManualKnowledgeRecovery}
const PREFIX='dmb.nativeManualKnowledge.v1:',OLD='dmb.buildManualKnowledge.v1:';
export const worldLockKey=(world:string)=>'dmb.nativeManualKnowledge.coord.v1:'+world;
export const recoveryKey=(s:Scope)=>PREFIX+JSON.stringify([s.worldId,s.documentId]);
function refuse(message='Saved manual authoring is invalid or conflicts. It is retained; no request was sent.'):never{throw new Error(message);}
export function uncertain(r:Recovery){return r.everUnknown||(r.submitted&&!r.zeroConfirmed&&r.receipt===null);}
export function validateRecovery(v:unknown,s:Scope):asserts v is Recovery{
  if(!record(v)||v.schema!=='dmb_native_manual_recovery_v1'||!record(v.scope)||v.scope.worldId!==s.worldId||v.scope.documentId!==s.documentId
    ||typeof v.submitted!=='boolean'||typeof v.everUnknown!=='boolean'||typeof v.zeroConfirmed!=='boolean'
    ||!Number.isSafeInteger(v.attempts)||Number(v.attempts)<0||!(v.receipt===null||record(v.receipt))||!record(v.operation))refuse();
  const op=v.operation;
  if(v.everUnknown&&v.zeroConfirmed)refuse();
  if(op.stage==='manual'){
    assertRequest(op.request);const r=op.request;
    if(r.source.managedWorldId!==s.worldId||r.source.documentId!==s.documentId||typeof op.witnessText!=='string')refuse();
    if(op.plan!==null){assertManualPlan(op.plan);if(!sameRequest(op.plan.review,r))refuse();}
    if(v.submitted&&op.plan===null)refuse();
    if(v.receipt!==null){if(op.plan===null)refuse();assertManualReceipt(v.receipt,op.plan);}
  }else if(op.stage==='profile'){
    assertProfileRequest(op.request);if(op.request.managedWorldId!==s.worldId)refuse();
    if(op.plan!==null)assertProfilePlan(op.plan,op.request);
    if(v.submitted&&op.plan===null)refuse();
    if(v.receipt!==null){if(op.plan===null)refuse();assertProfileReceipt(v.receipt,op.plan);}
  }else if(op.stage==='admission'){
    const t=op.target;if(!record(t)||t.worldId!==s.worldId||t.documentId!==s.documentId||!uuid(t.documentId)
      ||!Number.isSafeInteger(t.revision)||Number(t.revision)<1||!digest(t.bodySha256))refuse();
    if(v.receipt!==null){const a=v.receipt;if(!record(a)||a.schema_version!=='dmb_native_world_source_admission_status_v1'||a.state!=='admitted'||a.world_id!==s.worldId||a.document_id!==s.documentId
      ||a.loaded_revision!==t.revision||a.body_sha256!==t.bodySha256||!text(a.admission_id)||!text(a.space_id)
      ||!text(a.source_artifact_id)||!text(a.source_revision_id))refuse();}
  }else refuse();
}
export async function verifyRecovery(r:Recovery){
  validateRecovery(r,r.scope);
  if(r.operation.stage==='manual'){
    if(r.operation.plan)await verifyManualPlan(r.operation.plan);
    const b=new TextEncoder().encode(r.operation.witnessText),w=r.operation.request.witness;
    if(b.length!==w.endByte-w.startByte||await sha256(b)!==w.sliceSha256)refuse('Retained witness bytes do not match the original request.');
  }
}
function ownScope(key:string,prefix:string):unknown{
  try{return JSON.parse(key.slice(prefix.length));}catch{return null;}
}
/** Bounded selected-World/document discovery; original run/revision stays original. */
export function discover(scope:Scope):{native:Located|null;legacy:LegacyLocated|null}{
  if(localStorage.length>512)refuse('Too many saved records to safely discover manual recovery.');
  const native:Located[]=[],legacy:LegacyLocated[]=[];
  for(let i=0;i<localStorage.length;i++){
    const key=localStorage.key(i);if(!key||key.includes(':retained:'))continue;
    const raw=localStorage.getItem(key);if(raw===null)continue;
    if(key.startsWith(PREFIX)){
      const parts=ownScope(key,PREFIX);if(!Array.isArray(parts)||parts.length!==2)refuse();
      if(parts[0]!==scope.worldId)continue;
      let value:unknown;try{value=JSON.parse(raw);}catch{refuse();}
      // A pending profile transition is World-scoped and recoverable on another
      // document of that World; manual/admission never cross document boundaries.
      const isProfile=record(value)&&record(value.operation)&&value.operation.stage==='profile';
      if(parts[0]!==scope.worldId||(parts[1]!==scope.documentId&&!isProfile))continue;
      if(!record(value)||!record(value.scope)||value.scope.worldId!==parts[0]||value.scope.documentId!==parts[1])refuse();
      const saved={worldId:String(parts[0]),documentId:String(parts[1])};validateRecovery(value,saved);
      native.push({key,raw,value:clone(value)});
    }else if(key.startsWith(OLD)){
      const saved=ownScope(key,OLD);
      if(!record(saved)||!text(saved.worldId)||!text(saved.documentId)||!text(saved.runId)||!text(saved.artifactId)||!digest(saved.hash)||!Number.isSafeInteger(saved.revision)||Number(saved.revision)<1)refuse();
      if(saved.worldId!==scope.worldId||saved.documentId!==scope.documentId)continue;
      const value=readKnowledgeRecovery(raw,saved as ManualKnowledgeScope);if(!value)refuse();
      legacy.push({key,raw,value});
    }
  }
  if(native.length+legacy.length>1)refuse('Multiple saved manual operations conflict. All original records are retained.');
  return {native:native[0]??null,legacy:legacy[0]??null};
}
/** World coordination metadata only, never permission to replay another document. */
export function worldPending(world:string):Array<Located|LegacyLocated>{
  if(localStorage.length>512)refuse('Too many saved records to safely discover manual recovery.');
  const result:Array<Located|LegacyLocated>=[];
  for(let i=0;i<localStorage.length;i++){
    const key=localStorage.key(i);if(!key||key.includes(':retained:'))continue;
    if(key.startsWith(PREFIX)){
      const parts=ownScope(key,PREFIX);if(!Array.isArray(parts)||parts.length!==2)refuse();
      if(parts[0]!==world)continue;
      const raw=localStorage.getItem(key);if(raw===null)continue;
      let value:unknown;try{value=JSON.parse(raw);}catch{refuse();}
      const own={worldId:world,documentId:String(parts[1])};validateRecovery(value,own);
      if(value.receipt===null)result.push({key,raw,value:clone(value)});
    }else if(key.startsWith(OLD)){
      const own=ownScope(key,OLD);if(!record(own)||own.worldId!==world)continue;
      const raw=localStorage.getItem(key);if(raw===null)continue;
      const value=readKnowledgeRecovery(raw,own as ManualKnowledgeScope);if(!value)refuse();
      if(value.receipt===null)result.push({key,raw,value});
    }
  }
  return result;
}
async function locks<T>(keys:string[],fn:()=>Promise<T>|T):Promise<T>{
  if(!navigator.locks)refuse('This browser cannot safely retain authoring across tabs. No request was sent.');
  const unique=[...new Set(keys)].sort();
  const acquire=async(i:number):Promise<T>=>{if(i===unique.length)return await fn();return await navigator.locks.request(unique[i],()=>acquire(i+1));};
  return acquire(0);
}
export function freshRecovery(scope:Scope,operation:Operation):Recovery{return {schema:'dmb_native_manual_recovery_v1',scope:clone(scope),operation:clone(operation),submitted:false,everUnknown:false,attempts:0,zeroConfirmed:false,receipt:null};}
export async function store(scope:Scope,next:Recovery,previous:Located|null):Promise<Located>{
  validateRecovery(next,next.scope);
  const key=previous?.key??recoveryKey(scope),raw=JSON.stringify(next);
  return locks([worldLockKey(scope.worldId),recoveryKey(scope),key],()=>{
    const active=discover(scope);
    const peers=worldPending(scope.worldId).filter(x=>x.key!==previous?.key);
    if(peers.some(x=>next.operation.stage==='profile'||('operation' in x.value&&x.value.operation.stage==='profile')))
      refuse('Another operation is retained for this World. Recover its original source before changing the World capability.');
    if(active.legacy||active.native?.key!==previous?.key||active.native?.raw!==previous?.raw)refuse('Another tab changed manual authoring. Reopen the retained request.');
    if(active.native){
      const old=active.native.value;
      const identity=(op:Operation)=>op.stage==='manual'?[op.stage,op.request,op.witnessText]:op.stage==='profile'?[op.stage,op.request]:[op.stage,op.target];
      if(!same(identity(old.operation),identity(next.operation))||(old.submitted&&!next.submitted)
        ||(old.everUnknown&&!next.everUnknown)||next.attempts<old.attempts
        ||('plan' in old.operation&&old.operation.plan!==null&&(!('plan' in next.operation)||!same(old.operation.plan,next.operation.plan)))
        ||(old.receipt!==null&&!same(old.receipt,next.receipt)))refuse('The original operation is immutable; do not replace a submitted request.');
    }
    if(localStorage.getItem(key)!==(previous?.raw??null))refuse();
    localStorage.setItem(key,raw);if(localStorage.getItem(key)!==raw)refuse('The original request could not be retained. No request was sent.');
    return {key,raw,value:clone(next)};
  });
}
export function dispatched(r:Recovery):Recovery{if(uncertain(r))return clone(r);return {...clone(r),submitted:true,attempts:r.attempts+1,everUnknown:r.everUnknown||r.submitted,zeroConfirmed:false};}
export function failed(r:Recovery,verifiedZero:boolean,wasUncertain:boolean):Recovery{
  if(wasUncertain||r.everUnknown)return clone(r);
  const sticky=wasUncertain||r.everUnknown||r.attempts>1;
  return {...clone(r),everUnknown:sticky||!verifiedZero,zeroConfirmed:verifiedZero&&!sticky};
}
export async function archive(scope:Scope,located:Located|LegacyLocated):Promise<void>{
  const isNative='operation' in located.value;
  if(isNative){const r=located.value as Recovery;await verifyRecovery(r);if(!r.receipt&&(r.everUnknown||(r.submitted&&!r.zeroConfirmed)))refuse('The submitted outcome is uncertain. Keep and retry its original packet.');}
  else if(located.value.submitted&&!located.value.receipt)refuse('A submitted classic packet cannot be archived as unsubmitted.');
  const archiveKey=located.key+':retained:'+await sha256(located.raw);
  return locks([worldLockKey(scope.worldId),recoveryKey(scope),located.key],()=>{
    if(localStorage.getItem(located.key)!==located.raw)refuse('Another tab changed the original request.');
    const old=localStorage.getItem(archiveKey);if(old!==null&&old!==located.raw)refuse();
    localStorage.setItem(archiveKey,located.raw);if(localStorage.getItem(archiveKey)!==located.raw)refuse();
    localStorage.removeItem(located.key);if(localStorage.getItem(located.key)!==null)refuse();
  });
}

export async function legacyTransaction<T>(scope:Scope,located:LegacyLocated,fn:()=>Promise<T>):Promise<T>{
  return locks([worldLockKey(scope.worldId),recoveryKey(scope),located.key],async()=>{
    const active=discover(scope);
    if(active.native||active.legacy?.key!==located.key||active.legacy.raw!==located.raw)refuse('Another tab changed the original classic request.');
    if(localStorage.getItem(located.key)!==located.raw)refuse();
    return fn();
  });
}
