import {useState} from 'react';
import type {ManualCombatDraft} from './ManualCombatTypes';
import {actManualParticipant,finishManualParticipant,passManualSide,removeManualSide,selectManualSide} from './ManualCombatState';
import {ManualCombatValueInput} from './ManualCombatValueInput';

type Props={draft:ManualCombatDraft;disabled:boolean;onChange:(draft:ManualCombatDraft)=>boolean};

/** Selection is manual; phase markers are an aid, never an action economy. */
export function ManualSideTurnRail({draft,disabled,onChange}:Props) {
  const turn=draft.turn;
  if(turn.kind!=='side')return null;
  const side=draft.sides.find(side=>side.id===turn.active_side_id);
  const actors=draft.entities.filter(actor=>actor.side_id===side?.id&&actor.participation==='in_action');
  const next=draft.sides[(draft.sides.findIndex(item=>item.id===side?.id)+1)%draft.sides.length];
  return <>
    <strong>{side?`${side.label} acts`:'Side turns · not started'}</strong>
    <label>Active side<select disabled={disabled||!draft.sides.length} value={turn.active_side_id??''}
      onChange={event=>onChange(selectManualSide(draft,event.target.value||null))}>
      <option value="">Not started</option>{draft.sides.map(item=><option key={item.id} value={item.id}>{item.label}</option>)}
    </select></label>
    <label>Acting participant<select disabled={disabled||!side||!actors.length} value={turn.active_actor_id??''}
      onChange={event=>{if(event.target.value)onChange(actManualParticipant(draft,event.target.value));}}>
      <option value="" disabled>Choose who acts…</option>{actors.map(actor=><option key={actor.id} value={actor.id}>{actor.name}{turn.acted_actor_ids.includes(actor.id)?' · act again':''}</option>)}
    </select></label>
    <button disabled={disabled||!turn.active_actor_id} onClick={()=>onChange(finishManualParticipant(draft))}>Finish participant turn</button>
    <button disabled={disabled||!draft.sides.length} onClick={()=>onChange(passManualSide(draft))}>{side?'Pass side':'Start side turns'}</button>
    <span>Next side: {next?.label??'Add a side'}</span>
    {side&&!actors.length&&<span>No participants in action on this side. You can pass explicitly.</span>}
    {!draft.sides.length&&<span>Add sides below, then assign participants.</span>}
  </>;
}

export function ManualCombatSides({draft,disabled,onChange}:Props) {
  const [name,setName]=useState('');
  return <details className="manual-combat-sides"><summary>Manage sides · {draft.sides.length}</summary>
    <p>Sides take turns; display groups only collapse rows. Unassigned participants keep their values. Moving a participant clears its current turn marker.</p>
    {draft.sides.map(side=><div key={side.id} className="manual-combat-side">
      <ManualCombatValueInput label={`Name for side ${side.label}`} kind="name" maxLength={160} disabled={disabled} value={side.label}
        onValue={value=>onChange({...draft,sides:draft.sides.map(item=>item.id===side.id?{...item,label:String(value)}:item)})}/>
      <span>{draft.entities.filter(actor=>actor.side_id===side.id).length} participants</span>
      <button disabled={disabled} onClick={()=>onChange(removeManualSide(draft,side.id))}>Remove side {side.label}</button>
    </div>)}
    <form onSubmit={event=>{event.preventDefault();if(name.trim()&&onChange({...draft,sides:[...draft.sides,{id:crypto.randomUUID(),label:name.trim()}]}))setName('');}}>
      <label>Side name<input value={name} maxLength={160} disabled={disabled} onChange={event=>setName(event.target.value)}/></label>
      <button disabled={disabled||!name.trim()||draft.sides.length>=32}>Add side</button>
    </form>
  </details>;
}
