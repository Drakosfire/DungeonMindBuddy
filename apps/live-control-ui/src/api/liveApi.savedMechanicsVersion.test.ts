import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {openSavedMechanicsVersion,setNativeGraphAccessToken} from './liveApi';
import fixture from '../../../../tests/fixtures/statblocks/v1/exact-revision-response.json';
const world='test-world',draft='draft-a',revision=fixture.revision_id;
const packet=()=>({world_id:world,draft_id:draft,locator:{provider:'dungeonmind',statblock_id:fixture.statblock_id,revision_id:revision,definition_digest:fixture.definition_digest,contract:fixture.contract,contract_version:fixture.contract_version},resource:structuredClone(fixture)});
beforeEach(()=>{setNativeGraphAccessToken('read-test');});
afterEach(()=>{vi.restoreAllMocks();setNativeGraphAccessToken(null);});
it('uses one existing exact read without consulting history or local selection',async()=>{
 const value=packet(),fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(new Response(JSON.stringify(value),{status:200}));
 expect(await openSavedMechanicsVersion(draft,world,revision)).toEqual(value);
 expect(fetch).toHaveBeenCalledTimes(1);expect(String(fetch.mock.calls[0]![0])).toContain(`/threat-drafts/${draft}/mechanics-revisions/${revision}?world_id=${world}`);
});
it.each(['world','draft','revision','locator-revision','statblock','digest','contract','producer'] as const)('rejects a mismatched %s at the shared read boundary',async kind=>{
 const value=packet();if(kind==='world')value.world_id='foreign';if(kind==='draft')value.draft_id='foreign';if(kind==='revision')value.resource.revision_id='foreign';
 if(kind==='locator-revision')value.locator.revision_id='foreign';if(kind==='statblock')value.resource.statblock_id='foreign';if(kind==='digest')value.resource.definition_digest='foreign';
 if(kind==='contract')value.resource.contract_version='foreign';if(kind==='producer')value.locator.provider='foreign';
 const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(new Response(JSON.stringify(value),{status:200}));
 await expect(openSavedMechanicsVersion(draft,world,revision)).rejects.toThrow('Saved version identity changed');expect(fetch).toHaveBeenCalledTimes(1);
});
