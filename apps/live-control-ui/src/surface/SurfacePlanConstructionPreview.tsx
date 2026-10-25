import {useEffect,useRef} from 'react';
import type {BuildPlanConstructionProgress} from '../api/buildConstructionStream';
import './SurfacePageProposal.css';

/** Actual complete provider rows, inert until the separate final plan owner admits them. */
export function SurfacePlanConstructionPreview({steps,status,onVisible}:{steps:BuildPlanConstructionProgress['steps'];status:'building'|'incomplete';onVisible?:()=>void}){
 const seen=useRef(false);
 useEffect(()=>{if(steps.length&&!seen.current){seen.current=true;onVisible?.();}},[steps.length,onVisible]);
 if(!steps.length)return null;
 return <section className="surface-construction-preview" aria-label="Plan construction" aria-busy={status==='building'}>
  <small role="status">{status==='building'?'Planning…':'Incomplete · check the conversation'}</small>
  <ol>{steps.map((row,index)=><li key={index}><span aria-hidden="true">☐ </span>{row.text} <small>{row.kind==='discuss'?'Discuss':'Prepare an insertion'}</small></li>)}</ol>
 </section>;
}
