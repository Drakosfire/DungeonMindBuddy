import {useEffect,useId,useLayoutEffect,useRef,useState} from 'react';
import {createPortal} from 'react-dom';
import './SourceCitation.css';

/** Shared, keyboard-accessible citation marker. Details never trigger a read. */
export function SourceCitation({number,title,label,onOpen,expanded,controls}:{
  number:string;title:string;label?:string;onOpen:()=>void;expanded?:boolean;controls?:string;
}) {
  const tooltip=useId(),tooltipRef=useRef<HTMLSpanElement>(null);
  const [anchor,setAnchor]=useState<{left:number;top:number}|null>(null);
  const shown=anchor!==null;
  useEffect(()=>{
    if(!shown)return;
    const dismiss=()=>setAnchor(null);
    window.addEventListener('resize',dismiss);
    window.addEventListener('scroll',dismiss,true);
    return()=>{window.removeEventListener('resize',dismiss);window.removeEventListener('scroll',dismiss,true);};
  },[shown]);
  useLayoutEffect(()=>{
    if(!anchor || !tooltipRef.current)return;
    const height=tooltipRef.current.getBoundingClientRect().height;
    const top=Math.max(8,Math.min(anchor.top,window.innerHeight-height-8));
    if(top!==anchor.top)setAnchor({...anchor,top});
  });
  function show(button:HTMLButtonElement){
    const rect=button.getBoundingClientRect();
    const rootSize=Number.parseFloat(getComputedStyle(document.documentElement).fontSize)||16;
    const width=Math.min(18*rootSize,window.innerWidth-16);
    setAnchor({left:Math.max(8,Math.min(rect.left,window.innerWidth-width-8)),top:rect.bottom+8});
  }
  return <span className="source-citation">
    <button type="button" className="source-citation__button" aria-label={label ?? `Open source ${number}`}
      title={title} aria-describedby={tooltip} aria-expanded={expanded} aria-controls={controls} onClick={onOpen}
      onMouseEnter={e=>show(e.currentTarget)} onMouseLeave={()=>setAnchor(null)}
      onFocus={e=>show(e.currentTarget)} onBlur={()=>setAnchor(null)}
      onKeyDown={e=>{if(e.key==='Escape')setAnchor(null);}}>{number}</button>
    {createPortal(<span ref={tooltipRef} role="tooltip" id={tooltip} className="source-citation__tooltip" hidden={!anchor}
      style={anchor ?? undefined}>{title}</span>,document.body)}
  </span>;
}
