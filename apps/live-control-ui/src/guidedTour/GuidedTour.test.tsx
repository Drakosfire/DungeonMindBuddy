import {act,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,beforeEach,it,expect,vi} from 'vitest';
import {GuidedTourProvider,useGuidedTour,useTourOwnerReading} from './GuidedTour';
import {readWalkthrough,writeWalkthrough,pointerKey} from './storage';
import {createWalkthrough,reduceTour,type TargetPin} from './protocol';
import {useState} from 'react';
import {MediaImageWizard,type ImageGenerationPort} from '../media/MediaImageWizard';
import '../media/DocumentImageStudio.css';
const pin={kind:'source' as const,worldId:'world',objectId:'page',revision:1,digest:'a'.repeat(64)};
function Controls(){const tour=useGuidedTour();useTourOwnerReading({step:'source',target:pin,control:'source',status:'ready',observation:{step:'source',target:pin,origin:'existing',observedAt:'2026-01-01T00:00:00Z',receiptId:'verified-load'}});return <><button onClick={tour?.open}>Open guidance</button><button data-guided-control="source" onClick={()=>{throw new Error('Guidance must never execute this control');}}>Ordinary source control</button></>;}
afterEach(()=>vi.restoreAllMocks());
beforeEach(()=>{vi.spyOn(HTMLElement.prototype,'getClientRects').mockReturnValue([new DOMRect(0,0,100,24)] as unknown as DOMRectList);Object.defineProperty(HTMLElement.prototype,'scrollIntoView',{configurable:true,value:vi.fn()});Object.defineProperty(window,'matchMedia',{configurable:true,value:vi.fn(()=>({matches:true}))});localStorage.clear();Object.defineProperty(navigator,'locks',{configurable:true,value:{request:vi.fn(async(_name:string,callback:()=>unknown)=>callback())}});});
it('requires a managed World and keeps ordinary controls usable',()=>{render(<GuidedTourProvider worldId={null}><Controls/></GuidedTourProvider>);fireEvent.click(screen.getByText('Open guidance'));expect(screen.getByText('Select a managed World before starting a walkthrough.')).toBeInTheDocument();expect(screen.getByText('Ordinary source control')).toBeEnabled();});
it('stages an existing source, keeps Next separate from completion and retains restart history',async()=>{render(<GuidedTourProvider worldId='world'><Controls/></GuidedTourProvider>);fireEvent.click(screen.getByText('Open guidance'));fireEvent.click(screen.getByRole('button',{name:'Of Conks and Cons'}));await screen.findByRole('heading',{name:'Open the source'});fireEvent.click(screen.getByRole('button',{name:'Use this source'}));await screen.findByText('Existing example inspected');const old=readWalkthrough(localStorage,'world')!;expect(old.record.steps.source.state).toBe('existing');fireEvent.click(screen.getByRole('button',{name:'Next'}));await screen.findByRole('heading',{name:'Develop and save a page'});expect(readWalkthrough(localStorage,'world')?.record.steps.authoring.state).toBe('pending');fireEvent.click(screen.getByRole('button',{name:'Pause'}));await screen.findByText('Guidance paused');fireEvent.click(screen.getByRole('button',{name:'Resume'}));await screen.findByText('2 of 15');fireEvent.click(screen.getByRole('button',{name:'Restart guidance'}));await waitFor(()=>expect(readWalkthrough(localStorage,'world')?.record.id).not.toBe(old.record.id));expect(localStorage.getItem('dmb:guided-journey:v1:world:record:'+old.record.id)).not.toBeNull();});
it('reopens paused guidance after a component reload with the same bound identity',async()=>{const first=render(<GuidedTourProvider worldId='world'><Controls/></GuidedTourProvider>);fireEvent.click(screen.getByText('Open guidance'));fireEvent.click(screen.getByRole('button',{name:'A Wild Sheep Chase'}));await screen.findByRole('heading',{name:'Open the source'});fireEvent.click(screen.getByRole('button',{name:'Use this source'}));await screen.findByText('Existing example inspected');fireEvent.click(screen.getByRole('button',{name:'Pause'}));await screen.findByText('Guidance paused');first.unmount();render(<GuidedTourProvider worldId='world'><Controls/></GuidedTourProvider>);fireEvent.click(screen.getByText('Open guidance'));expect(screen.getByText('Guidance paused')).toBeInTheDocument();expect(readWalkthrough(localStorage,'world')?.record.bindings.source).toEqual(pin);});
it('preserves corrupt guidance and refuses replacement',async()=>{localStorage.setItem('dmb:guided-journey:v1:world:current','original damaged selection');render(<GuidedTourProvider worldId='world'><Controls/></GuidedTourProvider>);fireEvent.click(screen.getByText('Open guidance'));expect(screen.getByRole('alert')).toBeInTheDocument();expect(screen.getByRole('button',{name:'Of Conks and Cons'})).toBeDisabled();await act(async()=>{});expect(localStorage.getItem('dmb:guided-journey:v1:world:current')).toBe('original damaged selection');});

function UnavailableControls({status,reason}:{status:'failed'|'unavailable'|'pending';reason:string}){
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
function CreationOwner(){const tour=useGuidedTour(),[navigated,setNavigated]=useState(false);return <button onClick={()=>{tour?.recordRunCreation({step:'play',target:createdRun,parent:planPin,origin:'acknowledged',observedAt:new Date().toISOString(),receiptId:'verified-create',proof:{kind:'run-creation',entrySceneId:'scene',preparedSceneIds:['scene']}},tour.captureScope());setNavigated(true);}}>{navigated?'Ordinary navigation completed':'Owner acknowledged Run'}</button>;}
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
 expect(screen.queryByRole('complementary',{name:'Guided journey'})).not.toBeInTheDocument();
 expect(readWalkthrough(localStorage,'world')?.record.steps.source.state).toBe('pending');
 fireEvent.click(screen.getByText('Open guidance'));expect(ordinary).not.toHaveAttribute('data-guided-highlight');
 expect(screen.getByText(/Show control hides this panel/)).toBeInTheDocument();
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

async function startFocusTour(){fireEvent.click(screen.getByText('Open guidance'));fireEvent.click(screen.getByRole('button',{name:'Of Conks and Cons'}));await screen.findByRole('heading',{name:'Open the source'});}
it.each(['missing','duplicate','disabled','hidden'] as const)('retains guidance when its control is %s',async kind=>{
 render(<GuidedTourProvider worldId='world'><Controls/></GuidedTourProvider>);await startFocusTour();
 const target=screen.getByText('Ordinary source control'),parent=target.parentNode!;let duplicate:HTMLElement|undefined;
 if(kind==='missing')target.remove();else if(kind==='duplicate'){duplicate=target.cloneNode(true) as HTMLElement;document.body.append(duplicate);}else if(kind==='disabled')target.setAttribute('disabled','');else target.hidden=true;
 try{fireEvent.click(screen.getByRole('button',{name:'Show control'}));expect(screen.getByRole('complementary',{name:'Guided journey'})).toBeInTheDocument();expect(screen.getByRole('alert')).toBeInTheDocument();expect(target).not.toHaveAttribute('data-guided-highlight');expect(readWalkthrough(localStorage,'world')?.record.steps.source.state).toBe('pending');}finally{duplicate?.remove();if(kind==='missing')parent.appendChild(target);}
});
it('refuses a target removed during scrolling without focusing it',async()=>{
 render(<GuidedTourProvider worldId='world'><Controls/></GuidedTourProvider>);await startFocusTour();const target=screen.getByText('Ordinary source control');
 const parent=target.parentNode!;Object.defineProperty(target,'scrollIntoView',{configurable:true,value:()=>target.remove()});const focus=vi.spyOn(target,'focus');fireEvent.click(screen.getByRole('button',{name:'Show control'}));
 await screen.findByRole('alert');expect(focus).not.toHaveBeenCalled();expect(target).not.toHaveAttribute('data-guided-highlight');expect(screen.getByRole('complementary',{name:'Guided journey'})).toBeInTheDocument();parent.appendChild(target);
});
it('cleans the highlight if an ordinary control disconnects after guidance tucks away',async()=>{
 render(<GuidedTourProvider worldId='world'><Controls/></GuidedTourProvider>);await startFocusTour();const target=screen.getByText('Ordinary source control');
 const parent=target.parentNode!;fireEvent.click(screen.getByRole('button',{name:'Show control'}));expect(target).toHaveFocus();act(()=>target.remove());
 await screen.findByRole('alert');expect(target).not.toHaveAttribute('data-guided-highlight');expect(screen.getByRole('complementary',{name:'Guided journey'})).toBeInTheDocument();parent.appendChild(target);
});
it('cleans focus guidance on World change and unmount without any product action',async()=>{
 const mounted=render(<GuidedTourProvider worldId='world'><Controls/></GuidedTourProvider>);await startFocusTour();const target=screen.getByText('Ordinary source control');
 fireEvent.click(screen.getByRole('button',{name:'Show control'}));expect(target).toHaveAttribute('data-guided-highlight');
 mounted.rerender(<GuidedTourProvider worldId='other-world'><Controls/></GuidedTourProvider>);await waitFor(()=>expect(target).not.toHaveAttribute('data-guided-highlight'));mounted.unmount();expect(target).not.toHaveAttribute('data-guided-highlight');
});
it.each(['missing','unavailable','failed'] as const)('separates recorded completion from %s current inspection',async status=>{
 let walk=createWalkthrough('world','conks','retained',new Date().toISOString());walk=reduceTour(walk,{kind:'bind',pin});walk=reduceTour(walk,{kind:'observe',observation:{step:'source',target:pin,origin:'acknowledged',observedAt:new Date().toISOString(),receiptId:'actual-source-load'}});writeWalkthrough(localStorage,walk,null);
 render(<GuidedTourProvider worldId='world'>{status==='missing'?<button onClick={()=>{}}>Unused</button>:<UnavailableControls status={status} reason={status==='failed'?'Source integrity check failed.':'Select a saved source.'}/>}<Reopen/></GuidedTourProvider>);
 fireEvent.click(screen.getByText('Reopen guide'));expect(screen.getByText('Demonstrated during this walkthrough')).toBeInTheDocument();
 if(status==='failed')expect(screen.getByText('Current inspection failed: Source integrity check failed.')).toBeInTheDocument();else expect(screen.getByText('The recorded result is retained. Open its ordinary controls to inspect the current state.')).toBeInTheDocument();
 expect(screen.queryByText(/This walkthrough has not verified its result yet/)).not.toBeInTheDocument();await act(async()=>{});expect(readWalkthrough(localStorage,'world')?.record.steps.source.state).toBe('completed');
});
function Reopen(){const tour=useGuidedTour();return <button onClick={tour?.open}>Reopen guide</button>;}

it('shows historical14-step guidance read-only and restarts into a separate15-step tour',async()=>{
 const old=JSON.parse(JSON.stringify(createWalkthrough('world','conks','history','2020-01-01T00:00:00Z')));old.schema='dmb_guided_journey_v2';old.version=2;delete old.dispatchRevision;delete old.steps.generation;old.index=13;
 const bytes=JSON.stringify(old),key='dmb:guided-journey:v1:world:record:history';localStorage.setItem(key,bytes);localStorage.setItem(pointerKey('world'),JSON.stringify({schema:'dmb_guided_journey_pointer_v2',id:'history'}));
 render(<GuidedTourProvider worldId='world'><Controls/></GuidedTourProvider>);fireEvent.click(screen.getByText('Open guidance'));
 expect(screen.getByRole('heading',{name:'Ask about the session'})).toBeInTheDocument();expect(screen.getByRole('button',{name:'Next',exact:true})).toBeDisabled();expect(screen.getByRole('button',{name:'Show control'})).toBeDisabled();
 expect(localStorage.getItem(key)).toBe(bytes);fireEvent.click(screen.getByRole('button',{name:'Restart guidance'}));
 await waitFor(()=>expect(readWalkthrough(localStorage,'world')?.record.version).toBe(3));expect(readWalkthrough(localStorage,'world')?.record.steps.generation.state).toBe('pending');expect(localStorage.getItem(key)).toBe(bytes);
});

it('reconciles scoped unavailable to pending without credit and preserves failures',async()=>{
 let walk=reduceTour(createWalkthrough('world','conks','pending',new Date().toISOString()),{kind:'bind',pin});
 walk=reduceTour(walk,{kind:'disposition',step:'source',state:'unavailable',reason:'Owner was blocked.'});writeWalkthrough(localStorage,walk,null);
 const mounted=render(<GuidedTourProvider worldId='world'><UnavailableControls status='pending' reason='Use the ordinary source control.'/></GuidedTourProvider>);
 fireEvent.click(screen.getByText('Open guidance'));
 await waitFor(()=>expect(readWalkthrough(localStorage,'world')?.record.steps.source).toEqual({state:'pending',reason:null,evidence:[]}));
 expect(screen.getByText('Use the ordinary source control.')).toBeInTheDocument();
 mounted.rerender(<GuidedTourProvider worldId='world'><UnavailableControls status='failed' reason='Current source read failed.'/></GuidedTourProvider>);
 await waitFor(()=>expect(readWalkthrough(localStorage,'world')?.record.steps.source.state).toBe('failed'));
 mounted.rerender(<GuidedTourProvider worldId='world'><UnavailableControls status='pending' reason='Try the ordinary controls.'/></GuidedTourProvider>);
 await act(async()=>{});expect(readWalkthrough(localStorage,'world')?.record.steps.source.state).toBe('failed');
});

it('focuses guidance only on opening and restores a usable invoker on explicit Close',async()=>{
 const mounted=render(<GuidedTourProvider worldId='world'><UnavailableControls status='pending' reason='Inspect the source.'/></GuidedTourProvider>);
 const invoker=screen.getByText('Open guidance');invoker.focus();fireEvent.click(invoker);
 const close=screen.getByRole('button',{name:'Close tour panel'});expect(close).toHaveFocus();
 fireEvent.click(screen.getByRole('button',{name:'Of Conks and Cons'}));await screen.findByRole('heading',{name:'Open the source'});
 const next=screen.getByRole('button',{name:'Next'});next.focus();
 mounted.rerender(<GuidedTourProvider worldId='world'><UnavailableControls status='pending' reason='Updated owner instructions.'/></GuidedTourProvider>);
 expect(next).toHaveFocus();fireEvent.click(close);expect(invoker).toHaveFocus();
 invoker.focus();fireEvent.click(invoker);expect(screen.getByRole('button',{name:'Close tour panel'})).toHaveFocus();
});

it('keeps the actual nonmodal Studio and its typed draft mounted while guidance opens and closes',async()=>{
 const port:ImageGenerationPort={capabilities:vi.fn().mockResolvedValue({configured:true,library_ready:true,storage_configured:false,models:[{id:'model',label:'Model',formats:['png'],controls:[]}]}),generate:vi.fn(),list:vi.fn(),get:vi.fn(),save:vi.fn()};
 render(<GuidedTourProvider worldId='world'><Reopen/><aside className='document-image-studio' aria-label='Image Studio fixture'><MediaImageWizard port={port} onClose={()=>{}}/></aside></GuidedTourProvider>);
 await screen.findByRole('option',{name:'Model'});
 const prompt=screen.getByRole('textbox',{name:'What would you like to see?'});fireEvent.change(prompt,{target:{value:'Layer test only; do not generate.'}});
 const invoker=screen.getByRole('button',{name:'Open guided journey'});invoker.focus();fireEvent.click(invoker);
 expect(screen.getByRole('button',{name:'Close tour panel'})).toHaveFocus();expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Close tour panel'}));
 expect(screen.getByRole('textbox',{name:'What would you like to see?'})).toBe(prompt);expect(prompt).toHaveValue('Layer test only; do not generate.');expect(invoker).toHaveFocus();
 expect(port.generate).not.toHaveBeenCalled();expect(port.save).not.toHaveBeenCalled();
});
