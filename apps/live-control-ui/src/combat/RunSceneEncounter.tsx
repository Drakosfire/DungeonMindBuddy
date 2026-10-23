import {useEffect,useRef,useState} from 'react';
import {CombatRosterModule} from '../surface/modules/CombatRosterModule';
import {exactIntent,withIntentLock} from './exactIntent';
import {materializeRunEncounter,previewRunEncounter,readRunEncounter,type EncounterApplied,type EncounterOutcome,type EncounterPreview,type MaterializeRequest,type RunEncounterScope} from './runEncountersApi';

export type RunEncounterContext=RunEncounterScope&{worldId:string;sceneTitle:string;readOnly?:boolean};
export function RunSceneEncounter({context}:{context:RunEncounterContext}){
 const {worldId,runId,sceneId}=context,epoch=useRef(0);
 const key=`dmb.scene.encounter.creation:${JSON.stringify([worldId,runId,sceneId])}`;
 const [pending,setPending]=useState<MaterializeRequest|null>(null),[current,setCurrent]=useState<EncounterApplied|null>(null);
 const [preview,setPreview]=useState<EncounterPreview|null>(null),[busy,setBusy]=useState(false),[fatal,setFatal]=useState(false),[message,setMessage]=useState('');
 function verify(result:EncounterOutcome,request:MaterializeRequest){
  const intent=result.state==='applied'?result.receipt.intent:result;
  if(intent.world_id!==worldId||intent.run_id!==runId||intent.scene_id!==sceneId||exactIntent(intent.request)!==exactIntent(request))throw new Error('Encounter receipt differs from the retained scene intent');
  if(result.state==='applied'&&(result.encounter.world_id!==worldId||result.receipt.encounter_id!==result.encounter.encounter_id))throw new Error('Encounter belongs to another scene');
 }
 useEffect(()=>{const generation=++epoch.current;setBusy(true);
  try{const raw=localStorage.getItem(key);if(raw){const request=JSON.parse(raw) as MaterializeRequest;if(request.schema_version!=='dmb_scene_encounter_materialize_v1'||!request.operation_id||!request.template)throw new Error('Stored encounter intent is invalid. It has been preserved.');setPending(request);setMessage('A creation is retained. Check, retry or cancel its exact request.');setBusy(false);return()=>{epoch.current++;};}}
  catch(error){setFatal(true);setMessage(String(error));setBusy(false);return()=>{epoch.current++;};}
  readRunEncounter(worldId,context).then(async result=>{if(epoch.current!==generation)return;
   if(result){if(result.encounter.world_id!==worldId||result.receipt.encounter_id!==result.encounter.encounter_id||result.receipt.intent.world_id!==worldId||result.receipt.intent.run_id!==runId||result.receipt.intent.scene_id!==sceneId)throw new Error('Saved encounter belongs to another session scene');setCurrent(result);return;}
   const proposed=await previewRunEncounter(worldId,context);if(epoch.current!==generation)return;
   if(proposed.world_id!==worldId||proposed.run_id!==runId||proposed.scene_id!==sceneId)throw new Error('Preparation belongs to another session scene');setPreview(proposed);
  }).catch(error=>{if(epoch.current===generation)setMessage(String(error));}).finally(()=>{if(epoch.current===generation)setBusy(false);});
  return()=>{epoch.current++;};
 },[key]);
 async function submit(request:MaterializeRequest,action:''|'/cancel'|'/inspect'=''){
  const generation=++epoch.current;setBusy(true);setMessage('Checking encounter creation…');
  try{
   const retained=localStorage.getItem(key);if(!retained||exactIntent(JSON.parse(retained))!==exactIntent(request))throw new Error('Retained encounter intent changed; recovery is preserved');
   const result=await materializeRunEncounter(worldId,context,request,action);if(epoch.current!==generation)return;
   if(!result){setMessage('No terminal result yet. Retry or cancel this same retained request.');return;}
   verify(result,request);await withIntentLock(key,()=>{const raw=localStorage.getItem(key);if(raw&&exactIntent(JSON.parse(raw))!==exactIntent(request))throw new Error('Retained encounter changed; recovery is preserved');localStorage.removeItem(key);});if(epoch.current!==generation)return;setPending(null);
   if(result.state==='applied'){setCurrent(result);setMessage('');}else{setMessage('Encounter creation canceled.');}
  }catch(error){if(epoch.current===generation)setMessage(`${String(error)} The creation intent remains retained.`);}
  finally{if(epoch.current===generation)setBusy(false);}
 }
 async function start(){if(!preview)return;const generation=epoch.current;try{
  const request:MaterializeRequest={schema_version:'dmb_scene_encounter_materialize_v1',operation_id:crypto.randomUUID(),expected_preparation_digest:preview.preparation_digest,template:preview.template,initialization_policy:preview.initialization_policy,preview_digest:preview.preview_digest};
  await withIntentLock(key,()=>{if(epoch.current!==generation)throw new Error('Scene changed before encounter creation');if(localStorage.getItem(key))throw new Error('Resolve the retained scene creation first');localStorage.setItem(key,JSON.stringify(request));});
  if(epoch.current!==generation)return;setPending(request);void submit(request);
 }catch(error){if(epoch.current===generation)setMessage(String(error));}}

 if(current)return <CombatRosterModule scope={{worldId,encounterId:current.encounter.encounter_id,label:context.sceneTitle,initialRecord:current.encounter,runScope:{runId,sceneId}}}/>;
 return <section aria-label="Scene encounter"><h3>{context.sceneTitle}</h3>{message&&<p role="status">{message}</p>}{busy&&<p>Loading encounter…</p>}
 {pending?<><button disabled={busy||fatal} onClick={()=>void submit(pending,'/inspect')}>Check creation</button><button disabled={busy||fatal||context.readOnly} onClick={()=>void submit(pending)}>Retry creation</button><button disabled={busy||fatal} onClick={()=>void submit(pending,'/cancel')}>Cancel creation</button></>:preview&&<>
 <h4>{preview.title}</h4><p>This starts a separate encounter from the preparation captured when this session began.</p>
 <ul>{preview.actors.map(actor=><li key={actor.actor_id}><strong>{actor.name}</strong> · HP {String(actor.hp_before??'unset')} → {String(actor.hp_after??'unset')}{!actor.typed_maximum?' (no numeric maximum; current HP kept)':''} · temporary HP {actor.temp_hp_before} → 0 · conditions {actor.conditions_before.join(', ') || 'none'} → none · undefeated</li>)}</ul>
 <p>Start at round 1 with no active turn. Names, initiative, notes, groups and saved mechanics are kept.</p>
 <button disabled={busy||fatal||context.readOnly} onClick={start}>Start this encounter</button>{context.readOnly&&<p>Reopen the session to start its encounter.</p>}</>}
 </section>;
}
