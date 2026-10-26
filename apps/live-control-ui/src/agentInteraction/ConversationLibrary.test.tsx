import {act,cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,beforeAll,beforeEach,expect,it,vi} from 'vitest';
import {ConversationLibrary} from './ConversationLibrary';
import * as api from '../api/conversationLibraryApi';
vi.mock('../api/conversationLibraryApi',()=>({listConversations:vi.fn(),readConversationName:vi.fn(),readConversationTurns:vi.fn(),renameConversation:vi.fn()}));
vi.mock('../planSurface/components/BuddyContextTraceLoader',()=>({BuddyContextTraceLoader:()=> <p>Explicit trace</p>}));
const current='11111111-1111-4111-8111-111111111111',old='22222222-2222-4222-8222-222222222222';
const meta=(id=current,world='world-one')=>({conversation_id:id,world_id:world,title:id===current?'Current piece':'Archived piece',name_revision:0,status:id===current?'active' as const:'archived' as const,turn_count:1,created_at:'2026-10-24T12:00:00Z',updated_at:'2026-10-24T12:00:00Z'});
const page=(id=current,world='world-one')=>({schema:'dmb_conversation_library_turns_v3' as const,world_id:world,conversation_id:id,turns:[{turn_id:'33333333-3333-4333-8333-333333333333',sequence:1,status:'completed',user_text:id===current?'Current question':'Archived question',assistant_text:'Saved reply',reply_object:null,retry_context:null}],next_before_sequence:null});
beforeAll(()=>{Object.defineProperty(HTMLDialogElement.prototype,'showModal',{configurable:true,value(this:HTMLDialogElement){this.setAttribute('open','');}});});
beforeEach(()=>{vi.clearAllMocks();vi.mocked(api.listConversations).mockImplementation(async(world,status)=>({schema:'dmb_conversation_library_v1',world_id:world,status,items:[meta(current,world),meta(old,world)],next_before:null}));vi.mocked(api.readConversationName).mockImplementation(async(world,id)=>meta(id,world));vi.mocked(api.readConversationTurns).mockImplementation(async(world,id)=>page(id,world));});
afterEach(()=>cleanup());
it('reads and names archived work without touching the current composer',async()=>{
 render(<><textarea aria-label="Current composer" defaultValue="Unsent work"/><ConversationLibrary worldId="world-one" onClose={()=>{}}/></>);
 await screen.findByText('Current question');fireEvent.click(screen.getByRole('button',{name:/Archived piece/}));await screen.findByText('Archived question');
 expect(screen.getByRole('button',{name:'Export conversation',exact:true})).toBeInTheDocument();
 expect(screen.getByRole('button',{name:'Export with diagnostics'})).toBeInTheDocument();
 expect(screen.getByLabelText('Current composer')).toHaveValue('Unsent work');
 fireEvent.change(screen.getByLabelText('Conversation name'),{target:{value:'Shop relationships'}});
 vi.mocked(api.renameConversation).mockResolvedValue({...meta(old),title:'Shop relationships',name_revision:1});
 fireEvent.click(screen.getByRole('button',{name:'Save name'}));await screen.findByText('Name saved.');expect(api.renameConversation).toHaveBeenCalledWith('world-one',old,'Shop relationships',0);
});
it('keeps an uncertain typed name and retries its exact revision',async()=>{
 render(<ConversationLibrary worldId="world-one" onClose={()=>{}}/>);await screen.findByText('Current question');fireEvent.change(screen.getByLabelText('Conversation name'),{target:{value:'Keep name'}});
 vi.mocked(api.renameConversation).mockRejectedValueOnce(new Error('Connection lost')).mockResolvedValueOnce({...meta(),title:'Keep name',name_revision:1});
 fireEvent.click(screen.getByRole('button',{name:'Save name'}));await screen.findByRole('alert');expect(screen.getByLabelText('Conversation name')).toHaveValue('Keep name');
 fireEvent.click(screen.getByRole('button',{name:'Save name'}));await screen.findByText('Name saved.');expect(vi.mocked(api.renameConversation).mock.calls).toEqual([['world-one',current,'Keep name',0],['world-one',current,'Keep name',0]]);
});
it('ignores departed World reads even after A B A',async()=>{
 let finish!:(v:api.ConversationSummary)=>void;vi.mocked(api.readConversationName).mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve;}));
 const view=render(<ConversationLibrary worldId="world-one" onClose={()=>{}}/>);await waitFor(()=>expect(api.readConversationName).toHaveBeenCalled());
 view.rerender(<ConversationLibrary worldId="world-two" onClose={()=>{}}/>);await screen.findByText('Current question');view.rerender(<ConversationLibrary worldId="world-one" onClose={()=>{}}/>);await screen.findByText('Current question');
 await act(async()=>{finish({...meta(),title:'STALE NAME'});});expect(screen.queryByDisplayValue('STALE NAME')).not.toBeInTheDocument();
});
it('ignores a late transcript after another selection',async()=>{
 let finish!:(v:api.LibraryTurns)=>void;vi.mocked(api.readConversationTurns).mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve;}));
 render(<ConversationLibrary worldId="world-one" onClose={()=>{}}/>);fireEvent.click(await screen.findByRole('button',{name:/Archived piece/}));await screen.findByText('Archived question');
 await act(async()=>{finish(page());});expect(screen.queryByText('Current question')).not.toBeInTheDocument();
});
it('loads earlier turns and traces only on request',async()=>{
 vi.mocked(api.readConversationTurns).mockResolvedValueOnce({...page(),turns:[{...page().turns[0],sequence:51}],next_before_sequence:51}).mockResolvedValueOnce({...page(),turns:[{...page().turns[0],turn_id:'44444444-4444-4444-8444-444444444444',user_text:'Earlier question'}]});
 render(<ConversationLibrary worldId="world-one" onClose={()=>{}}/>);fireEvent.click(await screen.findByRole('button',{name:'Earlier messages'}));await screen.findByText('Earlier question');expect(api.readConversationTurns).toHaveBeenLastCalledWith('world-one',current,51);
 expect(screen.queryByText('Explicit trace')).not.toBeInTheDocument();fireEvent.click(screen.getAllByText('Trace')[0]);await screen.findByText('Explicit trace');
});

it('shows saved object-only questions and page object links without editable chat plans',async()=>{
 const source={world_id:'world-one',conversation_id:current,turn_id:page().turns[0].turn_id,document_id:'source page',surface_id:'build' as const};
 vi.mocked(api.readConversationTurns).mockResolvedValue({...page(),turns:[
  {...page().turns[0],assistant_text:'',reply_object:{kind:'questions',source,questions:[{text:'Which shop should we develop?'}]}},
  {...page().turns[0],turn_id:old,sequence:2,user_text:'Prepare a plan',assistant_text:'Held for review.',reply_object:{kind:'page_object',object_kind:'plan',source:{...source,turn_id:old}}},
 ]});
 render(<><textarea aria-label="Current composer" defaultValue="Newer unsent note"/><ConversationLibrary worldId="world-one" onClose={()=>{}}/></>);
 expect(await screen.findByRole('region',{name:'Saved clarifying questions'})).toHaveTextContent('Which shop should we develop?');
 expect(screen.queryByText('No saved reply.')).not.toBeInTheDocument();
 expect(screen.getByRole('link',{name:'Open source page'})).toHaveAttribute('href','/build?world=world-one&documentId=source+page');
 expect(screen.getByText('Held for review.')).toBeInTheDocument();
 expect(screen.queryByRole('button',{name:'Continue step'})).not.toBeInTheDocument();
 expect(screen.getByLabelText('Current composer')).toHaveValue('Newer unsent note');
});
