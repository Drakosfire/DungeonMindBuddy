import {useEffect,useRef,useState} from 'react';
import type {ManualCombatActor,ManualCombatDraft,ManualCombatRecord} from './ManualCombatTypes';
import type {RunEncounterScope} from './runEncountersApi';
import {CombatRecoverySession,combatDraftEqual,type CombatRecovery} from './combatRecovery';
import {getAnyWorldCombatEncounter,saveManualCombatEncounter} from './combatApi';
import {isManualCombatRecord} from './ManualCombatTypes';
import {advanceManualTurn,adjustManualResource,newManualActor,setManualParticipation} from './ManualCombatState';
import {CombatSavedStatblock} from './CombatMechanicsInspection';
import {ManualCombatSourcePicker} from './ManualCombatSourcePicker';
import {validManualDraft} from './validateCombatRecovery';

const copy=<T,>(value:T):T=>JSON.parse(JSON.stringify(value)) as T;
function StatusField({actor,disabled,onChange}:{actor:ManualCombatActor;disabled:boolean;onChange:(statuses:string[])=>void}) {
  const [text,setText]=useState(actor.statuses.join(', '));
  useEffect(()=>setText(actor.statuses.join(', ')),[actor.statuses]);
  return <label>Statuses<input aria-label={`Statuses for ${actor.name}`} disabled={disabled} value={text}
    onChange={event=>setText(event.target.value)} onBlur={()=>onChange([...new Set(text.split(',').map(value=>value.trim()).filter(Boolean))])}
    onKeyDown={event=>{if(event.key==='Enter')event.currentTarget.blur();}}/></label>;
}
type Props={record:ManualCombatRecord;scope?:RunEncounterScope;onSaved:(record:ManualCombatRecord)=>void;onBlocked:(blocked:boolean)=>void};

/** One recovery/Save owner; parent hosts retain committed records only. */
export function ManualCombatEditor({record,scope,onSaved,onBlocked}:Props) {
  const session=useRef(new CombatRecoverySession<ManualCombatRecord>());
  const state=useRef({base:record,draft:copy(record.draft),pending:null as CombatRecovery<ManualCombatRecord>['pending']});
  const [draft,setDraft]=useState(state.current.draft),[base,setBase]=useState(record);
  const [ready,setReady]=useState(false),[saving,setSaving]=useState(false);
  const [recovery,setRecovery]=useState<CombatRecovery<ManualCombatRecord>|null>(null);
  const [error,setError]=useState<string|null>(null),[message,setMessage]=useState<string|null>(null);
  const [name,setName]=useState(''),[projection,setProjection]=useState<string|null>(null);
  const [groupName,setGroupName]=useState(''),[groupMembers,setGroupMembers]=useState<string[]>([]);
  const alive=useRef(false);
  const dirty=!combatDraftEqual(base.draft,draft), blocked=!ready||recovery!==null;
  useEffect(()=>{
    alive.current=true;
    void session.current.open(record,()=>alive.current,!scope).then(result=>{
      if(!alive.current)return;
      setRecovery(result.recovery);setReady(true);
      if(result.committedMatch)setMessage('The submitted Save is committed. Later edits remain available to recover.');
    }).catch(caught=>{if(alive.current)setError(String(caught));});
    return ()=>{alive.current=false;session.current.close();};
  },[]);
  useEffect(()=>{onBlocked(dirty||blocked||saving||state.current.pending!==null);},[dirty,blocked,saving,onBlocked]);
  function update(next:ManualCombatDraft) {
    if(blocked||state.current.pending&&!saving)return;
    try {
      if(!validManualDraft(state.current.base,next))throw new Error('Enter valid values for the pinned profile before applying this change.');
      session.current.write(state.current.base,next,state.current.pending);
      state.current.draft=next;setDraft(next);setError(null);
    } catch(caught){setError(String(caught));}
  }
  function actorChange(actor:ManualCombatActor) {update({...state.current.draft,entities:state.current.draft.entities.map(item=>item.id===actor.id?actor:item)});}
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
    if(saving)return;
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
  const disabled=blocked||!!state.current.pending&&!saving;
  return <section className="manual-combat" aria-label="Manual combat encounter">
    <div className="combat-roster-save-rail">
      <span>{base.ruleset.name} · {base.ruleset.system_id} · revision {base.revision}</span>
      <button disabled={blocked||saving||!dirty&&!state.current.pending} onClick={()=>void save()}>{saving?'Saving…':state.current.pending?'Retry Save':'Save'}</button>
      <button disabled={blocked||saving||!dirty||!!state.current.pending} onClick={revert}>Revert</button>
      <button disabled={saving} onClick={()=>void reload()}>Reload committed encounter</button>
      <span role="status">{dirty?'Unsaved changes':'Saved'}{message?` · ${message}`:''}</span>
    </div>
    {error&&<p role="alert" className="module-error">{error}</p>}
    {recovery&&<aside aria-label="Retained Combat draft"><p>Local edits are available. Recover or discard them before editing.</p><button onClick={recover}>Recover local edits</button><button onClick={discard}>Discard retained draft</button></aside>}
    <label>Encounter title<input value={draft.title} maxLength={160} disabled={disabled} onChange={event=>update({...draft,title:event.target.value})}/></label>
    <section className="combat-roster-turn-rail" aria-label="Turn order">
      {draft.turn.kind==='ordered_rounds'&&<strong>Round {draft.turn.round}</strong>}
      <span>Current: {active?.name??'Not started'}</span><span>Next: {next?.name??'No participants'}</span>
      <button disabled={disabled||!participating.length} onClick={()=>{try{update(advanceManualTurn(draft));}catch(caught){setError(String(caught));}}}>{active?'Next turn':'Start turns'}</button>
    </section>
    <div className="manual-combat-workspace">
      <div className="manual-combat-roster">
        {draft.groups.map(group=><div key={group.id} className="manual-combat-group">
          <button disabled={disabled} aria-expanded={!group.collapsed} onClick={()=>update({...draft,groups:draft.groups.map(item=>item.id===group.id?{...item,collapsed:!item.collapsed}:item)})}>{group.label} · {group.member_ids.length} participants</button>
          <button disabled={disabled} onClick={()=>update({...draft,groups:draft.groups.filter(item=>item.id!==group.id)})}>Ungroup {group.label}</button>
        </div>)}
        {draft.entities.map(actor=><article key={actor.id} hidden={active?.id!==actor.id&&draft.groups.some(group=>group.collapsed&&group.member_ids.includes(actor.id))} className={`manual-combat-row ${active?.id===actor.id?'is-active':''}`} aria-label={actor.name}>
          <header><label>Name<input aria-label={`Name for ${actor.name}`} value={actor.name} maxLength={160} disabled={disabled} onChange={event=>actorChange({...actor,name:event.target.value})}/></label>
            <span>{actor.participation==='out_of_action'?'Out of action':active?.id===actor.id?'Current turn':'In action'}</span>
            <button disabled={disabled} onClick={()=>update(setManualParticipation(draft,actor.id,actor.participation==='in_action'?'out_of_action':'in_action'))}>{actor.participation==='in_action'?'Take out of action':'Return to action'}</button>
            <button aria-label={`Move ${actor.name} earlier`} disabled={disabled||participating[0]?.id===actor.id||actor.participation!=='in_action'} onClick={()=>move(actor.id,-1)}>Earlier</button>
            <button aria-label={`Move ${actor.name} later`} disabled={disabled||participating.at(-1)?.id===actor.id||actor.participation!=='in_action'} onClick={()=>move(actor.id,1)}>Later</button>
            {actor.mechanics_snapshot&&<button aria-pressed={projection===actor.id} onClick={()=>setProjection(actor.id)}>Project source for {actor.name}</button>}
          </header>
          <div className="manual-combat-values">
            {base.ruleset.stats.map(field=><label key={field.field_id}>{field.label}
              <input aria-label={`${field.label} for ${actor.name}`} type={field.value_type==='integer'?'number':'text'} min={field.value_type==='integer'?-999999:undefined} max={field.value_type==='integer'?999999:undefined} maxLength={256}
                value={actor.values.stats[field.field_id]??''} disabled={disabled} onChange={event=>actorChange({...actor,values:{...actor.values,stats:{...actor.values.stats,[field.field_id]:event.target.value===''?null:field.value_type==='integer'?Number(event.target.value):event.target.value}}})}/>
            </label>)}
            {base.ruleset.resources.map(field=><fieldset key={field.field_id}><legend>{field.label}</legend>
              {(['current','minimum','maximum'] as const).map(key=><label key={key}>{key}<input aria-label={`${field.label} ${key} for ${actor.name}`} type="number" min={-999999} max={999999} disabled={disabled}
                value={actor.values.resources[field.field_id][key]??''} onChange={event=>actorChange({...actor,values:{...actor.values,resources:{...actor.values.resources,[field.field_id]:{...actor.values.resources[field.field_id],[key]:event.target.value===''?null:Number(event.target.value)}}}})}/></label>)}
              {([-1,1] as const).map(direction=><button key={direction} disabled={disabled||actor.values.resources[field.field_id].current===null} aria-label={`${direction===1?'Increase':'Decrease'} ${field.label} for ${actor.name}`} onClick={()=>{try{actorChange({...actor,values:{...actor.values,resources:{...actor.values.resources,[field.field_id]:adjustManualResource(actor.values.resources[field.field_id],direction,1)}}});}catch(caught){setError(String(caught));}}}>{direction===1?'+1':'−1'}</button>)}
            </fieldset>)}
          </div>
          <StatusField actor={actor} disabled={disabled} onChange={statuses=>actorChange({...actor,statuses})}/>
          <label>Notes<textarea aria-label={`Notes for ${actor.name}`} value={actor.notes} maxLength={4096} disabled={disabled} onChange={event=>actorChange({...actor,notes:event.target.value})}/></label>
          {actor.world_identity&&<p>Graph: {actor.world_identity.label}</p>}
        </article>)}
        {!draft.entities.length&&<p>Add participants to begin. Values come from this encounter’s profile.</p>}
        <form onSubmit={event=>{event.preventDefault();if(!name.trim())return;update({...draft,entities:[...draft.entities,newManualActor(base.ruleset,name.trim())]});setName('');}}>
          <label>Participant name<input value={name} maxLength={160} disabled={disabled} onChange={event=>setName(event.target.value)}/></label><button disabled={disabled||!name.trim()||draft.entities.length>=100}>Add participant</button>
        </form>
        <details><summary>Group participants</summary><label>Group name<input value={groupName} maxLength={160} disabled={disabled} onChange={event=>setGroupName(event.target.value)}/></label>
          {draft.entities.filter(actor=>!draft.groups.some(group=>group.member_ids.includes(actor.id))).map(actor=><label key={actor.id}><input type="checkbox" disabled={disabled} checked={groupMembers.includes(actor.id)} onChange={event=>setGroupMembers(items=>event.target.checked?[...items,actor.id]:items.filter(id=>id!==actor.id))}/>{actor.name}</label>)}
          <button disabled={disabled||!groupName.trim()||!groupMembers.length} onClick={()=>{update({...draft,groups:[...draft.groups,{id:crypto.randomUUID(),label:groupName.trim(),member_ids:groupMembers,collapsed:false}]});setGroupName('');setGroupMembers([]);}}>Create group</button>
        </details>
        <ManualCombatSourcePicker worldId={base.world_id} disabled={disabled||draft.entities.length>=100} onAdd={(identity,source)=>{
          const actor=newManualActor(base.ruleset,identity.label);actor.world_identity=identity;actor.mechanics_snapshot=source;
          update({...draft,entities:[...draft.entities,actor]});
        }}/>
      </div>
      {projected?.mechanics_snapshot&&<aside className="manual-combat-source" aria-label={`Exact source for ${projected.name}`}>
        <header><strong>{projected.name} · exact source</strong><button onClick={()=>setProjection(null)}>Close source</button></header>
        <p>Authored tracker values are independent of this saved source.</p>
        <CombatSavedStatblock revision={projected.mechanics_snapshot.resource} chrome="campaign"/>
      </aside>}
    </div>
  </section>;
}
