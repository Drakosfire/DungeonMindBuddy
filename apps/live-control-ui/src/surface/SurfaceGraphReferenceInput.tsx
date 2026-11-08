import {useEffect,useId,useState} from 'react';
import {createPortal} from 'react-dom';
import type {AuthoredGraphReferenceV1,AuthoredReference} from '../api/types';
import {mergeAuthoredReferences,referenceIdentity} from '../agentInteraction/authoredGraphReferences';
import {NativeSourceInspection} from '../graphLens/NativeSourceInspection';
import {NativeGraphInspection} from '../graphLens/NativeGraphInspection';
import type {InspectionPin} from '../api/nativeGraphInspection';
import './SurfaceGraphReferenceInput.css';
import {NativeGraphObjectPreview} from '../graphLens/NativeGraphObjectPreview';

/** One input renderer for composer, plan roots and pending steps. Selection is unread. */
export function SurfaceGraphReferenceInput({worldId,value,onChange,disabled=false,readOnly=false,label='References',triggerHost,sourceOnly=false}:{worldId:string;value:AuthoredReference[];onChange:(next:AuthoredReference[])=>void;disabled?:boolean;readOnly?:boolean;label?:string;triggerHost?:HTMLElement|null;sourceOnly?:boolean}) {
 const pickerId=useId();
 const [preview,setPreview]=useState<AuthoredGraphReferenceV1|null>(null);
 const previewSelected=preview?.managed_world_id===worldId&&value.some(candidate=>candidate.schema==='dmb_authored_graph_reference_v1'&&referenceIdentity(candidate)===referenceIdentity(preview)&&candidate.binding_version===preview.binding_version&&candidate.graph_revision===preview.graph_revision);
 useEffect(()=>{if(!previewSelected)setPreview(null);},[previewSelected]);
 const [selectedKind,setKind]=useState<'objects'|'sources'>('objects');
 const kind=sourceOnly?'sources':selectedKind;
 const [open,setOpen]=useState(false),[error,setError]=useState<string|null>(null);
 function choose(pin:InspectionPin,entityId:string,label:string){
  if(sourceOnly||disabled||readOnly||pin.managed_world_id!==worldId)return;
  try{onChange(mergeAuthoredReferences(value,[{schema:'dmb_authored_graph_reference_v1',managed_world_id:worldId,native_world_id:pin.native_world_id,binding_version:pin.binding_version,graph_revision:pin.revision_id,node_id:entityId,label}]));setError(null);setOpen(false);}catch(e){setError(String(e));}
 }
 const trigger=!readOnly&&<button type="button" className={triggerHost?'conversation-dock__icon-button':undefined} disabled={disabled} aria-label="@ Reference" title="References" aria-controls={pickerId} aria-expanded={open} onClick={()=>setOpen(!open)}>{triggerHost?'@':'@ Reference'}</button>;
 return <section className="surface-graph-reference-input" aria-label={label} hidden={Boolean(triggerHost)&&!value.length&&!open&&!error}>
  <div className="surface-graph-reference-input__chips">{value.map(ref=><span key={referenceIdentity(ref)} className="surface-graph-reference-input__chip">{ref.schema==='dmb_authored_graph_reference_v1'?<button type="button" disabled={ref.managed_world_id!==worldId} aria-label={`Inspect ${ref.label}`} onClick={()=>setPreview(ref)}>@{ref.label}</button>:<span title={readOnly?'Selected for this request; see its trace for read results.':'Selected, unread until this request runs'}>@{ref.label}</span>}{!readOnly&&<button type="button" disabled={disabled} aria-label={`Remove reference ${ref.label}`} onClick={()=>onChange(value.filter(item=>referenceIdentity(item)!==referenceIdentity(ref)))}>×</button>}</span>)}
   {triggerHost?createPortal(trigger,triggerHost):trigger}
  </div>
  {preview&&previewSelected&&<NativeGraphObjectPreview key={JSON.stringify(preview)} reference={preview} onClose={()=>setPreview(null)}/>}
  {error&&<p role="alert">{error}</p>}
  {open&&!readOnly&&<div id={pickerId} className="surface-graph-reference-input__picker">
   <div role="group" aria-label="Reference type">{!sourceOnly&&<button type="button" aria-pressed={kind==='objects'} onClick={()=>setKind('objects')}>Objects</button>}<button type="button" aria-pressed={kind==='sources'} onClick={()=>setKind('sources')}>Sources</button></div>
   {kind==='objects'?<NativeGraphInspection key={worldId} worldId={worldId} onChoose={choose} disabled={disabled}/>:<NativeSourceInspection key={worldId} worldId={worldId} disabled={disabled} onChoose={ref=>{if(disabled||readOnly||ref.managed_world_id!==worldId)return;try{onChange(mergeAuthoredReferences(value,[ref]));setError(null);setOpen(false);}catch(e){setError(String(e));}}}/>}
  </div>}
 </section>;
}
