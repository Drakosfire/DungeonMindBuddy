import {useEffect,useState} from 'react';
import type {InspectionPin} from '../api/nativeGraphInspection';
import type {WorldMechanicsAssociation} from '../api/worldMechanicsTypes';
import {listWorldMechanicsAssociations} from '../api/liveApi';
import {SavedStatblockButton} from '../statblocks/SavedStatblockSession';
import {savedStatblockHref} from '../statblocks/savedStatblockLocation';
import {interceptPrimaryNavigationClick} from '../chrome/appNavigation';

/** Read existing APP links; a preview never adopts mechanics or changes Graph facts. */
export function NativeObjectStatblock({pin,entityId}:{pin:InspectionPin;entityId:string}) {
 const [result,setResult]=useState<{key:string;records:WorldMechanicsAssociation[]}|null>(null);
 const [failure,setFailure]=useState<{key:string;text:string}|null>(null),[retry,setRetry]=useState(0);
 const key=JSON.stringify([pin,entityId]);
 useEffect(()=>{
  let active=true;setResult(null);setFailure(null);
  listWorldMechanicsAssociations(pin.managed_world_id).then(records=>{
   if(active)setResult({key,records:records.filter(record=>{
    const t=record.request.target;
    return t.managed_world_id===pin.managed_world_id&&t.native_world_id===pin.native_world_id
     &&t.binding_version===pin.binding_version&&t.node_id===entityId
     &&(pin.scope_mode==='world'||t.campaign_scope===null||t.campaign_scope===pin.campaign_id);
   })});
  }).catch(error=>{if(active)setFailure({key,text:error instanceof Error?error.message:'Linked statblocks could not be loaded.'});});
  return()=>{active=false;};
 },[key,retry]);
 const records=result?.key===key?result.records:null,error=failure?.key===key?failure.text:null;
 return <section aria-label="Linked statblocks">
  {error?<><p role="alert">{error}</p><button type="button" onClick={()=>setRetry(v=>v+1)}>Retry linked statblocks</button></>:!records?<p role="status">Loading linked statblocks…</p>:!records.length?<p>No statblock linked in this view.</p>:records.map(record=>{
   const target={worldId:pin.managed_world_id,draftId:record.request.draft_id,revisionId:record.proof.locator.revision_id};
   return <section key={record.association_id} aria-label={`Statblock · ${record.request.target.campaign_scope??'World'}`}>
    <p>Saved statblock · {record.request.target.campaign_scope??'World'}</p>
    <SavedStatblockButton {...target} label="Preview and edit statblock"/>
    <a href={savedStatblockHref(target)} onClick={interceptPrimaryNavigationClick}>Open full statblock</a>
    <details><summary>Link details</summary><p>Saved version: {target.revisionId}</p><p>Linked at Graph revision: {record.request.target.graph_revision_id}</p><p>This link does not adopt mechanics into an encounter.</p></details>
   </section>;
  })}
 </section>;
}
