import {sameInspectionPin} from '../api/nativeGraphInspection';
import {useEffect,useId,useRef,useState} from 'react';
import {getNativeGraphCatalog,inspectNativeGraph} from '../api/liveApi';
import type {NativeGraphCatalog,NativeGraphEntity,InspectionPin} from '../api/nativeGraphInspection';
import {NativeGraphObjectDetails} from './NativeGraphObjectDetails';

const errorText=(e:unknown)=>e instanceof Error?e.message:'Reviewed Graph inspection is unavailable.';

/** Native inspection and optional authored selection share the same catalogue. */
export function NativeGraphInspection({worldId,onChoose,disabled=false}:{worldId:string;onChoose?:(pin:InspectionPin,entityId:string,label:string)=>void;disabled?:boolean}) {
 const queryId=useId();
 const [catalog,setCatalog]=useState<NativeGraphCatalog|null>(null);
 const [failure,setFailure]=useState<string|null>(null);
 const [refresh,setRefresh]=useState(0);
 const [query,setQuery]=useState('');
 const [selected,setSelected]=useState<string|null>(null);
 const [detail,setDetail]=useState<NativeGraphEntity|null>(null);
 const [detailFailure,setDetailFailure]=useState<string|null>(null);
 const generation=useRef(0);
 useEffect(()=>{
  const epoch=++generation.current,abort=new AbortController();
  setCatalog(null);setFailure(null);setSelected(null);setDetail(null);setDetailFailure(null);
  getNativeGraphCatalog({managed_world_id:worldId,scope_mode:'world',campaign_id:null},abort.signal)
   .then(packet=>{if(epoch===generation.current){if(packet.schema!=='dmb_native_graph_catalog_v1'||packet.scope.managed_world_id!==worldId||packet.scope.scope_mode!=='world'||packet.scope.campaign_id!==null||packet.catalogue.identity.space_id!==packet.scope.native_world_id||packet.catalogue.identity.revision_id!==packet.scope.revision_id)throw new Error('The World changed; refresh this view.');setCatalog(packet);}})
   .catch(e=>{if(epoch===generation.current&&!abort.signal.aborted)setFailure(errorText(e));});
  return()=>{generation.current++;abort.abort();};
 },[worldId,refresh]);
 useEffect(()=>{
  setDetail(null);setDetailFailure(null);
  if(!catalog||!selected)return;
  let active=true;const abort=new AbortController();
  inspectNativeGraph(catalog.scope,{kind:'entity',entity_id:selected},abort.signal)
   .then(packet=>{if(active){if(packet.schema!=='dmb_native_graph_entity_v1'||!sameInspectionPin(packet.scope,catalog.scope))throw new Error('The selected view changed; refresh it.');setDetail(packet);}})
   .catch(e=>{if(active&&!abort.signal.aborted)setDetailFailure(errorText(e));});
  return()=>{active=false;abort.abort();};
 },[catalog,selected]);
 const namesBySubject=new Map<string,Set<string>>();
 for(const a of catalog?.assertions??[]) {
  if(a.predicate==='dnd5e:name'&&a.value.kind==='literal'&&typeof a.value.value==='string') {
   const names=namesBySubject.get(a.subject_entity_id)??new Set<string>();
   names.add(a.value.value);namesBySubject.set(a.subject_entity_id,names);
  }
 }
 const labels=new Map((catalog?.catalogue.entities??[]).map(node=>{
  const names=namesBySubject.get(node.entity_id);
  return [node.entity_id,names?.size?[...names].sort().join(' / '):node.entity_id];
 }));
 const nodes=(catalog?.catalogue.entities??[]).filter(n=>(labels.get(n.entity_id)??n.entity_id).toLocaleLowerCase().includes(query.toLocaleLowerCase()));
 return <section aria-label="Reviewed Graph inspection">
  <p role="note">{onChoose?'Select an object as context. Its sources are read when your request runs.':'Read-only reviewed material. Question sources and publication are selected separately.'}</p>
  <button type="button" onClick={()=>{setCatalog(null);setDetail(null);setSelected(null);setRefresh(v=>v+1);}}>Refresh reviewed Graph</button>
  {failure?<p role="alert">{failure}</p>:!catalog?<p role="status">Loading reviewed Graph…</p>:<>
   <p role="status">{catalog.catalogue.entities.length} objects · {catalog.assertions.filter(a=>a.value.kind==='entity_ref').length} connections · {catalog.catalogue.completeness.status==='complete'?'Complete for this view':'Partial view'}</p>
   <p>This describes the selected published revision, not the completeness of your sources.</p>
   <div className="loaded-graph-explorer__layout"><nav aria-label="Reviewed Graph objects">
    <label htmlFor={queryId}>Find an object</label><input id={queryId} type="search" autoFocus={Boolean(onChoose)} value={query} onChange={e=>setQuery(e.target.value)}/>
    <ul>{nodes.map(n=><li key={n.entity_id}><button type="button" aria-current={selected===n.entity_id?'true':undefined}
     onClick={()=>{if(selected===n.entity_id)return;setDetail(null);setDetailFailure(null);setSelected(n.entity_id);}}>{labels.get(n.entity_id)}{onChoose&&<small>{n.entity_id}</small>}</button>{onChoose&&<button type="button" disabled={disabled} aria-label={`Use ${labels.get(n.entity_id)} as context`} onClick={()=>{if(!disabled&&catalog.scope.managed_world_id===worldId)onChoose(catalog.scope,n.entity_id,labels.get(n.entity_id)??n.entity_id);}}>Use as context</button>}</li>)}</ul>
    {!nodes.length?<p>{catalog.catalogue.entities.length?'No matching objects.':'No reviewed objects are available in this view.'}</p>:null}
   </nav><article aria-label="Reviewed object details">
    {!selected?<p>Select an object to inspect its records and sources.</p>:detailFailure?<p role="alert">{detailFailure}</p>:!detail?<p role="status">Loading selected object…</p>:<>
     <NativeGraphObjectDetails detail={detail} entityId={selected} label={labels.get(selected)??selected} labels={labels}/>
    </>}
   </article></div>
   <details><summary>View details</summary><p>Revision: {catalog.scope.revision_id}</p><p>World: {catalog.scope.managed_world_id}</p></details>
  </>}
 </section>;
}
