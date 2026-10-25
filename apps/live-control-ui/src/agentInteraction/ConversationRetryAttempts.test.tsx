import {fireEvent,render,screen} from '@testing-library/react';
import {it,expect,vi,beforeEach} from 'vitest';
import {ConversationRetryAttempts} from './ConversationRetryAttempts';
import {readRetryAttempts,type TurnRetryContext} from '../api/conversationRetryApi';
vi.mock('../api/conversationRetryApi',()=>({readRetryAttempts:vi.fn()}));
vi.mock('../planSurface/components/BuddyContextTraceLoader',()=>({BuddyContextTraceLoader:()=>null}));
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
