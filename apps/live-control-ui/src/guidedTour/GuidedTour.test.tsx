import {act,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {beforeEach,it,expect,vi} from 'vitest';
import {GuidedTourProvider,useGuidedTour,useTourOwnerReading} from './GuidedTour';
import {readWalkthrough,writeWalkthrough,pointerKey} from './storage';
import {createWalkthrough,reduceTour,type TargetPin} from './protocol';
import {useState} from 'react';
const pin={kind:'source' as const,worldId:'world',objectId:'page',revision:1,digest:'a'.repeat(64)};
function Controls(){const tour=useGuidedTour();useTourOwnerReading({step:'source',target:pin,control:'source',status:'ready',observation:{step:'source',target:pin,origin:'existing',observedAt:'2026-01-01T00:00:00Z',receiptId:'verified-load'}});return <><button onClick={tour?.open}>Open guidance</button><button data-guided-control="source" onClick={()=>{throw new Error('Guidance must never execute this control');}}>Ordinary source control</button></>;}
beforeEach(()=>{localStorage.clear();Object.defineProperty(navigator,'locks',{configurable:true,value:{request:vi.fn(async(_name:string,callback:()=>unknown)=>callback())}});});
it('requires a managed World and keeps ordinary controls usable',()=>{render(<GuidedTourProvider worldId={null}><Controls/></GuidedTourProvider>);fireEvent.click(screen.getByText('Open guidance'));expect(screen.getByText('Select a managed World before starting a walkthrough.')).toBeInTheDocument();expect(screen.getByText('Ordinary source control')).toBeEnabled();});
it('stages an existing source, keeps Next separate from completion and retains restart history',async()=>{render(<GuidedTourProvider worldId='world'><Controls/></GuidedTourProvider>);fireEvent.click(screen.getByText('Open guidance'));fireEvent.click(screen.getByRole('button',{name:'Of Conks and Cons'}));await screen.findByRole('heading',{name:'Open the source'});fireEvent.click(screen.getByRole('button',{name:'Use this source'}));await screen.findByText('Existing example inspected');const old=readWalkthrough(localStorage,'world')!;expect(old.record.steps.source.state).toBe('existing');fireEvent.click(screen.getByRole('button',{name:'Next'}));await screen.findByRole('heading',{name:'Develop and save a page'});expect(readWalkthrough(localStorage,'world')?.record.steps.authoring.state).toBe('pending');fireEvent.click(screen.getByRole('button',{name:'Pause'}));await screen.findByText('Guidance paused');fireEvent.click(screen.getByRole('button',{name:'Resume'}));await screen.findByText('2 of 14');fireEvent.click(screen.getByRole('button',{name:'Restart guidance'}));await waitFor(()=>expect(readWalkthrough(localStorage,'world')?.record.id).not.toBe(old.record.id));expect(localStorage.getItem('dmb:guided-journey:v1:world:record:'+old.record.id)).not.toBeNull();});
it('reopens paused guidance after a component reload with the same bound identity',async()=>{const first=render(<GuidedTourProvider worldId='world'><Controls/></GuidedTourProvider>);fireEvent.click(screen.getByText('Open guidance'));fireEvent.click(screen.getByRole('button',{name:'A Wild Sheep Chase'}));await screen.findByRole('heading',{name:'Open the source'});fireEvent.click(screen.getByRole('button',{name:'Use this source'}));await screen.findByText('Existing example inspected');fireEvent.click(screen.getByRole('button',{name:'Pause'}));await screen.findByText('Guidance paused');first.unmount();render(<GuidedTourProvider worldId='world'><Controls/></GuidedTourProvider>);fireEvent.click(screen.getByText('Open guidance'));expect(screen.getByText('Guidance paused')).toBeInTheDocument();expect(readWalkthrough(localStorage,'world')?.record.bindings.source).toEqual(pin);});
it('preserves corrupt guidance and refuses replacement',async()=>{localStorage.setItem('dmb:guided-journey:v1:world:current','original damaged selection');render(<GuidedTourProvider worldId='world'><Controls/></GuidedTourProvider>);fireEvent.click(screen.getByText('Open guidance'));expect(screen.getByRole('alert')).toBeInTheDocument();expect(screen.getByRole('button',{name:'Of Conks and Cons'})).toBeDisabled();await act(async()=>{});expect(localStorage.getItem('dmb:guided-journey:v1:world:current')).toBe('original damaged selection');});

function UnavailableControls({status,reason}:{status:'failed'|'unavailable';reason:string}){
 const tour=useGuidedTour();useTourOwnerReading({step:'source',target:pin,control:'source',status,reason});
 return <button onClick={tour?.open}>Open guidance</button>;
}
it('retains distinct owner failure and unavailable outcomes without claiming completion',async()=>{
 const mounted=render(<GuidedTourProvider worldId='world'><UnavailableControls status='failed' reason='Source read failed.'/></GuidedTourProvider>);
 fireEvent.click(screen.getByText('Open guidance'));fireEvent.click(screen.getByRole('button',{name:'Of Conks and Cons'}));
 await waitFor(()=>expect(readWalkthrough(localStorage,'world')?.record.steps.source).toMatchObject({state:'failed',reason:'Source read failed.',evidence:[]}));
 mounted.rerender(<GuidedTourProvider worldId='world'><UnavailableControls status='unavailable' reason='Select a saved source.'/></GuidedTourProvider>);
 await waitFor(()=>expect(readWalkthrough(localStorage,'world')?.record.steps.source).toMatchObject({state:'unavailable',reason:'Select a saved source.',evidence:[]}));
});

const planPin:TargetPin={kind:'plan',worldId:'world',objectId:'plan',revision:1,revisionId:'work-1',digest:'a'.repeat(64)};
const createdRun:TargetPin={kind:'run',worldId:'world',objectId:'new-run',revision:1,digest:'a'.repeat(64)};
function CreationOwner(){const tour=useGuidedTour(),[navigated,setNavigated]=useState(false);return <button onClick={()=>{tour?.recordRunCreation({step:'play',target:createdRun,parent:planPin,origin:'acknowledged',observedAt:new Date().toISOString(),receiptId:'verified-create',proof:{kind:'run-creation',entrySceneId:'scene',preparedSceneIds:['scene']}});setNavigated(true);}}>{navigated?'Ordinary navigation completed':'Owner acknowledged Run'}</button>;}
it('retains a verified Run creation through ordinary navigation without replaying creation',async()=>{
 let walk=createWalkthrough('world','conks','walk','2026-01-01T00:00:00Z');walk=reduceTour(walk,{kind:'bind',pin:planPin});writeWalkthrough(localStorage,walk,null);
 const mounted=render(<GuidedTourProvider worldId='world'><CreationOwner/></GuidedTourProvider>);
 await act(async()=>{});fireEvent.click(screen.getByText('Owner acknowledged Run'));
 await waitFor(()=>expect(readWalkthrough(localStorage,'world')?.record.steps.play.state).toBe('completed'));
 expect(readWalkthrough(localStorage,'world')?.record.bindings.run).toEqual(createdRun);
 mounted.unmount();render(<GuidedTourProvider worldId='world'><Controls/></GuidedTourProvider>);
 expect(readWalkthrough(localStorage,'world')?.record.steps.play.evidence.filter(e=>e.origin==='acknowledged')).toHaveLength(1);
});
it('does not silently advance the selected Plan to bind a different parent Run',async()=>{
 let walk=createWalkthrough('world','conks','walk','2026-01-01T00:00:00Z');walk=reduceTour(walk,{kind:'bind',pin:{...planPin,revisionId:'different-work'}});writeWalkthrough(localStorage,walk,null);
 render(<GuidedTourProvider worldId='world'><CreationOwner/></GuidedTourProvider>);
 await act(async()=>{});fireEvent.click(screen.getByText('Owner acknowledged Run'));await act(async()=>{});
 expect(readWalkthrough(localStorage,'world')?.record.bindings.run).toBeUndefined();expect(readWalkthrough(localStorage,'world')?.record.steps.play.state).toBe('pending');
});

it('highlights and focuses an existing control with reduced motion, without clicking it',async()=>{
 const scroll=vi.fn();Object.defineProperty(HTMLElement.prototype,'scrollIntoView',{configurable:true,value:scroll});
 Object.defineProperty(window,'matchMedia',{configurable:true,value:vi.fn(()=>({matches:true}))});
 render(<GuidedTourProvider worldId='world'><Controls/></GuidedTourProvider>);
 fireEvent.click(screen.getByText('Open guidance'));fireEvent.click(screen.getByRole('button',{name:'Of Conks and Cons'}));await screen.findByRole('heading',{name:'Open the source'});
 fireEvent.click(screen.getByRole('button',{name:'Show control'}));
 const ordinary=screen.getByText('Ordinary source control');expect(ordinary).toHaveFocus();expect(ordinary).toHaveAttribute('data-guided-highlight','true');expect(scroll).toHaveBeenCalledWith({block:'center',behavior:'auto'});
 fireEvent.click(screen.getByRole('button',{name:'Close tour panel'}));expect(ordinary).not.toHaveAttribute('data-guided-highlight');
});

it('refuses an action from the old rendered walkthrough after another tab switches it',async()=>{
 const initial=createWalkthrough('world','conks','first',new Date().toISOString());writeWalkthrough(localStorage,initial,null);
 render(<GuidedTourProvider worldId='world'><Controls/></GuidedTourProvider>);fireEvent.click(screen.getByText('Open guidance'));
 const oldNext=screen.getByRole('button',{name:'Next'});
 await act(async()=>{
  const saved=readWalkthrough(localStorage,'world')!;
  writeWalkthrough(localStorage,createWalkthrough('world','sheep','other-tab',new Date().toISOString()),saved);
  window.dispatchEvent(new StorageEvent('storage',{key:pointerKey('world')}));
  fireEvent.click(oldNext);
 });
 await screen.findByRole('alert');expect(readWalkthrough(localStorage,'world')?.record.id).toBe('other-tab');expect(readWalkthrough(localStorage,'world')?.record.index).toBe(0);
});
