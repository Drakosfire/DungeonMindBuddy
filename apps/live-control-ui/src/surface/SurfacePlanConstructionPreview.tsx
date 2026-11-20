import {useEffect,useRef} from 'react';
import type {BuildPlanConstructionProgress} from '../api/buildConstructionStream';
import './SurfacePageProposal.css';

/** Actual complete provider rows, inert until the separate final plan owner admits them. */
export function SurfacePlanConstructionPreview({steps,status,onVisible,objective=null}:{objective?:string|null;steps:BuildPlanConstructionProgress['steps'];status:'building'|'incomplete';onVisible?:()=>void}){
 const seen=useRef(false);
 useEffect(()=>{if((steps.length||objective)&&!seen.current){seen.current=true;onVisible?.();}},[steps.length,objective,onVisible]);
 if(!steps.length&&!objective)return null;
 return <section className="surface-construction-preview" aria-label="Plan construction" aria-busy={status==='building'}>
  <small role="status">{status==='building'?'Planning…':'Incomplete · check the conversation'}</small>
  {objective?<p><strong>Expected outcome</strong><br/>{objective}</p>:null}
  <ol>{steps.map((row,index)=><li key={index}><span aria-hidden="true">{'selected' in row&&row.selected?'☑ ':'☐ '}</span>{row.text} <small>{row.kind==='discuss'?'Discuss':'Prepare an insertion'}</small></li>)}</ol>
 </section>;
}
