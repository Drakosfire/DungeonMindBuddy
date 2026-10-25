import {fireEvent,render,screen} from '@testing-library/react';
import {it,expect,vi,beforeEach} from 'vitest';
import {ConversationRetryAttempts} from './ConversationRetryAttempts';
import {readRetryAttempts,type TurnRetryContext} from '../api/conversationRetryApi';
vi.mock('../api/conversationRetryApi',()=>({readRetryAttempts:vi.fn()}));
import {BuddyTurnInspection} from '../planSurface/components/BuddyTurnInspection';
import {getWorldAgentTurnContextTrace} from '../api/liveApi';
vi.mock('../api/liveApi',async importOriginal=>({...await importOriginal<typeof import('../api/liveApi')>(),getWorldAgentTurnContextTrace:vi.fn()}));
const context={world_id:'world',conversation_id:'conversation',turn_id:'leaf',root_id:'root',ordinal:2,revision:4,predecessor_id:'prior',successor_id:null,eligible:false,reason:'not_terminal'} as TurnRetryContext;
const page=(id:string,n:number,next:number|null)=>({schema:'dmb_conversation_library_turns_v3' as const,world_id:'world',conversation_id:'conversation',turns:[{turn_id:id,sequence:n+1,status:'interrupted',user_text:'question',assistant_text:null,reply_object:null,retry_context:{...context,turn_id:id,ordinal:n}}],next_before_sequence:next});
beforeEach(()=>vi.clearAllMocks());
it('loads bounded previous attempts only on expansion, then deliberate pagination',async()=>{
 vi.mocked(readRetryAttempts).mockResolvedValueOnce(page('prior',1,2)).mockResolvedValueOnce(page('root',0,null));
 render(<ConversationRetryAttempts context={context}/>);expect(readRetryAttempts).not.toHaveBeenCalled();
 const details=screen.getByText('Previous attempts · 2').closest('details')!;details.open=true;fireEvent(details,new Event('toggle'));
 await screen.findByText('Attempt 2 · interrupted');expect(readRetryAttempts).toHaveBeenCalledTimes(1);
 fireEvent.click(screen.getByRole('button',{name:'Earlier attempts'}));await screen.findByText('Attempt 1 · interrupted');
 expect(readRetryAttempts).toHaveBeenLastCalledWith('world','conversation','leaf',2);expect(screen.queryByRole('button',{name:'Retry question'})).not.toBeInTheDocument();
});
it('rejects foreign chain content',async()=>{
 const value=page('bad',0,null);value.turns[0].retry_context.root_id='foreign';
 vi.mocked(readRetryAttempts).mockResolvedValueOnce(value);render(<ConversationRetryAttempts context={context}/>);
 const details=screen.getByText('Previous attempts · 2').closest('details')!;details.open=true;fireEvent(details,new Event('toggle'));
 expect(await screen.findByRole('alert')).toHaveTextContent('differ');expect(screen.queryByText('Attempt 1 · interrupted')).not.toBeInTheDocument();
});

function traceResponse(conversation='conversation'){
 return {schema:'dmb_agent_turn_context_trace_response_v1' as const,world_id:'world',turn_id:'root',attempts:[{
  schema:'dmb_turn_context_trace_v1' as const,trace_id:'captured-root',world_id:'world',conversation_id:conversation,turn_id:'root',
  attempt:1,execution_start_sequence:0,started_at:'2026-10-25T00:00:00Z',closed_at:'2026-10-25T00:00:01Z',
  terminal_status:'interrupted' as const,capture_status:'complete' as const,capture_failure_code:null,observations:[],
 }]};
}
it.each([true,false])('reads an ancestor trace with its own inspection owner (nested in current turn: %s)',async nested=>{
 vi.mocked(readRetryAttempts).mockResolvedValue(page('root',0,null));
 vi.mocked(getWorldAgentTurnContextTrace).mockResolvedValue(traceResponse());
 const child=<ConversationRetryAttempts context={context}/>;
 render(nested?<BuddyTurnInspection worldId="world" conversationId="conversation" turnId="leaf" lifecycle="completed">{child}</BuddyTurnInspection>:child);
 const attempts=screen.getByText('Previous attempts · 2').closest('details')!;attempts.open=true;fireEvent(attempts,new Event('toggle'));
 await screen.findByText('Attempt 1 · interrupted');expect(getWorldAgentTurnContextTrace).not.toHaveBeenCalled();
 const trace=screen.getByText('Trace').closest('details')!;trace.open=true;fireEvent(trace,new Event('toggle'));
 await screen.findByText('Reply error report');
 expect(getWorldAgentTurnContextTrace).toHaveBeenCalledExactlyOnceWith('world','root',expect.any(AbortSignal));
 expect(screen.queryByText('Trace does not match this conversation turn.')).not.toBeInTheDocument();
 expect(screen.queryByRole('button',{name:'Retry question'})).not.toBeInTheDocument();
});
it('still rejects a foreign ancestor trace response',async()=>{
 vi.mocked(readRetryAttempts).mockResolvedValue(page('root',0,null));
 vi.mocked(getWorldAgentTurnContextTrace).mockResolvedValue(traceResponse('foreign'));
 render(<ConversationRetryAttempts context={context}/>);
 const attempts=screen.getByText('Previous attempts · 2').closest('details')!;attempts.open=true;fireEvent(attempts,new Event('toggle'));
 await screen.findByText('Attempt 1 · interrupted');
 const trace=screen.getByText('Trace').closest('details')!;trace.open=true;fireEvent(trace,new Event('toggle'));
 expect(await screen.findByRole('alert')).toHaveTextContent('Execution trace is unavailable');
 expect(screen.queryByText('How Buddy built this reply')).not.toBeInTheDocument();
});
