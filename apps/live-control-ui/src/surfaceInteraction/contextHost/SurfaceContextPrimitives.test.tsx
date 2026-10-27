import {afterEach, describe, expect, it, vi} from 'vitest';
import {act, fireEvent, render, screen} from '@testing-library/react';
import {SurfaceContextPopover} from './SurfaceContextPrimitives';

afterEach(()=>{vi.restoreAllMocks();vi.unstubAllGlobals();});

describe('shared Surface popover viewport placement',()=>{
  it.each([
    ['below','end',20,52,1200,'start'],
    ['below','start',1140,1172,1200,'end'],
    ['below','end',600,632,1200,'end'],
    ['beside','start',20,52,1200,'end'],
    ['beside','end',1140,1172,1200,'start'],
    ['beside','end',20,52,700,'start'],
  ] as const)('%s %s at %s stays inside viewport', (placement,align,left,right,viewport,expected)=>{
    vi.stubGlobal('innerWidth',viewport);
    vi.spyOn(HTMLElement.prototype,'getBoundingClientRect').mockImplementation(function(){
      return {left,right,width:right-left,top:10,bottom:42,height:32,x:left,y:10,toJSON:()=>({}),
        ...(this.classList.contains('surface-context-popover__panel')?{width:256}:{} )};
    });
    render(<SurfaceContextPopover open onOpenChange={()=>{}} align={align} placement={placement} trigger={<button>Start session</button>}>Confirmation</SurfaceContextPopover>);
    expect(screen.getByRole('dialog')).toHaveAttribute('data-align',expected);
    vi.unstubAllGlobals();
  });
});

describe('vertical viewport lifecycle',()=>{
 it('fits async content and resize, preserves internal scroll/state and cleans up',()=>{
  vi.stubGlobal('innerHeight',654);vi.stubGlobal('innerWidth',1164);
  let top=100,height=100;
  let notify: ResizeObserverCallback=()=>{};
  const disconnect=vi.fn();
  vi.stubGlobal('ResizeObserver',class {
   constructor(callback: ResizeObserverCallback){notify=callback;}
   observe=vi.fn();disconnect=disconnect;
  });
  vi.spyOn(HTMLElement.prototype,'getBoundingClientRect').mockImplementation(function(){
   const panel=this.classList.contains('surface-context-popover__panel');
   const y=panel?top:10,h=panel?Math.min(height,parseFloat(this.style.maxHeight)||height):32;
   return {left:100,right:356,width:256,top:y,bottom:y+h,height:h,x:100,y,toJSON:()=>({})};
  });
  const change=vi.fn();
  const {rerender,unmount}=render(<SurfaceContextPopover open onOpenChange={change} trigger={<button>Start</button>}><input aria-label="Name" defaultValue="Retain me" /></SurfaceContextPopover>);
  const panel=screen.getByRole('dialog');
  expect(panel.style.translate).toBe('0 0px');
  expect(panel.style.maxHeight).toBe('630px');
  top=90;height=900;act(()=>notify([],{} as ResizeObserver));
  expect(panel.style.translate).toBe('0 -78px');
  fireEvent.change(screen.getByRole('textbox'),{target:{value:'Still here'}});
  vi.stubGlobal('innerHeight',500);fireEvent(window,new Event('resize'));
  expect(panel.style.maxHeight).toBe('476px');
  expect(screen.getByRole('textbox')).toHaveValue('Still here');
  top=150;fireEvent.scroll(panel);
  expect(panel.style.translate).toBe('0 -78px');
  fireEvent.scroll(window);expect(panel.style.translate).toBe('0 -138px');
  fireEvent.keyDown(document,{key:'Escape'});fireEvent.mouseDown(document.body);
  expect(change.mock.calls).toEqual([[false],[false]]);
  rerender(<SurfaceContextPopover open={false} onOpenChange={change} trigger={<button>Start</button>}>Closed</SurfaceContextPopover>);
  expect(disconnect).toHaveBeenCalled();
  const previous=panel.style.maxHeight;
  vi.stubGlobal('innerHeight',300);fireEvent(window,new Event('resize'));
  expect(panel.style.maxHeight).toBe(previous);unmount();
 });
});
