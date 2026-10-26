import {useState} from 'react';
import type {AuthoredGraphReferenceV1} from '../api/types';
import {mergeAuthoredReferences,referenceIdentity} from '../agentInteraction/authoredGraphReferences';
import {useOptionalWorldGraphLensProjection,useWorldGraphLensProjectionDemand} from '../graphLens/useWorldGraphLensProjection';
import {GraphReferenceSearch} from '../graphReference/GraphReferenceSearch';
import {adaptWorldGraphProjectionSearchItems} from '../buildSurface/reference/buildWorldGraphSurfaceInformation';
import {useOptionalAgentInteraction} from '../agentInteraction/AgentInteractionProvider';
import {glanceOnlyForGraphReference} from '../graphReference/openGraphReferencePolicy';
import {extractExactGraphReferenceScope} from '../graphReference/resolveGraphReference';
import {buildGraphObjectCardFromNodeView} from '../graphObjectCard';
import type {GraphReferenceResolution,GraphReferenceSearchItem} from '../graphReference/types';
import './SurfaceGraphReferenceInput.css';

/** One input renderer for composer, plan roots and pending steps. Selection is unread. */
export function SurfaceGraphReferenceInput({worldId,value,onChange,disabled=false,readOnly=false,label='Graph context'}:{worldId:string;value:AuthoredGraphReferenceV1[];onChange:(next:AuthoredGraphReferenceV1[])=>void;disabled?:boolean;readOnly?:boolean;label?:string}) {
 const [open,setOpen]=useState(false),[error,setError]=useState<string|null>(null);
 const graph=useOptionalWorldGraphLensProjection();
 useWorldGraphLensProjectionDemand(open&&!disabled&&!readOnly);
 const interaction=useOptionalAgentInteraction();
 const binding=graph?.managedBinding,projection=graph?.projection;
 const ready=graph?.projectionState==='ready'&&projection&&binding?.managedWorldId===worldId;
 function choose(item:GraphReferenceSearchItem){
  if(disabled||readOnly||!ready||!binding||!projection||!projection.nodes.some(node=>node.nodeId===item.nodeId))return;
  try{onChange(mergeAuthoredReferences(value,[{schema:'dmb_authored_graph_reference_v1',managed_world_id:worldId,native_world_id:binding.nativeWorldId,binding_version:binding.bindingVersion,graph_revision:projection.snapshot.revisionId,node_id:item.nodeId,label:item.label}]));setError(null);setOpen(false);}catch(e){setError(String(e));}
 }
 function view(item:GraphReferenceSearchItem){
  if(!ready||!projection)return;const scope=extractExactGraphReferenceScope(projection);if(!scope)return;
  const resolution:GraphReferenceResolution={kind:'resolved_graph',locator:`dmb-node:${item.nodeId}`,reference:item.reference,graphNodeId:item.nodeId,graphObject:buildGraphObjectCardFromNodeView(item.nodeView),graphScope:scope,projectionState:'ready'};
  interaction?.openGraphReference({resolution,projectionState:'ready',glanceOnly:glanceOnlyForGraphReference(resolution)});
 }
 return <section className="surface-graph-reference-input" aria-label={label}>
  <div className="surface-graph-reference-input__chips">{value.map(ref=><span key={referenceIdentity(ref)} className="surface-graph-reference-input__chip"><span title={readOnly?'Selected for this request; see its trace for read results.':'Selected, unread until this request runs'}>@{ref.label}</span>{!readOnly&&<button type="button" disabled={disabled} aria-label={`Remove reference ${ref.label}`} onClick={()=>onChange(value.filter(item=>referenceIdentity(item)!==referenceIdentity(ref)))}>×</button>}</span>)}
   {!readOnly&&<button type="button" disabled={disabled} aria-expanded={open} onClick={()=>setOpen(!open)}>@ Reference</button>}
  </div>
  {error&&<p role="alert">{error}</p>}
  {open&&!readOnly&&<div className="surface-graph-reference-input__picker">
   {!ready&&graph?.projectionState==='ready'&&<p role="alert">This Graph projection has no verified binding to the current World. Your references are retained.</p>}
   <GraphReferenceSearch items={ready?adaptWorldGraphProjectionSearchItems(projection):[]} projectionState={graph?.projectionState==='idle'?'loading':graph?.projectionState??'unavailable'} projectionError={graph?.projectionError} onChoose={choose} chooseDisabled={!ready||disabled} onView={interaction?view:undefined}/>
  </div>}
 </section>;
}
