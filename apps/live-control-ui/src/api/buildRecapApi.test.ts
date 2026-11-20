import {afterEach,expect,it,vi} from 'vitest';
import * as live from './liveApi';
import {assertRecapLaunchBinding,launchBuildRecap,recoverBuildRecap,validRecapRequest,type BuildRecapLaunchRequest} from './buildRecapApi';
const request:BuildRecapLaunchRequest={request_id:'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',document_id:'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
  expected_revision:2,expected_content_sha256:'a'.repeat(64),managed_world_id:'managed-a',campaign_id:'longmont-c2',session:30,session_evidence:[]};
afterEach(()=>vi.restoreAllMocks());
it('sends one authenticated exact request and recovers it with an authenticated read',async()=>{
 const fetch=vi.spyOn(live,'authenticatedApiFetch').mockResolvedValue({response:new Response(JSON.stringify({run:{run_id:'run-a'}}),{status:200})} as any);
 await launchBuildRecap(request);
 expect(fetch).toHaveBeenCalledWith('/api/live/graph-preview/build-recap-launches',expect.objectContaining({method:'POST',body:JSON.stringify(request),cache:'no-store'}));
 fetch.mockResolvedValue({response:new Response(JSON.stringify({run:{run_id:'run-a'}}),{status:200})} as any);
 await recoverBuildRecap(request);
 const path=fetch.mock.calls[1][0] as string;
 expect(path).toContain(`/build-recap-launches/${request.request_id}?`);
 expect(new URL(path,'http://local').searchParams.get('document_id')).toBe(request.document_id);
 expect(new URL(path,'http://local').searchParams.get('managed_world_id')).toBe(request.managed_world_id);
 expect(fetch).toHaveBeenCalledTimes(2);
});
it('retains HTTP missing status for deliberate saved-request recovery',async()=>{
 vi.spyOn(live,'authenticatedApiFetch').mockResolvedValue({response:new Response(JSON.stringify({detail:'request not found'}),{status:404})} as any);
 await expect(recoverBuildRecap(request)).rejects.toMatchObject({status:404,message:'request not found'});
});
it.each([{...request,expected_revision:true},{...request,session:0},{...request,request_id:'not-a-uuid'},
 {...request,raw_text:'foreign document'},{...request,session_evidence:[{run_id:'not-a-run',review_revision:1,sha256:'a'.repeat(64)}]}])('refuses malformed saved recovery identity',value=>{
 expect(validRecapRequest(value)).toBe(false);
});
it.each([null,[],{run_id:request.request_id,review_revision:1,sha256:'a'.repeat(64),extra:'unexpected'}])('safely refuses malformed saved evidence pin',pin=>{
 expect(validRecapRequest({...request,session_evidence:[pin]})).toBe(false);
});

it.each([['recap_category_v1','1.0'],['recap_category_v2','2.0']])('accepts only the profile frozen with the original %s request', (profile,version)=>{
 const response:any={run:{source_domain:'recap',campaign_id:request.campaign_id,session_id:`session-${request.session}`,profile_id:`${profile}@${version}`,
 lineage:{build_launch:{schema:'dmb_build_recap_launch_v1',request,server_configuration:{profile_id:profile,profile_version:version}},world_campaign_ingest_context:{managed_world_id:request.managed_world_id}}}};
 expect(()=>assertRecapLaunchBinding(request,response)).not.toThrow();
 response.run.lineage.build_launch.server_configuration.profile_version='foreign';
 expect(()=>assertRecapLaunchBinding(request,response)).toThrow('does not match');
});
