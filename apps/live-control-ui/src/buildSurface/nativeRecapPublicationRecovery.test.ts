import {webcrypto} from 'node:crypto';
import {beforeEach,afterEach,expect,it,vi} from 'vitest';
import {sha256,targetFor,type Snapshot} from '../api/nativeRecapPublicationApi';
import {retain,readNativeRecovery,verifyRecovery,archiveKnown,replaceAdmissionWithResume,recoveryKey,type Recovery} from './nativeRecapPublicationRecovery';
let s:Snapshot;
beforeEach(async()=>{vi.stubGlobal('crypto',webcrypto);localStorage.clear();Object.defineProperty(navigator,'locks',{configurable:true,value:{request:(_k:string,fn:()=>unknown)=>Promise.resolve(fn())}});s={worldId:'world',nativeWorldId:'native',bindingVersion:1,runId:'run',runRevision:2,campaignId:'campaign',sessionId:'session-8',artifactId:'app-source',sourceRevisionId:'00000000-0000-4000-8000-000000000001',sourceSha256:await sha256('Ari arrived.'),candidateSha256:'a'.repeat(64),spanIndexSha256:'b'.repeat(64),sourceMarkdown:'Ari arrived.'};});
afterEach(()=>{vi.restoreAllMocks();vi.unstubAllGlobals();});
it('retains the actual admission target before dispatch and locates it independently of current source/revision',async()=>{const located=await retain(s,{stage:'admission',mode:'admit',target:targetFor(s)});expect(readNativeRecovery('world','run')).toEqual(located);expect(readNativeRecovery('foreign','run')).toBeNull();await verifyRecovery(located);expect(JSON.parse(located.raw).operation.target.sourceRevisionId).toBe(s.sourceRevisionId);});
it('never overwrites another tab operation and requires browser locks',async()=>{const first=await retain(s,{stage:'admission',mode:'admit',target:targetFor(s)});await expect(retain({...s,candidateSha256:'c'.repeat(64)},{stage:'admission',mode:'admit',target:targetFor(s)})).rejects.toThrow('overwrite');expect(localStorage.getItem(first.key)).toBe(first.raw);Object.defineProperty(navigator,'locks',{value:undefined,configurable:true});await expect(retain(s,first.value.operation)).rejects.toThrow('across tabs');});
it('archives exact bytes using bounded private hash keys before clearing active storage',async()=>{const located=await retain(s,{stage:'admission',mode:'admit',target:targetFor(s)});await archiveKnown(located);expect(localStorage.getItem(located.key)).toBeNull();const key=localStorage.key(0)!;expect(key).toMatch(/:retained:admission:[a-f0-9]{64}$/);expect(key.length).toBeLessThan(180);expect(localStorage.getItem(key)).toBe(located.raw);});
it('preserves active bytes when archive storage fails',async()=>{const located=await retain(s,{stage:'admission',mode:'admit',target:targetFor(s)});const original=Storage.prototype.setItem;vi.spyOn(Storage.prototype,'setItem').mockImplementation(function(k,v){if(k.includes(':retained:'))throw new Error('full');return original.call(this,k,v);});await expect(archiveKnown(located)).rejects.toThrow('full');expect(localStorage.getItem(located.key)).toBe(located.raw);});
it('blocks conflicting classic packets without modifying either family',async()=>{const scope=JSON.stringify(['world','native','run','artifact','sha256:old']);const key='dmb.buildRecapPublication.v1:'+scope;localStorage.setItem(key,'exact old bytes');await expect(retain(s,{stage:'admission',mode:'admit',target:targetFor(s)})).rejects.toThrow('classic');expect(localStorage.getItem(key)).toBe('exact old bytes');});
it.each(['world','run','uuid','target','body','schema'])('refuses corrupt/foreign retained %s',async damage=>{const located=await retain(s,{stage:'admission',mode:'admit',target:targetFor(s)});const v=JSON.parse(located.raw) as Recovery;if(damage==='world')v.snapshot.worldId='foreign';if(damage==='run')v.snapshot.runId='foreign';if(damage==='uuid')v.snapshot.sourceRevisionId='sha256:'+s.sourceSha256;if(damage==='target'&&v.operation.stage==='admission')v.operation.target.sourceArtifactId='foreign';if(damage==='body')v.snapshot.sourceMarkdown+='tail';if(damage==='schema')(v as {schema:string}).schema='unknown';localStorage.setItem(recoveryKey('world','run'),JSON.stringify(v));if(damage==='body')await expect(verifyRecovery(readNativeRecovery('world','run')!)).rejects.toThrow('bytes');else expect(()=>readNativeRecovery('world','run')).toThrow();});
it('stores and verifies the exact immutable extension request, including UTF8 slice hash',async()=>{const request={managed_world_id:'world',extension_id:'stable-extension',original_admission_id:'original',source_artifact_id:'native-source',source_revision_id:'native-revision',expected_body_sha256:s.sourceSha256,expected_parent_revision_id:'rev:before',expected_source_authority_epoch:3,created_at:'2026-11-19T00:00:00Z',spans:[{client_ref:'witness',evidence_role:'support' as const,start_byte:0,end_byte:3,expected_slice_sha256:await sha256('Ari')}]};const located=await retain(s,{stage:'extension',request});await verifyRecovery(located);expect(readNativeRecovery('world','run')?.value.operation).toEqual({stage:'extension',request});const corrupt=JSON.parse(located.raw);corrupt.operation.request.spans[0].end_byte=4;localStorage.setItem(located.key,JSON.stringify(corrupt));await expect(verifyRecovery(readNativeRecovery('world','run')!)).rejects.toThrow();});


it('keeps the unknown admission active if the resume replacement write fails after archival',async()=>{
  const located=await retain(s,{stage:'admission',mode:'admit',target:targetFor(s)});
  const previous={schema_version:'dmb_native_recap_source_status_v2' as const,state:'conflict' as const,
    run_id:'00000000-0000-4000-8000-000000000002',run_revision:3,managed_world_id:s.worldId,native_world_id:s.nativeWorldId,
    binding_version:s.bindingVersion,campaign_id:s.campaignId,session_id:s.sessionId,app_source_artifact_id:s.artifactId,
    app_source_revision_id:s.sourceRevisionId,app_body_sha256:s.sourceSha256,admission_id:'actual',admission_committed:false,
    command_sha256:null,published_revision_id:null,evidence_ref_id:null,failure_code:null,opening:{state:'not_checked' as const}};
  const original=Storage.prototype.setItem,remove=vi.spyOn(Storage.prototype,'removeItem');
  vi.spyOn(Storage.prototype,'setItem').mockImplementation(function(key,value){
    if(key===located.key){
      // Equivalent observable crash window: archive exists, OLD active pointer
      // must still resolve before the replacement atomic setItem happens.
      expect(readNativeRecovery('world','run')).toEqual(located);
      expect(Object.keys(localStorage).some(k=>k.includes(':retained:admission:'))).toBe(true);
      throw new Error('quota during new active write');
    }
    original.call(this,key,value);
  });
  await expect(replaceAdmissionWithResume(located,{stage:'admission',mode:'resume',target:targetFor(s),previous})).rejects.toThrow('quota');
  expect(remove).not.toHaveBeenCalled();expect(readNativeRecovery('world','run')).toEqual(located);
  expect(localStorage.getItem(located.key)).toBe(located.raw);
});
