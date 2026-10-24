import {describe,it,expect} from 'vitest';
import type {WorldAgentConversationHistoryTurn} from '../api/types';
import {groupConversationAttempts} from './conversationAttemptGroups';
type Item={kind:'world';turn:WorldAgentConversationHistoryTurn}|{kind:'proposal'};
const row=(sequence:number,status='interrupted',question='Discuss this page',surface='build',object='page',world='world',text=''):Item=>({kind:'world',turn:{
 turn_id:`turn-${sequence}`,sequence,lifecycle_status:status,user_text:question,assistant_text:text,
 provenance:{world_id:world,surface_id:surface,primary_work:{object_id:object}},
} as WorldAgentConversationHistoryTurn});
const project=(rows:Item[],barriers?:Set<number>)=>groupConversationAttempts(rows,x=>x.kind==='world'?x.turn:null,barriers);
describe('matching request presentation, never execution authority',()=>{
 it('replaces repeated failures with the latest pending, failed or successful request without changing history',()=>{
  for(const status of ['accepted','running','failed','completed']){
   const rows=[row(1),row(2,'failed'),row(3,status)];const snapshot=JSON.stringify(rows);const groups=project(rows);
   expect(groups).toEqual([{item:rows[2],previous:[rows[0],rows[1]]}]);expect(JSON.stringify(rows)).toBe(snapshot);
  }
 });
 it('keeps successful repeats, partial replies, different questions/worlds/surfaces/objects, gaps and intervening proposals separate',()=>{
  for(const second of [row(2,'interrupted','Other'),row(2,'interrupted','Discuss this page','plan'),
   row(2,'interrupted','Discuss this page','build','other'),row(2,'interrupted','Discuss this page','build','page','other'),row(3)])
    expect(project([row(1),second])).toHaveLength(2);
  expect(project([row(1,'completed'),row(2)])).toHaveLength(2);
  expect(project([row(1,'interrupted','Discuss this page','build','page','world','Partial output'),row(2)])).toHaveLength(2);
  expect(project([row(1),{kind:'proposal'},row(2)])).toHaveLength(3);
  expect(project([row(1),row(2)],new Set([1]))).toHaveLength(2);
 });
 it('stops the chain after an accepted answer, preserving a later intentional repeated question',()=>{
  const rows=[row(1),row(2,'completed'),row(3)];expect(project(rows).map(x=>x.previous.length)).toEqual([1,0]);
 });
});
