import {expect,it} from 'vitest';
import {parseWorkPlanReference,parseWorkPlanFence,workPlanFence,workPlanIdentity,workPlanBelongsTo,type WorkPlanReference} from './workPlanReference';
const ref:WorkPlanReference={schema:'dmb_surface_work_plan_ref_v1',world_id:'world',document_id:'page',conversation_id:'11111111-1111-4111-8111-111111111111',source_turn_id:'22222222-2222-4222-8222-222222222222',source_answer_sha256:'a'.repeat(64),title:'Plan'};
it('round-trips a closed reference, keeping page title outside plan identity',()=>{
 const text=workPlanFence({...ref,title:'A title with "quotes": and ``` fences'});
 expect(parseWorkPlanFence(text)).toEqual({...ref,title:'A title with "quotes": and ``` fences'});
 expect(workPlanIdentity({...ref,title:'Renamed'})).toBe(workPlanIdentity(ref));
 expect(text).not.toContain('steps');expect(text).not.toContain('dispatches');
});
it.each([
 {...ref,steps:[]},{...ref,title:''},{...ref,world_id:' '},{...ref,document_id:null},
 {...ref,source_turn_id:'turn'},{...ref,conversation_id:'no'},{...ref,source_answer_sha256:'x'},
])('rejects malformed or extra reference fields',value=>expect(()=>parseWorkPlanReference(JSON.stringify(value))).toThrow());
it('rejects duplicate and escaped duplicate keys rather than accepting the last value',()=>{
 const raw=JSON.stringify(ref).slice(0,-1);
 expect(()=>parseWorkPlanReference(raw+',"title":"Other"}')).toThrow(/Duplicate/);
 expect(()=>parseWorkPlanReference(raw+',"ti\\u0074le":"Other"}')).toThrow(/Duplicate/);
});
it.each(['```dmb-work-plan-v1\n{}','```dmb-work-plan-v1\n{}\n~~~','````dmb-work-plan-v1\n{}\n```'])('refuses an unclosed or different fence',raw=>expect(()=>parseWorkPlanFence(raw)).toThrow());
it('keeps same-world and same-page checks independent from reference syntax',()=>{
 expect(workPlanBelongsTo(ref,{worldId:'world',documentId:'page'})).toBe(true);
 expect(workPlanBelongsTo(ref,{worldId:'other',documentId:'page'})).toBe(false);
 expect(workPlanBelongsTo(ref,{worldId:'world',documentId:'other'})).toBe(false);
});
