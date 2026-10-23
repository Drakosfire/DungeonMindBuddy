import {useEffect,useRef,useState} from 'react';
import {listSavedMechanicsVersions,openSavedMechanicsVersion,saveMechanicsRevision,recoverMechanicsRevision,inspectMechanicsRevision,validateStatblockDefinition} from '../../api/liveApi';
import {StatblockDefinitionEditor} from '../editor/StatblockDefinitionEditor';
import {createEditorStateFromOutput,fingerprintDefinition,type StatblockEditorState} from '../editor/statblockEditorState';
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

export function SavedMechanicsRevisionEditor({worldId,draftId}:{worldId:string;draftId:string}) {
  const [writer]=useState(()=>{
    const key='dmb-manual-mechanics-writer';
    try{let id=sessionStorage.getItem(key);if(!id){id=crypto.randomUUID();sessionStorage.setItem(key,id);}return {id,recoverable:true};}
    catch{return {id:crypto.randomUUID(),recoverable:false};}
  });
  const scope=`dmb-manual-mechanics:${JSON.stringify([writer.id,worldId,draftId])}`;
  const [history,setHistory]=useState<SavedMechanicsVersionList|null>(null);
  const [opened,setOpened]=useState<OpenSavedMechanicsVersion|null>(null);
  const [editor,setEditor]=useState<StatblockEditorState|null>(null);
  const [summary,setSummary]=useState('Manual mechanics revision');
  const [pending,setPending]=useState<string|null>(null);
  const [validated,setValidated]=useState<string|null>(null);
  const [busy,setBusy]=useState(false),[message,setMessage]=useState('');
  const epoch=useRef(0);
  useEffect(()=>()=>{epoch.current++;},[]);
  const sourceKey=(revision:string)=>`${scope}:version:${revision}`;
  function remember(state:StatblockEditorState,changeSummary=summary) {
    if(!opened)return;
    localStorage.setItem(sourceKey(opened.locator.revision_id),JSON.stringify({schema:'dmb_manual_mechanics_work_v1',
      base:opened.locator,baseline:state.baselineFingerprint,workingCopy:state.workingCopy,summary:changeSummary}));
  }
  async function load(revision?:string,offset=0) {
    const token=++epoch.current;setBusy(true);setMessage('Opening saved mechanics…');
    try {
      const page=await listSavedMechanicsVersions(draftId,worldId,offset);
      if(token!==epoch.current)return;
      if(page.world_id!==worldId||page.draft_id!==draftId)throw new Error('Saved versions belong to another creature.');
      const combined=offset&&history?{...page,operations:[...history.operations,...page.operations]}:page;
      setHistory(combined);
      const retained=localStorage.getItem(`${scope}:pending`);
      const operation=page.pending?.operation_id??retained;
      setPending(operation);
      if(offset&&history)return; // Paging metadata must not reopen or replace dirty source content.
      const selected=revision??page.pending?.base.revision_id??localStorage.getItem(`${scope}:selected`)??page.original.revision_id;
      const exact=await openSavedMechanicsVersion(draftId,worldId,selected);
      if(token!==epoch.current)return;
      if(exact.world_id!==worldId||exact.draft_id!==draftId||exact.locator.revision_id!==selected
        ||exact.resource.revision_id!==selected||exact.resource.statblock_id!==page.original.statblock_id)throw new Error('Saved version identity changed.');
      let state=createEditorStateFromOutput(exact.resource.definition),changeSummary='Manual mechanics revision';
      const recovery=localStorage.getItem(sourceKey(selected));
      if(recovery){
        const value=JSON.parse(recovery);
        if(value.schema!=='dmb_manual_mechanics_work_v1'||JSON.stringify(value.base)!==JSON.stringify(exact.locator)
          ||value.baseline!==state.baselineFingerprint||!sameShape(state.workingCopy,value.workingCopy)||typeof value.summary!=='string')
          throw new Error('Saved edits could not be verified; they remain retained in this browser.');
        state={...state,workingCopy:value.workingCopy,stateRevision:1};changeSummary=value.summary;
      }
      localStorage.setItem(`${scope}:selected`,selected);
      setOpened(exact);setEditor(state);setSummary(changeSummary);setValidated(null);
      setMessage(operation?'A Save needs its outcome checked. Recover it before making another version.':'');
    } catch(error){if(token===epoch.current)setMessage(error instanceof Error?error.message:String(error));}
    finally{if(token===epoch.current)setBusy(false);}
  }
  async function validate() {
    if(!editor)return;const token=++epoch.current,working=editor.workingCopy;setBusy(true);setMessage('Validating new mechanics…');
    try {
      const result=await validateStatblockDefinition({definition:working});if(token!==epoch.current)return;
      if(result.outcome!=='success'||!result.validation_receipt||result.validation_receipt.status==='invalid'
        ||result.validation_receipt.issues?.some(issue=>issue.severity==='error'))throw new Error('Correct validation errors before saving.');
      setValidated(fingerprintDefinition(working));setMessage('Validated. Save creates a new version; encounters stay unchanged.');
    }catch(error){if(token===epoch.current){setValidated(null);setMessage(error instanceof Error?error.message:String(error));}}
    finally{if(token===epoch.current)setBusy(false);}
  }
  function clearPending(id:string){if(localStorage.getItem(`${scope}:pending`)===id)localStorage.removeItem(`${scope}:pending`);setPending(null);}
  async function applyOutcome(outcome:RevisionSaveOutcome,token:number,expectedId:string) {
    if(token!==epoch.current)return;
    if(outcome.operation_id!==expectedId||!opened||JSON.stringify(outcome.base)!==JSON.stringify(opened.locator))throw new Error('Save outcome belongs to another version or operation.');
    if(outcome.state==='committed'||outcome.state==='refused'){
      clearPending(expectedId);
      if(outcome.state==='committed'&&outcome.result){
        if(opened)localStorage.removeItem(sourceKey(opened.locator.revision_id));
        await load(outcome.result.revision_id);if(epoch.current===token+1)setMessage('New mechanics version saved. Encounters and World associations are unchanged.');
      }else setMessage('The source version changed. Your edits are retained; inspect the saved versions before trying again.');
    }else setMessage('Save outcome is unknown. Recover this Save; do not start another version.');
  }
  async function save() {
    if(!writer.recoverable||!opened||!editor||pending||validated!==fingerprintDefinition(editor.workingCopy))return;
    const retained=localStorage.getItem(`${scope}:pending`);if(retained){setPending(retained);setMessage('Recover the existing Save before making another version.');return;}
    const token=++epoch.current,id=crypto.randomUUID();setBusy(true);setMessage('Saving new mechanics version…');
    try {
      remember(editor);localStorage.setItem(`${scope}:pending`,id);setPending(id);
      const result=await saveMechanicsRevision(draftId,{operation_id:id,world_id:worldId,base:opened.locator,
        definition:editor.workingCopy,change_summary:summary});
      await applyOutcome(result,token,id);
    }catch(error){
      if(token!==epoch.current)return;
      // Inspection never cancels an in-flight preflight. Only the explicit
      // recover action can fence an absent operation before unlocking edits.
      try {
        const status=await inspectMechanicsRevision(draftId,worldId,id);
        if(token!==epoch.current)return;
        if(status.operation)await applyOutcome(status.operation,token,id);
        else setMessage('Save has no durable result yet. Recover Save to finish it or safely release its intent.');
      }catch{if(token===epoch.current)setMessage('Save outcome could not be checked. Your edits and Save identity are retained. Recover before continuing.');}
    }finally{if(token===epoch.current)setBusy(false);}
  }
  async function recover() {
    if(!pending)return;const token=++epoch.current;setBusy(true);setMessage('Checking saved result…');
    try{
      const result=await recoverMechanicsRevision(draftId,worldId,pending);if(token!==epoch.current)return;
      if(!result){clearPending(pending);setMessage('Save was safely canceled before dispatch. Your edits are available.');return;}
      await applyOutcome(result,token,pending);
    }catch(error){if(token===epoch.current)setMessage(error instanceof Error?error.message:String(error));}
    finally{if(token===epoch.current)setBusy(false);}
  }
  return <section className="statblock-section" aria-label="Saved mechanics versions">
    <h3>Saved versions</h3>
    <p>Edit saved mechanics and create a new version. Choosing it for a fight is a separate action.</p>
    <button type="button" disabled={busy} onClick={()=>void load()}>Open saved mechanics</button>
    {history&&<label>Mechanics version <select aria-label="Saved mechanics version" disabled={busy||!!pending} value={opened?.locator.revision_id??''} onChange={event=>void load(event.target.value)}>
      <option value={history.original.revision_id}>Original saved mechanics</option>
      {history.operations.filter(op=>op.state==='committed'&&op.result).map((op,index)=><option key={op.operation_id} value={op.result!.revision_id}>Version {index+2} · {op.change_summary}</option>)}
    </select></label>}
    {history?.next_offset!==null&&history?.next_offset!==undefined&&<button type="button" disabled={busy} onClick={()=>void load(opened?.locator.revision_id,history.next_offset!)}>More saved versions</button>}
    {opened&&editor&&<>
      <fieldset disabled={busy||!!pending}>
        <StatblockDefinitionEditor output={opened.resource.definition} editorState={editor}
          recoveryHint={writer.recoverable?"Unsaved edits are retained in this browser tab for this creature and source version.":"Browser recovery is unavailable. Keep this editor open."}
          onEditorStateChange={next=>{setEditor(next);setValidated(null);try{remember(next);}catch{setMessage('Browser recovery storage is unavailable. Keep this editor open.');}}}/>
        <label>Change summary <input value={summary} onChange={event=>{setSummary(event.target.value);try{remember(editor,event.target.value);}catch{setMessage('Browser recovery storage is unavailable.');}}}/></label>
      </fieldset>
      <button type="button" disabled={busy||!!pending} onClick={()=>{try{localStorage.removeItem(sourceKey(opened.locator.revision_id));setEditor(createEditorStateFromOutput(opened.resource.definition));setValidated(null);setMessage('Local edits reverted. Saved versions are unchanged.');}catch{setMessage('Could not clear local recovery; edits remain retained.');}}}>Revert local edits</button>
      <button type="button" disabled={busy||!!pending} onClick={()=>void validate()}>Validate new version</button>
      <button type="button" disabled={!writer.recoverable||busy||!!pending||!summary.trim()||validated!==fingerprintDefinition(editor.workingCopy)} onClick={()=>void save()}>Save new version</button>
    </>}
    {pending&&<button type="button" disabled={busy} onClick={()=>void recover()}>Recover Save</button>}
    {message&&<p role="status">{message}</p>}
  </section>;
}
