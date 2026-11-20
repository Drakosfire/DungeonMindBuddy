import {webcrypto} from 'node:crypto';
import {beforeEach,afterEach,expect,it,vi} from 'vitest';
import {prepareNativeThreat,confirmNativeThreat,getNativeThreat,setNativeGraphAccessToken} from './liveApi';
import {verifyNativeThreatReply} from './nativeThreatCreation';
import {threatPacket,threatCreated,threatDraftId} from '../test/nativeThreatCreationFixture';
beforeEach(()=>{vi.stubGlobal('crypto',webcrypto);setNativeGraphAccessToken('native-creation-test');});
afterEach(()=>{vi.restoreAllMocks();vi.unstubAllGlobals();setNativeGraphAccessToken('');});
it('authenticates prepare, exact confirm and read without changing the opaque review',async()=>{
 const packet=await threatPacket(),created=threatCreated();
 const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValueOnce(Response.json(packet)).mockResolvedValueOnce(Response.json(created)).mockResolvedValueOnce(Response.json(created));
 expect(await prepareNativeThreat(threatDraftId,'elderwyld',3)).toEqual(packet);
 expect(await confirmNativeThreat(packet)).toEqual(created);expect(await getNativeThreat(threatDraftId,'elderwyld')).toEqual(created);
 for(const [,init] of fetch.mock.calls){expect(new Headers(init?.headers).get('Authorization')).toBe('Bearer native-creation-test');expect(init?.credentials).toBe('same-origin');expect(init?.redirect).toBe('error');}
 expect(JSON.parse(String(fetch.mock.calls[0][1]?.body))).toEqual({world_id:'elderwyld',expected_draft_version:3});
 expect(JSON.parse(String(fetch.mock.calls[1][1]?.body))).toEqual({review:packet.review,prepared:packet.prepared,token:packet.token});
 expect(fetch.mock.calls[2][0]).toBe(`/api/live/threat-drafts/${threatDraftId}/native-creature?world_id=elderwyld`);
});
it.each(['world','draft','body','binding','state'])('rejects a mismatched %s retained packet',async change=>{
 const p=await threatPacket();if(change==='world')p.review.world_id='other';else if(change==='draft')p.review.draft_id='other';else if(change==='body')p.source_text+=' changed';else if(change==='binding')p.review.binding.managed_world_id='other';else (p as {state:string}).state='unknown';
 await expect(verifyNativeThreatReply(p,'elderwyld',threatDraftId)).rejects.toThrow('retained review');
});
it('leaves expiry decisions to committed-result recovery at the server',async()=>{
 const p=await threatPacket();p.review.expires_at='2020-01-01T00:00:00Z';expect(await verifyNativeThreatReply(p,'elderwyld',threatDraftId)).toEqual(p);
});
it('rejects an acknowledgement for a different native binding',async()=>{
 const p=await threatPacket();vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json({...threatCreated(),native_world_id:'other'}));
 await expect(confirmNativeThreat(p)).rejects.toThrow('another World binding');
});
it('rejects preparation from a different draft version and accepts an empty status',async()=>{
 vi.spyOn(globalThis,'fetch').mockResolvedValueOnce(Response.json(await threatPacket())).mockResolvedValueOnce(Response.json(null));
 await expect(prepareNativeThreat(threatDraftId,'elderwyld',4)).rejects.toThrow('another draft version');expect(await getNativeThreat(threatDraftId,'elderwyld')).toBeNull();
});
