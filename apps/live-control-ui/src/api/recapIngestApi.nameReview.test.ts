import {afterEach,expect,it,vi} from 'vitest';
const body={operation:'generate_recap_memory' as const,campaign_id:'c',managed_world_id:'w',session:30,raw_text:'Marlna waits.'};
const result={schema:'dmb_recap_name_review_v1',scope:{managed_world_id:'w',native_world_id:'n',binding_version:1,campaign_id:'c'},source_sha256:'a'.repeat(64),catalog_sha256:'b'.repeat(64),review_id:'c'.repeat(64),exact_mention_count:0,suggestions:[]};
afterEach(()=>{vi.restoreAllMocks();vi.unstubAllEnvs();vi.resetModules();});
async function setup(base=''){vi.stubEnv('VITE_LIVE_API_BASE_URL',base);vi.resetModules();const live=await import('./liveApi');const recap=await import('./recapIngestApi');return {live,recap};}
it('bootstraps local session and sends CSRF with the actual name-review wrapper',async()=>{
 const {recap}=await setup();let reviews=0;
 vi.spyOn(globalThis,'fetch').mockImplementation(async(url,init)=>{
  if(String(url)==='/api/live/agent/local-session')return init?.method==='POST'?Response.json({status:'active',csrf_token:'synthetic-csrf'}):new Response(null,{status:401});
  expect(url).toBe('/api/live/recap-name-review');reviews++;
  expect(init).toMatchObject({method:'POST',credentials:'same-origin',redirect:'error',cache:'no-store'});
  expect(new Headers(init?.headers).get('X-DMB-Graph-CSRF')).toBe('synthetic-csrf');expect(JSON.parse(String(init?.body))).toEqual(body);
  return Response.json(result);
 });
 await expect(recap.postRecapNameReview(body)).resolves.toEqual(result);expect(reviews).toBe(1);
});
it('renews expired session and retries this read-only review with identical bytes once',async()=>{
 const {recap}=await setup();let boots=0;const requests:string[]=[];
 vi.spyOn(globalThis,'fetch').mockImplementation(async(url,init)=>{
  if(String(url)==='/api/live/agent/local-session'){
   if(init?.method==='POST'){boots++;return Response.json({status:'active',csrf_token:`csrf-${boots}`});}
   return new Response(null,{status:401});
  }
  requests.push(String(init?.body));expect(new Headers(init?.headers).get('X-DMB-Graph-CSRF')).toBe(`csrf-${boots}`);
  return requests.length===1?Response.json({detail:{code:'graph_auth_required'}},{status:401}):Response.json(result);
 });
 await recap.postRecapNameReview(body);expect(requests).toHaveLength(2);expect(requests[0]).toBe(requests[1]);expect(boots).toBe(2);
});
it('does not send local credentials to remote review endpoints',async()=>{
 const {live,recap}=await setup('https://outside.invalid');live.setNativeGraphAccessToken('synthetic-name-review-token');const fetch=vi.spyOn(globalThis,'fetch');
 await expect(recap.postRecapNameReview(body)).rejects.toThrow(/loopback/);expect(fetch).not.toHaveBeenCalled();
});
it('does not authenticate similarly named unregistered paths',async()=>{
 const {live}=await setup();live.setNativeGraphAccessToken('synthetic-name-review-token');const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json({}));
 await live.authenticatedApiFetch('/api/live/recap-name-review-extra',{method:'POST'});
 expect(new Headers(fetch.mock.calls[0][1]?.headers).has('Authorization')).toBe(false);
});
