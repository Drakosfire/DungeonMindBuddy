import {useEffect,useRef,useState} from 'react';
import {createPortal} from 'react-dom';
import type {AuthoredGraphReferenceV1} from '../api/types';
import {sameInspectionPin,type InspectionPin,type NativeGraphEntity} from '../api/nativeGraphInspection';
import {inspectNativeGraph} from '../api/liveApi';
import {NativeGraphObjectDetails} from './NativeGraphObjectDetails';
import '../statblocks/SavedStatblockDialog.css';

/** Inspect the reference's captured pin, without changing selection or resolving latest. */
export function NativeGraphObjectPreview({reference:ref,onClose}:{reference:AuthoredGraphReferenceV1;onClose:()=>void}) {
 const dialog=useRef<HTMLDialogElement>(null);
 const [detail,setDetail]=useState<NativeGraphEntity|null>(null),[failure,setFailure]=useState<string|null>(null),[retry,setRetry]=useState(0);
 useEffect(()=>{const node=dialog.current;node?.showModal();return()=>node?.close();},[]);
 useEffect(()=>{
  let active=true;const abort=new AbortController();setDetail(null);setFailure(null);
  const pin:InspectionPin={managed_world_id:ref.managed_world_id,native_world_id:ref.native_world_id,binding_version:ref.binding_version,revision_id:ref.graph_revision,scope_mode:'world',campaign_id:null};
  inspectNativeGraph(pin,{kind:'entity',entity_id:ref.node_id},abort.signal).then(packet=>{
   if(!active)return;
   if(packet.schema!=='dmb_native_graph_entity_v1'||!sameInspectionPin(packet.scope,pin))throw new Error('The object read did not match this reference.');
   setDetail(packet);
  }).catch(error=>{if(active&&!abort.signal.aborted)setFailure(error instanceof Error?error.message:'This object could not be opened.');});
  return()=>{active=false;abort.abort();};
 },[ref,retry]);
 return createPortal(<dialog ref={dialog} className="saved-statblock-dialog native-graph-object-preview" aria-label={`Object · ${ref.label}`} onClose={onClose} onKeyDown={event=>{if(event.key==='Escape')event.stopPropagation();}}>
  <header><strong>Object reference</strong><button type="button" autoFocus aria-label="Close object preview" onClick={onClose}>×</button></header>
  <div className="saved-statblock-dialog__body">
   {failure?<><p role="alert">{failure}</p><button type="button" onClick={()=>setRetry(v=>v+1)}>Retry object preview</button></>:!detail?<p role="status">Loading selected object…</p>:<NativeGraphObjectDetails detail={detail} entityId={ref.node_id} label={ref.label}/>}
  </div>
 </dialog>,document.body);
}
