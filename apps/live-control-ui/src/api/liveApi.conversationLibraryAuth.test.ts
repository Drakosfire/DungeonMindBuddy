import {afterEach,expect,it,vi} from 'vitest';
const id='11111111-1111-4111-8111-111111111111';
const meta={conversation_id:id,world_id:'world-one',title:'Work',name_revision:1,status:'archived',turn_count:2,created_at:'2026-10-24T12:00:00Z',updated_at:'2026-10-24T12:00:00Z'};
afterEach(()=>{vi.restoreAllMocks();vi.unstubAllEnvs();vi.resetModules();});
async function modules(base=''){vi.stubEnv('VITE_LIVE_API_BASE_URL',base);vi.resetModules();return {live:await import('./liveApi'),library:await import('./conversationLibraryApi')};}
it.each(['list','name','turns','rename'] as const)('uses guarded bearer transport for %s',async operation=>{
 const {live,library}=await modules();live.setNativeGraphAccessToken('synthetic-library-token');
 const body=operation==='list'?{schema:'dmb_conversation_library_v1',world_id:'world-one',status:'all',items:[meta],next_before:null}:operation==='turns'?{schema:'dmb_conversation_library_turns_v3',world_id:'world-one',conversation_id:id,turns:[],next_before_sequence:null}:meta;
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

it('uses guarded resume transport with exact command identity and excludes near misses',async()=>{
 const {live,library}=await modules();live.setNativeGraphAccessToken('synthetic-library-token');
 const command={world_id:'world-one',conversation_id:id,command_id:'22222222-2222-4222-8222-222222222222',expected_pointer_revision:8,expected_active_conversation_id:null};
 const receipt={world_id:'world-one',conversation_id:id,command_id:command.command_id,command_kind:'reopen',active_conversation_id:id,pointer_revision:9,recorded_at:'2026-11-05T12:00:00Z'};
 const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json(receipt));await library.resumeConversation(command);
 expect(new Headers(fetch.mock.calls[0][1]?.headers).get('Authorization')).toBe('Bearer synthetic-library-token');expect(JSON.parse(String(fetch.mock.calls[0][1]?.body))).toEqual(command);
 await live.authenticatedApiFetch('/api/live/agent/worlds/world-one/conversations/'+id+'/resume-extra',{method:'POST'});
 expect(new Headers(fetch.mock.calls[1][1]?.headers).has('Authorization')).toBe(false);
});

it.each(['trash','restore'] as const)('uses guarded lifecycle transport for %s only',async operation=>{
 const {live,library}=await modules();live.setNativeGraphAccessToken('synthetic-library-token');
 const command={world_id:'world-one',conversation_id:id,command_id:'22222222-2222-4222-8222-222222222222',expected_pointer_revision:8,expected_active_conversation_id:null};
 const receipt={world_id:'world-one',conversation_id:id,command_id:command.command_id,command_kind:operation,active_conversation_id:null,pointer_revision:9,recorded_at:'2026-11-05T12:00:00Z'};
 const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json(receipt));await library.changeConversationLifecycle(command,operation);
 expect(new Headers(fetch.mock.calls[0][1]?.headers).get('Authorization')).toBe('Bearer synthetic-library-token');
 await live.authenticatedApiFetch('/api/live/agent/worlds/world-one/conversations/'+id+'/'+operation+'-extra',{method:'POST'});expect(new Headers(fetch.mock.calls[1][1]?.headers).has('Authorization')).toBe(false);
});

it('guards the text-only message endpoint and excludes near misses',async()=>{
 const {live,library}=await modules();live.setNativeGraphAccessToken('synthetic-library-token');const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json({schema:'dmb_conversation_messages_v1',world_id:'world-one',conversation_id:id,messages:[],next_before_sequence:null}));
 await library.readConversationMessages('world-one',id);expect(new Headers(fetch.mock.calls[0][1]?.headers).get('Authorization')).toBe('Bearer synthetic-library-token');
 await live.authenticatedApiFetch('/api/live/agent/worlds/world-one/conversations/'+id+'/messages-extra');expect(new Headers(fetch.mock.calls[1][1]?.headers).has('Authorization')).toBe(false);
});


it('shares the guarded active message read and never authorizes a near-miss route',async()=>{
 const {live,library}=await modules();live.setNativeGraphAccessToken('synthetic-library-token');
 let finish!:(response:Response)=>void;const waiting=new Promise<Response>(resolve=>{finish=resolve});
 const fetch=vi.spyOn(globalThis,'fetch').mockReturnValue(waiting);
 const first=library.readActiveConversationMessages('world-one'),second=library.readActiveConversationMessages('world-one');
 await vi.waitFor(()=>expect(fetch).toHaveBeenCalledTimes(1));
 expect(new Headers(fetch.mock.calls[0][1]?.headers).get('Authorization')).toBe('Bearer synthetic-library-token');
 finish(Response.json({schema:'dmb_active_conversation_messages_v2',world_id:'world-one',conversation_state:'active',conversation_id:id,active_conversation_id:id,pointer_revision:3,messages:[],next_before_sequence:null}));
 await Promise.all([first,second]);
 fetch.mockResolvedValue(Response.json({}));await live.authenticatedApiFetch('/api/live/agent/worlds/world-one/conversations/active/messages-extra');
 expect(new Headers(fetch.mock.calls[1][1]?.headers).has('Authorization')).toBe(false);
});
