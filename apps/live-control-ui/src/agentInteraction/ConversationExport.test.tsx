import {act,cleanup,fireEvent,render,screen} from '@testing-library/react';
import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {ConversationExport} from './ConversationExport';
import {collectConversationExport,downloadConversationExport} from './conversationExport';
vi.mock('./conversationExport',()=>({collectConversationExport:vi.fn(),downloadConversationExport:vi.fn()}));
const file={filename:'conversation.md',mime:'text/markdown',content:'Complete conversation'};
beforeEach(()=>{vi.resetAllMocks();vi.mocked(collectConversationExport).mockResolvedValue(file);});afterEach(cleanup);
it('collects only after click and preserves the composer',async()=>{
 render(<><textarea aria-label="Composer" defaultValue="Newer unsent work"/><ConversationExport worldId="world" conversationId="one"/></>);
 expect(collectConversationExport).not.toHaveBeenCalled();fireEvent.click(screen.getByRole('button',{name:'Export conversation',exact:true}));
 await screen.findByText('Conversation download prepared.');expect(collectConversationExport).toHaveBeenCalledWith('world','one','readable',expect.any(Function));expect(downloadConversationExport).toHaveBeenCalledWith(file);expect(screen.getByLabelText('Composer')).toHaveValue('Newer unsent work');
});
it('suppresses download and notices for retired selection',async()=>{
 let resolve!:(result:typeof file)=>void;vi.mocked(collectConversationExport).mockReturnValue(new Promise(r=>resolve=r));
 const view=render(<ConversationExport worldId="world" conversationId="one"/>);fireEvent.click(screen.getByRole('button',{name:'Export with diagnostics'}));
 expect(screen.getByRole('button',{name:'Export conversation',exact:true})).toBeDisabled();view.rerender(<ConversationExport worldId="world" conversationId="two"/>);await act(async()=>resolve(file));
 expect(downloadConversationExport).not.toHaveBeenCalled();expect(screen.queryByText('Conversation download prepared.')).toBeNull();
});
it('makes a failed read retryable without download',async()=>{
 vi.mocked(collectConversationExport).mockRejectedValue(new Error('A reply changed during export. Retry to collect the latest saved reply.'));
 render(<ConversationExport worldId="world" conversationId="one"/>);fireEvent.click(screen.getByRole('button',{name:'Export conversation',exact:true}));await screen.findByRole('alert');expect(downloadConversationExport).not.toHaveBeenCalled();expect(screen.getByRole('button',{name:'Export conversation',exact:true})).toBeEnabled();
});
