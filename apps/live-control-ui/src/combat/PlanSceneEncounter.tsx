import {EncounterTourObservation} from '../guidedTour/OwnerObservations';
import {CombatMechanicsInspection} from './CombatMechanicsInspection';
import {useEffect,useRef,useState} from 'react';
import {getWorldOwnedPlanCommittedRevision} from '../api/liveApi';
import {CombatRosterModule} from '../surface/modules/CombatRosterModule';
import {assertSceneCreation,assertSceneTemplate,cancelSceneTemplateCreation,sceneCreationDigest,createSceneTemplate,getSceneTemplate,getSceneTemplateVersion,inspectSceneTemplateCreation,type PlanEncounterContext,type SceneTemplateIntent,type SceneTemplateView} from './sceneTemplatesApi';
import type {CombatEncounterRecord} from './combatTypes';

function recoveryKey(context:PlanEncounterContext){return `dmb-scene-template-create-v1:${context.worldId}:${context.documentId}:${context.sceneId}`;}
function defaultTitle(sceneTitle:string){return Array.from(`${sceneTitle} encounter`.trim()).slice(0,160).join('');}
export function PlanSceneEncounter({context}:{context:PlanEncounterContext}){
 const latest=useRef(context);latest.current=context;
 const epoch=useRef(0);
 const [view,setView]=useState<SceneTemplateView|null>(null);
 const [acknowledgedOperation,setAcknowledgedOperation]=useState<string|null>(null);
 const [recoveryInvalid,setRecoveryInvalid]=useState(false);
 const [pending,setPending]=useState<SceneTemplateIntent|null>(null);
 const [busy,setBusy]=useState(false);
 const [loaded,setLoaded]=useState(false);
 const [error,setError]=useState<string|null>(null);
 const [historical,setHistorical]=useState<CombatEncounterRecord|null>(null);
 const [title,setTitle]=useState(defaultTitle(context.sceneTitle));
 const identity=`${context.worldId}:${context.documentId}:${context.sceneId}`;
 function accept(result:SceneTemplateView){assertSceneTemplate(result,context);setView(result);}
 useEffect(()=>{
  const current=++epoch.current;setView(null);setAcknowledgedOperation(null);setPending(null);setRecoveryInvalid(false);setLoaded(false);setHistorical(null);setError(null);setBusy(false);setTitle(defaultTitle(context.sceneTitle));
  void (async()=>{
   try{
    const retained=sessionStorage.getItem(recoveryKey(context));
    if(retained){
     let intent:SceneTemplateIntent;
     try {intent=JSON.parse(retained) as SceneTemplateIntent;
     if(intent.schema_version!=='dmb_scene_template_create_v1'||intent.pin.document_id!==context.documentId||intent.pin.scene_id!==context.sceneId||!intent.operation_id||typeof intent.encounter?.title!=='string'||!intent.pin.work_revision_id||!intent.pin.content_sha256||!Number.isInteger(intent.pin.revision_n))throw new Error('Retained encounter intent is invalid; it has been preserved.');
     }catch(caught){if(current===epoch.current)setRecoveryInvalid(true);throw caught;}
     if(current===epoch.current)setPending(intent);
    }
    const result=await getSceneTemplate(context);
    if(current!==epoch.current)return;
    if(result)accept(result);
    setLoaded(true);
   }catch(caught){if(current===epoch.current)setError(String(caught));}
  })();
  return()=>{epoch.current++;};
 },[identity]);
 async function create(retry=false){
  if(busy||(!retry&&!latest.current.canCreate))return;
  const current=epoch.current;setBusy(true);setError(null);
  try{
   let intent=pending;
   if(!intent){
    const encounterTitle=title.trim();
    if(!encounterTitle||Array.from(encounterTitle).length>160)throw new Error('Enter an encounter name of 1–160 characters before preparing it.');
    const committed=await getWorldOwnedPlanCommittedRevision(context.documentId);
    const now=latest.current;
    if(current!==epoch.current)return;
    if(!now.canCreate||committed.schema_version!=='dmb_workspace_committed_revision_v2'||committed.scope_mode!=='world'||committed.world_id!==context.worldId||committed.document_id!==context.documentId||committed.kind!=='plan'||committed.status!=='active'||committed.has_divergent_working_copy||committed.object_revision!==now.objectRevision||committed.content_sha256!==now.contentSha256)throw new Error('Save and reopen this Plan before preparing its encounter.');
    intent={schema_version:'dmb_scene_template_create_v1',operation_id:crypto.randomUUID(),pin:{document_id:context.documentId,scene_id:context.sceneId,revision_n:committed.revision_n,work_revision_id:committed.work_revision_id,content_sha256:committed.content_sha256},encounter:{title:encounterTitle}};
    sessionStorage.setItem(recoveryKey(context),JSON.stringify(intent));setPending(intent);
   }
   const result=await createSceneTemplate(context.worldId,intent);
   if(current!==epoch.current)return;
   await assertSceneCreation(result,context,intent);
   if(current!==epoch.current)return;
   sessionStorage.removeItem(recoveryKey(context));setPending(null);setAcknowledgedOperation(result.binding.operation_id);accept(result);setLoaded(true);
  }catch(caught){if(current===epoch.current)setError(String(caught));}
  finally{if(current===epoch.current)setBusy(false);}
 }
 async function inspect(){
  if(!pending||busy)return;
  const current=epoch.current;setBusy(true);setError(null);
  try{
   const result=await inspectSceneTemplateCreation(context.worldId,pending.operation_id);
   if(current!==epoch.current)return;
   if(!result){setError('Creation is not acknowledged yet. The original request is retained; retry it explicitly.');return;}
   await assertSceneCreation(result,context,pending);
   if(current!==epoch.current)return;
   sessionStorage.removeItem(recoveryKey(context));setPending(null);setAcknowledgedOperation(result.binding.operation_id);accept(result);setLoaded(true);
  }catch(caught){if(current===epoch.current)setError(String(caught));}
  finally{if(current===epoch.current)setBusy(false);}
 }
 async function cancel(){
  if(!pending||busy)return;
  const current=epoch.current;setBusy(true);setError(null);
  try{
   const result=await cancelSceneTemplateCreation(context.worldId,pending);
   if(current!==epoch.current)return;
   if(result.state==='applied'){await assertSceneCreation(result.view,context,pending);if(current!==epoch.current)return;setAcknowledgedOperation(result.view.binding.operation_id);accept(result.view);}
   else if(result.state!=='canceled'||result.operation_id!==pending.operation_id||result.world_id!==context.worldId||result.request_digest!==await sceneCreationDigest(context.worldId,pending))throw new Error('Cancellation acknowledgement differs from retained intent.');
   if(current!==epoch.current)return;
   sessionStorage.removeItem(recoveryKey(context));setPending(null);setLoaded(true);
  }catch(caught){if(current===epoch.current)setError(String(caught));}
  finally{if(current===epoch.current)setBusy(false);}
 }
 async function history(revision:number){
  const current=epoch.current;setBusy(true);setError(null);
  try{const record=await getSceneTemplateVersion(context,revision);if(current!==epoch.current)return;if(record.world_id!==context.worldId||record.encounter_id!==view?.binding.encounter_id||record.revision!==revision)throw new Error('Prepared version differs from selected encounter.');setHistorical(record);}
  catch(caught){if(current===epoch.current)setError(String(caught));}
  finally{if(current===epoch.current)setBusy(false);}
 }
 async function refresh(){const current=epoch.current;setBusy(true);setError(null);try{const result=await getSceneTemplate(context);if(current===epoch.current){if(result)accept(result);setLoaded(true);}}catch(caught){if(current===epoch.current)setError(String(caught));}finally{if(current===epoch.current)setBusy(false);}}
 return <section data-guided-control="encounter" tabIndex={-1} aria-label={`Encounter preparation for ${context.sceneTitle}`}>
  <EncounterTourObservation view={view} context={context} acknowledgedOperation={acknowledgedOperation} error={error} pending={!!pending||busy}/>
  <h2>{context.sceneTitle} · Encounter</h2>
  <p>Prepare this scene’s enemies here. Saved versions stay with the Plan.</p>
  {error&&<p role="alert">{error}</p>}{!loaded&&error&&!recoveryInvalid&&<button disabled={busy} onClick={()=>void refresh()}>Retry opening encounter</button>}
  {pending&&<section aria-label="Encounter creation recovery"><p>Creation outcome is unconfirmed. Its exact request is retained.</p><button disabled={busy} onClick={()=>void inspect()}>Check creation</button><button disabled={busy} onClick={()=>void create(true)}>Retry same creation</button><button disabled={busy} onClick={()=>void cancel()}>Cancel creation</button>{view&&view.binding.operation_id!==pending.operation_id&&<button disabled={busy} onClick={()=>{sessionStorage.removeItem(recoveryKey(context));setPending(null);}}>Open existing scene encounter</button>}</section>}
  {!loaded&&!error&&<p>Opening scene encounter…</p>}
  {loaded&&!view&&!pending&&!recoveryInvalid&&<><label>Encounter name<input aria-label="Prepared encounter name" maxLength={160} value={title} onChange={event=>setTitle(event.target.value)}/></label><button disabled={busy||!context.canCreate||!title.trim()} onClick={()=>void create()}>Prepare encounter</button>{!context.canCreate&&<p>Save the Plan before creating its encounter. Your Plan draft is retained.</p>}</>}
  {view&&!pending&&<>
   {!view.scene_present&&<p role="status">This scene is absent from the saved Plan. Encounter work is retained.</p>}
   <details><summary>Prepared versions</summary><button disabled={busy} onClick={()=>void refresh()}>Refresh prepared versions</button>{view.versions.map(version=><button key={version.revision} disabled={busy} onClick={()=>void history(version.revision)}>Inspect version {version.revision}</button>)}{historical&&<section aria-label="Saved prepared version"><h3>{historical.draft.title} · version {historical.revision}</h3><ul>{historical.draft.entities.map(actor=><li key={actor.id}>{actor.name} · AC {actor.ac??'—'} · HP {actor.hp??'—'}/{actor.max_hp??'—'}{actor.mechanics_snapshot&&<CombatMechanicsInspection snapshot={actor.mechanics_snapshot}/>}</li>)}</ul><p>Saved version · read only</p></section>}</details>
   <CombatRosterModule key={view.binding.encounter_id} scope={{worldId:context.worldId,encounterId:view.binding.encounter_id,initialRecord:view.encounter,label:`${context.sceneTitle} · prepared encounter`}}/>
  </>}
 </section>;
}
