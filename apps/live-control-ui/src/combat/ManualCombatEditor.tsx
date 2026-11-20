import {useEffect,useId,useLayoutEffect,useRef,useState} from 'react';
import type {ManualCombatActor,ManualCombatDraft,ManualCombatRecord} from './ManualCombatTypes';
import type {RunEncounterScope} from './runEncountersApi';
import {CombatRecoverySession,combatDraftEqual,type CombatRecovery} from './combatRecovery';
import {getAnyWorldCombatEncounter,saveManualCombatEncounter} from './combatApi';
import {isManualCombatRecord} from './ManualCombatTypes';
import {advanceManualTurn,assignManualSide,newManualActor,removeManualActor,setManualParticipation} from './ManualCombatState';
import {ManualCombatSides,ManualSideTurnRail} from './ManualCombatSides';
import {ManualSpotlightRail} from './ManualCombatSpotlight';
import {CombatSavedStatblock} from './CombatMechanicsInspection';
import {ManualCombatSourcePicker} from './ManualCombatSourcePicker';
import {validManualDraft} from './validateCombatRecovery';
import {ManualCombatValueInput} from './ManualCombatValueInput';
import {ManualCombatRosterTable} from './ManualCombatRosterTable';

const copy=<T,>(value:T):T=>JSON.parse(JSON.stringify(value)) as T;

type Props={externallyDisabled?:boolean;record:ManualCombatRecord;scope?:RunEncounterScope;onSaved:(record:ManualCombatRecord)=>void;onBlocked:(blocked:boolean)=>void};

/** One recovery/Save owner; parent hosts retain committed records only. */
export function ManualCombatEditor({record,scope,onSaved,onBlocked,externallyDisabled=false}:Props) {
  const session=useRef(new CombatRecoverySession<ManualCombatRecord>());
  const state=useRef({base:record,draft:copy(record.draft),pending:null as CombatRecovery<ManualCombatRecord>['pending']});
  const [draft,setDraft]=useState(state.current.draft),[base,setBase]=useState(record);
  const [ready,setReady]=useState(false),[saving,setSaving]=useState(false);
  const [recovery,setRecovery]=useState<CombatRecovery<ManualCombatRecord>|null>(null);
  const [error,setError]=useState<string|null>(null),[message,setMessage]=useState<string|null>(null);
  const [name,setName]=useState(''),[projection,setProjection]=useState<string|null>(null);
  const [additionSide,setAdditionSide]=useState<string|null>(null);
  const [groupName,setGroupName]=useState(''),[groupMembers,setGroupMembers]=useState<string[]>([]);
  const alive=useRef(false);
  const lifetime=useRef(0),workspace=useRef<HTMLElement>(null),sourcePanel=useRef<HTMLElement>(null);
  const sourceTrigger=useRef<HTMLButtonElement|null>(null),rail=useRef<HTMLElement>(null);
  const sourceRegionId=useId();
  const dirty=!combatDraftEqual(base.draft,draft), blocked=!ready||recovery!==null||externallyDisabled;
  useEffect(()=>{
    const epoch=++lifetime.current;
    alive.current=true;
    void session.current.open(record,()=>alive.current&&lifetime.current===epoch,!scope).then(result=>{
      if(!alive.current||lifetime.current!==epoch)return;
      setRecovery(result.recovery);setReady(true);
      if(result.committedMatch)setMessage('The submitted Save is committed. Later edits remain available to recover.');
    }).catch(caught=>{if(alive.current&&lifetime.current===epoch)setError(String(caught));});
    return ()=>{alive.current=false;lifetime.current++;session.current.close();};
  },[]);
  useLayoutEffect(()=>{
    const panel=workspace.current,turnRail=rail.current;
    if(!panel||!turnRail)return;
    const measure=()=>panel.style.setProperty('--manual-turn-rail-height',`${turnRail.getBoundingClientRect().height}px`);
    measure();const observer=typeof ResizeObserver==='undefined'?null:new ResizeObserver(measure);
    observer?.observe(turnRail);return()=>observer?.disconnect();
  },[]);
  useLayoutEffect(()=>{
    const panel=sourcePanel.current;
    if(!projection||!panel)return;
    panel.focus({preventScroll:true});panel.scrollIntoView?.({block:'start'});
    // The deferred renderer grows after opening. Keep its focused heading below
    // the rail without moving the viewport once the user resumes roster edits.
    const observer=typeof ResizeObserver==='undefined'?null:new ResizeObserver(()=>{
      if(panel.contains(document.activeElement))panel.scrollIntoView?.({block:'start'});
    });
    observer?.observe(panel);return()=>observer?.disconnect();
  },[projection]);
  function closeProjection() {
    setProjection(null);
    const trigger=sourceTrigger.current;
    if(trigger?.isConnected&&!trigger.closest('[hidden]')&&!trigger.disabled){trigger.focus({preventScroll:true});trigger.scrollIntoView?.({block:'nearest',inline:'nearest'});}
    else workspace.current?.focus({preventScroll:true});
  }
  useEffect(()=>{onBlocked(dirty||blocked||saving||state.current.pending!==null);},[dirty,blocked,saving,onBlocked]);
  function update(next:ManualCombatDraft) {
    if(blocked||state.current.pending&&!saving)return false;
    try {
      if(!validManualDraft(state.current.base,next))throw new Error('Enter valid values for the pinned profile before applying this change.');
      if(combatDraftEqual(state.current.draft,next))return true;
      session.current.write(state.current.base,next,state.current.pending);
      state.current.draft=next;setDraft(next);setError(null);return true;
    } catch(caught){setError(String(caught));return false;}
  }
  function actorChange(actor:ManualCombatActor) {
    const assigned=assignManualSide(state.current.draft,actor.id,actor.side_id);
    return update({...assigned,entities:assigned.entities.map(item=>item.id===actor.id?actor:item)});
  }
  async function save() {
    if(blocked||saving)return;
    const submitted=state.current.pending??{expected_revision:state.current.base.revision,draft:copy(state.current.draft)};
    try {
      session.current.write(state.current.base,state.current.draft,submitted);state.current.pending=submitted;
      setSaving(true);setError(null);
      const result=await saveManualCombatEncounter(base.world_id,base.encounter_id,submitted.expected_revision,submitted.draft,scope);
      if(!alive.current)return;
      if(result.revision!==submitted.expected_revision+1||!combatDraftEqual(result.draft,submitted.draft)
        ||!combatDraftEqual(result.ruleset,base.ruleset))throw new Error('Save acknowledgement differs from the submitted encounter.');
      const later=state.current.draft;
      if(combatDraftEqual(later,submitted.draft))session.current.clear();
      else session.current.write(result,later);
      state.current={base:result,draft:later,pending:null};setBase(result);setDraft(later);onSaved(result);
      setMessage('Encounter saved.');
    } catch(caught){if(alive.current)setError(`${String(caught)} Local edits and the exact submitted Save are retained. Retry Save to settle its outcome.`);}
    finally{if(alive.current)setSaving(false);}
  }
  function recover() {
    if(!recovery)return;
    state.current={base:recovery.base,draft:copy(recovery.draft),pending:recovery.pending};
    setBase(recovery.base);setDraft(state.current.draft);setRecovery(null);setMessage('Recovered edits use their original base revision.');
  }
  async function reload() {
    if(saving||externallyDisabled)return;
    setSaving(true);setError(null);
    try {
      const current=await getAnyWorldCombatEncounter(base.world_id,base.encounter_id,scope);
      if(!alive.current)return;
      if(!isManualCombatRecord(current)||!combatDraftEqual(current.ruleset,base.ruleset))throw new Error('Pinned encounter profile changed.');
      const result=await session.current.open(current,()=>alive.current,!scope);
      if(!alive.current)return;
      state.current={base:current,draft:copy(current.draft),pending:null};setBase(current);setDraft(state.current.draft);
      setRecovery(result.recovery);setReady(true);onSaved(current);
      setMessage(result.committedMatch?'The submitted Save is committed. Later edits remain available to recover.':'Reloaded committed state. Retained edits require explicit recovery.');
    }catch(caught){if(alive.current){setReady(false);setError(String(caught));}}
    finally{if(alive.current)setSaving(false);}
  }
  function discard() {try{session.current.clear();setRecovery(null);}catch(caught){setError(String(caught));}}
  function revert() {
    if(state.current.pending)return;
    try{session.current.clear();state.current.draft=copy(base.draft);setDraft(state.current.draft);}catch(caught){setError(String(caught));}
  }
  function move(id:string,direction:1|-1) {
    const entities=[...draft.entities], participating=entities.filter(actor=>actor.participation==='in_action');
    const target=participating[participating.findIndex(actor=>actor.id===id)+direction];
    if(!target)return;
    const a=entities.findIndex(actor=>actor.id===id),b=entities.findIndex(actor=>actor.id===target.id);
    [entities[a],entities[b]]=[entities[b],entities[a]];update({...draft,entities});
  }
  const active=draft.entities.find(actor=>actor.id===draft.turn.active_actor_id);
  const participating=draft.entities.filter(actor=>actor.participation==='in_action');
  const next=participating[(participating.findIndex(actor=>actor.id===active?.id)+1)%participating.length];
  const projected=draft.entities.find(actor=>actor.id===projection);
  const newSide=draft.sides.some(side=>side.id===additionSide)?additionSide:null;
  useEffect(()=>{if(projection&&!projected?.mechanics_snapshot)closeProjection();},[projection,projected?.mechanics_snapshot]);
  const disabled=blocked||!!state.current.pending&&!saving;
  return <section ref={workspace} tabIndex={-1} className="manual-combat" aria-label="Manual combat encounter">
    <div className="combat-roster-save-rail">
      <span>{base.ruleset.name} · revision {base.revision}</span>
      <button disabled={blocked||saving||!dirty&&!state.current.pending} onClick={()=>void save()}>{saving?'Saving…':state.current.pending?'Retry Save':'Save'}</button>
      <button disabled={blocked||saving||!dirty||!!state.current.pending} onClick={revert}>Revert</button>
      <button disabled={saving||externallyDisabled} onClick={()=>void reload()}>Reload committed encounter</button>
      <span role="status">{state.current.pending?(saving?'Saving exact request…':'Save outcome unconfirmed · exact request retained'):dirty?'Unsaved changes':'Saved'}{message?` · ${message}`:''}</span>
    </div>
    {error&&<p role="alert" className="module-error">{error}</p>}
    {recovery&&<aside aria-label="Retained Combat draft"><p>Local edits are available. Recover or discard them before editing.</p><button onClick={recover}>Recover local edits</button><button onClick={discard}>Discard retained draft</button></aside>}
    <label>Encounter title<ManualCombatValueInput label="Encounter title" kind="name" value={draft.title} maxLength={160} disabled={disabled} onValue={value=>update({...draft,title:String(value)})}/></label>
    <section ref={rail} className="combat-roster-turn-rail" aria-label="Turn order">
      {draft.turn.kind==='side'?<ManualSideTurnRail draft={draft} disabled={disabled} onChange={update}/>
        :draft.turn.kind==='spotlight'?<ManualSpotlightRail draft={draft} disabled={disabled} onChange={update}/>:<>
      {draft.turn.kind==='ordered_rounds'&&<strong>Round {draft.turn.round}</strong>}
      <span>Current: {active?.name??'Not started'}</span><span>Next: {next?.name??'No participants'}</span>
      <button disabled={disabled||!participating.length} onClick={()=>{try{update(advanceManualTurn(draft));}catch(caught){setError(String(caught));}}}>{active?'Next turn':'Start turns'}</button>
      </>}
    </section>
    <div className="manual-combat-workspace">
      <div className="manual-combat-roster">
        {draft.groups.map(group=><div key={group.id} className="manual-combat-group">
          <button disabled={disabled} aria-expanded={!group.collapsed} onClick={()=>update({...draft,groups:draft.groups.map(item=>item.id===group.id?{...item,collapsed:!item.collapsed}:item)})}>{group.label} · {group.member_ids.length} participants</button>
          <button disabled={disabled} onClick={()=>update({...draft,groups:draft.groups.filter(item=>item.id!==group.id)})}>Ungroup {group.label}</button>
        </div>)}
        <ManualCombatRosterTable draft={draft} profile={base.ruleset} disabled={disabled} projection={projection} sourceRegionId={sourceRegionId}
          onTurnChange={update}
          onActorChange={actorChange} onParticipation={(id,participation)=>update(setManualParticipation(draft,id,participation))}
          onMove={move} onRemove={id=>{if(update(removeManualActor(draft,id)))setGroupMembers(ids=>ids.filter(item=>item!==id));}}
          onProject={(id,trigger)=>{sourceTrigger.current=trigger;setProjection(id);}} onError={setError}/>
        {!draft.entities.length&&<p>Add participants to begin. Values come from this encounter’s profile.</p>}
        {draft.turn.kind==='side'&&<ManualCombatSides draft={draft} disabled={disabled} onChange={update}/>}
        <form onSubmit={event=>{event.preventDefault();if(!name.trim())return;
          const actor=newManualActor(base.ruleset,name.trim());if(draft.turn.kind==='side')actor.side_id=newSide;
          if(update({...draft,entities:[...draft.entities,actor]}))setName('');}}>
          <label>Participant name<input value={name} maxLength={160} disabled={disabled} onChange={event=>setName(event.target.value)}/></label><button disabled={disabled||!name.trim()||draft.entities.length>=100}>Add participant</button>
          {draft.turn.kind==='side'&&<label>Side for new participants<select disabled={disabled} value={newSide??''} onChange={event=>setAdditionSide(event.target.value||null)}>
            <option value="">Unassigned</option>{draft.sides.map(side=><option key={side.id} value={side.id}>{side.label}</option>)}
          </select></label>}
        </form>
        <details><summary>Group participants</summary><label>Group name<input value={groupName} maxLength={160} disabled={disabled} onChange={event=>setGroupName(event.target.value)}/></label>
          {draft.entities.filter(actor=>!draft.groups.some(group=>group.member_ids.includes(actor.id))).map(actor=><label key={actor.id}><input type="checkbox" disabled={disabled} checked={groupMembers.includes(actor.id)} onChange={event=>setGroupMembers(items=>event.target.checked?[...items,actor.id]:items.filter(id=>id!==actor.id))}/>{actor.name}</label>)}
          <button disabled={disabled||!groupName.trim()||!groupMembers.length} onClick={()=>{if(update({...draft,groups:[...draft.groups,{id:crypto.randomUUID(),label:groupName.trim(),member_ids:groupMembers,collapsed:false}]})){setGroupName('');setGroupMembers([]);}}}>Create group</button>
        </details>
        <ManualCombatSourcePicker worldId={base.world_id} disabled={disabled||draft.entities.length>=100} onAdd={(identity,source)=>{
          const actor=newManualActor(base.ruleset,identity.label);actor.world_identity=identity;actor.mechanics_snapshot=source;
          if(draft.turn.kind==='side')actor.side_id=newSide;
          return update({...draft,entities:[...draft.entities,actor]});
        }}/>
      </div>
      {projected?.mechanics_snapshot&&<aside ref={sourcePanel} tabIndex={-1} id={sourceRegionId} className="manual-combat-source" aria-label={`Exact source for ${projected.name}`}>
        <header><strong>{projected.name} · exact source</strong><button onClick={closeProjection}>Close source</button></header>
        <p>Authored tracker values are independent of this saved source.</p>
        <CombatSavedStatblock revision={projected.mechanics_snapshot.resource} chrome="campaign"/>
      </aside>}
    </div>
  </section>;
}
