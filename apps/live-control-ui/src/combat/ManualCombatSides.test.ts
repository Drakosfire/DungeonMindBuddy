import {expect,it} from 'vitest';
import {sideCombatRecord} from './ManualCombat.testSupport';
import {actManualParticipant,assignManualSide,finishManualParticipant,passManualSide,removeManualActor,removeManualSide,selectManualSide,setManualParticipation} from './ManualCombatState';
import {validManualDraft} from './validateCombatRecovery';

it('selects arbitrary members and explicitly finishes or repeats a turn without a round counter',()=>{
  const record=sideCombatRecord(),base=structuredClone(record.draft),id=base.entities[0].id;
  let draft=selectManualSide(base,'crew');
  draft=actManualParticipant(draft,id);expect(draft.turn).toMatchObject({active_side_id:'crew',active_actor_id:id,acted_actor_ids:[]});
  draft=finishManualParticipant(draft);expect(draft.turn).toMatchObject({active_actor_id:null,acted_actor_ids:[id]});
  draft=actManualParticipant(draft,id);expect(draft.turn).toMatchObject({active_actor_id:id,acted_actor_ids:[]});
  expect(validManualDraft(record,draft)).toBe(true);expect(base).toEqual(record.draft);expect(draft.turn).not.toHaveProperty('round');
});

it('passes empty sides explicitly and resets markers even when one side cycles to itself',()=>{
  const {draft}=sideCombatRecord();const id=draft.entities[0].id;
  const finished=finishManualParticipant(actManualParticipant(selectManualSide(draft,'crew'),id));
  const empty=passManualSide(finished);expect(empty.turn).toEqual({kind:'side',active_side_id:'river',active_actor_id:null,acted_actor_ids:[]});
  expect(passManualSide(empty).turn).toMatchObject({active_side_id:'watch'});
  expect(passManualSide({...finished,sides:finished.sides.slice(0,1)}).turn).toMatchObject({active_side_id:'crew',acted_actor_ids:[]});
});

it('keeps a finished marker through defeat and return while an active defeat clears only the actor',()=>{
  const {draft}=sideCombatRecord(),id=draft.entities[0].id;
  const active=actManualParticipant(selectManualSide(draft,'crew'),id);
  const out=setManualParticipation(active,id,'out_of_action');
  expect(out.turn).toMatchObject({active_side_id:'crew',active_actor_id:null});
  const finished=finishManualParticipant(active);
  const returned=setManualParticipation(setManualParticipation(finished,id,'out_of_action'),id,'in_action');
  expect(returned.turn).toEqual(finished.turn);expect(returned.entities[0].values).toEqual(draft.entities[0].values);
});

it('repairs assignment, actor deletion and active-side deletion atomically without choosing another side',()=>{
  const record=sideCombatRecord(),id=record.draft.entities[0].id;
  const finished=finishManualParticipant(actManualParticipant(selectManualSide(record.draft,'crew'),id));
  const moved=assignManualSide(finished,id,'watch');expect(moved.turn).toMatchObject({active_side_id:'crew',acted_actor_ids:[]});
  expect(validManualDraft(record,moved)).toBe(true);
  const removed=removeManualActor(finished,id);expect(removed.turn).toMatchObject({acted_actor_ids:[]});expect(validManualDraft(record,removed)).toBe(true);
  const noSide=removeManualSide(finished,'crew');expect(noSide.turn).toEqual(record.draft.turn);expect(noSide.entities[0].side_id).toBeNull();
  expect(validManualDraft(record,noSide)).toBe(true);expect(()=>assignManualSide(finished,id,'foreign')).toThrow();
});

it('rejects stale side, duplicate or foreign markers and ordered state against a pinned side profile',()=>{
  const record=sideCombatRecord(),id=record.draft.entities[0].id;
  const draft=selectManualSide(record.draft,'crew');
  for(const turn of [
    {kind:'side',active_side_id:null,active_actor_id:id,acted_actor_ids:[]},
    {kind:'side',active_side_id:'foreign',active_actor_id:null,acted_actor_ids:[]},
    {kind:'side',active_side_id:'crew',active_actor_id:null,acted_actor_ids:[id,id]},
    {kind:'side',active_side_id:'crew',active_actor_id:null,acted_actor_ids:[record.draft.entities[1].id]},
    {kind:'side',active_side_id:'crew',active_actor_id:id,acted_actor_ids:[id]},
    {kind:'ordered',active_actor_id:null},
  ])expect(validManualDraft(record,{...draft,turn} as typeof draft)).toBe(false);
});
