import {beforeEach,expect,it,vi} from 'vitest';
import {readConversationTurns} from './conversationLibraryApi';
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
