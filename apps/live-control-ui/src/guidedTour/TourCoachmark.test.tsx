import {act,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {coachmarkPosition,TourCoachmark} from './TourCoachmark';
const box=(x:number,y:number,w:number,h:number)=>new DOMRect(x,y,w,h);
const viewport=box(0,0,1024,768);
it('flips near the right edge and fits a narrow screen below the control without covering it',()=>{
 expect(coachmarkPosition(box(900,30,100,30),box(0,0,300,240),viewport)).toEqual({left:588,top:30});
 expect(coachmarkPosition(box(200,20,100,30),box(0,0,340,240),box(0,0,390,844))).toEqual({left:42,top:62});
 expect(coachmarkPosition(box(0,0,390,844),box(0,0,340,240),box(0,0,390,844))).toBeNull();
});
let anchor:HTMLButtonElement,rect:DOMRect;
beforeEach(()=>{
 anchor=document.createElement('button');anchor.textContent='Actual control';document.body.appendChild(anchor);rect=box(100,100,80,30);
 vi.spyOn(HTMLElement.prototype,'getBoundingClientRect').mockImplementation(function(){return this===anchor?rect:box(0,0,300,220);});
});
afterEach(()=>{anchor.remove();vi.restoreAllMocks();Object.defineProperty(document,'fullscreenElement',{configurable:true,value:null});});
function Popup({onUnavailable=vi.fn()}:{onUnavailable?:(reason:string)=>void}){return <TourCoachmark anchor={anchor} title="Learn this control" instruction="Try the ordinary control." status="pending" onMore={vi.fn()} onUnavailable={onUnavailable}><button>Next</button></TourCoachmark>;}
it('repositions on ancestor scroll and resize without scrolling or activating its target',async()=>{
 const click=vi.fn();anchor.onclick=click;render(<Popup/>);const popup=await screen.findByRole('dialog');await waitFor(()=>expect(popup.style.left).toBe('192px'));
 rect=box(900,100,80,30);act(()=>document.dispatchEvent(new Event('scroll')));await waitFor(()=>expect(popup.style.left).toBe('588px'));
 rect=box(500,300,80,30);act(()=>window.dispatchEvent(new Event('resize')));await waitFor(()=>expect(popup.style.left).toBe('592px'));
 expect(click).not.toHaveBeenCalled();
});
it('returns an explicit unavailable result when the target scrolls offscreen',async()=>{
 const unavailable=vi.fn();render(<Popup onUnavailable={unavailable}/>);await screen.findByRole('dialog');rect=box(-10,100,80,30);
 act(()=>document.dispatchEvent(new Event('scroll')));await waitFor(()=>expect(unavailable).toHaveBeenCalledWith(expect.stringContaining('outside the visible area')));
});
it('uses the current fullscreen root, follows fullscreen exit and cleans its accessible description',async()=>{
 const root=document.createElement('section');document.body.appendChild(root);root.appendChild(anchor);Object.defineProperty(document,'fullscreenElement',{configurable:true,value:root});
 anchor.setAttribute('aria-describedby','existing');const view=render(<Popup/>);await screen.findByRole('dialog');expect(root.querySelector('[role="dialog"]')).not.toBeNull();
 expect(anchor.getAttribute('aria-describedby')).toContain('existing ');
 Object.defineProperty(document,'fullscreenElement',{configurable:true,value:null});act(()=>document.dispatchEvent(new Event('fullscreenchange')));
 await waitFor(()=>expect(screen.getByRole('dialog').parentElement).toBe(document.body));view.unmount();expect(anchor.getAttribute('aria-describedby')).toBe('existing');root.remove();
});

it('anchors to the explicit small group heading inside a tall panel and never activates the group controls',async()=>{
 const group=document.createElement('section'),heading=document.createElement('h2'),control=document.createElement('button');
 heading.textContent='Tracker';heading.tabIndex=-1;heading.dataset.guidedControlGroup='true';control.textContent='Save tracker';const save=vi.fn();control.onclick=save;
 group.append(heading,control);document.body.appendChild(group);
 vi.mocked(HTMLElement.prototype.getBoundingClientRect).mockImplementation(function(){return this===group?box(20,20,980,1500):this===heading?box(30,50,200,30):box(0,0,300,220);});
 const view=render(<TourCoachmark anchor={heading} title="Tracker controls" instruction="Use this tracker group." status="pending" onMore={vi.fn()} onUnavailable={vi.fn()}>Guide only</TourCoachmark>);
 const popup=await screen.findByRole('dialog',{name:'Tracker controls'});expect(popup).toBeVisible();expect(popup.style.left).toBe('242px');
 fireEvent.click(screen.getByRole('button',{name:'Focus controls'}));expect(heading).toHaveFocus();expect(save).not.toHaveBeenCalled();
 fireEvent.click(control);expect(save).toHaveBeenCalledOnce();view.unmount();group.remove();
});
it('measures again when the actual anchor or popup resizes',async()=>{
 let notify:()=>void=()=>{};const disconnect=vi.fn();
 vi.stubGlobal('ResizeObserver',class {constructor(callback:()=>void){notify=callback;}observe(){}disconnect=disconnect;});
 try{const view=render(<Popup/>);const popup=await screen.findByRole('dialog');rect=box(500,300,80,30);act(()=>notify());await waitFor(()=>expect(popup.style.left).toBe('592px'));view.unmount();expect(disconnect).toHaveBeenCalled();}finally{vi.unstubAllGlobals();}
});
