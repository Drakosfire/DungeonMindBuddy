import {useId,useState} from 'react';
import {createPortal} from 'react-dom';
import type {AuthoredReference} from '../api/types';
import {mergeAuthoredReferences,referenceIdentity} from '../agentInteraction/authoredGraphReferences';
import {NativeSourceInspection} from '../graphLens/NativeSourceInspection';
import {NativeGraphInspection} from '../graphLens/NativeGraphInspection';
import type {InspectionPin} from '../api/nativeGraphInspection';
import './SurfaceGraphReferenceInput.css';

/** One input renderer for composer, plan roots and pending steps. Selection is unread. */
export function SurfaceGraphReferenceInput({worldId,value,onChange,disabled=false,readOnly=false,label='References',triggerHost}:{worldId:string;value:AuthoredReference[];onChange:(next:AuthoredReference[])=>void;disabled?:boolean;readOnly?:boolean;label?:string;triggerHost?:HTMLElement|null}) {
 const pickerId=useId();
 const [kind,setKind]=useState<'objects'|'sources'>('objects');
 const [open,setOpen]=useState(false),[error,setError]=useState<string|null>(null);
 function choose(pin:InspectionPin,entityId:string,label:string){
  if(disabled||readOnly||pin.managed_world_id!==worldId)return;
  try{onChange(mergeAuthoredReferences(value,[{schema:'dmb_authored_graph_reference_v1',managed_world_id:worldId,native_world_id:pin.native_world_id,binding_version:pin.binding_version,graph_revision:pin.revision_id,node_id:entityId,label}]));setError(null);setOpen(false);}catch(e){setError(String(e));}
 }
 const trigger=!readOnly&&<button type="button" className={triggerHost?'conversation-dock__icon-button':undefined} disabled={disabled} aria-label="@ Reference" title="References" aria-controls={pickerId} aria-expanded={open} onClick={()=>setOpen(!open)}>{triggerHost?'@':'@ Reference'}</button>;
 return <section className="surface-graph-reference-input" aria-label={label} hidden={Boolean(triggerHost)&&!value.length&&!open&&!error}>
  <div className="surface-graph-reference-input__chips">{value.map(ref=><span key={referenceIdentity(ref)} className="surface-graph-reference-input__chip"><span title={readOnly?'Selected for this request; see its trace for read results.':'Selected, unread until this request runs'}>@{ref.label}</span>{!readOnly&&<button type="button" disabled={disabled} aria-label={`Remove reference ${ref.label}`} onClick={()=>onChange(value.filter(item=>referenceIdentity(item)!==referenceIdentity(ref)))}>×</button>}</span>)}
   {triggerHost?createPortal(trigger,triggerHost):trigger}
  </div>
  {error&&<p role="alert">{error}</p>}
  {open&&!readOnly&&<div id={pickerId} className="surface-graph-reference-input__picker">
   <div role="group" aria-label="Reference type"><button type="button" aria-pressed={kind==='objects'} onClick={()=>setKind('objects')}>Objects</button><button type="button" aria-pressed={kind==='sources'} onClick={()=>setKind('sources')}>Sources</button></div>
   {kind==='objects'?<NativeGraphInspection key={worldId} worldId={worldId} onChoose={choose} disabled={disabled}/>:<NativeSourceInspection key={worldId} worldId={worldId} disabled={disabled} onChoose={ref=>{if(disabled||readOnly||ref.managed_world_id!==worldId)return;try{onChange(mergeAuthoredReferences(value,[ref]));setError(null);setOpen(false);}catch(e){setError(String(e));}}}/>}
  </div>}
 </section>;
}
