import {act,cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,beforeAll,beforeEach,expect,it,vi} from 'vitest';
import {ConversationLibrary} from './ConversationLibrary';
import * as api from '../api/conversationLibraryApi';
import {getWorldAgentTurnContextTrace} from '../api/liveApi';
import type {WorldAgentTurnContextTraceResponse} from '../api/buddyContextTraceTypes';

vi.mock('../api/conversationLibraryApi',()=>({listConversations:vi.fn(),readConversationName:vi.fn(),readConversationTurns:vi.fn(),readConversationMessages:vi.fn(),renameConversation:vi.fn()}));
vi.mock('../api/liveApi',async importOriginal=>({...await importOriginal<typeof import('../api/liveApi')>(),getWorldAgentTurnContextTrace:vi.fn()}));
// Keep the real trace loader, inspection owner and timeline renderer together.
const current='11111111-1111-4111-8111-111111111111',archived='22222222-2222-4222-8222-222222222222';
const failedTurn='33333333-3333-4333-8333-333333333333',currentTurn='44444444-4444-4444-8444-444444444444';
const meta=(id=current)=>({conversation_id:id,world_id:'world-one',title:id===current?'Current piece':'Archived failure',name_revision:0,status:id===current?'active' as const:'archived' as const,turn_count:1,created_at:'2026-11-06T12:00:00Z',updated_at:'2026-11-06T12:00:00Z'});
const page=(id=current)=>({schema:'dmb_conversation_library_turns_v3' as const,world_id:'world-one',conversation_id:id,turns:[{turn_id:id===archived?failedTurn:currentTurn,sequence:1,status:id===archived?'interrupted':'completed',user_text:id===archived?'Archived request':'Current question',assistant_text:id===archived?null:'Current reply',reply_object:null,retry_context:null}],next_before_sequence:null});
function response(turnId=failedTurn,conversationId=archived):WorldAgentTurnContextTraceResponse{
 return {schema:'dmb_agent_turn_context_trace_response_v1',world_id:'world-one',turn_id:turnId,attempts:[{
  schema:'dmb_turn_context_trace_v1',trace_id:'trace-'+turnId,world_id:'world-one',conversation_id:conversationId,turn_id:turnId,
  attempt:1,execution_start_sequence:0,started_at:'2026-11-06T12:00:00Z',closed_at:'2026-11-06T12:00:02Z',terminal_status:turnId===failedTurn?'interrupted':'completed',capture_status:'complete',capture_failure_code:null,
  observations:turnId===failedTurn?[{kind:'failure',sequence:0,elapsed_ms:2000,phase:'generation',code:'writer_context_capacity_exceeded'}]:[]}]};
}
beforeAll(()=>Object.defineProperty(HTMLDialogElement.prototype,'showModal',{configurable:true,value(this:HTMLDialogElement){this.setAttribute('open','');}}));
beforeEach(()=>{
 vi.clearAllMocks();
 vi.mocked(api.listConversations).mockImplementation(async(_world,status)=>({schema:'dmb_conversation_library_v1',world_id:'world-one',status,items:[meta(),meta(archived)],next_before:null}));
 vi.mocked(api.readConversationName).mockImplementation(async(_world,id)=>meta(id));
 vi.mocked(api.readConversationTurns).mockImplementation(async(_world,id)=>page(id));
 vi.mocked(api.readConversationMessages).mockImplementation(async(_world,id)=>({schema:'dmb_conversation_messages_v1',world_id:'world-one',conversation_id:id,messages:page(id).turns.map(({turn_id,sequence,status,user_text,assistant_text})=>({turn_id,sequence,status,user_text,assistant_text})),next_before_sequence:null}));
 vi.mocked(getWorldAgentTurnContextTrace).mockImplementation(async(_world,turnId)=>response(turnId,turnId===failedTurn?archived:current));
});
afterEach(cleanup);
async function openArchived(){
 render(<ConversationLibrary worldId="world-one" onClose={()=>{}}/>);
 await screen.findByText('Current question');fireEvent.click(screen.getByRole('button',{name:/Archived failure/}));
 await screen.findByText('Archived request');
 expect(getWorldAgentTurnContextTrace).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole('button',{name:'Load saved details'}));await screen.findByText('Full saved details');
 await screen.findByText('Trace');expect(getWorldAgentTurnContextTrace).not.toHaveBeenCalled();
 fireEvent.click(screen.getByText('Trace'));
}
it('loads the archived failed turn under its own owner and renders its full failure timeline',async()=>{
 await openArchived();await screen.findByRole('heading',{name:'Reply error report'});
 expect(getWorldAgentTurnContextTrace).toHaveBeenCalledWith('world-one',failedTurn,expect.any(AbortSignal));
 expect(screen.getByText('Execution timeline').closest('details')).toHaveAttribute('open');
 expect(screen.getAllByText('writer_context_capacity_exceeded').length).toBeGreaterThan(0);
 expect(screen.queryByText('Could not load World conversation.')).not.toBeInTheDocument();
});
it('rejects a foreign conversation trace locally instead of displaying it',async()=>{
 vi.mocked(getWorldAgentTurnContextTrace).mockResolvedValue(response(failedTurn,current));
 await openArchived();expect(await screen.findByRole('alert')).toHaveTextContent('Execution trace is unavailable');
 expect(screen.queryByRole('heading',{name:'Reply error report'})).not.toBeInTheDocument();
 expect(screen.getByRole('dialog',{name:'Conversations'})).toBeInTheDocument();
});
it('discards a delayed archived read when another conversation is selected',async()=>{
 let resolve!:(value:WorldAgentTurnContextTraceResponse)=>void;
 vi.mocked(getWorldAgentTurnContextTrace).mockImplementationOnce(()=>new Promise(r=>{resolve=r}));
 await openArchived();await waitFor(()=>expect(getWorldAgentTurnContextTrace).toHaveBeenCalledTimes(1));
 const signal=vi.mocked(getWorldAgentTurnContextTrace).mock.calls[0][2];
 fireEvent.click(screen.getByRole('button',{name:/Current piece/}));await screen.findByText('Current question');
 await waitFor(()=>expect(signal?.aborted).toBe(true));
 fireEvent.click(await screen.findByText('Trace'));await screen.findByRole('heading',{name:'How Buddy built this reply'});
 await act(async()=>resolve(response()));
 expect(screen.queryByRole('heading',{name:'Reply error report'})).not.toBeInTheDocument();
 expect(getWorldAgentTurnContextTrace).toHaveBeenLastCalledWith('world-one',currentTurn,expect.any(AbortSignal));
});
it('retries only a failed trace read and keeps the selected transcript mounted',async()=>{
 vi.mocked(getWorldAgentTurnContextTrace).mockRejectedValueOnce(new Error('temporary read failure'));
 await openArchived();await screen.findByRole('alert');fireEvent.click(screen.getByRole('button',{name:'Retry trace read'}));
 await screen.findByRole('heading',{name:'Reply error report'});
 expect(getWorldAgentTurnContextTrace).toHaveBeenCalledTimes(2);expect(screen.getByText('Archived request')).toBeInTheDocument();
});
it('reports an unknown saved status without fabricating an inspection lifecycle',async()=>{
 vi.mocked(api.readConversationTurns).mockImplementation(async(_world,id)=>{const result=page(id);if(id===archived)result.turns[0].status='unknown';return result;});
 await openArchived();expect(await screen.findByRole('alert')).toHaveTextContent('unsupported status');
 expect(getWorldAgentTurnContextTrace).not.toHaveBeenCalled();expect(screen.getByRole('dialog',{name:'Conversations'})).toBeInTheDocument();
});

it('reuses the same bounded closed trace snapshot when reopened on its saved turn',async()=>{
 await openArchived();await screen.findByRole('heading',{name:'Reply error report'});
 fireEvent.click(screen.getByText('Trace'));
 await waitFor(()=>expect(screen.queryByRole('heading',{name:'Reply error report'})).not.toBeInTheDocument());
 fireEvent.click(screen.getByText('Trace'));await screen.findByRole('heading',{name:'Reply error report'});
 expect(getWorldAgentTurnContextTrace).toHaveBeenCalledTimes(1);
});
