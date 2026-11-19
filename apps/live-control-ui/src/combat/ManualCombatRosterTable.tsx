import {useEffect,useLayoutEffect,useRef,useState} from 'react';
import type {ManualCombatActor,ManualCombatDraft,ManualCombatProfile} from './ManualCombatTypes';
import {ManualCombatValueInput} from './ManualCombatValueInput';
import {actManualParticipant,adjustManualResource,finishManualParticipant,selectManualSpotlight} from './ManualCombatState';

function StatusField({actor,disabled,onChange}:{actor:ManualCombatActor;disabled:boolean;onChange:(statuses:string[])=>boolean}) {
  const [text,setText]=useState(actor.statuses.join(', '));
  const focused=useRef(false);
  useEffect(()=>{if(!focused.current)setText(actor.statuses.join(', '));},[actor.statuses]);
  const parsed=(value:string)=>[...new Set(value.split(',').map(item=>item.trim()).filter(Boolean))];
  return <input aria-label={`Statuses for ${actor.name}`} disabled={disabled} value={text}
    placeholder="Add statuses…" onFocus={()=>{focused.current=true;}}
    onChange={event=>{setText(event.target.value);onChange(parsed(event.target.value));}}
    onBlur={()=>{focused.current=false;setText(onChange(parsed(text))?parsed(text).join(', '):actor.statuses.join(', '));}}
    onKeyDown={event=>{if(event.key==='Enter')event.currentTarget.blur();}}/>;
}

export function ManualCombatRosterTable({draft,profile,disabled,projection,sourceRegionId,onActorChange,onParticipation,onMove,onRemove,onProject,onError,onTurnChange}:{
  draft:ManualCombatDraft;profile:ManualCombatProfile;disabled:boolean;projection:string|null;sourceRegionId:string;
  onActorChange:(actor:ManualCombatActor)=>boolean;
  onParticipation:(id:string,participation:ManualCombatActor['participation'])=>void;
  onMove:(id:string,direction:1|-1)=>void;onRemove:(id:string)=>void;
  onProject:(id:string,trigger:HTMLButtonElement)=>void;onError:(message:string)=>void;
  onTurnChange?:(draft:ManualCombatDraft)=>boolean;
}) {
  const participating=draft.entities.filter(actor=>actor.participation==='in_action');
  const activeRow=useRef<HTMLTableRowElement>(null);
  useLayoutEffect(()=>{activeRow.current?.scrollIntoView?.({block:'nearest',inline:'nearest'});},[draft.turn.active_actor_id]);
  return <div className="manual-combat-table-workspace">
    <p className="manual-combat-count">{draft.entities.length} participants · {participating.length} in action. Scroll across for every profile field and notes.</p>
    <div className="manual-combat-table-scroll" tabIndex={0} role="region" aria-label="Scrollable combat participants">
    <table className="manual-combat-table">
      <caption>Profile tracker values by participant</caption>
      <thead><tr><th scope="col">Participant</th>
        {profile.stats.map(field=><th scope="col" key={field.field_id}>{field.label}</th>)}
        {profile.resources.map(field=><th scope="col" key={field.field_id}>{field.label}</th>)}
        <th scope="col">Statuses</th><th scope="col">Notes and options</th>
      </tr></thead>
      <tbody>{draft.entities.map(actor=>{
        const active=draft.turn.active_actor_id===actor.id;
        const sideTurn=draft.turn.kind==='side'?draft.turn:null;
        const group=draft.groups.find(item=>item.member_ids.includes(actor.id));
        return <tr key={actor.id} ref={active?activeRow:undefined} aria-label={actor.name} hidden={!active&&!!group?.collapsed}
          className={`manual-combat-row${active?' is-active':''}${actor.participation==='out_of_action'?' is-out-of-action':''}`}>
          <th scope="row" className="manual-combat-participant">
            <ManualCombatValueInput label={`Name for ${actor.name}`} kind="name" value={actor.name} maxLength={160} disabled={disabled}
              onValue={value=>onActorChange({...actor,name:String(value)})}/>
            <div className="manual-combat-participant-actions">
              <span>{actor.participation==='out_of_action'?'Out of action':active?'Current turn':'In action'}</span>
              <button disabled={disabled} aria-label={actor.participation==='in_action'?'Take out of action':'Return to action'}
                onClick={()=>onParticipation(actor.id,actor.participation==='in_action'?'out_of_action':'in_action')}>{actor.participation==='in_action'?'Out':'Return'}</button>
              {actor.mechanics_snapshot&&<button aria-label={`Project source for ${actor.name}`} aria-pressed={projection===actor.id} aria-controls={sourceRegionId}
                onClick={event=>onProject(actor.id,event.currentTarget)}>Source</button>}
            </div>
            {draft.turn.kind==='spotlight'&&<button disabled={disabled||!onTurnChange||actor.participation!=='in_action'}
              aria-label={`${active?'Finish spotlight for':'Give spotlight to'} ${actor.name}`}
              onClick={()=>onTurnChange?.(selectManualSpotlight(draft,active?null:actor.id))}>{active?'Finish spotlight':'Spotlight'}</button>}
            {sideTurn&&<>
              <label>Side<select aria-label={`Side for ${actor.name}`} disabled={disabled} value={actor.side_id??''}
                onChange={event=>onActorChange({...actor,side_id:event.target.value||null})}>
                <option value="">Unassigned</option>{draft.sides.map(side=><option key={side.id} value={side.id}>{side.label}</option>)}
              </select></label>
              {sideTurn.acted_actor_ids.includes(actor.id)&&<span className="manual-combat-turn-marker">Took a turn</span>}
              <button disabled={disabled||!onTurnChange||actor.participation!=='in_action'||sideTurn.active_side_id===null||actor.side_id!==sideTurn.active_side_id}
                aria-label={`${active?'Finish turn for':sideTurn.acted_actor_ids.includes(actor.id)?'Act again with':'Act now with'} ${actor.name}`}
                onClick={()=>onTurnChange?.(active?finishManualParticipant(draft):actManualParticipant(draft,actor.id))}>
                {active?'Finish turn':sideTurn.acted_actor_ids.includes(actor.id)?'Act again':'Act now'}
              </button>
            </>}
            {group&&<span className="manual-combat-group-label">{group.label}</span>}
            {actor.world_identity&&<span className="manual-combat-group-label">Graph: {actor.world_identity.label}</span>}
          </th>
          {profile.stats.map(field=><td key={field.field_id} className={`manual-combat-stat${field.value_type==='text'?' is-text':''}`}>
            <ManualCombatValueInput label={`${field.label} for ${actor.name}`} kind={field.value_type} value={actor.values.stats[field.field_id]} disabled={disabled}
              onValue={value=>onActorChange({...actor,values:{...actor.values,stats:{...actor.values.stats,[field.field_id]:value}}})}/>
          </td>)}
          {profile.resources.map(field=>{
            const resource=actor.values.resources[field.field_id];
            const canIncrease=resource.current!==null&&(resource.maximum===null||resource.current<resource.maximum);
            const canDecrease=resource.current!==null&&(resource.minimum===null||resource.current>resource.minimum);
            return <td key={field.field_id} className="manual-combat-resource">
            <div className="manual-combat-resource-current">
              <ManualCombatValueInput label={`${field.label} current for ${actor.name}`} kind="integer" disabled={disabled} value={resource.current}
                onValue={value=>onActorChange({...actor,values:{...actor.values,resources:{...actor.values.resources,[field.field_id]:{...resource,current:value as number|null}}}})}/>
              {([-1,1] as const).map(direction=><button key={direction} disabled={disabled||!(direction===1?canIncrease:canDecrease)}
                aria-label={`${direction===1?'Increase':'Decrease'} ${field.label} for ${actor.name}`} onClick={()=>{
                  try{onActorChange({...actor,values:{...actor.values,resources:{...actor.values.resources,[field.field_id]:adjustManualResource(resource,direction,1)}}});}
                  catch(caught){onError(String(caught));}
                }}>{direction===1?'+':'−'}</button>)}
            </div>
            <details><summary>Bounds{resource.minimum!==null||resource.maximum!==null
              ?` · ${resource.minimum??'—'}…${resource.maximum??'—'}`:''}</summary>{(['minimum','maximum'] as const).map(key=><label key={key}>{key}
              <ManualCombatValueInput label={`${field.label} ${key} for ${actor.name}`} kind="integer" disabled={disabled} value={resource[key]}
                onValue={value=>onActorChange({...actor,values:{...actor.values,resources:{...actor.values.resources,[field.field_id]:{...resource,[key]:value as number|null}}}})}/>
            </label>)}</details>
          </td>;})}
          <td className="manual-combat-statuses"><StatusField actor={actor} disabled={disabled} onChange={statuses=>onActorChange({...actor,statuses})}/></td>
          <td className="manual-combat-options"><details><summary>Notes and participant options{actor.notes?' · notes retained':''}</summary>
            <label>Notes<textarea aria-label={`Notes for ${actor.name}`} value={actor.notes} maxLength={4096} disabled={disabled} onChange={event=>onActorChange({...actor,notes:event.target.value})}/></label>
            <div className="manual-combat-participant-actions">
              <button aria-label={`Move ${actor.name} earlier`} disabled={disabled||participating[0]?.id===actor.id||actor.participation!=='in_action'} onClick={()=>onMove(actor.id,-1)}>Earlier</button>
              <button aria-label={`Move ${actor.name} later`} disabled={disabled||participating.at(-1)?.id===actor.id||actor.participation!=='in_action'} onClick={()=>onMove(actor.id,1)}>Later</button>
            </div>
            <button disabled={disabled} onClick={()=>onRemove(actor.id)}>Remove {actor.name} from encounter draft</button>
          </details></td>
        </tr>;
      })}</tbody>
    </table>
    </div>
  </div>;
}
