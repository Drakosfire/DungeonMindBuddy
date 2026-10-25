import {Editor} from '@tiptap/core';
import StarterKit from '@tiptap/starter-kit';
import {webcrypto} from 'node:crypto';
import {act,cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,beforeAll,beforeEach,expect,it,vi} from 'vitest';
import {BuildConnectedPageControl} from './BuildConnectedPageControl';
import * as api from '../api/connectedPageApi';
import * as workflow from './connectedPageAuthoring';
import {postManagedWorldGraphProjection} from '../api/liveApi';
import type {ConnectedPageIntent,ConnectedPageOperation} from '../api/connectedPageApi';
const state=vi.hoisted(()=>({session:null as any,setPaneOpen:vi.fn()}));
vi.mock('../markdownCanvas/MarkdownCanvasSession',()=>({useOptionalMarkdownCanvasSession:()=>state.session}));
vi.mock('../agentInteraction/AgentInteractionProvider',()=>({useOptionalAgentInteraction:()=>({setPaneOpen:state.setPaneOpen})}));
vi.mock('../worldGraph/verifyManagedWorldGraphProjectionResponse',()=>({verifyManagedWorldGraphProjectionResponse:()=>null}));
vi.mock('../api/liveApi',async original=>({...await original<typeof import('../api/liveApi')>(),postManagedWorldGraphProjection:vi.fn()}));
vi.mock('../api/connectedPageApi',async original=>({...await original<typeof import('../api/connectedPageApi')>(),prepareConnectedPage:vi.fn(),confirmConnectedPage:vi.fn(),recoverConnectedPage:vi.fn(),readConnectedPageForPage:vi.fn()}));
const source='11111111-1111-4111-8111-111111111111',page='22222222-2222-4222-8222-222222222222';
let editor:Editor;
function operation(request:ConnectedPageIntent,phase:'prepared'|'complete'='prepared'):ConnectedPageOperation{
 return {schema:'dmb_connected_page_operation_v1',operation_id:request.operation_id,phase,intent:request,
  page:{document_id:page,world_id:'elderwyld',campaign_id:'elderwyld',kind:'worldbuilding_source',status:'active',connected_page_operation_id:request.operation_id,revision:2} as any,
  initial_source:{documentId:page,revision:2,contentSha256:'b'.repeat(64)},prepared:{confirm_token:'sealed',assertions_preview:[]},
  receipt:phase==='complete'?{committed:true,created_node_ids:{place:'native-place'}}:null,
  connections:phase==='complete'?{place_node_id:'native-place',person_node_id:request.person?.node_id??null,relationships:request.relationships}:null};
}
beforeAll(()=>{Object.defineProperty(HTMLDialogElement.prototype,'showModal',{configurable:true,value(this:HTMLDialogElement){this.setAttribute('open','');}});});
beforeEach(()=>{
 vi.clearAllMocks();sessionStorage.clear();vi.stubGlobal('crypto',webcrypto);
 editor=new Editor({extensions:[StarterKit],content:'<p><strong>Brin’s Blacksmithy</strong>: Repairs gear.</p>'});
 editor.commands.setTextSelection({from:1,to:1+'Brin’s Blacksmithy'.length});vi.spyOn(editor.view,'coordsAtPos').mockReturnValue({left:100,right:100,top:100,bottom:120});
 state.session={editor,record:{document_id:source,world_id:'elderwyld',campaign_id:'elderwyld',kind:'worldbuilding_source'},snapshot:{loaded_revision:31,content_sha256:'a'.repeat(64)},dirty:true,activeCommand:null};
 vi.mocked(postManagedWorldGraphProjection).mockResolvedValue({projection:{nodes:[{nodeId:'node:brin',label:'Brin',kind:'npc',aliases:[]}]}} as any);
 vi.mocked(api.prepareConnectedPage).mockImplementation(async request=>operation(request));
 vi.mocked(api.confirmConnectedPage).mockImplementation(async value=>operation(value.intent,'complete'));
 vi.mocked(api.recoverConnectedPage).mockImplementation(async request=>operation(request));
});
afterEach(()=>{cleanup();editor.destroy();vi.restoreAllMocks();});
async function open(){fireEvent.click(screen.getByRole('button',{name:'＋ New page'}));await screen.findByRole('dialog',{name:'New page from selection'});await waitFor(()=>expect(screen.queryByText('Finding existing people and places…')).not.toBeInTheDocument());}
async function connections(){fireEvent.change(screen.getByLabelText('Person identity'),{target:{value:'node:brin'}});
 fireEvent.click(screen.getByRole('checkbox',{name:'Brin owns Brin’s Blacksmithy'}));fireEvent.click(screen.getByRole('checkbox',{name:'Brin operates Brin’s Blacksmithy'}));}
it('reviews exact existing Brin and both relationships before one create/confirm, preserving the dirty source',async()=>{
 const select=vi.fn(async()=>true),before=editor.getJSON();
 render(<BuildConnectedPageControl selectDocument={select} refreshDocuments={vi.fn()}/>);await open();await connections();
 expect(api.prepareConnectedPage).not.toHaveBeenCalled();expect(api.confirmConnectedPage).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole('button',{name:'Create page'}));
 await waitFor(()=>expect(select).toHaveBeenCalledWith(page));
 const request=vi.mocked(api.prepareConnectedPage).mock.calls[0][0];
 expect(request.person).toEqual({node_id:'node:brin',label:'Brin',kind:'npc'});expect(request.relationships).toEqual(['owns','operates']);
 expect(request.origin.selected_text).toBe('Brin’s Blacksmithy');expect(JSON.parse(request.origin.editor_json)).toEqual(before);
 expect(editor.getJSON()).toEqual(before);expect(api.prepareConnectedPage).toHaveBeenCalledTimes(1);expect(api.confirmConnectedPage).toHaveBeenCalledTimes(1);
 expect(sessionStorage.getItem(workflow.connectedPageRecoveryKey('elderwyld',source))).toBeNull();
});
it('retains exact request before dispatch and requires deliberate retry after reload',async()=>{
 const select=vi.fn(async()=>true);let original:ConnectedPageIntent;
 vi.mocked(api.prepareConnectedPage).mockImplementationOnce(async request=>{original=request;
  expect(workflow.readConnectedPageRecovery('elderwyld',source)).toEqual(request);throw new Error('Connection lost');});
 let view=render(<BuildConnectedPageControl selectDocument={select} refreshDocuments={vi.fn()}/>);await open();
 fireEvent.click(screen.getByRole('button',{name:'Create page'}));await screen.findByText('Connection lost');
 view.unmount();view=render(<BuildConnectedPageControl selectDocument={select} refreshDocuments={vi.fn()}/>);
 await screen.findByRole('button',{name:'Resume page creation'});expect(api.prepareConnectedPage).toHaveBeenCalledTimes(1);expect(api.confirmConnectedPage).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole('button',{name:'Resume page creation'}));fireEvent.click(await screen.findByRole('button',{name:'↻ Retry'}));
 await waitFor(()=>expect(select).toHaveBeenCalledWith(page));expect(vi.mocked(api.prepareConnectedPage).mock.calls[1][0]).toEqual(original!);
});
it('queues build out only after exact page activation and leaves writer authority to the conversation',async()=>{
 const queued=vi.spyOn(workflow,'queueConnectedPageBuildOut').mockImplementation(()=>{}),select=vi.fn(async()=>true);
 render(<BuildConnectedPageControl selectDocument={select} refreshDocuments={vi.fn()}/>);await open();
 fireEvent.click(screen.getByRole('radio',{name:'Build out — let Buddy develop it'}));fireEvent.click(screen.getByRole('button',{name:'Create page'}));
 await waitFor(()=>expect(queued).toHaveBeenCalledTimes(1));expect(select).toHaveBeenCalledBefore(queued);expect(state.setPaneOpen).toHaveBeenCalledWith(true);
});
it('keeps the completed request when activation fails, without queueing generation',async()=>{
 const queued=vi.spyOn(workflow,'queueConnectedPageBuildOut').mockImplementation(()=>{});
 render(<BuildConnectedPageControl selectDocument={vi.fn(async()=>false)} refreshDocuments={vi.fn()}/>);await open();
 fireEvent.click(screen.getByRole('radio',{name:'Build out — let Buddy develop it'}));fireEvent.click(screen.getByRole('button',{name:'Create page'}));
 await screen.findByText('The page was created. Open it again to continue.');expect(queued).not.toHaveBeenCalled();
 expect(workflow.readConnectedPageRecovery('elderwyld',source)).not.toBeNull();
});
it('refuses a source edited after capture before any request',async()=>{
 render(<BuildConnectedPageControl selectDocument={vi.fn(async()=>true)} refreshDocuments={vi.fn()}/>);await open();
 act(()=>{editor.commands.insertContent('changed');});fireEvent.click(screen.getByRole('button',{name:'Create page'}));
 await screen.findByText('The source changed. Close this form and select the passage again.');expect(api.prepareConnectedPage).not.toHaveBeenCalled();
});
it('allows a new capture only after the server confirms no operation exists',async()=>{
 const {LiveApiError}=await import('../api/liveApi');
 vi.mocked(api.prepareConnectedPage).mockRejectedValueOnce(new LiveApiError('Saved source changed',409));
 vi.mocked(api.recoverConnectedPage).mockRejectedValue(new LiveApiError('Not found',404));
 render(<BuildConnectedPageControl selectDocument={vi.fn(async()=>true)} refreshDocuments={vi.fn()}/>);await open();
 fireEvent.click(screen.getByRole('button',{name:'Create page'}));
 fireEvent.click(await screen.findByRole('button',{name:'Choose a new selection'}));
 expect(workflow.readConnectedPageRecovery('elderwyld',source)).toBeNull();expect(api.prepareConnectedPage).toHaveBeenCalledTimes(1);
});
it('does not dispatch creation when this tab cannot retain its exact request',async()=>{
 render(<BuildConnectedPageControl selectDocument={vi.fn(async()=>true)} refreshDocuments={vi.fn()}/>);await open();
 vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw new Error('Storage unavailable');});
 fireEvent.click(screen.getByRole('button',{name:'Create page'}));await screen.findByText('Storage unavailable');
 expect(api.prepareConnectedPage).not.toHaveBeenCalled();expect(api.confirmConnectedPage).not.toHaveBeenCalled();
});
