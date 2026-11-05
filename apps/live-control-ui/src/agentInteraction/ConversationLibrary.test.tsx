import {act,cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,beforeAll,beforeEach,expect,it,vi} from 'vitest';
import {ConversationLibrary} from './ConversationLibrary';
import {LiveApiError} from '../api/liveApi';
import * as api from '../api/conversationLibraryApi';
vi.mock('../api/conversationLibraryApi',()=>({listConversations:vi.fn(),readConversationName:vi.fn(),readConversationTurns:vi.fn(),readConversationMessages:vi.fn(),renameConversation:vi.fn()}));
vi.mock('../planSurface/components/BuddyContextTraceLoader',()=>({BuddyContextTraceLoader:()=> <p>Explicit trace</p>}));
const current='11111111-1111-4111-8111-111111111111',old='22222222-2222-4222-8222-222222222222';
const meta=(id=current,world='world-one')=>({conversation_id:id,world_id:world,title:id===current?'Current piece':'Archived piece',name_revision:0,status:id===current?'active' as const:'archived' as const,turn_count:1,created_at:'2026-10-24T12:00:00Z',updated_at:'2026-10-24T12:00:00Z'});
const page=(id=current,world='world-one')=>({schema:'dmb_conversation_library_turns_v3' as const,world_id:world,conversation_id:id,turns:[{turn_id:'33333333-3333-4333-8333-333333333333',sequence:1,status:'completed',user_text:id===current?'Current question':'Archived question',assistant_text:'Saved reply',reply_object:null,retry_context:null}],next_before_sequence:null});
const messages=(id=current,world='world-one')=>({schema:'dmb_conversation_messages_v1' as const,world_id:world,conversation_id:id,messages:page(id,world).turns.map(({turn_id,sequence,status,user_text,assistant_text})=>({turn_id,sequence,status,user_text,assistant_text})),next_before_sequence:null as number|null});
beforeAll(()=>{Object.defineProperty(HTMLDialogElement.prototype,'showModal',{configurable:true,value(this:HTMLDialogElement){this.setAttribute('open','');}});});
beforeEach(()=>{vi.clearAllMocks();vi.mocked(api.listConversations).mockImplementation(async(world,status)=>({schema:'dmb_conversation_library_v1',world_id:world,status,items:[meta(current,world),meta(old,world)],next_before:null}));vi.mocked(api.readConversationName).mockImplementation(async(world,id)=>meta(id,world));vi.mocked(api.readConversationTurns).mockImplementation(async(world,id)=>page(id,world));vi.mocked(api.readConversationMessages).mockImplementation(async(world,id)=>messages(id,world));});
afterEach(()=>cleanup());
it('reads and names archived work without touching the current composer',async()=>{
 render(<><textarea aria-label="Current composer" defaultValue="Unsent work"/><ConversationLibrary worldId="world-one" onClose={()=>{}}/></>);
 await screen.findByText('Current question');fireEvent.click(screen.getByRole('button',{name:/Archived piece/}));await screen.findByText('Archived question');
 fireEvent.click(screen.getByText('•••'));
 expect(screen.getByRole('button',{name:'Export conversation',exact:true})).toBeInTheDocument();
 expect(screen.getByRole('button',{name:'Export with diagnostics'})).toBeInTheDocument();
 expect(screen.getByLabelText('Current composer')).toHaveValue('Unsent work');
 fireEvent.click(screen.getByRole('button',{name:'Rename conversation'}));
 fireEvent.change(screen.getByLabelText('Conversation name'),{target:{value:'Shop relationships'}});
 vi.mocked(api.renameConversation).mockResolvedValue({...meta(old),title:'Shop relationships',name_revision:1});
 fireEvent.click(screen.getByRole('button',{name:'Save name'}));await screen.findByText('Name saved.');expect(api.renameConversation).toHaveBeenCalledWith('world-one',old,'Shop relationships',0);
});
it('keeps an uncertain typed name and retries its exact revision',async()=>{
 render(<ConversationLibrary worldId="world-one" onClose={()=>{}}/>);await screen.findByText('Current question');fireEvent.click(screen.getByText('•••'));fireEvent.click(screen.getByRole('button',{name:'Rename conversation'}));fireEvent.change(screen.getByLabelText('Conversation name'),{target:{value:'Keep name'}});
 vi.mocked(api.renameConversation).mockRejectedValueOnce(new Error('Connection lost')).mockResolvedValueOnce({...meta(),title:'Keep name',name_revision:1});
 fireEvent.click(screen.getByRole('button',{name:'Save name'}));await screen.findByRole('alert');expect(screen.getByLabelText('Conversation name')).toHaveValue('Keep name');
 fireEvent.click(screen.getByRole('button',{name:'Save name'}));await screen.findByText('Name saved.');expect(vi.mocked(api.renameConversation).mock.calls).toEqual([['world-one',current,'Keep name',0],['world-one',current,'Keep name',0]]);
});
it('ignores departed World reads even after A B A',async()=>{
 let finish!:(v:api.ConversationSummary)=>void;vi.mocked(api.readConversationName).mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve;}));
 const view=render(<ConversationLibrary worldId="world-one" onClose={()=>{}}/>);await waitFor(()=>expect(api.readConversationName).toHaveBeenCalled());
 view.rerender(<ConversationLibrary worldId="world-two" onClose={()=>{}}/>);await screen.findByText('Current question');view.rerender(<ConversationLibrary worldId="world-one" onClose={()=>{}}/>);await screen.findByText('Current question');
 await act(async()=>{finish({...meta(),title:'STALE NAME'});});expect(screen.queryByDisplayValue('STALE NAME')).not.toBeInTheDocument();expect(screen.queryByText('STALE NAME')).not.toBeInTheDocument();
});
it('ignores a late transcript after another selection',async()=>{
 let finish!:(v:api.ConversationMessages)=>void;vi.mocked(api.readConversationMessages).mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve;}));
 render(<ConversationLibrary worldId="world-one" onClose={()=>{}}/>);fireEvent.click(await screen.findByRole('button',{name:/Archived piece/}));await screen.findByText('Archived question');
 await act(async()=>{finish(messages());});expect(screen.queryByText('Current question')).not.toBeInTheDocument();
});
it('loads earlier turns and traces only on request',async()=>{
 vi.mocked(api.readConversationMessages).mockResolvedValueOnce({...messages(),messages:[{...messages().messages[0],sequence:51}],next_before_sequence:51}).mockResolvedValueOnce({...messages(),messages:[{...messages().messages[0],turn_id:'44444444-4444-4444-8444-444444444444',user_text:'Earlier question'}]});
 render(<ConversationLibrary worldId="world-one" onClose={()=>{}}/>);fireEvent.click(await screen.findByRole('button',{name:'Earlier messages'}));await screen.findByText('Earlier question');expect(api.readConversationMessages).toHaveBeenLastCalledWith('world-one',current,51);
 expect(screen.queryByText('Explicit trace')).not.toBeInTheDocument();fireEvent.click(screen.getByRole('button',{name:'Load saved details'}));await screen.findByText('Full saved details');fireEvent.click(screen.getAllByText('Trace')[0]);await screen.findByText('Explicit trace');
});

it('shows saved object-only questions and page object links without editable chat plans',async()=>{
 const source={world_id:'world-one',conversation_id:current,turn_id:page().turns[0].turn_id,document_id:'source page',surface_id:'build' as const};
 vi.mocked(api.readConversationTurns).mockResolvedValue({...page(),turns:[
  {...page().turns[0],assistant_text:'',reply_object:{kind:'questions',source,questions:[{text:'Which shop should we develop?'}]}},
  {...page().turns[0],turn_id:old,sequence:2,user_text:'Prepare a plan',assistant_text:'Held for review.',reply_object:{kind:'page_object',object_kind:'plan',source:{...source,turn_id:old}}},
 ]});
 render(<><textarea aria-label="Current composer" defaultValue="Newer unsent note"/><ConversationLibrary worldId="world-one" onClose={()=>{}}/></>);
 await screen.findByRole('button',{name:'Load saved details'});expect(api.readConversationTurns).not.toHaveBeenCalled();fireEvent.click(screen.getByRole('button',{name:'Load saved details'}));
 expect(await screen.findByRole('region',{name:'Saved clarifying questions'})).toHaveTextContent('Which shop should we develop?');
 expect(screen.queryByText('No saved reply.')).not.toBeInTheDocument();
 expect(screen.getByRole('link',{name:'Open source page'})).toHaveAttribute('href','/build?world=world-one&documentId=source+page');
 expect(screen.getByText('Held for review.')).toBeInTheDocument();
 expect(screen.queryByRole('button',{name:'Continue step'})).not.toBeInTheDocument();
 expect(screen.getByLabelText('Current composer')).toHaveValue('Newer unsent note');
});


it('previews without switching and explicitly continues with the existing pointer command',async()=>{
 const onContinue=vi.fn().mockResolvedValue(undefined);
 render(<><textarea aria-label="Unsent draft" defaultValue="Keep my idea"/><ConversationLibrary worldId="world-one" onClose={()=>{}} pointer={{revision:8,activeId:current}} onContinue={onContinue}/></>);
 await screen.findByText('Current question');fireEvent.click(screen.getByRole('button',{name:/Archived piece/}));await screen.findByText('Archived question');
 expect(onContinue).not.toHaveBeenCalled();fireEvent.click(screen.getByRole('button',{name:'Continue conversation',exact:true}));
 await waitFor(()=>expect(onContinue).toHaveBeenCalledTimes(1));expect(onContinue.mock.calls[0][0]).toMatchObject({world_id:'world-one',conversation_id:old,expected_pointer_revision:8,expected_active_conversation_id:current});
 expect(screen.getByLabelText('Unsent draft')).toHaveValue('Keep my idea');
});
it('retries an uncertain switch with the same command identity and blocks unavailable switching',async()=>{
 const onContinue=vi.fn().mockRejectedValueOnce(new Error('Connection lost')).mockResolvedValue(undefined);
 const view=render(<ConversationLibrary worldId="world-one" onClose={()=>{}} pointer={{revision:8,activeId:current}} onContinue={onContinue} continueDisabledReason="Reply in progress"/>);
 fireEvent.click(await screen.findByRole('button',{name:/Archived piece/}));await screen.findByText('Archived question');expect(screen.getByRole('button',{name:'Continue conversation',exact:true})).toBeDisabled();
 view.rerender(<ConversationLibrary worldId="world-one" onClose={()=>{}} pointer={{revision:8,activeId:current}} onContinue={onContinue}/>);
 fireEvent.click(screen.getByRole('button',{name:'Continue conversation',exact:true}));await screen.findByRole('alert');
 fireEvent.click(screen.getByRole('button',{name:'Continue conversation',exact:true}));await waitFor(()=>expect(onContinue).toHaveBeenCalledTimes(2));expect(onContinue.mock.calls[1][0]).toEqual(onContinue.mock.calls[0][0]);
});

it('rebases a definitively rejected switch after refreshing the pointer',async()=>{
 const onContinue=vi.fn().mockRejectedValueOnce(new LiveApiError('Pointer changed',409)).mockResolvedValue(undefined);
 const view=render(<ConversationLibrary worldId="world-one" onClose={()=>{}} pointer={{revision:8,activeId:current}} onContinue={onContinue}/>);
 fireEvent.click(await screen.findByRole('button',{name:/Archived piece/}));await screen.findByText('Archived question');fireEvent.click(screen.getByRole('button',{name:'Continue conversation',exact:true}));await screen.findByRole('alert');
 view.rerender(<ConversationLibrary worldId="world-one" onClose={()=>{}} pointer={{revision:9,activeId:current}} onContinue={onContinue}/>);
 fireEvent.click(screen.getByRole('button',{name:'Refresh conversations'}));await screen.findByText('Current question');fireEvent.click(screen.getByRole('button',{name:/Archived piece/}));await screen.findByText('Archived question');fireEvent.click(screen.getByRole('button',{name:'Continue conversation',exact:true}));
 await waitFor(()=>expect(onContinue).toHaveBeenCalledTimes(2));expect(onContinue.mock.calls[1][0].command_id).not.toEqual(onContinue.mock.calls[0][0].command_id);expect(onContinue.mock.calls[1][0].expected_pointer_revision).toBe(9);
});

it('moves to recoverable Trash explicitly and restores without continuing',async()=>{
 const onLifecycle=vi.fn().mockResolvedValue(undefined),onContinue=vi.fn();
 const view=render(<ConversationLibrary worldId="world-one" onClose={()=>{}} pointer={{revision:8,activeId:current}} onContinue={onContinue} onLifecycle={onLifecycle}/>);
 await screen.findByText('Current question');fireEvent.click(screen.getByText('•••'));fireEvent.click(screen.getByRole('button',{name:'Move to Trash'}));await waitFor(()=>expect(onLifecycle).toHaveBeenCalledTimes(1));
 expect(onLifecycle.mock.calls[0]).toEqual([expect.objectContaining({conversation_id:current,expected_pointer_revision:8}),'trash']);expect(onContinue).not.toHaveBeenCalled();
 vi.mocked(api.listConversations).mockImplementation(async(world,status)=>({schema:'dmb_conversation_library_v1',world_id:world,status,items:[{...meta(current,world),status:'trashed'}],next_before:null}));
 vi.mocked(api.readConversationName).mockResolvedValue({...meta(),status:'trashed'});
 fireEvent.change(screen.getByLabelText('Show'),{target:{value:'trashed'}});await screen.findByText('In Trash · Read-only transcript');
 expect(screen.queryByRole('button',{name:'Continue conversation',exact:true})).not.toBeInTheDocument();
 view.rerender(<ConversationLibrary worldId="world-one" onClose={()=>{}} pointer={{revision:9,activeId:null}} onContinue={onContinue} onLifecycle={onLifecycle}/>);
 fireEvent.click(screen.getByRole('button',{name:'Restore conversation'}));await waitFor(()=>expect(onLifecycle).toHaveBeenCalledTimes(2));
 expect(onLifecycle.mock.calls[1]).toEqual([expect.objectContaining({expected_pointer_revision:9,expected_active_conversation_id:null}),'restore']);expect(onContinue).not.toHaveBeenCalled();
});
it('retries uncertain Trash using the same command and does not substitute Restore',async()=>{
 const onLifecycle=vi.fn().mockRejectedValueOnce(new Error('Connection lost')).mockResolvedValue(undefined);
 render(<ConversationLibrary worldId="world-one" onClose={()=>{}} pointer={{revision:8,activeId:current}} onLifecycle={onLifecycle}/>);
 await screen.findByText('Current question');fireEvent.click(screen.getByText('•••'));fireEvent.click(screen.getByRole('button',{name:'Move to Trash'}));await screen.findByRole('alert');
 fireEvent.click(screen.getByRole('button',{name:'Move to Trash'}));await waitFor(()=>expect(onLifecycle).toHaveBeenCalledTimes(2));expect(onLifecycle.mock.calls[1]).toEqual(onLifecycle.mock.calls[0]);
});

it('keeps previews lightweight and loads full saved detail only on request',async()=>{
 render(<ConversationLibrary worldId="world-one" onClose={()=>{}}/>);await screen.findByText('Current question');expect(api.readConversationMessages).toHaveBeenCalled();expect(api.readConversationTurns).not.toHaveBeenCalled();expect(screen.queryByText('Trace')).not.toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Load saved details'}));await screen.findByText('Full saved details');expect(api.readConversationTurns).toHaveBeenCalledWith('world-one',current,undefined);expect(screen.getByText('Trace')).toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Show message preview'}));await screen.findByText(/Saved-message preview/);expect(screen.queryByText('Trace')).not.toBeInTheDocument();
});

it('keeps Continue outside the actions menu and reveals rename and Trash deliberately',async()=>{
 const onContinue=vi.fn(),onLifecycle=vi.fn();render(<ConversationLibrary worldId="world-one" onClose={()=>{}} pointer={{revision:8,activeId:current}} onContinue={onContinue} onLifecycle={onLifecycle}/>);
 fireEvent.click(await screen.findByRole('button',{name:/Archived piece/}));await screen.findByText('Archived question');
 expect(screen.getByRole('button',{name:'Continue conversation',exact:true})).toBeVisible();expect(screen.getByRole('button',{name:'Move to Trash'})).not.toBeVisible();expect(screen.queryByLabelText('Conversation name')).not.toBeInTheDocument();
 fireEvent.click(screen.getByText('•••'));expect(screen.getByRole('button',{name:'Export with diagnostics'})).toBeVisible();fireEvent.click(screen.getByRole('button',{name:'Rename conversation'}));expect(screen.getByLabelText('Conversation name')).toHaveFocus();
 fireEvent.change(screen.getByLabelText('Conversation name'),{target:{value:'Local rename'}});fireEvent.click(screen.getByRole('button',{name:'Cancel',exact:true}));expect(api.renameConversation).not.toHaveBeenCalled();expect(screen.queryByLabelText('Conversation name')).not.toBeInTheDocument();
});
it('Escape dismisses the actions menu before closing the dialog',async()=>{
 const onClose=vi.fn();render(<ConversationLibrary worldId="world-one" onClose={onClose}/>);await screen.findByText('Current question');const summary=screen.getByText('•••');fireEvent.click(summary);expect(summary.closest('details')).toHaveAttribute('open');fireEvent.keyDown(summary,{key:'Escape'});expect(summary.closest('details')).not.toHaveAttribute('open');expect(onClose).not.toHaveBeenCalled();expect(summary).toHaveFocus();
});

it('disables exports while full details are loading and enables them after the owning read settles',async()=>{
 let finish!:(value:api.LibraryTurns)=>void;vi.mocked(api.readConversationTurns).mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve;}));
 render(<ConversationLibrary worldId="world-one" onClose={()=>{}}/>);await screen.findByText('Current question');fireEvent.click(screen.getByRole('button',{name:'Load saved details'}));fireEvent.click(screen.getByText('•••'));
 expect(screen.getByRole('button',{name:'Export conversation',exact:true})).toBeDisabled();expect(screen.getByRole('button',{name:'Export with diagnostics'})).toBeDisabled();expect(screen.getByRole('button',{name:'Rename conversation'})).toBeDisabled();
 await act(async()=>finish(page()));await waitFor(()=>expect(screen.getByRole('button',{name:'Export conversation',exact:true})).not.toBeDisabled());
});
