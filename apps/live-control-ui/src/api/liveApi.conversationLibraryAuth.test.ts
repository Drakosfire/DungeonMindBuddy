import {afterEach,expect,it,vi} from 'vitest';
const id='11111111-1111-4111-8111-111111111111';
const meta={conversation_id:id,world_id:'world-one',title:'Work',name_revision:1,status:'archived',turn_count:2,created_at:'2026-10-24T12:00:00Z',updated_at:'2026-10-24T12:00:00Z'};
afterEach(()=>{vi.restoreAllMocks();vi.unstubAllEnvs();vi.resetModules();});
async function modules(base=''){vi.stubEnv('VITE_LIVE_API_BASE_URL',base);vi.resetModules();return {live:await import('./liveApi'),library:await import('./conversationLibraryApi')};}
it.each(['list','name','turns','rename'] as const)('uses guarded bearer transport for %s',async operation=>{
 const {live,library}=await modules();live.setNativeGraphAccessToken('synthetic-library-token');
 const body=operation==='list'?{schema:'dmb_conversation_library_v1',world_id:'world-one',status:'all',items:[meta],next_before:null}:operation==='turns'?{schema:'dmb_conversation_library_turns_v1',world_id:'world-one',conversation_id:id,turns:[],next_before_sequence:null}:meta;
 const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json(body));
 if(operation==='list')await library.listConversations('world-one','all');if(operation==='name')await library.readConversationName('world-one',id);if(operation==='turns')await library.readConversationTurns('world-one',id);if(operation==='rename')await library.renameConversation('world-one',id,'Work',0);
 expect(new Headers(fetch.mock.calls[0][1]?.headers).get('Authorization')).toBe('Bearer synthetic-library-token');expect(fetch.mock.calls[0][1]).toMatchObject({redirect:'error',cache:'no-store'});
});
it('uses session CSRF for naming and refuses remote dispatch',async()=>{
 let {library}=await modules();const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValueOnce(Response.json({status:'active',csrf_token:'synthetic-csrf'})).mockResolvedValueOnce(Response.json(meta));await library.renameConversation('world-one',id,'Work',0);expect(new Headers(fetch.mock.calls[1][1]?.headers).get('X-DMB-Graph-CSRF')).toBe('synthetic-csrf');
 vi.restoreAllMocks();const foreign=await modules('https://outside.invalid');foreign.live.setNativeGraphAccessToken('synthetic-library-token');const untouched=vi.spyOn(globalThis,'fetch');await expect(foreign.library.listConversations('world-one','all')).rejects.toThrow(/loopback/);expect(untouched).not.toHaveBeenCalled();
});
it('does not attach credentials to near-miss library paths',async()=>{
 const {live}=await modules();live.setNativeGraphAccessToken('synthetic-library-token');const fetch=vi.spyOn(globalThis,'fetch').mockImplementation(async()=>Response.json({}));for(const path of ['/api/live/agent/worlds/world-one/conversations-extra','/api/live/agent/worlds/world-one/conversations/not-id/name','/api/live/agent/worlds/world-one/conversations/'+id+'/name-extra'])await live.authenticatedApiFetch(path);fetch.mock.calls.forEach(call=>expect(new Headers(call[1]?.headers).has('Authorization')).toBe(false));
});
it('refuses metadata from a different World',async()=>{
 const {live,library}=await modules();live.setNativeGraphAccessToken('synthetic-library-token');vi.spyOn(globalThis,'fetch').mockResolvedValueOnce(Response.json({...meta,world_id:'foreign'}));await expect(library.readConversationName('world-one',id)).rejects.toThrow(/owner/);
});
