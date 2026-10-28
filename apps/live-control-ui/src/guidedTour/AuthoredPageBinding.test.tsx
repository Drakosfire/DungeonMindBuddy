import {act,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {useRef,useState} from 'react';
import {beforeEach,expect,it,vi} from 'vitest';
import type {MarkdownCanvasSessionValue} from '../markdownCanvas/MarkdownCanvasSession';
import type {SavedWorldBuildConversationContext} from '../agentInteraction/WorldAgentConversation';
import {BuildTourObservations} from './OwnerObservations';
import {GuidedTourProvider,useGuidedTour,type TourDispatchScope} from './GuidedTour';
import {readWalkthrough} from './storage';
function Owner({sameDocument=false}:{sameDocument?:boolean}){
 const tour=useGuidedTour()!,[documentId,setDocumentId]=useState('source'),[revision,setRevision]=useState(1),[receipt,setReceipt]=useState<unknown>(null),[scope,setScope]=useState<TourDispatchScope|null>(null);
 const pending=useRef<(()=>void)|null>(null);
 const save=(captured:TourDispatchScope|null)=>{const next=revision+1;setScope(captured);setRevision(next);setReceipt({writer_ok:true,committed_record:{world_id:'world',updated_at:new Date().toISOString()},document_id:documentId,registry_revision:next,normalized_content_sha256:'a'.repeat(64)});};
 const source={worldId:'world',documentId,revision,contentSha256:'a'.repeat(64),dirty:false,title:documentId} as SavedWorldBuildConversationContext;
 const session={phase:'ready_clean',activeCommand:null,lastCommitReceipt:receipt,tourSaveScope:scope,saveDisabledReason:null} as MarkdownCanvasSessionValue;
 return <><BuildTourObservations source={source} session={session}/><button onClick={tour.open}>Open guidance</button>
 <button onClick={()=>{setDocumentId(sameDocument?'source':'notes');setReceipt(null);}}>Open authored page</button>
 <button onClick={()=>{setDocumentId('different');setReceipt(null);}}>Open different page</button>
 <button onClick={()=>save(tour.captureScope())}>Ordinary Save</button>
 <button onClick={()=>{const captured=tour.captureScope();pending.current=()=>save(captured);}}>Dispatch pending Save</button><button onClick={()=>pending.current?.()}>Finish pending Save</button></>;
}
beforeEach(()=>{localStorage.clear();Object.defineProperty(navigator,'locks',{configurable:true,value:{request:vi.fn(async(_name:string,callback:()=>unknown)=>callback())}});});
async function start(){
 fireEvent.click(screen.getByText('Open guidance'));fireEvent.click(screen.getByRole('button',{name:'A Wild Sheep Chase'}));await screen.findByRole('button',{name:'Use this source · source'});fireEvent.click(screen.getByRole('button',{name:'Use this source · source'}));await waitFor(()=>expect(readWalkthrough(localStorage,'world')?.record.bindings.source?.objectId).toBe('source'));fireEvent.click(screen.getByRole('button',{name:'Next'}));await screen.findByRole('heading',{name:'Develop and save a page'});
}
it.each([false,true])('explicitly tracks the authored page independently; same document=%s',async sameDocument=>{
 render(<GuidedTourProvider worldId='world'><Owner sameDocument={sameDocument}/></GuidedTourProvider>);await start();fireEvent.click(screen.getByText('Open authored page'));
 const pageId=sameDocument?'source':'notes';await screen.findByRole('button',{name:'Use this page · '+pageId});fireEvent.click(screen.getByRole('button',{name:'Use this page · '+pageId}));await waitFor(()=>expect(readWalkthrough(localStorage,'world')?.record.bindings.page?.objectId).toBe(pageId));
 fireEvent.click(screen.getByText('Ordinary Save'));await waitFor(()=>expect(readWalkthrough(localStorage,'world')?.record.steps.authoring.state).toBe('completed'));
 const record=readWalkthrough(localStorage,'world')!.record;expect(record.bindings.source?.objectId).toBe('source');expect(record.bindings.source?.revision).toBe(1);expect(record.steps.authoring.evidence.at(-1)?.target).toMatchObject({kind:'page',objectId:pageId,revision:2});expect(record.bindings.plan).toBeUndefined();
});
it('does not bind or credit a Save before explicit page selection',async()=>{
 render(<GuidedTourProvider worldId='world'><Owner/></GuidedTourProvider>);await start();fireEvent.click(screen.getByText('Open authored page'));fireEvent.click(screen.getByText('Ordinary Save'));await act(async()=>{});expect(readWalkthrough(localStorage,'world')?.record.bindings.page).toBeUndefined();
 fireEvent.click(screen.getByRole('button',{name:'Use this page · notes'}));await waitFor(()=>expect(readWalkthrough(localStorage,'world')?.record.steps.authoring.state).toBe('existing'));
 fireEvent.click(screen.getByText('Ordinary Save'));await waitFor(()=>expect(readWalkthrough(localStorage,'world')?.record.steps.authoring.state).toBe('completed'));
});
it('refuses a different page Save after selection',async()=>{
 render(<GuidedTourProvider worldId='world'><Owner/></GuidedTourProvider>);await start();fireEvent.click(screen.getByText('Open authored page'));fireEvent.click(screen.getByRole('button',{name:'Use this page · notes'}));await waitFor(()=>expect(readWalkthrough(localStorage,'world')?.record.bindings.page?.objectId).toBe('notes'));
 fireEvent.click(screen.getByText('Open different page'));fireEvent.click(screen.getByText('Ordinary Save'));await act(async()=>{});
 expect(readWalkthrough(localStorage,'world')?.record.steps.authoring.state).toBe('existing');expect(readWalkthrough(localStorage,'world')?.record.bindings.page?.objectId).toBe('notes');expect(screen.getByText(/This is a different target/)).toBeInTheDocument();
});

it('does not credit work dispatched before page selection even if it completes afterward',async()=>{
 render(<GuidedTourProvider worldId='world'><Owner/></GuidedTourProvider>);await start();fireEvent.click(screen.getByText('Open authored page'));fireEvent.click(screen.getByText('Dispatch pending Save'));
 fireEvent.click(screen.getByRole('button',{name:'Use this page · notes'}));await waitFor(()=>expect(readWalkthrough(localStorage,'world')?.record.bindings.page?.objectId).toBe('notes'));
 fireEvent.click(screen.getByText('Finish pending Save'));await act(async()=>{});expect(readWalkthrough(localStorage,'world')?.record.steps.authoring.state).toBe('existing');
});
