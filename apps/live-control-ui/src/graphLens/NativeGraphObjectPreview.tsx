import {displayClassification} from "../nativeGraphDemo/nativeGraphPresentation";
import {GraphNodeViewer} from "./GraphNodeViewer";
import {useEffect,useRef,useState} from 'react';
import {createPortal} from 'react-dom';
import type {AuthoredGraphReferenceV1} from '../api/types';
import {sameInspectionPin,type InspectionPin,type NativeGraphEntity} from '../api/nativeGraphInspection';
import {inspectNativeGraph} from '../api/liveApi';
import {NodeDossier} from './NodeDossier';
import {buildNodeExplorer} from './nodeExplorerModel';
import '../statblocks/SavedStatblockDialog.css';

/** Inspect the reference's captured pin, without changing selection or resolving latest. */
export function NativeGraphObjectPreview({reference:ref,onClose,inlineHost}:{reference:AuthoredGraphReferenceV1;onClose:()=>void;inlineHost?:HTMLElement}) {
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
 const labels = new Map([[ref.node_id, ref.label]]);
 const dossier = detail?.entity.found ? buildNodeExplorer(detail, ref.node_id, labels) : null;
 const kind = dossier && displayClassification(dossier.identityAssertions.flatMap(assertion =>
  assertion.predicate.endsWith(':classification') && assertion.value.kind === 'term_ref' ? [assertion.value.term] : []
 ));
 return createPortal(<dialog ref={dialog} className="saved-statblock-dialog native-graph-object-preview" aria-label={`Object · ${ref.label}`} onClose={event=>{if(!event.currentTarget.open)onClose();}} onKeyDown={event=>{if(event.key==='Escape')event.stopPropagation();}}>
  <div className="saved-statblock-dialog__body">
  <GraphNodeViewer dialog label={ref.label} kind={kind || undefined} partial={detail?.entity.completeness.status === "partial"} controls={<button type="button" autoFocus aria-label="Close object preview" onClick={onClose}>×</button>}>
   {failure?<><p role="alert">{failure}</p><button type="button" onClick={()=>setRetry(v=>v+1)}>Retry object preview</button></>:!detail?<p role="status">Loading selected object…</p>:dossier ? <>
    {detail.scope.scope_mode === "world" && <a href={"/build?" + new URLSearchParams({
      world: detail.scope.managed_world_id,
      nativeWorld: detail.scope.native_world_id,
      bindingVersion: String(detail.scope.binding_version),
      graphRevision: detail.scope.revision_id,
      graphNodeId: ref.node_id,
    })}>Open object in Build</a>}
    <NodeDossier model={dossier} detail={detail} entityId={ref.node_id} labels={labels}
      showStatblocks={kind !== "event"} eagerStatblocks inlineHost={inlineHost} onInlineOpened={onClose} />
   </> : <p>This object is unavailable in the selected revision.</p>}
  </GraphNodeViewer>
  </div>
 </dialog>,document.body);
}
