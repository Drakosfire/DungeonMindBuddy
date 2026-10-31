import {useEffect,useRef,useState} from 'react';
import {getNativeGraphCatalog,inspectNativeGraph} from '../api/liveApi';
import type {NativeAssertion,NativeGraphCatalog,NativeGraphEntity,InspectionPin} from '../api/nativeGraphInspection';
import {SourceCitationEvidence,type CitationChoice} from '../planSurface/components/SourceCitationEvidence';

function valueText(a:NativeAssertion,labels:Map<string,string>):string {
 const v=a.value;
 return v.kind==='entity_ref' ? labels.get(v.entity_id)??v.entity_id
  :v.kind==='term_ref' ? v.term :typeof v.value==='string' ? v.value :JSON.stringify(v.value);
}
const samePin=(a:InspectionPin,b:InspectionPin)=>a.managed_world_id===b.managed_world_id&&a.native_world_id===b.native_world_id&&a.revision_id===b.revision_id&&a.binding_version===b.binding_version&&a.scope_mode===b.scope_mode&&a.campaign_id===b.campaign_id;
const errorText=(e:unknown)=>e instanceof Error?e.message:'Reviewed Graph inspection is unavailable.';

/** Only native inspection packets enter here; selections never leave for authoring. */
export function NativeGraphInspection({worldId}:{worldId:string}) {
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
   .then(packet=>{if(epoch===generation.current){if(packet.scope.managed_world_id!==worldId)throw new Error('The World changed; refresh this view.');setCatalog(packet);}})
   .catch(e=>{if(epoch===generation.current&&!abort.signal.aborted)setFailure(errorText(e));});
  return()=>{generation.current++;abort.abort();};
 },[worldId,refresh]);
 useEffect(()=>{
  setDetail(null);setDetailFailure(null);
  if(!catalog||!selected)return;
  let active=true;const abort=new AbortController();
  inspectNativeGraph(catalog.scope,{kind:'entity',entity_id:selected},abort.signal)
   .then(packet=>{if(active){if(packet.schema!=='dmb_native_graph_entity_v1'||!samePin(packet.scope,catalog.scope))throw new Error('The selected view changed; refresh it.');setDetail(packet);}})
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
  return [node.entity_id,names?.size===1?[...names][0]:node.entity_id];
 }));
 const nodes=(catalog?.catalogue.entities??[]).filter(n=>(labels.get(n.entity_id)??n.entity_id).toLocaleLowerCase().includes(query.toLocaleLowerCase()));
 return <section aria-label="Reviewed Graph inspection">
  <p role="note">Read-only reviewed material. Question sources and publication are selected separately.</p>
  <button type="button" onClick={()=>{setCatalog(null);setDetail(null);setSelected(null);setRefresh(v=>v+1);}}>Refresh reviewed Graph</button>
  {failure?<p role="alert">{failure}</p>:!catalog?<p role="status">Loading reviewed Graph…</p>:<>
   <p role="status">{catalog.catalogue.entities.length} objects · {catalog.assertions.filter(a=>a.value.kind==='entity_ref').length} connections · {catalog.catalogue.completeness.status==='complete'?'Complete for this view':'Partial view'}</p>
   <p>This describes the selected published revision, not the completeness of your sources.</p>
   <div className="loaded-graph-explorer__layout"><nav aria-label="Reviewed Graph objects">
    <label>Find an object<input type="search" value={query} onChange={e=>setQuery(e.target.value)}/></label>
    <ul>{nodes.map(n=><li key={n.entity_id}><button type="button" aria-current={selected===n.entity_id?'true':undefined}
     onClick={()=>{setDetail(null);setDetailFailure(null);setSelected(n.entity_id);}}>{labels.get(n.entity_id)}</button></li>)}</ul>
    {!nodes.length?<p>{catalog.catalogue.entities.length?'No matching objects.':'No reviewed objects are available in this view.'}</p>:null}
   </nav><article aria-label="Reviewed object details">
    {!selected?<p>Select an object to inspect its records and sources.</p>:detailFailure?<p role="alert">{detailFailure}</p>:!detail?<p role="status">Loading selected object…</p>:<>
     <h3>{labels.get(selected)??selected}</h3>
     {detail.entity.completeness.status!=='complete'?<p role="status">Some records are unavailable.</p>:null}
     {!detail.entity.assertions.length?<p>No admitted records for this object in this view.</p>:null}
     {detail.entity.assertions.map(a=><NativeRecord key={`${selected}:${a.assertion_id}`} assertion={a} detail={detail} labels={labels}/>)}
    </>}
   </article></div>
   <details><summary>View details</summary><p>Revision: {catalog.scope.revision_id}</p><p>World: {catalog.scope.managed_world_id}</p></details>
  </>}
 </section>;
}

function NativeRecord({assertion:a,detail,labels}:{assertion:NativeAssertion;detail:NativeGraphEntity;labels:Map<string,string>}) {
 const choices:CitationChoice[]=detail.entity.evidence.filter(e=>a.metadata.evidence_ref_ids.includes(e.evidence_ref_id)&&e.evidence_role==='support')
  .map((e,i)=>({key:e.evidence_ref_id,number:i+1,title:'Supporting source · exact excerpt',label:'Read supporting source',kind:'passage',load:async()=>{
   const packet=await inspectNativeGraph(detail.scope,{kind:'source',assertion_id:a.assertion_id,evidence_ref_id:e.evidence_ref_id});
   if(packet.schema!=='dmb_native_graph_source_v1'||!samePin(packet.scope,detail.scope))throw new Error('Source unavailable');
   return packet.source.text;
  }}));
 const text=`${labels.get(a.subject_entity_id)??a.subject_entity_id} · ${a.predicate.split(':').at(-1)!.replaceAll('_',' ')}: ${valueText(a,labels)}`;
 return <section aria-label="Reviewed Graph record">
  <p>{a.metadata.claim_mode.replace('dungeonbuddy.claim:','')} · {a.metadata.epistemic_basis} · {a.metadata.standing}</p>
  <SourceCitationEvidence identity={`${detail.scope.managed_world_id}:${detail.scope.revision_id}:${a.assertion_id}`}
   statements={[{text,choices}]}/>
  <details><summary>Record qualifications</summary><pre>{JSON.stringify(a.metadata,null,2)}</pre></details>
 </section>;
}
