import {Editor} from '@tiptap/core';
import StarterKit from '@tiptap/starter-kit';
import {webcrypto} from 'node:crypto';
import {act,cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,beforeAll,beforeEach,expect,it,vi} from 'vitest';
import {useConnectedPageReviewHost,type ConnectedPageReviewSeed} from './connectedPageReviewHost';
import {BuildConnectedPageControl} from './BuildConnectedPageControl';
import * as api from '../api/connectedPageApi';
import * as workflow from './connectedPageAuthoring';
import {ConversationConnectedPageReview} from '../planSurface/components/ConversationConnectedPageReview';
import {getAgentRelatedPage,postManagedWorldGraphProjection,getGraphObjectAuthoringKinds} from '../api/liveApi';
import type {ConnectedPageIntent,ConnectedPageOperation} from '../api/connectedPageApi';
const state=vi.hoisted(()=>({session:null as any,setPaneOpen:vi.fn()}));
vi.mock('../markdownCanvas/MarkdownCanvasSession',()=>({useOptionalMarkdownCanvasSession:()=>state.session}));
vi.mock('../agentInteraction/AgentInteractionProvider',()=>({useOptionalAgentInteraction:()=>({setPaneOpen:state.setPaneOpen})}));
vi.mock('../worldGraph/verifyManagedWorldGraphProjectionResponse',()=>({verifyManagedWorldGraphProjectionResponse:()=>null}));
vi.mock('../api/liveApi',async original=>({...await original<typeof import('../api/liveApi')>(),postManagedWorldGraphProjection:vi.fn(),getAgentRelatedPage:vi.fn(),getGraphObjectAuthoringKinds:vi.fn()}));
vi.mock('../api/connectedPageApi',async original=>({...await original<typeof import('../api/connectedPageApi')>(),prepareConnectedPage:vi.fn(),confirmConnectedPage:vi.fn(),recoverConnectedPage:vi.fn(),readConnectedPageForPage:vi.fn()}));
const source='11111111-1111-4111-8111-111111111111',page='22222222-2222-4222-8222-222222222222';
let editor:Editor;
function operation(request:ConnectedPageIntent,phase:'prepared'|'complete'='prepared'):ConnectedPageOperation{
 return {schema:'kind' in request.origin?'dmb_connected_page_operation_v2':'dmb_connected_page_operation_v1',operation_id:request.operation_id,phase,intent:request,
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
it('retains an uncertain request even when its recovery read returns not found',async()=>{
 const {LiveApiError}=await import('../api/liveApi');
 vi.mocked(api.prepareConnectedPage).mockRejectedValueOnce(new LiveApiError('Saved source changed',409));
 vi.mocked(api.recoverConnectedPage).mockRejectedValue(new LiveApiError('Not found',404));
 render(<BuildConnectedPageControl selectDocument={vi.fn(async()=>true)} refreshDocuments={vi.fn()}/>);await open();
 fireEvent.click(screen.getByRole('button',{name:'Create page'}));
 await screen.findByText('Saved source changed');
 expect(screen.queryByRole('button',{name:'Choose a new selection'})).not.toBeInTheDocument();
 expect(workflow.readConnectedPageRecovery('elderwyld',source)).not.toBeNull();expect(api.prepareConnectedPage).toHaveBeenCalledTimes(1);
});
it('does not dispatch creation when this tab cannot retain its exact request',async()=>{
 render(<BuildConnectedPageControl selectDocument={vi.fn(async()=>true)} refreshDocuments={vi.fn()}/>);await open();
 vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw new Error('Storage unavailable');});
 fireEvent.click(screen.getByRole('button',{name:'Create page'}));await screen.findByText('Storage unavailable');
 expect(api.prepareConnectedPage).not.toHaveBeenCalled();expect(api.confirmConnectedPage).not.toHaveBeenCalled();
});

it.each(['document','world','unmount'] as const)('does not activate or confirm a late prepare after %s departure',async departure=>{
 let finish!:(value:ConnectedPageOperation)=>void;let request!:ConnectedPageIntent;
 vi.mocked(api.prepareConnectedPage).mockImplementation(value=>{request=value;return new Promise(resolve=>{finish=resolve;});});
 const select=vi.fn(async()=>true),view=render(<BuildConnectedPageControl selectDocument={select} refreshDocuments={vi.fn()}/>);await open();
 fireEvent.click(screen.getByRole('button',{name:'Create page'}));await waitFor(()=>expect(api.prepareConnectedPage).toHaveBeenCalledTimes(1));
 if(departure==='unmount')view.unmount();else{state.session={...state.session,record:{...state.session.record,[departure==='world'?'world_id':'document_id']:'other'}};view.rerender(<BuildConnectedPageControl selectDocument={select} refreshDocuments={vi.fn()}/>);}
 await act(async()=>{finish(operation(request));});expect(api.confirmConnectedPage).not.toHaveBeenCalled();expect(select).not.toHaveBeenCalled();
 expect(workflow.readConnectedPageRecovery('elderwyld',source)).not.toBeNull();
});
it('does not navigate on late confirmation after leaving the source',async()=>{
 let finish!:(value:ConnectedPageOperation)=>void;let prepared!:ConnectedPageOperation;
 vi.mocked(api.confirmConnectedPage).mockImplementation(value=>{prepared=value;return new Promise(resolve=>{finish=resolve;});});
 const select=vi.fn(async()=>true),view=render(<BuildConnectedPageControl selectDocument={select} refreshDocuments={vi.fn()}/>);await open();
 fireEvent.click(screen.getByRole('button',{name:'Create page'}));await waitFor(()=>expect(api.confirmConnectedPage).toHaveBeenCalledTimes(1));
 state.session={...state.session,record:{...state.session.record,document_id:'other'}};view.rerender(<BuildConnectedPageControl selectDocument={select} refreshDocuments={vi.fn()}/>);
 await act(async()=>{finish(operation(prepared.intent,'complete'));});expect(select).not.toHaveBeenCalled();
});

it('distinguishes same-name canonical people before review',async()=>{
 vi.mocked(postManagedWorldGraphProjection).mockResolvedValue({projection:{nodes:[{nodeId:'node:brin',label:'Brin',kind:'npc'},{nodeId:'node:other-brin',label:'Brin',kind:'npc'}]}} as any);
 render(<BuildConnectedPageControl selectDocument={vi.fn(async()=>true)} refreshDocuments={vi.fn()}/>);await open();
 expect(screen.getByRole('option',{name:'Existing: Brin (node:brin)'})).toBeInTheDocument();
 expect(screen.getByRole('option',{name:'Existing: Brin (node:other-brin)'})).toBeInTheDocument();
});

it('hosts relationships and origin only in Source actions, without a generation action',async()=>{
 const request={operation_id:'33333333-3333-4333-8333-333333333333',world_id:'elderwyld',title:'Brin’s Blacksmithy',origin:{document_id:source,revision:31,content_sha256:'a'.repeat(64)},place:{node_id:null,label:'Brin’s Blacksmithy',kind:'location'},person:{node_id:'node:brin',label:'Brin',kind:'npc'},relationships:['owns','operates'],mode:'scaffold',instructions:''} as ConnectedPageIntent;
 state.session.record={...state.session.record,document_id:page,connected_page_operation_id:request.operation_id};
 vi.mocked(api.readConnectedPageForPage).mockResolvedValue(operation(request,'complete'));
 const host=document.createElement('div');document.body.appendChild(host);
 try{
  const view=render(<BuildConnectedPageControl selectDocument={vi.fn(async()=>true)} refreshDocuments={vi.fn()} relationshipsHost={host}/>);
  const summary=await screen.findByText('Relationships & origin');expect(host.contains(summary)).toBe(true);fireEvent.click(summary);
  expect(screen.getByRole('link',{name:'Original passage'})).toHaveAttribute('href',expect.stringContaining(source));
  expect(screen.queryByRole('button',{name:'Build out this page'})).not.toBeInTheDocument();
  view.rerender(<BuildConnectedPageControl selectDocument={vi.fn(async()=>true)} refreshDocuments={vi.fn()} relationshipsHost={null}/>);
  expect(screen.queryByText('Relationships & origin')).not.toBeInTheDocument();
 }finally{host.remove();}
});

const reviewSeed:ConnectedPageReviewSeed={worldId:'elderwyld',ownerDocumentId:source,sourceTurnId:'turn',proposal:{kind:'connected_page',title:'Copper Workshop',read_id:page,quote:'Copper',person_label:null,relationships:[],instructions:'A practical workshop'},origin:{kind:'saved_page_excerpt',document_id:page,revision:7,content_sha256:'b'.repeat(64),line_start:3,line_end:3,selected_text:'Copper House keeps a lantern.'}};
function ReviewProbe(){const host=useConnectedPageReviewHost();return <button disabled={!host} onClick={()=>host!.open(reviewSeed)}>Open provided review</button>;}
it('retains edited cross-page review through reload, then creates once with no source mutation',async()=>{
 const select=vi.fn(async()=>true),before=editor.getJSON();let view=render(<><BuildConnectedPageControl selectDocument={select} refreshDocuments={vi.fn()}/><ReviewProbe/></>);
 fireEvent.click(screen.getByRole('button',{name:'Open provided review'}));await screen.findByRole('dialog',{name:'New page from selection'});
 expect(api.prepareConnectedPage).not.toHaveBeenCalled();fireEvent.change(screen.getByLabelText('Page title'),{target:{value:'Copper Lantern Workshop'}});
 fireEvent.click(screen.getByRole('button',{name:'Close new page'}));view.unmount();
 view=render(<><BuildConnectedPageControl selectDocument={select} refreshDocuments={vi.fn()}/><ReviewProbe/></>);
 fireEvent.click(await screen.findByRole('button',{name:'Resume page review'}));expect(screen.getByLabelText('Page title')).toHaveValue('Copper Lantern Workshop');
 await waitFor(()=>expect(screen.getByRole('button',{name:'Create page'})).toBeEnabled());fireEvent.click(screen.getByRole('button',{name:'Create page'}));await waitFor(()=>expect(select).toHaveBeenCalledWith(page));
 const request=vi.mocked(api.prepareConnectedPage).mock.calls[0][0];expect(request.origin).toEqual(reviewSeed.origin);expect(request.title).toBe('Copper Lantern Workshop');expect(api.confirmConnectedPage).toHaveBeenCalledTimes(1);expect(editor.getJSON()).toEqual(before);
});
it('recovers the same cross-page operation after an uncertain prepare without duplicating its identity',async()=>{
 vi.mocked(api.prepareConnectedPage).mockRejectedValueOnce(new Error('Connection lost'));
 let view=render(<><BuildConnectedPageControl selectDocument={vi.fn(async()=>true)} refreshDocuments={vi.fn()}/><ReviewProbe/></>);
 fireEvent.click(screen.getByRole('button',{name:'Open provided review'}));await waitFor(()=>expect(screen.getByRole('button',{name:'Create page'})).toBeEnabled());fireEvent.click(screen.getByRole('button',{name:'Create page'}));await screen.findByText('Connection lost');
 const first=vi.mocked(api.prepareConnectedPage).mock.calls[0][0];expect(workflow.readConnectedPageRecovery('elderwyld',source)).toEqual(first);view.unmount();
 view=render(<BuildConnectedPageControl selectDocument={vi.fn(async()=>true)} refreshDocuments={vi.fn()}/>);fireEvent.click(await screen.findByRole('button',{name:'Resume page creation'}));fireEvent.click(screen.getByRole('button',{name:'↻ Retry'}));await waitFor(()=>expect(api.prepareConnectedPage).toHaveBeenCalledTimes(2));expect(vi.mocked(api.prepareConnectedPage).mock.calls[1][0]).toEqual(first);
});

it('connects the actual conversation review card to the shared form without an editor selection',async()=>{
 const body='| Name | Task |\n| Copper House | Repair lantern |\n',hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(body))),b=>b.toString(16).padStart(2,'0')).join('');
 const proposal={...reviewSeed.proposal,quote:'Copper House | Repair lantern'};
 vi.mocked(getAgentRelatedPage).mockResolvedValue({schema:'dmb_agent_related_page_read_v1',world_id:'elderwyld',turn_id:'turn',read_id:proposal.read_id,page:{world_id:'elderwyld',document_id:page,registry_revision:7,title:'Households',visibility:'internal',content_sha256:hash},markdown:body});
 editor.commands.setTextSelection(1);const before=editor.getJSON(),select=vi.fn(async()=>true);
 render(<><BuildConnectedPageControl selectDocument={select} refreshDocuments={vi.fn()}/><ConversationConnectedPageReview worldId='elderwyld' documentId={source} turnId='turn' proposal={proposal} disabled={false}/></>);
 fireEvent.click(screen.getByRole('button',{name:'Review new page'}));await screen.findByLabelText('Page title');expect(api.prepareConnectedPage).not.toHaveBeenCalled();
 fireEvent.change(screen.getByLabelText('Page title'),{target:{value:'Reviewed Copper Workshop'}});await waitFor(()=>expect(screen.getByRole('button',{name:'Create page'})).toBeEnabled());fireEvent.click(screen.getByRole('button',{name:'Create page'}));await waitFor(()=>expect(select).toHaveBeenCalledWith(page));
 expect(vi.mocked(api.prepareConnectedPage).mock.calls[0][0]).toMatchObject({title:'Reviewed Copper Workshop',origin:{kind:'saved_page_excerpt',document_id:page,line_start:2,line_end:2,selected_text:'| Copper House | Repair lantern |'}});expect(editor.getJSON()).toEqual(before);
});

it('retains the exact request after rejection and an absent recovery result',async()=>{
 vi.mocked(api.prepareConnectedPage).mockRejectedValue(new (await import('../api/liveApi')).LiveApiError('Saved source changed',409));
 vi.mocked(api.recoverConnectedPage).mockRejectedValue(new (await import('../api/liveApi')).LiveApiError('Not found',404));
 render(<><BuildConnectedPageControl selectDocument={vi.fn(async()=>true)} refreshDocuments={vi.fn()}/><ReviewProbe/></>);
 fireEvent.click(screen.getByRole('button',{name:'Open provided review'}));await waitFor(()=>expect(screen.getByRole('button',{name:'Create page'})).toBeEnabled());fireEvent.click(screen.getByRole('button',{name:'Create page'}));await screen.findByText('Saved source changed');
 expect(screen.queryByRole('button',{name:'Start a fresh review'})).not.toBeInTheDocument();expect(workflow.readConnectedPageRecovery('elderwyld',source)?.operation_id).toBe(vi.mocked(api.prepareConnectedPage).mock.calls[0][0].operation_id);
});

it('opens relationship review from the shared selection toolbar only on a saved page',async()=>{
 localStorage.clear();Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async(_key:string,fn:()=>unknown)=>fn()}});
 vi.mocked(getGraphObjectAuthoringKinds).mockResolvedValue({objectKinds:['npc','location']});
 render(<BuildConnectedPageControl selectDocument={vi.fn(async()=>true)} refreshDocuments={vi.fn()}/>);
 fireEvent.click(screen.getByRole('button',{name:'Relationship'}));expect(await screen.findByRole('alert')).toHaveTextContent('Save the page');expect(screen.queryByRole('dialog',{name:'Review relationship'})).not.toBeInTheDocument();
 state.session.dirty=false;fireEvent.click(screen.getByRole('button',{name:'Relationship'}));await screen.findByRole('dialog',{name:'Review relationship'});expect(await screen.findByLabelText('Supporting passage')).toHaveValue('Brin’s Blacksmithy');
 expect(api.prepareConnectedPage).not.toHaveBeenCalled();expect(api.confirmConnectedPage).not.toHaveBeenCalled();
 localStorage.clear();
});
