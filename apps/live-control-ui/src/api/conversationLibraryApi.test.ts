import {beforeEach,expect,it,vi} from 'vitest';
import {readConversationTurns,resumeConversation,changeConversationLifecycle} from './conversationLibraryApi';
import {authenticatedApiFetch} from './liveApi';
vi.mock('./liveApi',async original=>({...await original<typeof import('./liveApi')>(),authenticatedApiFetch:vi.fn()}));
const cid='11111111-1111-4111-8111-111111111111',tid='22222222-2222-4222-8222-222222222222';
const source={world_id:'world',conversation_id:cid,turn_id:tid,document_id:'page',surface_id:'build'};
const object={kind:'questions',questions:[{text:'Which shop?'}],source};
const page=()=>({schema:'dmb_conversation_library_turns_v3',world_id:'world',conversation_id:cid,turns:[{turn_id:tid,sequence:1,status:'completed',user_text:'Ask me',assistant_text:'',retry_context:null,reply_object:object}],next_before_sequence:null});
function response(body:unknown){vi.mocked(authenticatedApiFetch).mockResolvedValue({response:Response.json(body)} as Awaited<ReturnType<typeof authenticatedApiFetch>>);}
beforeEach(()=>vi.clearAllMocks());
it('admits exact read-only object scope and preserves empty prose',async()=>{response(page());expect((await readConversationTurns('world',cid)).turns[0].assistant_text).toBe('');});
it.each(['world_id','conversation_id','turn_id','surface_id','document_id'])('refuses a foreign or missing object %s',async field=>{const value=page();value.turns[0].reply_object={...object,source:{...source,[field]:field==='document_id'?'':'foreign'}};response(value);await expect(readConversationTurns('world',cid)).rejects.toThrow();});
it.each([
 {kind:'questions',questions:[],source},
 {kind:'questions',questions:[{text:' '}],source},
 {...object,execute:true},
 {kind:'questions',questions:[{text:'Question',answer:'invented'}],source},
 {kind:'page_object',object_kind:'execute',source},
])('refuses malformed typed objects',async object=>{const value=page();response({...value,turns:[{...value.turns[0],retry_context:null,reply_object:object}]});await expect(readConversationTurns('world',cid)).rejects.toThrow();});
it('refuses objects on incomplete turns and an obsolete projection schema',async()=>{const value=page();response({...value,turns:[{...value.turns[0],status:'running'}]});await expect(readConversationTurns('world',cid)).rejects.toThrow();response({...value,schema:'dmb_conversation_library_turns_v1'});await expect(readConversationTurns('world',cid)).rejects.toThrow();});
it('admits page labels without making their review executable',async()=>{const value=page();response({...value,turns:[{...value.turns[0],reply_object:{kind:'page_object',object_kind:'plan',source}}]});expect((await readConversationTurns('world',cid)).turns[0].reply_object?.kind).toBe('page_object');});

it('retains captured reference input and rejects a foreign World',async()=>{
 const references={schema:'dmb_authored_references_v2',references:[{schema:'dmb_authored_graph_reference_v1',managed_world_id:'world',native_world_id:'native',binding_version:1,graph_revision:'revision',node_id:'node',label:'Selected object'}]};
 const value=page();response({...value,turns:[{...value.turns[0],authored_references:references}]});
 expect((await readConversationTurns('world',cid)).turns[0].authored_references).toEqual(references);
 references.references[0].managed_world_id='foreign';response({...value,turns:[{...value.turns[0],authored_references:references}]});
 await expect(readConversationTurns('world',cid)).rejects.toThrow('reference input');
});

it('accepts only the exact durable reopen receipt',async()=>{
 const command={world_id:'world',conversation_id:cid,command_id:tid,expected_pointer_revision:4,expected_active_conversation_id:null};
 const receipt={world_id:'world',conversation_id:cid,command_id:tid,command_kind:'reopen',active_conversation_id:cid,pointer_revision:5,recorded_at:'2026-11-05T12:00:00Z'};
 response(receipt);expect(await resumeConversation(command)).toEqual(receipt);
 for(const patch of [{command_kind:'new'},{world_id:'foreign'},{active_conversation_id:null},{pointer_revision:6},{command_id:cid},{conversation_id:tid}]){response({...receipt,...patch});await expect(resumeConversation(command)).rejects.toThrow(/switch/);}
});

it('validates lifecycle receipt operation and exact resulting active pointer',async()=>{
 const command={world_id:'world',conversation_id:cid,command_id:tid,expected_pointer_revision:4,expected_active_conversation_id:cid};
 const receipt={world_id:'world',conversation_id:cid,command_id:tid,command_kind:'trash',active_conversation_id:null,pointer_revision:5,recorded_at:'2026-11-05T12:00:00Z'};
 response(receipt);expect(await changeConversationLifecycle(command,'trash')).toEqual(receipt);
 for(const patch of [{command_kind:'restore'},{active_conversation_id:cid},{world_id:'foreign'},{pointer_revision:6}]){response({...receipt,...patch});await expect(changeConversationLifecycle(command,'trash')).rejects.toThrow('lifecycle');}
 response({...receipt,command_kind:'restore'});expect((await changeConversationLifecycle({...command,expected_active_conversation_id:null},'restore')).active_conversation_id).toBeNull();
});
