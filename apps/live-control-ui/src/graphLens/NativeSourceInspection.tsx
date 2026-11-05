import {useEffect,useId,useRef,useState} from 'react';
import {getNativeSourceCatalog,readNativeSource} from '../api/liveApi';
import {sameInspectionPin} from '../api/nativeGraphInspection';
import type {NativeSourceCatalog,NativeSourceMetadata} from '../api/nativeSourceInspection';
import {WorldPlanAgentAnswer} from '../planSurface/components/WorldPlanAgentAnswer';

const identity=(s:NativeSourceMetadata)=>`${s.source_artifact.source_artifact_id}:${s.source_revision.source_revision_id}`;
const label=(s:NativeSourceMetadata)=>s.navigation.label??'Unnamed source';
const failureText=(e:unknown)=>e instanceof Error?e.message:'Sources are unavailable.';

/** Human navigation and exact reads; filters never restrict agent evidence. */
export function NativeSourceInspection({worldId}:{worldId:string}) {
 const id=useId(),generation=useRef(0);
 const [catalog,setCatalog]=useState<NativeSourceCatalog|null>(null),[failure,setFailure]=useState<string|null>(null);
 const [refresh,setRefresh]=useState(0),[query,setQuery]=useState(''),[kind,setKind]=useState(''),[campaign,setCampaign]=useState(''),[session,setSession]=useState('');
 const [readAttempt,setReadAttempt]=useState(0);
 const [selected,setSelected]=useState<NativeSourceMetadata|null>(null),[body,setBody]=useState<string|null>(null),[readFailure,setReadFailure]=useState<string|null>(null);
 useEffect(()=>{
  const epoch=++generation.current,abort=new AbortController();
  setCatalog(null);setFailure(null);setSelected(null);setBody(null);setReadFailure(null);
  setQuery('');setKind('');setCampaign('');setSession('');
  getNativeSourceCatalog({managed_world_id:worldId,scope_mode:'world',campaign_id:null},abort.signal)
   .then(packet=>{if(epoch!==generation.current)return;
    if(packet.schema!=='dmb_native_source_catalog_v1'||packet.scope.managed_world_id!==worldId||packet.scope.scope_mode!=='world'||packet.scope.campaign_id!==null||packet.catalogue.space_id!==packet.scope.native_world_id||packet.catalogue.revision_id!==packet.scope.revision_id)throw new Error('The World changed. Refresh sources.');
    if(!Array.isArray(packet.catalogue.sources)||packet.catalogue.sources.some(s=>!s.navigation))throw new Error('Source navigation metadata is unavailable. Refresh sources.');
    setCatalog(packet);
   }).catch(e=>{if(epoch===generation.current&&!abort.signal.aborted)setFailure(failureText(e));});
  return()=>{generation.current++;abort.abort();};
 },[worldId,refresh]);
 const current=catalog?.scope.managed_world_id===worldId?catalog:null;
 useEffect(()=>{
  setBody(null);setReadFailure(null);
  if(!current||!selected)return;
  let active=true;const abort=new AbortController();
  const evidence=selected.evidence_ref_ids[0];
  if(!evidence){setReadFailure('This exact source has no available opening.');return;}
  readNativeSource(current.scope,{source_artifact_id:selected.source_artifact.source_artifact_id,source_revision_id:selected.source_revision.source_revision_id,evidence_ref_id:evidence},abort.signal)
   .then(packet=>{if(!active)return;
    if(packet.schema!=='dmb_native_source_body_v1'||!sameInspectionPin(packet.scope,current.scope)||packet.source.status!=='available'||typeof packet.source.body_text!=='string'||packet.source.source_artifact_id!==selected.source_artifact.source_artifact_id||packet.source.source_revision_id!==selected.source_revision.source_revision_id||packet.source.body_sha256!==selected.source_revision.content_sha256||packet.source.evidence_ref_id!==evidence)throw new Error('The exact source is unavailable. Refresh sources and choose it again.');
    setBody(packet.source.body_text);
   }).catch(e=>{if(active&&!abort.signal.aborted)setReadFailure(failureText(e));});
  return()=>{active=false;abort.abort();};
 },[current,selected,readAttempt]);
 const sources=current?.catalogue.sources??[];
 const campaigns=[...new Set(sources.flatMap(s=>s.navigation.campaign_id?[s.navigation.campaign_id]:[]))].sort();
 const sessions=[...new Set(sources.filter(s=>!campaign||s.navigation.campaign_id===campaign).flatMap(s=>s.navigation.session_id?[s.navigation.session_id]:[]))].sort((a,b)=>a.localeCompare(b,undefined,{numeric:true}));
 const found=sources.filter(s=>(!kind||s.navigation.kind===kind)&&(!campaign||s.navigation.campaign_id===campaign)&&(!session||s.navigation.session_id===session)&&[label(s),s.navigation.campaign_id??'',s.navigation.session_id??'',s.source_artifact.source_artifact_id].join(' ').toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()));
 return <section aria-label="Source browser">
  <button type="button" onClick={()=>{setCatalog(null);setSelected(null);setBody(null);setRefresh(v=>v+1);}}>Refresh sources</button>
  {failure?<p role="alert">{failure}</p>:!current?<p role="status">Loading sources…</p>:<>
   <p role="status">{sources.length} admitted sources · {current.catalogue.complete?'Complete source view':'Partial source view'}</p>
   {!current.navigation_complete&&<p role="status">Some source names or filters are unavailable. Unnamed sources can still be opened; filtered results may omit them.</p>}
   <div className="native-source-inspection__filters">
    <label htmlFor={`${id}-query`}>Find a source<input id={`${id}-query`} type="search" value={query} onChange={e=>setQuery(e.target.value)}/></label>
    <label htmlFor={`${id}-type`}>Type<select id={`${id}-type`} value={kind} onChange={e=>setKind(e.target.value)}><option value="">All sources</option><option value="recap">Recaps</option><option value="worldbuilding">Worldbuilding</option><option value="other">Other</option></select></label>
    <label htmlFor={`${id}-campaign`}>Campaign<select id={`${id}-campaign`} value={campaign} onChange={e=>{setCampaign(e.target.value);setSession('');}}><option value="">All campaigns</option>{campaigns.map(c=><option key={c}>{c}</option>)}</select></label>
    <label htmlFor={`${id}-session`}>Session<select id={`${id}-session`} value={session} onChange={e=>setSession(e.target.value)}><option value="">All sessions</option>{sessions.map(s=><option key={s}>{s}</option>)}</select></label>
   </div>
   <p>{found.length} matching sources</p>
   <div className="loaded-graph-explorer__layout"><nav aria-label="Available sources"><ul>{found.map(s=><li key={identity(s)}><button type="button" aria-current={selected&&identity(selected)===identity(s)?'true':undefined} onClick={()=>{setBody(null);setReadFailure(null);setSelected(s);setReadAttempt(v=>v+1);}}>{label(s)}<small>{[s.navigation.campaign_id,s.navigation.session_id].filter(Boolean).join(' · ')}</small></button></li>)}</ul>{!found.length&&<p>{sources.length?'No sources match these filters.':'No admitted sources are available in this view.'}</p>}</nav>
    <article aria-label="Selected source">
     {!selected?<p>Choose a source to read its saved text.</p>:<><h3>{label(selected)}</h3>
      {selected.navigation.origin_matches_current_metadata===false&&<p>Current page name; the text below is the selected saved source version.</p>}
      {readFailure?<p role="alert">{readFailure}</p>:body===null?<p role="status">Opening exact source…</p>:<WorldPlanAgentAnswer answer={body}/>}
      <details><summary>Source version</summary><p>{selected.source_artifact.source_artifact_id}</p><p>{selected.source_revision.source_revision_id}</p><p>Body SHA-256: {selected.source_revision.content_sha256}</p><p>Knowledge revision: {current.scope.revision_id}</p></details>
     </>}
    </article>
   </div>
  </>}
 </section>;
}
