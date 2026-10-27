import {afterEach,expect,it,vi} from 'vitest';
const action='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
const origin='b'.repeat(64),commandId='cccccccc-cccc-4ccc-8ccc-cccccccccccc';
function review(){return {schema:'dmb_plan_authoring_review_v1',world_id:'world-a',action_id:action,
  origin_sha256:origin,revision:1,state:'editing',markdown:'Proposed work',markdown_sha256:'d'.repeat(64),
  capture:{world_id:'world-a'},applications:[],last_command_id:commandId,last_command_sha256:'e'.repeat(64),updated_at:'2026-10-26T00:00:00Z'};}
async function modules(base=''){
  vi.stubEnv('VITE_LIVE_API_BASE_URL',base);vi.resetModules();
  const live=await import('./liveApi');live.setNativeGraphAccessToken('synthetic-plan-review-token');
  return {live,api:await import('./planAuthoringReviewApi')};
}
afterEach(()=>{vi.restoreAllMocks();vi.unstubAllEnvs();vi.resetModules();});
it('reads the exact proposal origin without opening or editing its review',async()=>{
  const {api}=await modules();
  const snapshot={schema:'dmb_plan_authoring_review_snapshot_v1',world_id:'world-a',action_id:action,origin_sha256:origin,review:null};
  const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json(snapshot));
  expect(await api.readPlanAuthoringReview('world-a',action)).toEqual(snapshot);
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(fetch.mock.calls[0][1]).toMatchObject({cache:'no-store',redirect:'error',credentials:'same-origin'});
  expect(fetch.mock.calls[0][1]?.body).toBeUndefined();
  expect(new Headers(fetch.mock.calls[0][1]?.headers).get('Authorization')).toBe('Bearer synthetic-plan-review-token');
});
it('sends the caller-retained command once and verifies its acknowledgment',async()=>{
  const {api}=await modules();const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json(review()));
  const command={operation:'open' as const,command_id:commandId,origin_sha256:origin,expected_revision:0};
  expect((await api.commandPlanAuthoringReview('world-a',action,command)).last_command_id).toBe(commandId);
  expect(fetch).toHaveBeenCalledTimes(1);expect(JSON.parse(fetch.mock.calls[0][1]?.body as string)).toEqual(command);
  expect(new Headers(fetch.mock.calls[0][1]?.headers).get('Authorization')).toBe('Bearer synthetic-plan-review-token');
});
it.each(['world','origin','action','command'])('refuses a mismatched %s reply',async(field)=>{
  const {api}=await modules();const bad=review();
  if(field==='world')bad.world_id='other';if(field==='origin')bad.origin_sha256='0'.repeat(64);
  if(field==='action')bad.action_id='dddddddd-dddd-4ddd-8ddd-dddddddddddd';if(field==='command')bad.last_command_id='other';
  vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json(bad));
  await expect(api.commandPlanAuthoringReview('world-a',action,{operation:'open',command_id:commandId,origin_sha256:origin,expected_revision:0})).rejects.toThrow();
});
it('refuses conflicts without automatically retrying',async()=>{
  const {api}=await modules();const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json({}, {status:409}));
  await expect(api.commandPlanAuthoringReview('world-a',action,{operation:'discard',command_id:commandId,origin_sha256:origin,expected_revision:4})).rejects.toThrow(/local copy is retained/);
  expect(fetch).toHaveBeenCalledTimes(1);
});
it('refuses a remote destination before transmitting credentials or working copies',async()=>{
  const {api}=await modules('https://outside.invalid');const fetch=vi.spyOn(globalThis,'fetch');
  await expect(api.commandPlanAuthoringReview('world-a',action,{operation:'save',command_id:commandId,origin_sha256:origin,expected_revision:1,markdown:'Private author draft'})).rejects.toThrow(/loopback/);
  expect(fetch).not.toHaveBeenCalled();
});
it('does not attach credentials to near-miss review paths',async()=>{
  const {live}=await modules();const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json({}));
  for(const suffix of ['review-extra','review/extra'])await live.authenticatedApiFetch(`/api/live/agent/worlds/world-a/plan-proposals/${action}/${suffix}`);
  await live.authenticatedApiFetch('/api/live/agent/worlds/world-a/plan-proposals/not-a-uuid/review');
  for(const call of fetch.mock.calls){expect(new Headers(call[1]?.headers).has('Authorization')).toBe(false);expect(new Headers(call[1]?.headers).has('X-DMB-Graph-CSRF')).toBe(false);}
});
