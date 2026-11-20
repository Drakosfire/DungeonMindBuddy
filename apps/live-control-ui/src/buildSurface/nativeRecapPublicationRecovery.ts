import {assertConfirmation,clone,digest,positive,record,sha256,text,type Snapshot,type Confirmation,type Extension} from '../api/nativeRecapPublicationApi';
import type {RecapSourceTarget,NativeRecapSourceStatus} from '../api/nativeRecapSourceApi';

export type Operation = {stage:'admission';mode:'admit';target:RecapSourceTarget}
  | {stage:'admission';mode:'resume';target:RecapSourceTarget;previous:NativeRecapSourceStatus}
  | {stage:'extension';request:Extension}
  | {stage:'confirmation';packet:Confirmation};
export interface Recovery {schema:'dmb_native_recap_publication_recovery_v1';snapshot:Snapshot;operation:Operation;submitted:true}
export interface Located {key:string;raw:string;value:Recovery}
const PREFIX='dmb.nativeRecapPublication.v1:';
export const recoveryKey=(world:string,run:string)=>PREFIX+JSON.stringify([world,run]);
const uuid=(v:unknown)=>typeof v==='string'&&/^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$/i.test(v);
function refuse(message='Saved native Recap operation is corrupt or conflicts with another request. Recover the original operation.'):never{throw new Error(message);}
export function assertSnapshot(v:unknown):asserts v is Snapshot{
  if(!record(v)||![v.worldId,v.nativeWorldId,v.runId,v.campaignId,v.artifactId].every(text)||!positive(v.bindingVersion)||!positive(v.runRevision)
    ||typeof v.sessionId!=='string'||!/^session-[1-9]\d*$/.test(v.sessionId)||!uuid(v.sourceRevisionId)
    ||![v.sourceSha256,v.candidateSha256,v.spanIndexSha256].every(digest)||typeof v.sourceMarkdown!=='string')refuse();
}
export function validateRecovery(v:unknown,world:string,run:string):asserts v is Recovery{
  if(!record(v)||v.schema!=='dmb_native_recap_publication_recovery_v1'||v.submitted!==true)refuse();
  assertSnapshot(v.snapshot);const s=v.snapshot;
  if(s.worldId!==world||s.runId!==run||!record(v.operation))refuse('Saved operation does not match the selected World/run.');
  const op=v.operation;
  if(op.stage==='confirmation'){assertConfirmation(op.packet,s);return;}
  if(op.stage==='admission'){
    if(!record(op.target))refuse();const t=op.target;
    if(t.managedWorldId!==world||t.nativeWorldId!==s.nativeWorldId||t.bindingVersion!==s.bindingVersion
      ||t.campaignId!==s.campaignId||t.session!==Number(s.sessionId.slice(8))||t.sourceArtifactId!==s.artifactId
      ||t.sourceRevisionId!==s.sourceRevisionId||t.contentSha256!==s.sourceSha256)refuse();
    if(op.mode==='admit'&&Object.keys(op).every(k=>['stage','mode','target'].includes(k)))return;
    if(op.mode!=='resume'||!record(op.previous))refuse();const p=op.previous;
    if(p.schema_version!=='dmb_native_recap_source_status_v2'||!uuid(p.run_id)||!positive(p.run_revision)||(p.command_sha256!==null&&!digest(p.command_sha256))
      ||p.managed_world_id!==world||p.native_world_id!==s.nativeWorldId||p.binding_version!==s.bindingVersion
      ||p.campaign_id!==s.campaignId||p.session_id!==s.sessionId||p.app_source_artifact_id!==s.artifactId
      ||p.app_source_revision_id!==s.sourceRevisionId||p.app_body_sha256!==s.sourceSha256||p.admission_committed!==false)refuse();
    return;
  }
  if(op.stage!=='extension'||!record(op.request))refuse();const r=op.request;
  if(r.managed_world_id!==world||![r.extension_id,r.original_admission_id,r.source_artifact_id,r.source_revision_id,r.expected_parent_revision_id].every(text)
    ||r.expected_body_sha256!==s.sourceSha256||!positive(r.expected_source_authority_epoch)||typeof r.created_at!=='string'
    ||!/(?:Z|[+-]\d\d:\d\d)$/.test(r.created_at)||!Number.isFinite(Date.parse(r.created_at))||!Array.isArray(r.spans)||!r.spans.length)refuse();
  const seen=new Set<string>(),refs=new Set<string>();
  for(const span of r.spans){if(!record(span)||!text(span.client_ref)||refs.has(span.client_ref)||span.evidence_role!=='support'
    ||!Number.isSafeInteger(span.start_byte)||!Number.isSafeInteger(span.end_byte)||Number(span.start_byte)<0||Number(span.end_byte)<=Number(span.start_byte)||!digest(span.expected_slice_sha256))refuse();
    const key=span.start_byte+':'+span.end_byte;if(seen.has(key))refuse();seen.add(key);refs.add(span.client_ref);}
}
export async function verifyRecovery(located:Located){
  const s=located.value.snapshot;if(await sha256(s.sourceMarkdown)!==s.sourceSha256)refuse('Saved source bytes do not match the original operation.');
  if(located.value.operation.stage==='extension'){
    const bytes=new TextEncoder().encode(s.sourceMarkdown);
    for(const span of located.value.operation.request.spans){
      if(span.end_byte>bytes.length||(span.start_byte===0&&span.end_byte===bytes.length)
        ||await sha256(bytes.slice(span.start_byte,span.end_byte))!==span.expected_slice_sha256)refuse();
      new TextDecoder('utf-8',{fatal:true}).decode(bytes.slice(span.start_byte,span.end_byte));
    }
  }
}
/** Locate by selected World/run, not today's source/candidate or revision. */
export function readNativeRecovery(world:string,run:string):Located|null{
  const key=recoveryKey(world,run),raw=localStorage.getItem(key);
  if(raw===null)return null;
  const value:unknown=JSON.parse(raw);validateRecovery(value,world,run);return {key,raw,value:clone(value)};
}
export function classicRecoveryKeys(world:string,run:string):string[]{
  const result:string[]=[];
  for(let i=0;i<localStorage.length;i++){
    const key=localStorage.key(i);if(!key?.startsWith('dmb.buildRecapPublication.v1:')||key.includes(':retained'))continue;
    let scope:unknown;try{scope=JSON.parse(key.slice('dmb.buildRecapPublication.v1:'.length));}catch{refuse();}
    if(Array.isArray(scope)&&scope[0]===world&&scope[2]===run)result.push(key);
  }
  return result.sort();
}
export function assertNoClassicConflict(world:string,run:string){if(classicRecoveryKeys(world,run).length)refuse('Recover the retained classic Recap before starting a native request.');}
async function locked<T>(world:string,run:string,fn:()=>T):Promise<T>{
  if(!navigator.locks)refuse('This browser cannot safely retain publication requests across tabs.');
  return navigator.locks.request(recoveryKey(world,run),fn);
}
export async function retain(snapshot:Snapshot,operation:Operation):Promise<Located>{
  const value:Recovery={schema:'dmb_native_recap_publication_recovery_v1',snapshot:clone(snapshot),operation:clone(operation),submitted:true};
  validateRecovery(value,snapshot.worldId,snapshot.runId);
  const key=recoveryKey(snapshot.worldId,snapshot.runId),raw=JSON.stringify(value);
  return locked(snapshot.worldId,snapshot.runId,()=>{
    assertNoClassicConflict(snapshot.worldId,snapshot.runId);
    const previous=localStorage.getItem(key);if(previous!==null&&previous!==raw)refuse('Another native Recap request is retained. Do not overwrite it.');
    localStorage.setItem(key,raw);if(localStorage.getItem(key)!==raw)refuse('The exact request could not be retained. No request was sent.');
    return {key,raw,value};
  });
}
/** Only call after a verified stage result or definitive precommit rejection.
 * Archive exact prior bytes before removing the active key; storage failures
 * leave it recoverable. Unknown responses never enter this transition. */
export async function archiveKnown(located:Located){
  const s=located.value.snapshot;
  const archiveDigest=await sha256(located.raw);
  return locked(s.worldId,s.runId,()=>{
    if(localStorage.getItem(located.key)!==located.raw)refuse('Another tab changed the retained request.');
    const archive=located.key+':retained:'+located.value.operation.stage+':'+archiveDigest;
    // Private storage identity only; the exact request bytes remain the value.
    localStorage.setItem(archive,located.raw);if(localStorage.getItem(archive)!==located.raw)refuse();
    localStorage.removeItem(located.key);
  });
}

/** Explicit known APP admission -> exact resume transition. Archive first, but
 * never remove the active pointer: localStorage.setItem replaces it atomically.
 * If archival or replacement fails, the original active bytes still recover. */
export async function replaceAdmissionWithResume(located:Located,operation:Extract<Operation,{stage:'admission';mode:'resume'}>):Promise<Located>{
  const s=located.value.snapshot;
  if(located.value.operation.stage!=='admission')refuse('Only the saved admission may transition to its explicit resume.');
  const value:Recovery={schema:'dmb_native_recap_publication_recovery_v1',snapshot:clone(s),operation:clone(operation),submitted:true};
  validateRecovery(value,s.worldId,s.runId);
  const raw=JSON.stringify(value),archiveDigest=await sha256(located.raw);
  return locked(s.worldId,s.runId,()=>{
    assertNoClassicConflict(s.worldId,s.runId);
    if(localStorage.getItem(located.key)!==located.raw)refuse('Another tab changed the retained request.');
    const archive=located.key+':retained:admission:'+archiveDigest;
    localStorage.setItem(archive,located.raw);
    if(localStorage.getItem(archive)!==located.raw)refuse('The original admission could not be archived.');
    // No removeItem: a thrown quota error or a crash before this atomic write
    // leaves the old request active. After success, the new exact request is active.
    localStorage.setItem(located.key,raw);
    if(localStorage.getItem(located.key)!==raw)refuse('The exact resume request could not be retained.');
    return {key:located.key,raw,value};
  });
}
