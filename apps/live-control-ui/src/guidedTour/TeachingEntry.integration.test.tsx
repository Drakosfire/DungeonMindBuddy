import {act,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {CompactAppNavigation} from '../chrome/CompactAppNavigation';
import {GuidedTourProvider,useTourOwnerReading} from './GuidedTour';
import {createWalkthrough} from './protocol';
import {readWalkthrough,writeWalkthrough} from './storage';
vi.mock('../selectedWorld/SelectedWorldContext',()=>({useSelectedWorld:()=>({kind:'managed',worldId:'world',name:'World'})}));
vi.mock('../selectedWorld/WorldSelector',()=>({WorldSelector:()=>null}));
vi.mock('../chrome/AppChromeWorldGraphStatus',()=>({AppChromeWorldGraphStatus:()=>null}));
const clicked=vi.fn();
const pin={kind:'source' as const,worldId:'world',objectId:'source',revision:1,digest:'a'.repeat(64)};
function Controls({kind='ready'}:{kind?:string}){
 useTourOwnerReading({step:'source',target:pin,control:'source',status:kind==='waiting'?'pending':'ready'});
 return <>{kind!=='missing'&&kind!=='waiting'&&<button data-guided-control="source" disabled={kind==='disabled'} hidden={kind==='hidden'} onClick={clicked}>Ordinary source</button>}{kind==='duplicate'&&<button data-guided-control="source">Other source</button>}</>;
}
function Workspace({kind='ready',worldId='world'}:{kind?:string;worldId?:string}){return <GuidedTourProvider worldId={worldId}><CompactAppNavigation activeRoute="build"/><Controls kind={kind}/></GuidedTourProvider>;}
function seed(phase:'running'|'paused'|'exited'='running'){
 const record=createWalkthrough('world','conks','walk','2026-10-30T00:00:00Z');record.phase=phase;writeWalkthrough(localStorage,record,null);
}
beforeEach(()=>{
 localStorage.clear();clicked.mockClear();
 vi.spyOn(HTMLElement.prototype,'getBoundingClientRect').mockReturnValue(new DOMRect(100,100,100,24));
 vi.spyOn(HTMLElement.prototype,'getClientRects').mockReturnValue([new DOMRect(100,100,100,24)] as unknown as DOMRectList);
 Object.defineProperty(HTMLElement.prototype,'scrollIntoView',{configurable:true,value:vi.fn()});
 Object.defineProperty(window,'matchMedia',{configurable:true,value:vi.fn(()=>({matches:true}))});
 Object.defineProperty(navigator,'locks',{configurable:true,value:{request:vi.fn(async(_name:string,callback:()=>unknown)=>callback())}});
});
afterEach(()=>vi.restoreAllMocks());
it('starts with explicit adventure choice, then teaches at the real control without binding or clicking',async()=>{
 render(<Workspace/>);fireEvent.click(screen.getByRole('button',{name:'Start tour'}));
 expect(readWalkthrough(localStorage,'world')).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'Of Conks and Cons'}));
 await waitFor(()=>expect(screen.getByRole('button',{name:'Ordinary source'})).toHaveAttribute('data-guided-highlight','true'));
 expect(screen.getByRole('button',{name:'Ordinary source'})).toHaveFocus();
 expect(screen.queryByRole('complementary',{name:'Guided journey'})).not.toBeInTheDocument();
 expect(readWalkthrough(localStorage,'world')?.record.bindings.source).toBeUndefined();
 expect(clicked).not.toHaveBeenCalled();
 fireEvent.click(await screen.findByRole('button',{name:'Use this source'}));
 await waitFor(()=>expect(readWalkthrough(localStorage,'world')?.record.bindings.source).toEqual(pin));
 expect(readWalkthrough(localStorage,'world')?.record.steps.source.state).toBe('pending');
});
it('resumes directly beside the control without rewriting retained guidance',async()=>{
 seed();const bytes=localStorage.getItem('dmb:guided-journey:v1:world:record:walk');const write=vi.spyOn(Storage.prototype,'setItem');
 render(<Workspace/>);fireEvent.click(screen.getByRole('button',{name:'Resume tour'}));
 expect(screen.getByRole('button',{name:'Ordinary source'})).toHaveFocus();
 expect(screen.queryByRole('complementary',{name:'Guided journey'})).not.toBeInTheDocument();
 expect(write).not.toHaveBeenCalled();expect(localStorage.getItem('dmb:guided-journey:v1:world:record:walk')).toBe(bytes);expect(clicked).not.toHaveBeenCalled();
 fireEvent.click(await screen.findByRole('button',{name:'More guidance'}));expect(screen.getByRole('button',{name:'Export walkthrough'})).toBeVisible();
});
it.each(['paused','exited'] as const)('requires explicit Resume for %s guidance',async phase=>{
 seed(phase);render(<Workspace/>);fireEvent.click(screen.getByRole('button',{name:'Resume tour'}));
 expect(readWalkthrough(localStorage,'world')?.record.phase).toBe(phase);
 expect(screen.getByRole('button',{name:'Ordinary source'})).not.toHaveAttribute('data-guided-highlight');
 fireEvent.click(screen.getByRole('button',{name:'Resume',exact:true}));
 await waitFor(()=>expect(screen.getByRole('button',{name:'Ordinary source'})).toHaveAttribute('data-guided-highlight','true'));
 expect(clicked).not.toHaveBeenCalled();
});
it.each(['missing','duplicate','disabled','hidden'])('explains a %s target in the compact card',kind=>{
 seed();render(<Workspace kind={kind}/>);fireEvent.click(screen.getByRole('button',{name:'Resume tour'}));
 expect(screen.getByRole('complementary',{name:'Guided journey'})).toBeVisible();expect(screen.getByRole('alert')).toBeVisible();
 expect(screen.queryByRole('button',{name:'Export walkthrough'})).not.toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'More guidance'}));expect(screen.getByRole('button',{name:'Export walkthrough'})).toBeVisible();
 expect(clicked).not.toHaveBeenCalled();
});
it('drops old teaching focus on a World change',()=>{
 seed();const view=render(<Workspace/>);fireEvent.click(screen.getByRole('button',{name:'Resume tour'}));
 view.rerender(<Workspace worldId="other"/>);
 expect(document.querySelector('[data-guided-highlight]')).toBeNull();expect(clicked).not.toHaveBeenCalled();
});
it('waits for normal owner mount, but Close cancels that pending teaching',()=>{
 seed();const view=render(<Workspace kind="waiting"/>);fireEvent.click(screen.getByRole('button',{name:'Resume tour'}));
 fireEvent.click(screen.getByRole('button',{name:'Close tour panel'}));view.rerender(<Workspace/>);
 expect(document.querySelector('[data-guided-highlight]')).toBeNull();expect(screen.queryByRole('complementary',{name:'Guided journey'})).not.toBeInTheDocument();
});
it('returns to explained guidance when a focused target becomes disabled',async()=>{
 seed();const view=render(<Workspace/>);fireEvent.click(screen.getByRole('button',{name:'Resume tour'}));view.rerender(<Workspace kind="disabled"/>);
 await screen.findByRole('alert');expect(document.querySelector('[data-guided-highlight]')).toBeNull();
 expect(screen.getByRole('button',{name:'More guidance'})).toBeVisible();expect(clicked).not.toHaveBeenCalled();
});
it('reopens the same paused record after reload without repeating actions',()=>{
 seed('paused');const first=render(<Workspace/>);fireEvent.click(screen.getByRole('button',{name:'Resume tour'}));first.unmount();
 render(<Workspace/>);fireEvent.click(screen.getByRole('button',{name:'Resume tour'}));
 expect(screen.getByText('Guidance paused')).toBeVisible();expect(readWalkthrough(localStorage,'world')?.record.id).toBe('walk');expect(clicked).not.toHaveBeenCalled();
});

it('cancels pending teaching when another tab clears all retained guidance',()=>{
 seed();const view=render(<Workspace kind="waiting"/>);fireEvent.click(screen.getByRole('button',{name:'Resume tour'}));
 act(()=>{localStorage.clear();window.dispatchEvent(new StorageEvent('storage',{key:null}));});
 view.rerender(<Workspace/>);
 expect(screen.getByRole('button',{name:'Start tour'})).toBeVisible();
 expect(document.querySelector('[data-guided-highlight]')).toBeNull();
 expect(screen.queryByRole('heading',{name:'Open the source'})).not.toBeInTheDocument();expect(clicked).not.toHaveBeenCalled();
});
it('removes an active hint when another tab clears all retained guidance',()=>{
 seed();render(<Workspace/>);fireEvent.click(screen.getByRole('button',{name:'Resume tour'}));
 expect(document.querySelector('[data-guided-highlight]')).not.toBeNull();
 act(()=>{localStorage.clear();window.dispatchEvent(new StorageEvent('storage',{key:null}));});
 expect(document.querySelector('[data-guided-highlight]')).toBeNull();expect(clicked).not.toHaveBeenCalled();
});
