import { afterEach, expect, it, vi } from 'vitest';
import { dragScrollDelta, mediaDragScroll } from './mediaImageDragScroll';
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); document.body.replaceChildren(); });
it('scrolls a nested viewport continuously near the edge and stops on drop and cleanup', () => {
 const callbacks = new Map<number, FrameRequestCallback>(); let id=0;
 vi.stubGlobal('requestAnimationFrame', (callback:FrameRequestCallback) => {callbacks.set(++id,callback); return id;});
 vi.stubGlobal('cancelAnimationFrame', (key:number) => callbacks.delete(key));
 const scroller = document.body.appendChild(document.createElement('div')); scroller.style.overflowY='auto';
 Object.defineProperties(scroller,{scrollHeight:{value:2000},clientHeight:{value:400}});
 vi.spyOn(scroller,'getBoundingClientRect').mockReturnValue({top:100,bottom:500,left:0,right:800} as DOMRect);
 const editor = scroller.appendChild(document.createElement('div'));
 const image = editor.appendChild(document.createElement('span')); image.className='document-media-image';
 const destroy = mediaDragScroll(editor);
 image.dispatchEvent(new Event('dragstart',{bubbles:true}));
 const over = new MouseEvent('dragover',{bubbles:true,clientX:400,clientY:490}); editor.dispatchEvent(over);
 const step=()=>{const entries=[...callbacks];callbacks.clear(); entries.forEach(([,fn])=>fn(0));};
 step(); expect(scroller.scrollTop).toBeGreaterThan(0);
 const first=scroller.scrollTop; step(); expect(scroller.scrollTop).toBeGreaterThan(first);
 document.dispatchEvent(new Event('drop',{bubbles:true})); expect(callbacks.size).toBe(0);
 const last=scroller.scrollTop;step();expect(scroller.scrollTop).toBe(last);
 destroy(); image.dispatchEvent(new Event('dragstart',{bubbles:true})); editor.dispatchEvent(over); expect(callbacks.size).toBe(0);
});
it('supports saved-library drags and cancels on dragend',()=>{
 const request=vi.fn(()=>1),cancel=vi.fn();vi.stubGlobal('requestAnimationFrame',request);vi.stubGlobal('cancelAnimationFrame',cancel);
 const editor=document.body.appendChild(document.createElement('div'));const destroy=mediaDragScroll(editor);
 const event=new MouseEvent('dragover',{bubbles:true,clientX:100,clientY:100});Object.defineProperty(event,'dataTransfer',{value:{types:['application/x-dmb-media']}});
 editor.dispatchEvent(event);expect(request).toHaveBeenCalledOnce();document.dispatchEvent(new Event('dragend'));expect(cancel).toHaveBeenCalledWith(1);destroy();
});
it('uses both edges and leaves the middle stationary',()=>{
 expect(dragScrollDelta(105,100,500)).toBeLessThan(0);expect(dragScrollDelta(495,100,500)).toBeGreaterThan(0);
 expect(dragScrollDelta(300,100,500)).toBe(0);expect(dragScrollDelta(20,10,30)).toBe(0);expect(dragScrollDelta(0,0,0)).toBe(0);
});
