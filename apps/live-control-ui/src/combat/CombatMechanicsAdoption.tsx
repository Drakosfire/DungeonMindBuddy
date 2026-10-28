import {useGuidedTour} from '../guidedTour/GuidedTour';
import {useTourEncounter,sameEncounterScope} from '../guidedTour/EncounterScope';
import {AdoptionTourObservation,type AcknowledgedMechanicsAdoption} from '../guidedTour/MechanicsObservations';
import {useEffect,useRef,useState} from 'react';
import {adoptCombatMechanics,listAcceptedCombatMechanics,previewSavedCombatMechanics} from './combatApi';
import {listSavedMechanicsVersions} from '../api/liveApi';
import type {AcceptedCombatMechanicsChoice,ActorMechanicsAdoption,CombatEncounterRecord,MechanicsAdoptionPreview} from './combatTypes';
import type {SavedMechanicsLocator} from '../statblocks/revision/savedMechanicsRevisionTypes';
import {SavedMechanicsRevisionEditor} from '../statblocks/revision/SavedMechanicsRevisionEditor';
import {CombatMechanicsInspection} from './CombatMechanicsInspection';
import {SavedAdoptionHistory} from './SavedAdoptionHistory';
import {readPendingAdoption,sameAdoptionValue,verifyAdoptionOutcome,type PendingMechanicsAdoption} from './CombatMechanicsAdoptionRecovery';

export function CombatMechanicsAdoption({record,disabled,onLockChange,onReconciled,scope}:{record:CombatEncounterRecord;disabled:boolean;scope?:import("./runEncountersApi").RunEncounterScope;
  onLockChange:(locked:boolean)=>void;onReconciled:(current:CombatEncounterRecord)=>void}) {
 const guidance=useGuidedTour();
  const tourScope=useTourEncounter(),latestTourScope=useRef(tourScope);latestTourScope.current=tourScope;
  const [tourAcknowledged,setTourAcknowledged]=useState<AcknowledgedMechanicsAdoption|null>(null);
  const [tourInspected,setTourInspected]=useState<AcknowledgedMechanicsAdoption|null>(null);
  const worldId=record.world_id,encounterId=record.encounter_id,epoch=useRef(0);
  const [writer]=useState(()=>{try{const key='dmb-combat-adoption-writer';let id=sessionStorage.getItem(key);if(!id){id=crypto.randomUUID();sessionStorage.setItem(key,id);}return id;}catch{return null;}});
  const storageKey=`dmb.combat.adoption:${JSON.stringify([writer,worldId,encounterId])}`;
  const [pending,setPending]=useState<PendingMechanicsAdoption|null>(null),[busy,setBusy]=useState(false),[fatal,setFatal]=useState(false);
  const [message,setMessage]=useState(''),[choices,setChoices]=useState<AcceptedCombatMechanicsChoice[]>([]),[next,setNext]=useState<number|null>(0);
  const [source,setSource]=useState<AcceptedCombatMechanicsChoice|null>(null);
  const [versions,setVersions]=useState<{label:string;locator:SavedMechanicsLocator}[]>([]),[nextVersion,setNextVersion]=useState<number|null>(null);
  const [selected,setSelected]=useState(''),[preview,setPreview]=useState<MechanicsAdoptionPreview|null>(null);
  const [actors,setActors]=useState<Record<string,ActorMechanicsAdoption>>({});
  useEffect(()=>{try{setPending(readPendingAdoption(localStorage.getItem(storageKey),worldId,encounterId));}catch(error){setFatal(true);setMessage(String(error));}
    return()=>{epoch.current++;};},[storageKey,worldId,encounterId]);
  useEffect(()=>{onLockChange(!!pending||busy||fatal);return()=>onLockChange(false);},[pending,busy,fatal,onLockChange]);
  const blocked=disabled||busy||!!pending||fatal;
  async function sources(offset=0){
    const token=++epoch.current;setBusy(true);setMessage('Loading saved creatures…');
    try{const page=await listAcceptedCombatMechanics(worldId,offset);if(token!==epoch.current)return;
      setChoices(old=>offset?[...old,...page.choices]:page.choices);setNext(page.nextOffset);setMessage('');}
    catch(error){if(token===epoch.current)setMessage(String(error));}finally{if(token===epoch.current)setBusy(false);}
  }
  async function loadVersions(choice:AcceptedCombatMechanicsChoice,offset=0){
    const token=++epoch.current;setBusy(true);setMessage('Loading saved versions…');
    try{const page=await listSavedMechanicsVersions(choice.draft_id,worldId,offset);if(token!==epoch.current)return;
      if(page.world_id!==worldId||page.draft_id!==choice.draft_id)throw new Error('Versions belong to another creature.');
      const saved=page.operations.filter(op=>op.state==='committed'&&op.result).map(op=>({label:op.change_summary,locator:op.result!}));
      setVersions(old=>offset?[...old,...saved]:[{label:'Original saved mechanics',locator:page.original},...saved]);
      setSource(choice);setNextVersion(page.next_offset);
      if(!offset){setSelected(page.original.revision_id);setPreview(null);setActors({});}setMessage('');}
    catch(error){if(token===epoch.current)setMessage(String(error));}finally{if(token===epoch.current)setBusy(false);}
  }
  async function openPreview(){
    const version=versions.find(v=>v.locator.revision_id===selected);if(!source||!version)return;
    const token=++epoch.current;setBusy(true);setMessage('Checking exact saved version…');
    try{const result=await previewSavedCombatMechanics(worldId,source.draft_id,version.locator);if(token!==epoch.current)return;
      if(result.snapshot.origin!=='buddy_saved_mechanics_override_v1'||result.snapshot.managed_world_id!==worldId
        ||result.snapshot.draft_id!==source.draft_id||!sameAdoptionValue(result.snapshot.locator,version.locator))throw new Error('Preview belongs to another version.');
      setPreview(result);setActors({});setMessage('Choose actors and tracker policies, then explicitly use this version.');}
    catch(error){if(token===epoch.current)setMessage(String(error));}finally{if(token===epoch.current)setBusy(false);}
  }
  async function submit(retained:PendingMechanicsAdoption,cancel=false){
    const token=++epoch.current,tourAtDispatch=tourScope,tourDispatch=guidance?.captureScope()??null;setBusy(true);setMessage(cancel?'Checking cancellation…':'Applying exact saved version…');
    try{
      const raw=localStorage.getItem(storageKey);
      if(!raw||!sameAdoptionValue(readPendingAdoption(raw,worldId,encounterId),retained))throw new Error('Pending adoption changed; its recovery is retained.');
      const result=await adoptCombatMechanics(worldId,encounterId,retained.request,cancel,...(scope?[scope] as const:[] as const));if(token!==epoch.current)return;
      await verifyAdoptionOutcome(retained,result);if(token!==epoch.current)return;
      onReconciled(result.encounter);
      if(localStorage.getItem(storageKey)!==raw)throw new Error('Pending adoption storage changed; inspect its outcome again.');
      localStorage.removeItem(storageKey);setPending(null);setPreview(null);setActors({});
      if(tourAtDispatch&&sameEncounterScope(tourAtDispatch,latestTourScope.current)){setTourInspected(null);setTourAcknowledged({dispatchScope:tourDispatch,scope:tourAtDispatch,outcome:result});}
      setMessage(result.receipt.state==='canceled'?'Pending adoption canceled before commit. Current encounter state loaded; this command changed no actors.':
        result.advanced_since_apply?'This adoption committed earlier. Newer encounter changes are loaded and preserved.':
          cancel?'This adoption already committed; Cancel did not undo it.':'Selected actors now use this exact version. Other actors and World associations are unchanged.');
    }catch(error){if(token===epoch.current)setMessage(`Outcome unconfirmed. Exact choices are retained. Retry or cancel this pending adoption. ${String(error)}`);}
    finally{if(token===epoch.current)setBusy(false);}
  }
  function begin(){
    if(blocked||!writer||!preview||!source||!Object.keys(actors).length)return;
    try{
      if(localStorage.getItem(storageKey))throw new Error('A pending adoption already exists; reopen its recovery.');
      const retained:PendingMechanicsAdoption={schema:'dmb_pending_combat_adoption_v1',worldId,encounterId,afterDigest:preview.snapshot.snapshot_digest,
        request:{schema:'dmb_combat_mechanics_adoption_request_v1',operation_id:crypto.randomUUID(),expected_revision:record.revision,
          draft_id:source.draft_id,locator:preview.snapshot.locator,actors:Object.values(actors)}};
      const raw=JSON.stringify(retained);localStorage.setItem(storageKey,raw);
      if(localStorage.getItem(storageKey)!==raw)throw new Error('Could not retain adoption choices. Nothing was sent.');
      setPending(retained);void submit(retained);
    }catch(error){setMessage(String(error));}
  }
  return <section data-guided-control="adoption" tabIndex={-1} aria-label="Use saved mechanics version">
    <AdoptionTourObservation scope={tourScope} worldId={worldId} encounterId={encounterId} acknowledged={tourAcknowledged} inspected={tourInspected} blocked={blocked}/>
    <h3>Use a saved mechanics version</h3>
    <p>Choose which existing actors use a version. This is an encounter override; World creature associations stay unchanged.</p>
    <SavedAdoptionHistory key={JSON.stringify([worldId,encounterId,scope??null,tourScope])} worldId={worldId} encounterId={encounterId} scope={scope} onInspected={outcome=>{
      if(tourScope&&sameEncounterScope(tourScope,latestTourScope.current))setTourInspected({scope:tourScope,outcome});
    }}/>
    {disabled&&!pending&&<p>Save or recover the encounter draft before changing its mechanics.</p>}
    {!writer&&<p>Browser recovery is unavailable. Adoption is disabled.</p>}
    <fieldset disabled={blocked}>
      <button type="button" onClick={()=>void sources()}>Find saved creatures</button>
      {choices.map(choice=><button type="button" key={choice.draft_id} onClick={()=>void loadVersions(choice)}>{choice.name}</button>)}
      {next!==null&&choices.length>0&&<button type="button" onClick={()=>void sources(next)}>More saved creatures</button>}
      {source&&<>
        <label>Saved version <select aria-label="Version to use in encounter" value={selected} onChange={event=>{setSelected(event.target.value);setPreview(null);setActors({});}}>
          {versions.map((version,index)=><option key={version.locator.revision_id} value={version.locator.revision_id}>{index+1}. {version.label}</option>)}
        </select></label>
        <button type="button" onClick={()=>void loadVersions(source)}>Refresh versions</button>
        {nextVersion!==null&&<button type="button" onClick={()=>void loadVersions(source,nextVersion)}>More versions</button>}
        <button type="button" onClick={()=>void openPreview()}>Preview exact version</button>
      </>}
    </fieldset>
    {source&&!pending&&<details><summary>Edit saved mechanics separately</summary>
      <SavedMechanicsRevisionEditor key={source.draft_id} worldId={worldId} draftId={source.draft_id}/>
      <p>After saving, refresh versions above and preview the version you want to use.</p>
    </details>}
    {preview&&<>
      <CombatMechanicsInspection snapshot={preview.snapshot}/>
      <p>Saved AC: {preview.armor_class??'unavailable'} · Maximum HP: {preview.hit_points??'unavailable'}</p>
      <p>Keep preserves tracker values. Preserve current HP can leave it above the new maximum. Clamp uses the lower value. Reset heals to full but keeps defeated status, conditions and temporary HP.</p>
      <fieldset disabled={blocked}>
        {record.draft.entities.map((actor,index)=>{
          const compatible=actor.mechanics_snapshot?.locator.statblock_id===preview.snapshot.locator.statblock_id;
          const choice=actors[actor.id],label=`${actor.name} (${index+1})`;
          return <div key={actor.id}>
            <label><input type="checkbox" aria-label={`Select ${label}`} disabled={!compatible}
              checked={!!choice} onChange={event=>setActors(old=>{const next={...old};if(event.target.checked)next[actor.id]={actor_id:actor.id,
                expected_snapshot_digest:actor.mechanics_snapshot!.snapshot_digest,ac_policy:'keep',hp_policy:'keep'};else delete next[actor.id];return next;})}/>{label}</label>
            {!compatible&&<span> — Different or missing source mechanics</span>}
            {choice&&<>
              <label>AC {String(actor.ac??'unset')} → {choice.ac_policy==='keep'?String(actor.ac??'unset'):preview.armor_class}
                <select aria-label={`AC policy for ${label}`} value={choice.ac_policy} onChange={event=>setActors(old=>({...old,[actor.id]:{...choice,ac_policy:event.target.value as ActorMechanicsAdoption['ac_policy']}}))}>
                  <option value="keep">Keep tracked AC</option><option value="use_saved" disabled={preview.armor_class===null}>Use saved AC</option>
                </select></label>
              <label>HP {String(actor.hp??'unset')} / {String(actor.max_hp??'unset')}
                <select aria-label={`HP policy for ${label}`} value={choice.hp_policy} onChange={event=>setActors(old=>({...old,[actor.id]:{...choice,hp_policy:event.target.value as ActorMechanicsAdoption['hp_policy']}}))}>
                  <option value="keep">Keep current and maximum HP</option>
                  <option value="preserve_current" disabled={preview.hit_points===null}>Use saved maximum; preserve current HP</option>
                  <option value="clamp_current" disabled={preview.hit_points===null||typeof actor.hp!=='number'}>Use saved maximum; clamp current HP</option>
                  <option value="reset_full" disabled={preview.hit_points===null}>Use saved maximum; reset to full HP</option>
                </select></label>
              <p>After: HP {choice.hp_policy==='reset_full'?preview.hit_points:choice.hp_policy==='clamp_current'?Math.min(actor.hp as number,preview.hit_points!):String(actor.hp??'unset')} / {choice.hp_policy==='keep'?String(actor.max_hp??'unset'):preview.hit_points}. Temporary HP {actor.temp_hp}; {actor.defeated?'defeated status remains set':'defeated status unchanged'}.</p>
            </>}
          </div>;
        })}
        <button type="button" disabled={!writer||!Object.keys(actors).length} onClick={begin}>Use version for selected actors</button>
      </fieldset>
    </>}
    {pending&&<div aria-label="Pending mechanics adoption"><p>Exact adoption choices are retained. Cancel only stops an unapplied command; it cannot undo a committed adoption.</p>
      <button type="button" disabled={busy||disabled} onClick={()=>void submit(pending)}>Retry original adoption</button>
      <button type="button" disabled={busy||disabled} onClick={()=>void submit(pending,true)}>Cancel pending adoption</button>
    </div>}
    {message&&<p role="status">{message}</p>}
  </section>;
}
