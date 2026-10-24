import {afterEach,expect,it,vi} from 'vitest';
import {startProposalDragScroll} from './proposalDragScroll';

afterEach(()=>{vi.unstubAllGlobals();document.body.replaceChildren();});
it.each([['down',340,0,12],['up',55,200,188]] as const)('scrolls %s during an owned drag and stops on drop',(_name,y,start,expected)=>{
  const pane=document.createElement('div');pane.style.overflowY='auto';
  const editor=document.createElement('div');pane.append(editor);document.body.append(pane);
  Object.defineProperties(pane,{scrollHeight:{value:1000},clientHeight:{value:300}});
  pane.getBoundingClientRect=()=>({top:50,bottom:350} as DOMRect);pane.scrollTop=start;
  let next:FrameRequestCallback|undefined;
  vi.stubGlobal('requestAnimationFrame',vi.fn((callback:FrameRequestCallback)=>{next=callback;return 1;}));
  const cancel=vi.fn();vi.stubGlobal('cancelAnimationFrame',cancel);
  const stop=startProposalDragScroll(editor);
  const over=new Event('dragover');Object.defineProperty(over,'clientY',{value:y});document.dispatchEvent(over);
  next!(0);expect(pane.scrollTop).toBe(expected);
  document.dispatchEvent(new Event('drop'));next!(16);expect(pane.scrollTop).toBe(expected);
  expect(cancel).toHaveBeenCalled();stop();
});
it('cleans up on cancellation without ongoing scrolling',()=>{
  let next:FrameRequestCallback|undefined;
  vi.stubGlobal('requestAnimationFrame',vi.fn((callback:FrameRequestCallback)=>{next=callback;return 1;}));
  const cancel=vi.fn();vi.stubGlobal('cancelAnimationFrame',cancel);
  const editor=document.createElement('div');document.body.append(editor);
  const stop=startProposalDragScroll(editor);stop();next!(0);
  expect(cancel).toHaveBeenCalledOnce();expect(requestAnimationFrame).toHaveBeenCalledOnce();
});
