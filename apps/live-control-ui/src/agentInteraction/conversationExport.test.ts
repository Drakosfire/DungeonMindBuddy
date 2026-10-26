import {beforeEach,expect,it,vi} from 'vitest';
import {collectConversationExport} from './conversationExport';
import {readConversationName,readConversationTurns,type LibraryTurn} from '../api/conversationLibraryApi';
import {getWorldAgentTurnContextTrace,getWorldAgentTurnPrompt} from '../api/liveApi';
import type {BuddyTracePromptReference,BuddyTurnContextTrace} from '../api/buddyContextTraceTypes';
vi.mock('../api/conversationLibraryApi',()=>({readConversationName:vi.fn(),readConversationTurns:vi.fn()}));
vi.mock('../api/liveApi',()=>({getWorldAgentTurnContextTrace:vi.fn(),getWorldAgentTurnPrompt:vi.fn()}));
const id='11111111-1111-4111-8111-111111111111',world='world';
const uuid=(n:number)=>`22222222-2222-4222-8222-${String(n).padStart(12,'0')}`;
const turn=(n:number):LibraryTurn=>({turn_id:uuid(n),sequence:n,status:'completed',user_text:`Question ${n}`,assistant_text:`Reply ${n}`,reply_object:null,retry_context:null});
const meta=(n:number)=>({world_id:world,conversation_id:id,title:'Shop relationships',name_revision:0,status:'archived' as const,turn_count:n,created_at:'2026-10-25T00:00:00Z',updated_at:'2026-10-25T00:00:00Z'});
function pages(rows:LibraryTurn[]){
 vi.mocked(readConversationName).mockResolvedValue(meta(rows.length));
 vi.mocked(readConversationTurns).mockImplementation(async(w,c,before)=>{
  const selected=rows.filter(t=>before===undefined||t.sequence<before).slice(-50);
  return {schema:'dmb_conversation_library_turns_v3',world_id:w,conversation_id:c,turns:structuredClone(selected),next_before_sequence:selected.length===50?selected[0].sequence:null};
 });
}
beforeEach(()=>{vi.resetAllMocks();pages([turn(1)]);});
it('exports all 103 physical turns in order, including earlier failed retries, and no diagnostics reads',async()=>{
 const rows=Array.from({length:103},(_,i)=>turn(i+1));
 rows[0]={...rows[0],status:'interrupted',assistant_text:null,retry_context:{world_id:world,conversation_id:id,turn_id:uuid(1),root_id:uuid(1),revision:2,ordinal:0,predecessor_id:null,successor_id:uuid(2),eligible:false,reason:'retried'}};
 rows[1]={...rows[1],retry_context:{...rows[0].retry_context!,turn_id:uuid(2),ordinal:1,predecessor_id:uuid(1),successor_id:null,reason:'not_terminal'}};
 rows[102]={...rows[102],assistant_text:null,reply_object:{kind:'page_object',object_kind:'plan',source:{world_id:world,conversation_id:id,turn_id:uuid(103),document_id:'source page',surface_id:'build'}}};
 pages(rows);const result=await collectConversationExport(world,id,'readable',()=>{});
 expect(result.content.match(/^## Turn /gm)).toHaveLength(103);expect(result.content.indexOf('## Turn 1 · interrupted')).toBeLessThan(result.content.indexOf('## Turn 2 · completed'));
 expect(result.content).toContain('attempt 2');expect(result.content).toContain('Page object: plan (reference only)');expect(result.content).toContain('documentId=source+page');
 expect(vi.mocked(readConversationTurns).mock.calls.map(c=>c[2])).toEqual([undefined,54,4,undefined,54,4]);
 expect(getWorldAgentTurnContextTrace).not.toHaveBeenCalled();expect(getWorldAgentTurnPrompt).not.toHaveBeenCalled();
});
it('finishes exact multiples of 50 using the final empty page',async()=>{
 pages(Array.from({length:100},(_,i)=>turn(i+1)));await collectConversationExport(world,id,'readable',()=>{});
 expect(vi.mocked(readConversationTurns).mock.calls.map(c=>c[2])).toEqual([undefined,51,1,undefined,51,1]);
});
it('exports an empty conversation',async()=>{pages([]);expect((await collectConversationExport(world,id,'readable',()=>{})).content).toContain('Shop relationships');});
it.each(['repeat','nonadvancing','gap','wrong owner','read failure'])('refuses incomplete transcript: %s',async kind=>{
 if(kind==='read failure')vi.mocked(readConversationTurns).mockRejectedValue(new Error('Read failed'));
 else if(kind==='gap')pages([turn(2)]);
 else vi.mocked(readConversationTurns).mockResolvedValue({schema:'dmb_conversation_library_turns_v3',world_id:kind==='wrong owner'?'other':world,conversation_id:id,turns:[turn(1)],next_before_sequence:kind==='nonadvancing'?2:1});
 await expect(collectConversationExport(world,id,'readable',()=>{})).rejects.toThrow();
});
it('refuses a renamed conversation arriving during collection',async()=>{
 vi.mocked(readConversationName).mockResolvedValueOnce(meta(1)).mockResolvedValue({...meta(1),name_revision:1,title:'Changed'});
 await expect(collectConversationExport(world,id,'readable',()=>{})).rejects.toThrow('conversation changed');
});
it('refuses completion changing only a turn, even with unchanged summary',async()=>{
 vi.mocked(readConversationTurns).mockResolvedValueOnce({schema:'dmb_conversation_library_turns_v3',world_id:world,conversation_id:id,turns:[{...turn(1),status:'running',assistant_text:null}],next_before_sequence:null})
 .mockResolvedValue({schema:'dmb_conversation_library_turns_v3',world_id:world,conversation_id:id,turns:[turn(1)],next_before_sequence:null});
 await expect(collectConversationExport(world,id,'readable',()=>{})).rejects.toThrow('reply changed');
});
const reference:BuddyTracePromptReference={kind:'prompt_reference',sequence:0,elapsed_ms:0,evidence_id:'evidence',provider_attempt_id:'call',provider:'jev',model:'writer',api_mode:'chat',serializer_version:'1',payload_sha256:'a'.repeat(64),payload_utf8_bytes:2};
const trace=():BuddyTurnContextTrace=>({schema:'dmb_turn_context_trace_v1',trace_id:'trace',world_id:world,conversation_id:id,turn_id:uuid(1),attempt:1,execution_start_sequence:0,started_at:'2026-10-25T00:00:00Z',closed_at:null,terminal_status:null,capture_status:'incomplete',capture_failure_code:'capture_gap',observations:[reference]});
it('diagnostics includes exact bound prompts and labels unavailable traces',async()=>{
 pages([turn(1),turn(2)]);vi.mocked(getWorldAgentTurnContextTrace).mockResolvedValueOnce({schema:'dmb_agent_turn_context_trace_response_v1',world_id:world,turn_id:uuid(1),attempts:[trace()]}).mockRejectedValueOnce(new Error('No trace retained'));
 vi.mocked(getWorldAgentTurnPrompt).mockResolvedValue({schema:'dmb_agent_prompt_evidence_v1',world_id:world,conversation_id:id,turn_id:uuid(1),trace_id:'trace',attempt:1,reference,payload_json:'{}'});
 const data=JSON.parse((await collectConversationExport(world,id,'diagnostic',()=>{})).content);
 expect(data.turns).toHaveLength(2);expect(data.diagnostics[0].prompts[0].evidence.payload_json).toBe('{}');expect(data.diagnostics[0].trace.attempts[0].capture_failure_code).toBe('capture_gap');expect(data.diagnostics[1].unavailable).toBe('No trace retained');
 expect(getWorldAgentTurnPrompt).toHaveBeenCalledWith(world,uuid(1),'trace','call');
});
it('does not export prompt bytes belonging to another conversation',async()=>{
 vi.mocked(getWorldAgentTurnContextTrace).mockResolvedValue({schema:'dmb_agent_turn_context_trace_response_v1',world_id:world,turn_id:uuid(1),attempts:[trace()]});
 vi.mocked(getWorldAgentTurnPrompt).mockResolvedValue({schema:'dmb_agent_prompt_evidence_v1',world_id:world,conversation_id:'other',turn_id:uuid(1),trace_id:'trace',attempt:1,reference,payload_json:'{"private":"wrong owner"}'});
 const file=await collectConversationExport(world,id,'diagnostic',()=>{});expect(file.content).not.toContain('wrong owner');expect(file.content).toContain('Prompt differs');
});
it('stops traversal when selection retires',async()=>{
 let reads=0;const check=()=>{if(++reads>2)throw new Error('retired');};
 await expect(collectConversationExport(world,id,'diagnostic',check)).rejects.toThrow('retired');expect(getWorldAgentTurnContextTrace).not.toHaveBeenCalled();
});
