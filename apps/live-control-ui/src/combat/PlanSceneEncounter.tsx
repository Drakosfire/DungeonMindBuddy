import {useGuidedTour,type TourDispatchScope} from '../guidedTour/GuidedTour';
import {TourEncounterProvider} from '../guidedTour/EncounterScope';
import {planPin} from '../guidedTour/ownerPins';
import {EncounterTourObservation} from '../guidedTour/OwnerObservations';
import {CombatMechanicsInspection} from './CombatMechanicsInspection';
import {useCallback,useEffect,useRef,useState} from 'react';
import {getWorldOwnedPlanCommittedRevision} from '../api/liveApi';
import {combatDraftEqual} from './combatRecovery';
import {listAnyWorldCombatEncounters} from './combatApi';
import {sameEncounterScope} from '../guidedTour/EncounterScope';
import {CombatRosterModule,type PreparedCombatOwnerReading} from '../surface/modules/CombatRosterModule';
import {assertSceneCreation,assertSceneTemplate,cancelSceneTemplateCreation,sceneCreationDigest,createSceneTemplate,getSceneTemplate,getSceneTemplateVersion,inspectSceneTemplateCreation,type PlanEncounterContext,type SavedEncounterCopy,type SceneTemplateIntent,type SceneTemplateView} from './sceneTemplatesApi';
import type {AnyCombatRecord,ManualCombatProfile} from './ManualCombatTypes';
import {isManualCombatRecord} from './ManualCombatTypes';
import {ManualCombatProfileForm} from './ManualCombatProfileForm';

function recoveryKey(context:PlanEncounterContext){return `dmb-scene-template-create-v1:${context.worldId}:${context.documentId}:${context.sceneId}`;}
function defaultTitle(sceneTitle:string){return Array.from(`${sceneTitle} encounter`.trim()).slice(0,160).join('');}
function hasValidEncounterIntent(intent: SceneTemplateIntent): boolean {
 const encounter = intent.encounter;
 if (!encounter) return false;
 if ('source_encounter_id' in encounter) {
  return encounter.schema_version === 'dmb_scene_template_copy_saved_v1'
   && /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(encounter.source_encounter_id)
   && Number.isSafeInteger(encounter.expected_revision) && encounter.expected_revision > 0;
 }
 return typeof encounter.title === 'string';
}

export function PlanSceneEncounter({context}:{context:PlanEncounterContext}){
 const guidance=useGuidedTour();
 const [tourDispatchScope,setTourDispatchScope]=useState<TourDispatchScope|null>(null);
 const latest=useRef(context);latest.current=context;
 const epoch=useRef(0);
 const [view,setView]=useState<SceneTemplateView|null>(null);
 const [acknowledgedOperation,setAcknowledgedOperation]=useState<string|null>(null);
 const [recoveryInvalid,setRecoveryInvalid]=useState(false);
 const [pending,setPending]=useState<SceneTemplateIntent|null>(null);
 const [busy,setBusy]=useState(false);
 const [loaded,setLoaded]=useState(false);
 const [error,setError]=useState<string|null>(null);
 const [historical,setHistorical]=useState<AnyCombatRecord|null>(null);
 const [copySources,setCopySources]=useState<AnyCombatRecord[]|null>(null);
 const [copySourceId,setCopySourceId]=useState('');
 const copySource=copySources?.find(source=>source.encounter_id===copySourceId);
 const [title,setTitle]=useState(defaultTitle(context.sceneTitle));
 const identity=JSON.stringify([context.worldId,context.documentId,context.sceneId,context.objectRevision,context.contentSha256,context.verifiedPlan??null]);
 const [admittedIdentity,setAdmittedIdentity]=useState<string|null>(null);
 const [roster,setRoster]=useState<PreparedCombatOwnerReading|null>(null);
 const receiveRoster=useCallback((reading:PreparedCombatOwnerReading|null)=>setRoster(reading),[]);
 function accept(result:SceneTemplateView){assertSceneTemplate(result,context);setView(result);setAdmittedIdentity(identity);}
 useEffect(()=>{
  const current=++epoch.current;setView(null);setAdmittedIdentity(null);setRoster(null);setAcknowledgedOperation(null);setPending(null);setRecoveryInvalid(false);setLoaded(false);setHistorical(null);setError(null);setBusy(false);setCopySources(null);setCopySourceId('');setTitle(defaultTitle(context.sceneTitle));
  void (async()=>{
   try{
    const retained=sessionStorage.getItem(recoveryKey(context));
    if(retained){
     let intent:SceneTemplateIntent;
     try {intent=JSON.parse(retained) as SceneTemplateIntent;
     if(intent.schema_version!=='dmb_scene_template_create_v1'||intent.pin.document_id!==context.documentId||intent.pin.scene_id!==context.sceneId||!intent.operation_id||!hasValidEncounterIntent(intent)||!intent.pin.work_revision_id||!intent.pin.content_sha256||!Number.isInteger(intent.pin.revision_n))throw new Error('Retained encounter intent is invalid; it has been preserved.');
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
 async function loadCopySources(){
  if(busy||!latest.current.canCreate)return;
  const current=epoch.current;setBusy(true);setError(null);setCopySourceId('');
  try{
   const sources=await listAnyWorldCombatEncounters(context.worldId);
   if(current===epoch.current)setCopySources(sources.filter(source=>source.world_id===context.worldId));
  }catch(caught){if(current===epoch.current)setError(String(caught));}
  finally{if(current===epoch.current)setBusy(false);}
 }

 async function create(retry=false,manual?:{title:string;profile:ManualCombatProfile},copy?:SavedEncounterCopy){
  const tourDispatch=guidance?.captureScope()??null;
  if(busy||(!retry&&!latest.current.canCreate))return;
  const current=epoch.current;setBusy(true);setError(null);
  try{
   let intent=pending;
   if(!intent){
    const encounterTitle=(manual?.title??title).trim();
    if(!copy&&(!encounterTitle||Array.from(encounterTitle).length>160))throw new Error('Enter an encounter name of 1–160 characters before preparing it.');
    const committed=await getWorldOwnedPlanCommittedRevision(context.documentId);
    const now=latest.current;
    if(current!==epoch.current)return;
    if(!now.canCreate||committed.schema_version!=='dmb_workspace_committed_revision_v2'||committed.scope_mode!=='world'||committed.world_id!==context.worldId||committed.document_id!==context.documentId||committed.kind!=='plan'||committed.status!=='active'||committed.has_divergent_working_copy||committed.object_revision!==now.objectRevision||committed.content_sha256!==now.contentSha256)throw new Error('Save and reopen this Plan before preparing its encounter.');
    intent={schema_version:'dmb_scene_template_create_v1',operation_id:crypto.randomUUID(),pin:{document_id:context.documentId,scene_id:context.sceneId,revision_n:committed.revision_n,work_revision_id:committed.work_revision_id,content_sha256:committed.content_sha256},encounter:copy??(manual?{schema_version:'dmb_manual_combat_create_v2',title:encounterTitle,profile:manual.profile}:{title:encounterTitle})};
    sessionStorage.setItem(recoveryKey(context),JSON.stringify(intent));setPending(intent);
   }
   const result=await createSceneTemplate(context.worldId,intent);
   if(current!==epoch.current)return;
   await assertSceneCreation(result,context,intent);
   if(current!==epoch.current)return;
   sessionStorage.removeItem(recoveryKey(context));setPending(null);setTourDispatchScope(tourDispatch);setAcknowledgedOperation(result.binding.operation_id);accept(result);setLoaded(true);
  }catch(caught){if(current===epoch.current)setError(String(caught));}
  finally{if(current===epoch.current)setBusy(false);}
 }
 async function inspect(){
  const tourDispatch=guidance?.captureScope()??null;
  if(!pending||busy)return;
  const current=epoch.current;setBusy(true);setError(null);
  try{
   const result=await inspectSceneTemplateCreation(context.worldId,pending.operation_id);
   if(current!==epoch.current)return;
   if(!result){setError('Creation is not acknowledged yet. The original request is retained; retry it explicitly.');return;}
   await assertSceneCreation(result,context,pending);
   if(current!==epoch.current)return;
   sessionStorage.removeItem(recoveryKey(context));setPending(null);setTourDispatchScope(tourDispatch);setAcknowledgedOperation(result.binding.operation_id);accept(result);setLoaded(true);
  }catch(caught){if(current===epoch.current)setError(String(caught));}
  finally{if(current===epoch.current)setBusy(false);}
 }
 async function cancel(){
  const tourDispatch=guidance?.captureScope()??null;
  if(!pending||busy)return;
  const current=epoch.current;setBusy(true);setError(null);
  try{
   const result=await cancelSceneTemplateCreation(context.worldId,pending);
   if(current!==epoch.current)return;
   if(result.state==='applied'){await assertSceneCreation(result.view,context,pending);if(current!==epoch.current)return;setTourDispatchScope(tourDispatch);setAcknowledgedOperation(result.view.binding.operation_id);accept(result.view);}
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
 const currentView=admittedIdentity===identity?view:null;
 const verifiedPin=context.canCreate&&context.verifiedPlan?.contentSha256===context.contentSha256?context.verifiedPlan:null;
 const tourEncounter=currentView?.scene_present&&verifiedPin?{plan:planPin(context.worldId,context.documentId,verifiedPin),sceneId:context.sceneId,encounterId:currentView.binding.encounter_id}:null;
 // Read once after an admitted roster Save to pair that exact record with
 // its server version digest. Never repeat a Save or poll for changes.
 const saved=roster?.acknowledged;
 const manualCommitted=roster?.record&&isManualCombatRecord(roster.record)?roster.record:null;
 const committedForVersion=manualCommitted??(saved&&sameEncounterScope(tourEncounter,saved.scope)?saved.saved:null);
 const needsVersion=!!currentView&&!!committedForVersion&&!roster?.blocked&&!roster?.error&&roster?.record?.revision===committedForVersion.revision&&committedForVersion.revision>currentView.encounter.revision;
 useEffect(()=>{
  if(!needsVersion||!committedForVersion)return;
  let active=true;const current=epoch.current;
  void getSceneTemplate(context).then(result=>{
   if(!active||current!==epoch.current||!result)return;
   assertSceneTemplate(result,context);
   if(result.encounter.revision!==committedForVersion.revision||!combatDraftEqual(result.encounter.draft,committedForVersion.draft))throw new Error('Prepared version differs from the acknowledged Save.');
   accept(result);
  }).catch(caught=>{if(active&&current===epoch.current)setError(String(caught));});
  return()=>{active=false;};
 },[needsVersion,committedForVersion,identity]);
 return <section aria-label={`Encounter preparation for ${context.sceneTitle}`}>
  <EncounterTourObservation view={currentView} context={context} roster={roster} acknowledgedOperation={acknowledgedOperation} dispatchScope={tourDispatchScope} error={error} pending={!!pending||busy||admittedIdentity!==identity}/>
  <h2 data-guided-control="encounter" data-guided-control-group="true" tabIndex={-1}>{context.sceneTitle} · Encounter</h2>
  <p>Prepare this scene’s enemies here. Saved versions stay with the Plan.</p>
  {error&&<p role="alert">{error}</p>}{!loaded&&error&&!recoveryInvalid&&<button disabled={busy} onClick={()=>void refresh()}>Retry opening encounter</button>}
  {pending&&<section aria-label="Encounter creation recovery"><p>Creation outcome is unconfirmed. Its exact request is retained.</p><button disabled={busy} onClick={()=>void inspect()}>Check creation</button><button disabled={busy} onClick={()=>void create(true)}>Retry same creation</button><button disabled={busy} onClick={()=>void cancel()}>Cancel creation</button>{view&&view.binding.operation_id!==pending.operation_id&&<button disabled={busy} onClick={()=>{sessionStorage.removeItem(recoveryKey(context));setPending(null);}}>Open existing scene encounter</button>}</section>}
  {!loaded&&!error&&<p>Opening scene encounter…</p>}
  {loaded&&!view&&!pending&&!recoveryInvalid&&<><label>Encounter name<input aria-label="Prepared encounter name" maxLength={160} value={title} onChange={event=>setTitle(event.target.value)}/></label><button disabled={busy||!context.canCreate||!title.trim()} onClick={()=>void create()}>Prepare encounter</button>{!context.canCreate&&<p>Save the Plan before creating its encounter. Your Plan draft is retained.</p>}</>}
  {loaded&&!view&&!pending&&!recoveryInvalid&&<ManualCombatProfileForm disabled={busy||!context.canCreate} onCreate={(title,profile)=>create(false,{title,profile})}/>}
  {loaded&&!view&&!pending&&!recoveryInvalid&&<section aria-label="Prepare from saved Combat">
   <button type="button" disabled={busy||!context.canCreate} onClick={()=>void loadCopySources()}>
    {copySources?'Refresh saved encounters':'Choose a saved encounter'}
   </button>
   {copySources?.length===0&&<p>No saved standalone encounters in this World.</p>}
   {!!copySources?.length&&<label>Saved encounter
    <select value={copySourceId} disabled={busy||!context.canCreate} onChange={event=>setCopySourceId(event.target.value)}>
     <option value="">Select an encounter</option>
     {copySources.map(source=><option key={source.encounter_id} value={source.encounter_id}>{source.draft.title} · revision {source.revision}</option>)}
    </select>
   </label>}
   {copySource&&<section aria-label="Saved encounter preview">
    <h3>{copySource.draft.title} · revision {copySource.revision}</h3>
    <p>Copy to {context.sceneTitle} with {copySource.draft.entities.length} combatants and {copySource.draft.groups.length} groups.</p>
    <ul>{copySource.draft.entities.map(actor=><li key={actor.id}>{actor.name}</li>)}</ul>
    <button type="button" disabled={busy||!context.canCreate} onClick={()=>void create(false,undefined,{
     schema_version:'dmb_scene_template_copy_saved_v1',source_encounter_id:copySource.encounter_id,expected_revision:copySource.revision,
    })}>Confirm encounter copy</button>
   </section>}
  </section>}
  {view&&!pending&&<>
   {!view.scene_present&&<p role="status">This scene is absent from the saved Plan. Encounter work is retained.</p>}
   <details><summary>Prepared versions</summary><button disabled={busy} onClick={()=>void refresh()}>Refresh prepared versions</button>{view.versions.map(version=><button key={version.revision} disabled={busy} onClick={()=>void history(version.revision)}>Inspect version {version.revision}</button>)}{historical&&<section aria-label="Saved prepared version"><h3>{historical.draft.title} · version {historical.revision}</h3><ul>{historical.draft.entities.map(actor=><li key={actor.id}>{actor.name}{'values' in actor?<> · {actor.participation==='in_action'?'In action':'Out of action'} · {Object.values(actor.values.stats).map(value=>value??'—').join(' · ')}</>:<> · AC {actor.ac??'—'} · HP {actor.hp??'—'}/{actor.max_hp??'—'}</>}{actor.mechanics_snapshot&&<CombatMechanicsInspection snapshot={actor.mechanics_snapshot}/>}</li>)}</ul><p>Saved version · read only</p></section>}</details>
   <TourEncounterProvider scope={tourEncounter}><CombatRosterModule key={view.binding.encounter_id} scope={{worldId:context.worldId,encounterId:view.binding.encounter_id,initialRecord:view.encounter,onPreparedState:receiveRoster,label:`${context.sceneTitle} · prepared encounter`}}/></TourEncounterProvider>
  </>}
 </section>;
}
