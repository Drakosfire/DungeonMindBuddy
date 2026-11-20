import {useId,useLayoutEffect,useRef,useState,type ReactNode} from 'react';
import {createPortal} from 'react-dom';

type Box={left:number;top:number;right:number;bottom:number;width:number;height:number};
/** Prefer a side, then above/below. Never cover the ordinary control. */
export function coachmarkPosition(anchor:Box,popup:{width:number;height:number},viewport:Box){
 const gap=12,pad=8;
 const minX=viewport.left+pad,maxX=viewport.right-pad-popup.width;
 const minY=viewport.top+pad,maxY=viewport.bottom-pad-popup.height;
 if(maxX<minX||maxY<minY)return null;
 const x=Math.max(minX,Math.min(anchor.left,maxX)),y=Math.max(minY,Math.min(anchor.top,maxY));
 const candidates=[{left:anchor.right+gap,top:y},{left:anchor.left-gap-popup.width,top:y},{left:x,top:anchor.bottom+gap},{left:x,top:anchor.top-gap-popup.height}];
 return candidates.find(p=>p.left>=minX&&p.left<=maxX&&p.top>=minY&&p.top<=maxY)??null;
}
function viewportBox():Box{
 const v=window.visualViewport,left=v?.offsetLeft??0,top=v?.offsetTop??0,width=v?.width??window.innerWidth,height=v?.height??window.innerHeight;
 return {left,top,width,height,right:left+width,bottom:top+height};
}
function inView(anchor:HTMLElement,box:Box,viewport:Box){
 if(box.width<=0||box.height<=0||box.left<viewport.left||box.right>viewport.right||box.top<viewport.top||box.bottom>viewport.bottom)return false;
 for(let p=anchor.parentElement;p&&p!==document.body;p=p.parentElement){
  const style=getComputedStyle(p),r=p.getBoundingClientRect();
  if(/hidden|clip|auto|scroll/.test(style.overflowX)&&(box.left<r.left||box.right>r.right))return false;
  if(/hidden|clip|auto|scroll/.test(style.overflowY)&&(box.top<r.top||box.bottom>r.bottom))return false;
 }
 return true;
}
export function TourCoachmark({anchor,title,instruction,status,children,onMore,onUnavailable}:{anchor:HTMLElement;title:string;instruction:string;status:string;children:ReactNode;onMore:()=>void;onUnavailable:(reason:string)=>void}){
 const ref=useRef<HTMLDivElement>(null),id=useId();
 const [position,setPosition]=useState<{left:number;top:number}|null>(null);
 const [root,setRoot]=useState<Element>(document.fullscreenElement??document.body);
 useLayoutEffect(()=>{
  const changed=()=>setRoot(document.fullscreenElement??document.body);
  document.addEventListener('fullscreenchange',changed);return()=>document.removeEventListener('fullscreenchange',changed);
 },[]);
 useLayoutEffect(()=>{
  let frame=0,disposed=false;
  const measure=()=>{
   frame=0;if(disposed||!ref.current)return;
   const box=anchor.getBoundingClientRect(),viewport=viewportBox();
   if(!anchor.isConnected||!root.contains(anchor)||!inView(anchor,box,viewport)){onUnavailable('The control is outside the visible area. Reopen guidance when it is visible.');return;}
   const popup=ref.current.getBoundingClientRect(),next=coachmarkPosition(box,popup,viewport);
   if(!next){onUnavailable('There is not enough room beside this control. Use the guidance panel or enlarge the window.');return;}
   setPosition(old=>old?.left===next.left&&old.top===next.top?old:next);
  };
  const schedule=()=>{if(!frame)frame=requestAnimationFrame(measure);};
  const observer=typeof ResizeObserver==='undefined'?null:new ResizeObserver(schedule);
  observer?.observe(anchor);if(ref.current)observer?.observe(ref.current);
  document.addEventListener('scroll',schedule,true);window.addEventListener('resize',schedule);
  window.visualViewport?.addEventListener('resize',schedule);window.visualViewport?.addEventListener('scroll',schedule);
  schedule();
  return()=>{disposed=true;cancelAnimationFrame(frame);observer?.disconnect();document.removeEventListener('scroll',schedule,true);window.removeEventListener('resize',schedule);window.visualViewport?.removeEventListener('resize',schedule);window.visualViewport?.removeEventListener('scroll',schedule);};
 },[anchor,root,onUnavailable]);
 useLayoutEffect(()=>{
  const described=anchor.getAttribute('aria-describedby'),ids=[described,id].filter(Boolean).join(' ');anchor.setAttribute('aria-describedby',ids);
  const escape=(event:KeyboardEvent)=>{if(event.key==='Escape'&&!event.defaultPrevented&&(event.target===anchor||ref.current?.contains(event.target as Node))){event.preventDefault();onMore();}};
  document.addEventListener('keydown',escape);
  return()=>{document.removeEventListener('keydown',escape);if(anchor.getAttribute('aria-describedby')===ids){if(described)anchor.setAttribute('aria-describedby',described);else anchor.removeAttribute('aria-describedby');}};
 },[anchor,id,onMore]);
 return createPortal(<div ref={ref} role="dialog" aria-modal="false" aria-labelledby={`${id}-title`} className="guided-tour-coachmark" style={{left:position?.left??0,top:position?.top??0,visibility:position?'visible':'hidden'}}>
  <header><strong id={`${id}-title`}>{title}</strong><button type="button" aria-label="Return to tour guidance" onClick={onMore}>×</button></header>
  <p id={id}>{instruction}</p><p role="status" className="guided-tour-coachmark__status">{status}</p>
  <div className="guided-tour__actions"><button type="button" onClick={()=>anchor.focus({preventScroll:true})}>{anchor.dataset.guidedControlGroup==='true'?'Focus controls':'Use control'}</button><button type="button" onClick={onMore}>More guidance</button></div>
  {children}
 </div>,root);
}
