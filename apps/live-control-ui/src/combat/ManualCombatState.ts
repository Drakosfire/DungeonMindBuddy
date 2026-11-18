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
  return {...participating,entities,turn,groups:draft.groups.map(group=>({...group,member_ids:group.member_ids.filter(member=>member!==id)})).filter(group=>group.member_ids.length>0)};
}
