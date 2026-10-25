import {act,cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,beforeAll,beforeEach,expect,it,vi} from 'vitest';
import {BuildRelationshipReview} from './BuildRelationshipReview';
import {relationshipKey,readRelationshipReview} from './buildRelationshipRecovery';
import * as api from '../api/liveApi';
import {graphDocumentRelationshipRequest} from '../api/graphDocumentRelationshipApi';
const state=vi.hoisted(()=>({session:null as any}));
vi.mock('../markdownCanvas/MarkdownCanvasSession',()=>({useOptionalMarkdownCanvasSession:()=>state.session}));
vi.mock('../worldGraph/verifyManagedWorldGraphProjectionResponse',()=>({verifyManagedWorldGraphProjectionResponse:()=>null}));
vi.mock('../api/liveApi',()=>({getGraphObjectAuthoringKinds:vi.fn(),postManagedWorldGraphProjection:vi.fn(),prepareGraphObjectAuthoringWrite:vi.fn(),commitGraphObjectAuthoringWrite:vi.fn()}));
vi.mock('../api/graphDocumentRelationshipApi',()=>({graphDocumentRelationshipRequest:vi.fn()}));
const world='test-world',doc='11111111-1111-4111-8111-111111111111',key=relationshipKey(world,doc);
const seed={document_source:{documentId:doc,revision:4,contentSha256:'a'.repeat(64)},quote:'Rowan worked with Brin temporarily.'};
const prepared={prepared:true,campaign_id:world,world_id:'native-world',authority_operation_id:'operation',expressibility:'EXPRESSIBLE',confirm_token:'exact-token',current_overlay_token:null,assertions_preview:[{assertion_id:'r',summary:'Past temporary work'}]} as any;
const receipt={committed:true,campaign_id:world,world_id:'native-world',operation_id:'operation',published_revision_id:'revision'} as any;
function View({initial=seed}: {initial?:typeof seed|null}){return <BuildRelationshipReview worldId={world} documentId={doc} seed={initial} onConsumed={()=>{}}/>;}
const retained=()=>readRelationshipReview(localStorage.getItem(key),world,doc)!;
beforeAll(()=>Object.defineProperty(HTMLDialogElement.prototype,'showModal',{configurable:true,value(this:HTMLDialogElement){this.setAttribute('open','');}}));
beforeEach(()=>{
 vi.clearAllMocks();localStorage.clear();let queue=Promise.resolve();Object.defineProperty(navigator,'locks',{configurable:true,value:{request:(_key:string,fn:()=>unknown)=>{const next=queue.then(fn);queue=next.then(()=>{},()=>{});return next;}}});
 state.session={record:{world_id:world,document_id:doc},snapshot:{loaded_revision:4,content_sha256:'a'.repeat(64)},dirty:false,activeCommand:null};
 vi.mocked(api.getGraphObjectAuthoringKinds).mockResolvedValue({objectKinds:['npc','location']});
 vi.mocked(api.postManagedWorldGraphProjection).mockResolvedValue({projection:{nodes:[{nodeId:'node:brin',label:'Brin',kind:'npc'}]}} as any);
 vi.mocked(graphDocumentRelationshipRequest).mockImplementation(async i=>({worldId:world,campaignId:world,documentSource:i.document_source,proposals:[{localProposalId:'relationship',proposalKind:'relationship',selection:{selectedText:i.quote},relationshipType:i.predicate}]} as any));
 vi.mocked(api.prepareGraphObjectAuthoringWrite).mockResolvedValue(prepared);vi.mocked(api.commitGraphObjectAuthoringWrite).mockResolvedValue(receipt);
});
afterEach(cleanup);
async function edit(name:string,text:string){await act(async()=>{fireEvent.change(screen.getByLabelText(name,{exact:true}),{target:{value:text}});});}
async function filled(){await screen.findByRole('button',{name:'Preview relationship'});await waitFor(()=>expect(screen.getByRole('button',{name:'Preview relationship'})).toBeEnabled());
 await edit('source name','Rowan');await edit('target identity','node:brin');await edit('Relationship type','works_with');await edit('Readable relationship','worked together temporarily');await edit('Context, including when','A past temporary stint, not current employment.');}
async function preview(){fireEvent.click(screen.getByRole('button',{name:'Preview relationship'}));await screen.findByRole('button',{name:'Confirm relationship'});}
it('restores edited review and requires explicit confirmation after preview',async()=>{
 const view=render(<View/>);await filled();view.unmount();render(<View initial={null}/>);fireEvent.click(screen.getByRole('button',{name:'Resume relationship review'}));expect(await screen.findByLabelText('source name')).toHaveValue('Rowan');await waitFor(()=>expect(screen.getByRole('button',{name:'Preview relationship'})).toBeEnabled());await preview();expect(api.commitGraphObjectAuthoringWrite).not.toHaveBeenCalled();fireEvent.click(screen.getByRole('button',{name:'Confirm relationship'}));expect(await screen.findByRole('status')).toHaveTextContent('Relationship published');expect(api.commitGraphObjectAuthoringWrite).toHaveBeenCalledTimes(1);expect(retained().receipt).toEqual(receipt);
});
it('retries the exact uncertain confirmation after reload without another preview',async()=>{
 vi.mocked(api.commitGraphObjectAuthoringWrite).mockRejectedValueOnce(new Error('Response lost'));const view=render(<View/>);await filled();await preview();fireEvent.click(screen.getByRole('button',{name:'Confirm relationship'}));await screen.findByRole('alert');const sent=vi.mocked(api.commitGraphObjectAuthoringWrite).mock.calls[0][0];expect(retained().submitted).toBe(true);view.unmount();render(<View initial={null}/>);fireEvent.click(screen.getByRole('button',{name:'Resume relationship review'}));fireEvent.click(await screen.findByRole('button',{name:'Retry exact confirmation'}));await screen.findByRole('status');expect(vi.mocked(api.commitGraphObjectAuthoringWrite).mock.calls[1][0]).toEqual(sent);expect(api.prepareGraphObjectAuthoringWrite).toHaveBeenCalledTimes(1);
});
it('blocks dirty preview and stale first confirmation',async()=>{
 render(<View/>);await filled();state.session.dirty=true;fireEvent.click(screen.getByRole('button',{name:'Preview relationship'}));await screen.findByRole('alert');expect(graphDocumentRelationshipRequest).not.toHaveBeenCalled();state.session.dirty=false;await preview();state.session.snapshot.loaded_revision=5;fireEvent.click(screen.getByRole('button',{name:'Confirm relationship'}));await waitFor(()=>expect(screen.getByRole('alert')).toHaveTextContent('source changed'));expect(api.commitGraphObjectAuthoringWrite).not.toHaveBeenCalled();expect(retained().submitted).toBe(false);
});
it('refuses cross-tab changes before confirmation without overwriting them',async()=>{
 render(<View/>);await filled();await preview();const other=retained();other.intent.context='Changed in another tab';localStorage.setItem(key,JSON.stringify(other));fireEvent.click(screen.getByRole('button',{name:'Confirm relationship'}));await screen.findByRole('alert');expect(api.commitGraphObjectAuthoringWrite).not.toHaveBeenCalled();expect(retained().intent.context).toBe('Changed in another tab');
});
it('retains failed preview and allows deliberate editing before confirmation',async()=>{
 vi.mocked(api.prepareGraphObjectAuthoringWrite).mockRejectedValueOnce(new Error('Preview unavailable'));render(<View/>);await filled();fireEvent.click(screen.getByRole('button',{name:'Preview relationship'}));await screen.findByRole('alert');expect(retained().request).not.toBeNull();fireEvent.click(screen.getByRole('button',{name:'Edit relationship'}));await screen.findByRole('button',{name:'Preview relationship'});expect(retained().request).toBeNull();expect(screen.getByLabelText('source name')).toHaveValue('Rowan');expect(api.commitGraphObjectAuthoringWrite).not.toHaveBeenCalled();
});
it('does not apply a late preview after unmount and remount',async()=>{
 let finish!:(v:any)=>void;vi.mocked(api.prepareGraphObjectAuthoringWrite).mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve;}));const view=render(<View/>);await filled();fireEvent.click(screen.getByRole('button',{name:'Preview relationship'}));await waitFor(()=>expect(api.prepareGraphObjectAuthoringWrite).toHaveBeenCalledTimes(1));view.unmount();render(<View initial={null}/>);await act(async()=>finish(prepared));expect(retained().prepared).toBeNull();expect(api.commitGraphObjectAuthoringWrite).not.toHaveBeenCalled();
});
it('preserves corrupt retained bytes and sends nothing',async()=>{
 localStorage.setItem(key,'broken');render(<View initial={null}/>);expect(await screen.findByRole('alert')).toBeVisible();expect(localStorage.getItem(key)).toBe('broken');expect(graphDocumentRelationshipRequest).not.toHaveBeenCalled();
});
it('checks the current saved source inside a queued first-confirmation lock',async()=>{
 render(<View/>);await filled();await preview();let release!:()=>void;const gate=new Promise<void>(resolve=>{release=resolve;});
 Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async(_key:string,fn:()=>unknown)=>{await gate;return fn();}}});
 fireEvent.click(screen.getByRole('button',{name:'Confirm relationship'}));state.session.dirty=true;await act(async()=>release());
 expect(await screen.findByRole('alert')).toHaveTextContent('source changed');expect(api.commitGraphObjectAuthoringWrite).not.toHaveBeenCalled();expect(retained().submitted).toBe(false);
});
it('does not dispatch after unmount while the submission lock returns',async()=>{
 const view=render(<View/>);await filled();await preview();let release!:()=>void;const gate=new Promise<void>(resolve=>{release=resolve;});
 Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async(_key:string,fn:()=>unknown)=>{const result=fn();await gate;return result;}}});
 fireEvent.click(screen.getByRole('button',{name:'Confirm relationship'}));view.unmount();await act(async()=>release());expect(api.commitGraphObjectAuthoringWrite).not.toHaveBeenCalled();expect(retained().request).not.toBeNull();
});
it('rechecks first-confirmation source after submission storage completes',async()=>{
 render(<View/>);await filled();await preview();let first=true;
 Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async(_key:string,fn:()=>unknown)=>{const result=fn();if(first){first=false;state.session.dirty=true;}return result;}}});
 fireEvent.click(screen.getByRole('button',{name:'Confirm relationship'}));expect(await screen.findByRole('alert')).toHaveTextContent('source changed');expect(api.commitGraphObjectAuthoringWrite).not.toHaveBeenCalled();expect(retained().submitted).toBe(true);
});
it.each(['null-row','object-summary','bad-token','nonboolean-prepared','wrong-receipt'] as const)('preserves malformed %s recovery without crashing or dispatch',async mutation=>{
 const view=render(<View/>);await filled();await preview();const bad=retained() as any;view.unmount();
 if(mutation==='null-row')bad.prepared.assertions_preview=[null];
 else if(mutation==='object-summary')bad.prepared.assertions_preview[0].summary={text:'Invalid child'};
 else if(mutation==='bad-token')bad.prepared.confirm_token=42;
 else if(mutation==='nonboolean-prepared')bad.prepared.prepared='yes';
 else{bad.submitted=true;bad.receipt={...receipt,operation_id:'another-operation'};}
 const raw=JSON.stringify(bad);localStorage.setItem(key,raw);render(<View initial={null}/>);expect(await screen.findByRole('alert')).toHaveTextContent('unreadable');expect(localStorage.getItem(key)).toBe(raw);expect(api.commitGraphObjectAuthoringWrite).not.toHaveBeenCalled();
});
it('never reopens shared submission for editing while another tab has an exact retry in flight',async()=>{
 render(<View/>);await filled();await preview();let releaseFirst!:()=>void,finishCommit!:(r:any)=>void;const gate=new Promise<void>(resolve=>{releaseFirst=resolve;});let first=true;
 Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async(_key:string,fn:()=>unknown)=>{const result=fn();if(first){first=false;await gate;}return result;}}});
 vi.mocked(api.commitGraphObjectAuthoringWrite).mockImplementationOnce(()=>new Promise(resolve=>{finishCommit=resolve;}));
 fireEvent.click(screen.getByRole('button',{name:'Confirm relationship'}));expect(retained().submitted).toBe(true);
 render(<View initial={null}/>);fireEvent.click(screen.getByRole('button',{name:'Resume relationship review'}));await screen.findAllByRole('button',{name:'Retry exact confirmation'});
 const retryButtons=screen.getAllByRole('button',{name:'Retry exact confirmation'});fireEvent.click(retryButtons.find(button=>!button.hasAttribute('disabled'))!);
 await waitFor(()=>expect(api.commitGraphObjectAuthoringWrite).toHaveBeenCalledTimes(1));state.session.dirty=true;await act(async()=>releaseFirst());
 expect(await screen.findByRole('alert')).toHaveTextContent('shared submission remains retained');expect(retained().submitted).toBe(true);expect(screen.queryByRole('button',{name:'Discard review'})).not.toBeInTheDocument();expect(screen.queryByRole('button',{name:'Edit relationship'})).not.toBeInTheDocument();
 await act(async()=>finishCommit(receipt));expect(retained().receipt).toEqual(receipt);expect(api.commitGraphObjectAuthoringWrite).toHaveBeenCalledTimes(1);
});
