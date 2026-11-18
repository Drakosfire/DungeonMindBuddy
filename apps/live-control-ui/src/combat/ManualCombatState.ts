import type {ManualCombatActor,ManualCombatDraft,ManualCombatProfile,ManualResource} from './ManualCombatTypes';

export function newManualActor(profile:ManualCombatProfile,name:string):ManualCombatActor {
  return {id:crypto.randomUUID(),name,side_id:null,participation:'in_action',notes:'',statuses:[],tags:[],
    world_identity:null,mechanics_snapshot:null,values:{
      stats:Object.fromEntries(profile.stats.map(field=>[field.field_id,field.initial])),
      resources:Object.fromEntries(profile.resources.map(field=>[field.field_id,{...field.initial}]))}};
}
export function adjustManualResource(value:ManualResource,direction:1|-1,amount:number):ManualResource {
  if(value.current===null||!Number.isInteger(amount)||amount<=0)throw new Error('Set a current value and a positive whole adjustment.');
  const current=value.current;
  if(direction===1&&value.maximum!==null&&current>=value.maximum
    ||direction===-1&&value.minimum!==null&&current<=value.minimum)return value;
  const candidate=current+direction*amount;
  if(!Number.isSafeInteger(candidate)||Math.abs(candidate)>999999)throw new Error('Resource adjustment exceeds the supported range.');
  return {...value,current:direction===1&&value.maximum!==null?Math.min(candidate,value.maximum)
    :direction===-1&&value.minimum!==null?Math.max(candidate,value.minimum):candidate};
}
export function advanceManualTurn(draft:ManualCombatDraft):ManualCombatDraft {
  if(draft.turn.kind==='side')return passManualSide(draft);
  const actors=draft.entities.filter(actor=>actor.participation==='in_action');
  if(!actors.length)return {...draft,turn:{...draft.turn,active_actor_id:null}};
  const index=actors.findIndex(actor=>actor.id===draft.turn.active_actor_id);
  const next=actors[(index+1)%actors.length].id;
  if(draft.turn.kind==='ordered')return {...draft,turn:{...draft.turn,active_actor_id:next}};
  const anchor=draft.turn.round_start_actor_id;
  // An unavailable anchor remains a canonical position, so its successor marks
  // the boundary without silently restarting the round on defeat or reorder.
  const anchorIndex=draft.entities.findIndex(actor=>actor.id===anchor);
  const boundary=anchor===null?next:draft.entities.slice(anchorIndex).concat(draft.entities.slice(0,anchorIndex))
    .find(actor=>actor.participation==='in_action')?.id;
  const round=index!==-1&&next===boundary?draft.turn.round+1:draft.turn.round;
  if(round>9999)throw new Error('Round limit reached.');
  return {...draft,turn:{...draft.turn,active_actor_id:next,round,round_start_actor_id:anchor??next}};
}
export function setManualParticipation(draft:ManualCombatDraft,id:string,participation:ManualCombatActor['participation']):ManualCombatDraft {
  const entities=draft.entities.map(actor=>actor.id===id?{...actor,participation}:actor);
  if(draft.turn.active_actor_id!==id||participation==='in_action')return {...draft,entities};
  if(draft.turn.kind==='side')return {...draft,entities,turn:{...draft.turn,active_actor_id:null}};
  const index=entities.findIndex(actor=>actor.id===id);
  const successor=entities.slice(index+1).concat(entities.slice(0,index)).find(actor=>actor.participation==='in_action');
  return {...draft,entities,turn:{...draft.turn,active_actor_id:successor?.id??null}};
}

export function removeManualActor(draft:ManualCombatDraft,id:string):ManualCombatDraft {
  const participating=setManualParticipation(draft,id,'out_of_action');
  const index=draft.entities.findIndex(actor=>actor.id===id);
  const entities=participating.entities.filter(actor=>actor.id!==id);
  const turn={...participating.turn};
  if(turn.kind==='ordered_rounds'&&turn.round_start_actor_id===id) {
    turn.round_start_actor_id=entities[index%entities.length]?.id??null;
  }
  if(turn.kind==='side')turn.acted_actor_ids=turn.acted_actor_ids.filter(actor=>actor!==id);
  return {...participating,entities,turn,groups:draft.groups.map(group=>({...group,member_ids:group.member_ids.filter(member=>member!==id)})).filter(group=>group.member_ids.length>0)};
}

export function selectManualSide(draft:ManualCombatDraft,id:string|null):ManualCombatDraft {
  if(draft.turn.kind!=='side')throw new Error('This encounter uses ordered turns.');
  if(id!==null&&!draft.sides.some(side=>side.id===id))throw new Error('Choose a side in this encounter.');
  if(draft.turn.active_side_id===id)return draft;
  return {...draft,turn:{kind:'side',active_side_id:id,active_actor_id:null,acted_actor_ids:[]}};
}
export function passManualSide(draft:ManualCombatDraft):ManualCombatDraft {
  if(draft.turn.kind!=='side')throw new Error('This encounter uses ordered turns.');
  if(!draft.sides.length)return selectManualSide(draft,null);
  const activeSide=draft.turn.active_side_id;
  const index=draft.sides.findIndex(side=>side.id===activeSide);
  const next=draft.sides[(index+1)%draft.sides.length].id;
  // Passing a single side starts its next phase too; direct re-selection is a no-op.
  return {...draft,turn:{kind:'side',active_side_id:next,active_actor_id:null,acted_actor_ids:[]}};
}
export function actManualParticipant(draft:ManualCombatDraft,id:string):ManualCombatDraft {
  if(draft.turn.kind!=='side')throw new Error('This encounter uses ordered turns.');
  const actor=draft.entities.find(actor=>actor.id===id);
  if(!actor||actor.participation!=='in_action'||draft.turn.active_side_id===null||actor.side_id!==draft.turn.active_side_id)
    throw new Error('Choose an in-action participant on the active side.');
  return {...draft,turn:{...draft.turn,active_actor_id:id,acted_actor_ids:draft.turn.acted_actor_ids.filter(item=>item!==id)}};
}
export function finishManualParticipant(draft:ManualCombatDraft):ManualCombatDraft {
  if(draft.turn.kind!=='side'||!draft.turn.active_actor_id)return draft;
  return {...draft,turn:{...draft.turn,active_actor_id:null,acted_actor_ids:[...draft.turn.acted_actor_ids,draft.turn.active_actor_id]}};
}
export function assignManualSide(draft:ManualCombatDraft,id:string,sideId:string|null):ManualCombatDraft {
  if(sideId!==null&&!draft.sides.some(side=>side.id===sideId))throw new Error('Choose a side in this encounter.');
  const actor=draft.entities.find(actor=>actor.id===id);
  if(!actor||actor.side_id===sideId)return draft;
  const turn=draft.turn.kind==='side'?{...draft.turn,
    active_actor_id:draft.turn.active_actor_id===id?null:draft.turn.active_actor_id,
    acted_actor_ids:draft.turn.acted_actor_ids.filter(item=>item!==id)}:draft.turn;
  return {...draft,turn,entities:draft.entities.map(item=>item.id===id?{...item,side_id:sideId}:item)};
}
export function removeManualSide(draft:ManualCombatDraft,id:string):ManualCombatDraft {
  const turn=draft.turn.kind==='side'&&draft.turn.active_side_id===id
    ?{kind:'side' as const,active_side_id:null,active_actor_id:null,acted_actor_ids:[]}:draft.turn;
  return {...draft,turn,sides:draft.sides.filter(side=>side.id!==id),entities:draft.entities.map(actor=>actor.side_id===id?{...actor,side_id:null}:actor)};
}
