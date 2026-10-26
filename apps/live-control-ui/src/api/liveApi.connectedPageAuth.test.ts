import {afterEach,expect,it,vi} from 'vitest';
const id='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',doc='bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',page='cccccccc-cccc-4ccc-8ccc-cccccccccccc';
const request={operation_id:id,world_id:'world-a',title:'Forge',origin:{document_id:doc,revision:2,content_sha256:'a'.repeat(64),editor_json:'{}',editor_sha256:'b'.repeat(64),selection_from:1,selection_to:6,selected_text:'Forge'},place:{node_id:null,label:'Forge',kind:'location' as const},person:null,relationships:[],mode:'scaffold' as const,instructions:''};
function result(){return {schema:'dmb_connected_page_operation_v1',operation_id:id,phase:'prepared',intent:request,
 page:{document_id:page,world_id:'world-a',campaign_id:'world-a',kind:'worldbuilding_source',status:'active',connected_page_operation_id:id},
 initial_source:{documentId:page,revision:2,contentSha256:'c'.repeat(64)},prepared:{confirm_token:'signed',assertions_preview:[]},receipt:null,connections:null};}
afterEach(()=>{vi.restoreAllMocks();vi.unstubAllEnvs();vi.resetModules();});
async function modules(base=''){vi.stubEnv('VITE_LIVE_API_BASE_URL',base);vi.resetModules();return {live:await import('./liveApi'),pages:await import('./connectedPageApi')};}
it.each(['prepare','confirm','read','page'] as const)('uses the guarded bearer transport for %s',async operation=>{
 const {live,pages}=await modules();live.setNativeGraphAccessToken('synthetic-connected-page-token');
 const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json(result()));
 if(operation==='prepare')await pages.prepareConnectedPage(request);
 if(operation==='confirm')await pages.confirmConnectedPage(result() as any);
 if(operation==='read')await pages.recoverConnectedPage(request);
 if(operation==='page')await pages.readConnectedPageForPage(id,'world-a',page);
 expect(fetch).toHaveBeenCalledTimes(1);expect(new Headers(fetch.mock.calls[0][1]?.headers).get('Authorization')).toBe('Bearer synthetic-connected-page-token');
 expect(fetch.mock.calls[0][1]).toMatchObject({redirect:'error',credentials:'same-origin',cache:'no-store'});
});
it('uses local session CSRF for create and confirm, and authenticated read recovery',async()=>{
 const {pages}=await modules();
 const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValueOnce(Response.json({status:'active',csrf_token:'synthetic-csrf'}))
  .mockImplementation(async()=>Response.json(result()));
 await pages.prepareConnectedPage(request);await pages.confirmConnectedPage(result() as any);await pages.recoverConnectedPage(request);
 expect(new Headers(fetch.mock.calls[1][1]?.headers).get('X-DMB-Graph-CSRF')).toBe('synthetic-csrf');
 expect(new Headers(fetch.mock.calls[2][1]?.headers).get('X-DMB-Graph-CSRF')).toBe('synthetic-csrf');
});
it.each(['prepare','confirm','read'] as const)('refuses remote destinations before %s transmits any data',async operation=>{
 const {live,pages}=await modules('https://outside.invalid');live.setNativeGraphAccessToken('synthetic-connected-page-token');
 const fetch=vi.spyOn(globalThis,'fetch');
 await expect(operation==='prepare'?pages.prepareConnectedPage(request):operation==='confirm'?pages.confirmConnectedPage(result() as any):pages.recoverConnectedPage(request)).rejects.toThrow(/loopback/);
 expect(fetch).not.toHaveBeenCalled();
});
it('never attaches operator credentials to near-miss connected-page paths',async()=>{
 const {live}=await modules();live.setNativeGraphAccessToken('synthetic-connected-page-token');
 const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json({}));
 for(const path of ['/api/live/connected-pages/prepare-extra','/api/live/connected-pages/'+id+'/extra','/api/live/connected-pages/not-a-uuid'])await live.authenticatedApiFetch(path);
 for(const call of fetch.mock.calls){expect(new Headers(call[1]?.headers).has('Authorization')).toBe(false);expect(new Headers(call[1]?.headers).has('X-DMB-Graph-CSRF')).toBe(false);}
});

it('uses guarded exact connected-origin reads and excludes near misses',async()=>{
 const {live}=await modules();live.setNativeGraphAccessToken('synthetic-connected-page-token');
 const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json({}));
 await live.getAgentConnectedPageOrigin('world-a',id);
 expect(new Headers(fetch.mock.calls[0][1]?.headers).get('Authorization')).toBe('Bearer synthetic-connected-page-token');
 for(const path of [`/api/live/agent/worlds/world-a/conversation/turns/${id}/connected-page-origin-extra`,`/api/live/agent/worlds/world-a/conversation/turns/${id}/connected-page-origin/extra`])await live.authenticatedApiFetch(path);
 for(const call of fetch.mock.calls.slice(1))expect(new Headers(call[1]?.headers).has('Authorization')).toBe(false);
});
