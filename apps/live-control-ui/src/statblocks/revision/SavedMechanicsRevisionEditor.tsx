import {WorldMechanicsAssociationPanel} from '../WorldMechanicsAssociationPanel';
import {interceptPrimaryNavigationClick} from '../../chrome/appNavigation';
import {savedStatblockHref} from '../savedStatblockLocation';
import {MediaImageWizard} from '../../media/MediaImageWizard';
import {SavedMediaImage} from '../../media/SavedMediaImage';
import {MEDIA_ASSET_ID} from '../../media/mediaReferences';
import './SavedMechanicsRevisionEditor.css';
import {useGenerationPlan} from '../../guidedTour/GenerationObservations';
import type {GeneratedMechanicsScope} from '../../guidedTour/protocol';
import {useTourNavigationGuard} from '../../guidedTour/Navigation';
import {useGuidedTour,type TourDispatchScope} from '../../guidedTour/GuidedTour';
import {useTourEncounter,sameEncounterScope,type TourEncounterScope} from '../../guidedTour/EncounterScope';
import {MechanicsTourObservation,GeneratedMechanicsTourObservation,sameGeneratedMechanicsScope,type AcknowledgedGeneratedMechanicsSave,sameMechanicsLocator,type AcknowledgedMechanicsSave} from '../../guidedTour/MechanicsObservations';
import {useEffect,useLayoutEffect,useRef,useState} from 'react';
import {listSavedMechanicsVersions,openSavedMechanicsVersion,saveMechanicsRevision,recoverMechanicsRevision,inspectMechanicsRevision,validateStatblockDefinition} from '../../api/liveApi';
import {StatblockDefinitionEditor} from '../editor/StatblockDefinitionEditor';
import {StatblockRenderer} from '../render/StatblockRenderer';
import {createEditorStateFromOutput,fingerprintDefinition,type StatblockEditorState} from '../editor/statblockEditorState';
import type {ValidationIssueV1} from '../../contracts/dungeonbuddy-statblocks-v1/client';
import type {SavedMechanicsVersionList,OpenSavedMechanicsVersion,RevisionSaveOutcome} from './savedMechanicsRevisionTypes';

// Local recovery retains only this editor's scalar edits; it never grants Save
// authority. The server separately proves exact source and operation ownership.
function sameShape(base:unknown,value:unknown):boolean {
  if(base===null)return value===null;
  if(typeof base!==typeof value)return false;
  if(Array.isArray(base))return Array.isArray(value)&&base.length===value.length&&base.every((item,i)=>sameShape(item,value[i]));
  if(typeof base==='object')return !!value&&Object.keys(base).sort().join('|')===Object.keys(value).sort().join('|')
    &&Object.entries(base).every(([key,item])=>sameShape(item,(value as Record<string,unknown>)[key]));
  return typeof value!=='number'||Number.isFinite(value);
}

export type SavedMechanicsSessionState={revisionId:string|null;busy:boolean;switchReason:string|null};

export function SavedMechanicsRevisionEditor({worldId,draftId,autoLoad=false,initialRevisionId,onSessionStateChange}:{worldId:string;draftId:string;autoLoad?:boolean;initialRevisionId?:string;onSessionStateChange?:(state:SavedMechanicsSessionState)=>void}) {
 const guidance=useGuidedTour(),generationPlan=useGenerationPlan();
 const generatedScope=guidance&&generationPlan?guidance.captureMechanicsScope(generationPlan,draftId):null,latestGeneratedScope=useRef(generatedScope);latestGeneratedScope.current=generatedScope;
 const [generatedAcknowledged,setGeneratedAcknowledged]=useState<AcknowledgedGeneratedMechanicsSave|null>(null);
 const generatedDispatch=useRef<{operationId:string;scope:GeneratedMechanicsScope|null;dispatchScope:TourDispatchScope|null}|null>(null);
  const [writer]=useState(()=>{
    const key='dmb-manual-mechanics-writer';
    try{let id=sessionStorage.getItem(key);if(!id){id=crypto.randomUUID();sessionStorage.setItem(key,id);}return {id,recoverable:true};}
    catch{return {id:crypto.randomUUID(),recoverable:false};}
  });
  const scope=`dmb-manual-mechanics:${JSON.stringify([writer.id,worldId,draftId])}`;
  const tourScope=useTourEncounter(),latestTourScope=useRef(tourScope);latestTourScope.current=tourScope;
  const [tourAcknowledged,setTourAcknowledged]=useState<AcknowledgedMechanicsSave|null>(null);
  const [history,setHistory]=useState<SavedMechanicsVersionList|null>(null);
  const [associationBusy,setAssociationBusy]=useState(false);
  const [opened,setOpened]=useState<OpenSavedMechanicsVersion|null>(null);
  const [editor,setEditor]=useState<StatblockEditorState|null>(null);
  const [summary,setSummary]=useState('Manual mechanics revision');
  const [portraitAssetId,setPortraitAssetId]=useState<string|null>(null);
  const [studioOpen,setStudioOpen]=useState(false),[studioSource,setStudioSource]=useState<string|null>(null);
  const [pending,setPending]=useState<string|null>(null);
  const [recoverySource,setRecoverySource]=useState<string|null>(null),[blockedRecovery,setBlockedRecovery]=useState(false);
  const [successorToOpen,setSuccessorToOpen]=useState<string|null>(null);
  const [issues,setIssues]=useState<ValidationIssueV1[]>([]);
  const [validated,setValidated]=useState<string|null>(null);
  const [busy,setBusy]=useState(autoLoad),[message,setMessage]=useState('');
  const epoch=useRef(0),selectionEpoch=epoch.current;
  const studioKey=opened?JSON.stringify([worldId,draftId,opened.locator.revision_id]):null;
  const showStudio=studioOpen&&studioSource===studioKey;
  useEffect(()=>()=>{epoch.current++;},[]);
  const sourceKey=(revision:string)=>`${scope}:version:${revision}`;
  function remember(state:StatblockEditorState,changeSummary=summary,portrait=portraitAssetId) {
    if(!opened)return;
    localStorage.setItem(sourceKey(opened.locator.revision_id),JSON.stringify({schema:'dmb_manual_mechanics_work_v2',
      base:opened.locator,baseline:state.baselineFingerprint,workingCopy:state.workingCopy,summary:changeSummary,portraitAssetId:portrait}));
  }
  async function load(revision?:string,offset=0) {
    const token=++epoch.current;setBusy(true);setIssues([]);setMessage('Opening saved mechanics…');
    try {
      const page=await listSavedMechanicsVersions(draftId,worldId,offset);
      if(token!==epoch.current)return;
      if(page.world_id!==worldId||page.draft_id!==draftId)throw new Error('Saved versions belong to another creature.');
      const combined=offset&&history?{...page,operations:[...history.operations,...page.operations]}:page;
      setHistory(combined);
      const retained=localStorage.getItem(`${scope}:pending`);
      const operation=page.pending?.operation_id??retained;
      setPending(operation);
      if(offset&&history){setMessage(operation?'A Save needs its outcome checked. Recover it before making another version.':'');return;} // Metadata paging preserves dirty source content.
      // An exact entry point never borrows another version's Save base.
      let pendingBase=page.pending?.base.revision_id;
      if(operation&&revision&&!pendingBase){
        const inspected=await inspectMechanicsRevision(draftId,worldId,operation);
        if(token!==epoch.current)return;
        pendingBase=inspected.operation?.base.revision_id;
      }
      if(operation&&revision&&pendingBase!==revision){
        setRecoverySource(pendingBase??null);setBlockedRecovery(true);
        setMessage(pendingBase?'A Save belongs to another version. Open its source and recover it before choosing this version.'
          :'A retained Save has no confirmed source yet. Recover its original identity before opening this version.');
        return;
      }
      const selected=revision??pendingBase??localStorage.getItem(`${scope}:selected`)??page.original.revision_id;
      const exact=await openSavedMechanicsVersion(draftId,worldId,selected);
      if(token!==epoch.current)return;
      if(exact.resource.statblock_id!==page.original.statblock_id)throw new Error('Saved version differs from this creature’s history.');
      let state=createEditorStateFromOutput(exact.resource.definition),changeSummary='Manual mechanics revision';
      let restoredPortrait:string|null=null;
      const recovery=localStorage.getItem(sourceKey(selected));
      if(recovery){
        const value=JSON.parse(recovery);
        if(!['dmb_manual_mechanics_work_v1','dmb_manual_mechanics_work_v2'].includes(value.schema)||JSON.stringify(value.base)!==JSON.stringify(exact.locator)
          ||value.baseline!==state.baselineFingerprint||!sameShape(state.workingCopy,value.workingCopy)||typeof value.summary!=='string')
          throw new Error('Saved edits could not be verified; they remain retained in this browser.');
        if(value.schema==='dmb_manual_mechanics_work_v2'){
          if(!(value.portraitAssetId===null||typeof value.portraitAssetId==='string'&&MEDIA_ASSET_ID.test(value.portraitAssetId)))
            throw new Error('Saved portrait choice could not be verified; it remains retained in this browser.');
          restoredPortrait=value.portraitAssetId;
        }else if(value.portraitAssetId!==undefined)throw new Error('Saved edits contain an unknown portrait choice; they remain retained.');
        state={...state,workingCopy:value.workingCopy,stateRevision:1};changeSummary=value.summary;
      }
      localStorage.setItem(`${scope}:selected`,selected);
      if(opened?.locator.revision_id!==selected){setStudioOpen(false);setStudioSource(null);}
      setBlockedRecovery(false);setRecoverySource(null);setOpened(exact);setEditor(state);setSummary(changeSummary);setPortraitAssetId(restoredPortrait);setValidated(null);
      setSuccessorToOpen(current=>current===selected?null:current);
      setMessage(operation?'A Save needs its outcome checked. Recover it before making another version.':'');
      return exact;
    } catch(error){if(token===epoch.current)setMessage(error instanceof Error?error.message:String(error));}
    finally{if(token===epoch.current)setBusy(false);}
  }
  // Hosts keep this identity mounted after first opening; visibility never reloads it.
  useEffect(()=>{if(autoLoad)void load(initialRevisionId);},[autoLoad]);
  async function validate() {
    if(!editor)return;const token=++epoch.current,working=editor.workingCopy;setBusy(true);setIssues([]);setMessage('Validating new mechanics…');
    try {
      const result=await validateStatblockDefinition({definition:working});if(token!==epoch.current)return;
      if(result.outcome!=='success'||!result.validation_receipt)throw new Error('Mechanics validation is unavailable. Your edits are retained; try again when it is available.');
      setIssues(result.validation_receipt.issues??[]);
      if(result.validation_receipt.status==='invalid'
        ||result.validation_receipt.issues?.some(issue=>issue.severity==='error'))throw new Error('Correct validation errors before saving.');
      setValidated(fingerprintDefinition(working));setMessage('Validated. Save creates a new version; encounters stay unchanged.');
    }catch(error){if(token===epoch.current){setValidated(null);setMessage(error instanceof Error?error.message:String(error));}}
    finally{if(token===epoch.current)setBusy(false);}
  }
  function clearPending(id:string){if(localStorage.getItem(`${scope}:pending`)===id)localStorage.removeItem(`${scope}:pending`);setPending(null);}
  async function applyOutcome(outcome:RevisionSaveOutcome,token:number,expectedId:string,tourAtDispatch:TourEncounterScope|null,tourDispatch:TourDispatchScope|null,generatedAtDispatch:GeneratedMechanicsScope|null) {
    if(token!==epoch.current)return;
    if(outcome.operation_id!==expectedId||!opened||JSON.stringify(outcome.base)!==JSON.stringify(opened.locator))throw new Error('Save outcome belongs to another version or operation.');
    if(outcome.state==='committed'||outcome.state==='refused'){
      clearPending(expectedId);
      if(outcome.state==='committed'&&outcome.result){
        if(opened)localStorage.removeItem(sourceKey(opened.locator.revision_id));
        // This is a retained selection hint from a committed outcome, not Save authority.
        localStorage.setItem(`${scope}:selected`,outcome.result.revision_id);
        setSuccessorToOpen(outcome.result.revision_id);setValidated(null);
        const exact=await load(outcome.result.revision_id);if(epoch.current===token+1&&exact){
          setMessage('New mechanics version saved. Encounters and World associations are unchanged.');
          if(exact&&sameMechanicsLocator(exact.locator,outcome.result)&&generatedAtDispatch&&sameGeneratedMechanicsScope(generatedAtDispatch,latestGeneratedScope.current))setGeneratedAcknowledged({scope:generatedAtDispatch,dispatchScope:tourDispatch,operation:outcome});
          if(exact&&sameMechanicsLocator(exact.locator,outcome.result)&&tourAtDispatch&&sameEncounterScope(tourAtDispatch,latestTourScope.current))setTourAcknowledged({dispatchScope:tourDispatch,scope:tourAtDispatch,draftId,operation:outcome});
        }
      }else setMessage('The source version changed. Your edits are retained; inspect the saved versions before trying again.');
    }else setMessage('Save outcome is unknown. Recover this Save; do not start another version.');
  }
  async function save() {
    if(!writer.recoverable||!opened||!editor||pending||successorToOpen||validated!==fingerprintDefinition(editor.workingCopy))return;
    const retained=localStorage.getItem(`${scope}:pending`);if(retained){setPending(retained);setMessage('Recover the existing Save before making another version.');return;}
    const token=++epoch.current,id=crypto.randomUUID(),tourAtDispatch=tourScope,tourDispatch=guidance?.captureScope()??null,generatedAtDispatch=generatedScope;setBusy(true);setMessage('Saving new mechanics version…');
    generatedDispatch.current={operationId:id,scope:generatedAtDispatch,dispatchScope:tourDispatch};
    try {
      remember(editor);localStorage.setItem(`${scope}:pending`,id);setPending(id);
      const result=await saveMechanicsRevision(draftId,{operation_id:id,world_id:worldId,base:opened.locator,
        definition:editor.workingCopy,change_summary:summary,...(portraitAssetId?{portrait_asset_id:portraitAssetId}:{})});
      await applyOutcome(result,token,id,tourAtDispatch,tourDispatch,generatedAtDispatch);
    }catch(error){
      if(token!==epoch.current)return;
      // Inspection never cancels an in-flight preflight. Only the explicit
      // recover action can fence an absent operation before unlocking edits.
      try {
        const status=await inspectMechanicsRevision(draftId,worldId,id);
        if(token!==epoch.current)return;
        if(status.operation)await applyOutcome(status.operation,token,id,tourAtDispatch,tourDispatch,generatedAtDispatch);
        else setMessage('Save has no durable result yet. Recover Save to finish it or safely release its intent.');
      }catch{if(token===epoch.current)setMessage('Save outcome could not be checked. Your edits and Save identity are retained. Recover before continuing.');}
    }finally{if(token===epoch.current)setBusy(false);}
  }
  async function recover() {
    if(!pending)return;const token=++epoch.current,tourAtDispatch=tourScope,originalDispatch=generatedDispatch.current?.operationId===pending?generatedDispatch.current:null,tourDispatch=originalDispatch?.dispatchScope??guidance?.captureScope()??null,generatedAtDispatch=originalDispatch?.scope??null;setBusy(true);setMessage('Checking saved result…');
    try{
      const result=await recoverMechanicsRevision(draftId,worldId,pending);if(token!==epoch.current)return;
      if(!result){clearPending(pending);setBlockedRecovery(false);setRecoverySource(null);setMessage('Save was safely canceled before dispatch. Your edits are available.');return;}
      if(!opened||blockedRecovery){setRecoverySource(result.base.revision_id);setBlockedRecovery(true);setMessage('The saved outcome belongs to its original source. Open that source to finish recovery.');return;}
      await applyOutcome(result,token,pending,tourAtDispatch,tourDispatch,generatedAtDispatch);
    }catch(error){if(token===epoch.current)setMessage(error instanceof Error?error.message:String(error));}
    finally{if(token===epoch.current)setBusy(false);}
  }
  const workReason=busy?'Wait for the current statblock operation before opening another saved version.':pending||successorToOpen||studioSource===studioKey&&studioSource!==null||portraitAssetId!==null
    ||summary!=='Manual mechanics revision'||!!editor&&editor.baselineFingerprint!==fingerprintDefinition(editor.workingCopy)
    ?'Save, recover or revert the current statblock work before opening another statblock.':null;
  const switchReason=associationBusy?'Wait for the creature association before switching saved versions.':workReason;
  useLayoutEffect(()=>{onSessionStateChange?.({revisionId:opened?.locator.revision_id??null,busy:busy||associationBusy,switchReason});},[opened,busy,associationBusy,switchReason,onSessionStateChange]);
  useTourNavigationGuard({worldId,reason:()=>switchReason});
  return <section className="statblock-section" aria-label="Saved mechanics versions">
    {!tourScope&&<GeneratedMechanicsTourObservation scope={generatedScope} opened={opened} history={history} acknowledged={generatedAcknowledged} blocked={switchReason!==null}/>}
    <MechanicsTourObservation scope={tourScope} opened={opened} history={history} acknowledged={tourAcknowledged} blocked={switchReason!==null}/>
    <h3>Saved versions</h3>
    <p>Edit saved mechanics and create a new version. Choosing it for a fight is a separate action.</p>
    <button type="button" data-guided-control="mechanics" disabled={associationBusy||busy||showStudio} onClick={()=>void load(opened?.locator.revision_id??initialRevisionId)}>Open saved mechanics</button>
    {history&&<label>Mechanics version <select aria-label="Saved mechanics version" disabled={associationBusy||busy||showStudio||!!pending||!!successorToOpen} value={opened?.locator.revision_id??''} onChange={event=>void load(event.target.value)}>
      <option value={history.original.revision_id}>Original saved mechanics</option>
      {history.operations.filter(op=>op.state==='committed'&&op.result).map((op,index)=><option key={op.operation_id} value={op.result!.revision_id}>Version {index+2} · {op.change_summary}</option>)}
    </select></label>}
    {history?.next_offset!==null&&history?.next_offset!==undefined&&<button type="button" disabled={associationBusy||busy||showStudio} onClick={()=>void load(opened?.locator.revision_id,history.next_offset!)}>More saved versions</button>}
    {opened&&editor&&<>
      <div hidden={showStudio}>
      <section aria-label="Saved statblock">
        <p>Saved version. Local edits appear in the fields below until you save a new version.</p>
        <a onClick={interceptPrimaryNavigationClick} href={savedStatblockHref({worldId,draftId,revisionId:opened.locator.revision_id})}>Open full saved statblock</a>
        <StatblockRenderer revision={opened.resource} mode="full" chrome="campaign"/>
      </section>
      <fieldset disabled={associationBusy||busy||!!pending||!!successorToOpen}>
        <section className="saved-mechanics-portrait-controls" aria-label="Portrait selection">
          <button type="button" disabled={!writer.recoverable} onClick={()=>{setStudioSource(studioKey);setStudioOpen(true);}}>Generate or choose portrait</button>
          {portraitAssetId&&<>
            <p>Selected for the new version. Save the statblock to keep this portrait.</p>
            <div className="saved-mechanics-portrait-preview"><SavedMediaImage assetId={portraitAssetId} alt="Selected portrait"/></div>
            <button type="button" onClick={()=>{try{remember(editor,summary,null);setPortraitAssetId(null);setMessage('The saved portrait will be kept.');}catch{setMessage('Could not update portrait recovery. Your choice remains retained.');}}}>Keep saved portrait</button>
          </>}
        </section>
        <StatblockDefinitionEditor output={opened.resource.definition} editorState={editor}
          recoveryHint={writer.recoverable?"Unsaved edits are retained in this browser tab for this creature and source version.":"Browser recovery is unavailable. Keep this editor open."}
          onEditorStateChange={next=>{setEditor(next);setValidated(null);setIssues([]);try{remember(next);}catch{setMessage('Browser recovery storage is unavailable. Keep this editor open.');}}}/>
        <label>Change summary <input value={summary} onChange={event=>{setSummary(event.target.value);try{remember(editor,event.target.value);}catch{setMessage('Browser recovery storage is unavailable.');}}}/></label>
      </fieldset>
      <button type="button" disabled={associationBusy||busy||!!pending||!!successorToOpen} onClick={()=>{try{localStorage.removeItem(sourceKey(opened.locator.revision_id));setEditor(createEditorStateFromOutput(opened.resource.definition));setPortraitAssetId(null);setStudioOpen(false);setStudioSource(null);setSummary('Manual mechanics revision');setValidated(null);setIssues([]);setMessage('Local edits reverted. Saved versions are unchanged.');}catch{setMessage('Could not clear local recovery; edits remain retained.');}}}>Revert local edits</button>
      <button type="button" disabled={associationBusy||busy||!!pending||!!successorToOpen} onClick={()=>void validate()}>Validate new version</button>
      <button type="button" disabled={!writer.recoverable||associationBusy||busy||!!pending||!!successorToOpen||!summary.trim()||validated!==fingerprintDefinition(editor.workingCopy)} onClick={()=>void save()}>Save new version</button>
      </div>
      {studioSource===studioKey&&<div className="saved-mechanics-portrait-studio" hidden={!showStudio}>
        <MediaImageWizard key={studioKey!} selectionOnly requireSaved chooseLabel="Use as portrait"
          initialPrompt={[`Portrait of ${editor.workingCopy.identity.name}.`,editor.workingCopy.flavor_text?.summary??editor.workingCopy.flavor_text?.description??''].filter(Boolean).join(' ')}
          onClose={()=>setStudioOpen(false)} onChoose={(image,_result,placement)=>{
            if(placement.signal.aborted)return;
            if(!MEDIA_ASSET_ID.test(image.asset_id))throw new Error('This image has no valid saved reference. Reopen it from your library.');
            if(selectionEpoch!==epoch.current||busy||pending||successorToOpen)throw new Error('The source changed. Reopen the portrait studio before choosing.');
            try{remember(editor,summary,image.asset_id);}catch{throw new Error('Could not retain this portrait choice. Keep the editor open and try again.');}
            setPortraitAssetId(image.asset_id);setStudioOpen(false);setMessage('Portrait selected. Save a new version to keep it.');
          }}/>
      </div>}
    </>}
    {opened&&<WorldMechanicsAssociationPanel worldId={worldId} draftId={draftId} locator={opened.locator}
      disabledReason={workReason} onBusyChange={setAssociationBusy}/>}
    {successorToOpen&&<>
      <p role="status">A new version was saved but has not opened. The previous selected version is still displayed; editing is paused.</p>
      <button type="button" disabled={associationBusy||busy} onClick={()=>void load(successorToOpen)}>Open saved successor</button>
    </>}
    {blockedRecovery&&recoverySource&&<button type="button" disabled={associationBusy||busy} onClick={()=>void load(recoverySource)}>Open Save source for recovery</button>}
    {pending&&<button type="button" disabled={associationBusy||busy||blockedRecovery&&!!recoverySource} onClick={()=>void recover()}>Recover Save</button>}
    {issues.length>0&&<ul aria-label="Mechanics validation issues">{issues.map((issue,index)=><li key={index}>{issue.message} <small>{issue.field_path}</small></li>)}</ul>}
    {message&&<p role="status">{message}</p>}
  </section>;
}
