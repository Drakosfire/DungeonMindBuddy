import {afterEach,expect,it,vi} from 'vitest';
const world='public-test';const action='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
const path=`/api/live/agent/worlds/${world}/build-proposals/${action}/review`;
const record={schema:'dmb_build_proposal_review_v1',world_id:world,action_id:action,reservation_sha256:'a'.repeat(64),revision:1,state:'editing',markdown:'Public test suggestion',markdown_sha256:'b'.repeat(64),apply:null,updated_at:''};
afterEach(()=>{vi.restoreAllMocks();vi.unstubAllEnvs();vi.resetModules();});
async function modules(base=''){
 vi.stubEnv('VITE_LIVE_API_BASE_URL',base);vi.resetModules();
 const live=await import('./liveApi');const review=await import('./buildProposalReviewApi');return{live,review};
}
it('uses local session CSRF for actual review writes and authenticated credentials for reads',async()=>{
 const {review}=await modules();const fetch=vi.spyOn(globalThis,'fetch')
  .mockResolvedValueOnce(Response.json({status:'active',csrf_token:'public-test-csrf'}))
  .mockResolvedValueOnce(Response.json(record)).mockResolvedValueOnce(Response.json(record));
 const command={operation:'save' as const,expected_revision:1,markdown:'Public test suggestion'};
 await review.proposalReview(world,action,command);await review.proposalReview(world,action);
 expect(fetch).toHaveBeenCalledTimes(3);
 expect(fetch.mock.calls[1][0]).toBe(path);
 expect(new Headers(fetch.mock.calls[1][1]?.headers).get('X-DMB-Graph-CSRF')).toBe('public-test-csrf');
 expect(fetch.mock.calls[1][1]).toMatchObject({method:'POST',credentials:'same-origin',redirect:'error',cache:'no-store',body:JSON.stringify(command)});
 expect(fetch.mock.calls[2][1]).toMatchObject({credentials:'same-origin',redirect:'error',cache:'no-store'});
});
it.each(['read','write'])('sends the configured memory-only bearer for a review %s',async kind=>{
 const {live,review}=await modules();live.setNativeGraphAccessToken('public-test-bearer');
 const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json(record));
 await review.proposalReview(world,action,kind==='write'?{operation:'open',expected_revision:0}:undefined);
 expect(fetch).toHaveBeenCalledTimes(1);
 expect(new Headers(fetch.mock.calls[0][1]?.headers).get('Authorization')).toBe('Bearer public-test-bearer');
 expect(fetch.mock.calls[0][1]?.redirect).toBe('error');
});
it.each(['read','write'])('refuses a remote API before any review %s',async kind=>{
 const {live,review}=await modules('https://outside.invalid');live.setNativeGraphAccessToken('public-test-bearer');
 const fetch=vi.spyOn(globalThis,'fetch');
 await expect(review.proposalReview(world,action,kind==='write'?{operation:'open',expected_revision:0}:undefined)).rejects.toThrow(/loopback/);
 expect(fetch).not.toHaveBeenCalled();
});
it('does not broaden authorization to near-miss route suffixes',async()=>{
 const {live}=await modules();live.setNativeGraphAccessToken('public-test-bearer');
 const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json({}));
 await live.authenticatedApiFetch(path+'-other');await live.authenticatedApiFetch(path+'/extra');
 for(const call of fetch.mock.calls){expect(new Headers(call[1]?.headers).has('Authorization')).toBe(false);expect(new Headers(call[1]?.headers).has('X-DMB-Graph-CSRF')).toBe(false);}
});
