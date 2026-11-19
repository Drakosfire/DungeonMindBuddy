import type {ManualCombatDraft} from './ManualCombatTypes';
import {selectManualSpotlight} from './ManualCombatState';

export function ManualSpotlightRail({draft,disabled,onChange}:{draft:ManualCombatDraft;disabled:boolean;onChange:(draft:ManualCombatDraft)=>boolean}) {
  if(draft.turn.kind!=='spotlight')return null;
  const active=draft.turn.active_actor_id;
  return <>
    <strong>Free spotlight</strong>
    <label>Spotlight participant<select disabled={disabled} value={active??''} onChange={event=>onChange(selectManualSpotlight(draft,event.target.value||null))}>
      <option value="">Choose who acts…</option>{draft.entities.filter(actor=>actor.participation==='in_action').map(actor=><option key={actor.id} value={actor.id}>{actor.name}</option>)}
    </select></label>
    <button disabled={disabled||active===null} onClick={()=>onChange(selectManualSpotlight(draft,null))}>Finish spotlight</button>
    <span>No fixed sequence. Choose any participant who is in action.</span>
  </>;
}
