import {beforeEach,expect,it,vi} from 'vitest';
import {webcrypto} from 'node:crypto';
import type {BuildProposalBasis} from '../../api/buildDocumentProposalApi';
import type {WorkStep} from '../../api/conversationWorkPlanApi';
import type {WorkPlanReference} from './workPlanReference';
import {stagePlacement,readPlacement,changePlacement,replacePlacement,checkedPlacement,placementKey,type PlacementLocks,type PlacementStorage,type WorkPlanPlacement} from './workPlanPlacement';
const ref:WorkPlanReference={schema:'dmb_surface_work_plan_ref_v1',world_id:'world',document_id:'page',conversation_id:'11111111-1111-4111-8111-111111111111',source_turn_id:'22222222-2222-4222-8222-222222222222',source_answer_sha256:'a'.repeat(64),title:'Work plan'};
const basis:BuildProposalBasis={world_id:'world',document_id:'page',registry_revision:1,content_sha256:'b'.repeat(64),draft_sha256:'c'.repeat(64),editor_sha256:'d'.repeat(64),visibility:'internal',caret:1,draft_generation:0,selection_generation:0};
const rows:WorkStep[]=[{step_id:'33333333-3333-4333-8333-333333333333',text:'Read the page.',kind:'discuss',selected:true}];
let data:Map<string,string>,locked:boolean,storage:PlacementStorage,locks:PlacementLocks;
beforeEach(()=>{
 vi.stubGlobal('crypto',webcrypto);data=new Map();locked=false;let queue=Promise.resolve();
 storage={getItem:key=>data.get(key)??null,setItem:(key,value)=>{expect(locked).toBe(true);data.set(key,value);}};
 locks={request:(_name:string,fn:()=>Promise<unknown>)=>{const result=queue.then(async()=>{locked=true;try{return await fn();}finally{locked=false;}});queue=result.then(()=>undefined,()=>undefined);return result;}} as PlacementLocks;
});
async function applying(){
 const p=await stagePlacement(ref,basis,1,rows,0,storage,locks);
 return changePlacement(p,current=>({...current,phase:'applying',acknowledged_review_revision:1,
  prepared:{apply_id:'44444444-4444-4444-8444-444444444444',before_editor_sha256:basis.editor_sha256!,before_draft_sha256:basis.draft_sha256,after_editor_sha256:'e'.repeat(64),after_draft_sha256:'f'.repeat(64)}}),storage,locks);
}
it('locks before first shared write and stages the same identity only once',async()=>{
 const [first,second]=await Promise.all([stagePlacement(ref,basis,1,rows,0,storage,locks),stagePlacement(ref,{...basis,caret:2},1,rows,0,storage,locks)]);
 expect(second).toEqual(first);expect(second.basis.caret).toBe(1);expect(data.size).toBe(1);
});
it('a second tab cannot replace an applying attempt with newly staged bytes',async()=>{
 const current=await applying(),before=data.get(placementKey(ref));
 const [second,third]=await Promise.all([stagePlacement(ref,{...basis,caret:4},1,rows,0,storage,locks),stagePlacement(ref,basis,1,rows,0,storage,locks)]);
 expect(second).toEqual(current);expect(third).toEqual(current);expect(data.get(placementKey(ref))).toBe(before);
});
it('compares full retained state so same-command stale views cannot overwrite a later phase',async()=>{
 const original=await stagePlacement(ref,basis,1,rows,0,storage,locks);
 const newer=await changePlacement(original,current=>({...current,phase:'review_saving'}),storage,locks);
 await expect(changePlacement(original,current=>({...current,phase:'discarded'}),storage,locks)).rejects.toThrow(/another tab/);
 expect(await readPlacement(ref,storage)).toEqual(newer);
});
it('preserves exact uncertain predecessors on explicit new placement and refuses silent basis changes',async()=>{
 const previous=await applying();
 await expect(changePlacement(previous,current=>({...current,basis:{...basis,caret:4}}),storage,locks)).rejects.toThrow(/predecessor/);
 const next=await replacePlacement(previous,{...basis,caret:4},2,storage,locks);
 expect(next.command_id).not.toBe(previous.command_id);expect(next.prepared).toBeNull();expect(next.phase).toBe('review_saved');
 expect(next.retired_placements).toEqual([{command_id:previous.command_id,basis:previous.basis,reference:ref,reference_markdown:previous.reference_markdown,reference_sha256:previous.reference_sha256,prepared:previous.prepared,disposition:'superseded_unresolved'}]);
});
it('preserves corrupt retained bytes and refuses all mutation when storage or locks fail',async()=>{
 data.set(placementKey(ref),'corrupt bytes');
 await expect(stagePlacement(ref,basis,1,rows,0,storage,locks)).rejects.toThrow();
 expect(data.get(placementKey(ref))).toBe('corrupt bytes');data.clear();
 await expect(stagePlacement(ref,basis,1,rows,0,{getItem:()=>null,setItem:()=>{throw new Error('blocked storage');}},locks)).rejects.toThrow(/blocked storage/);
 await expect(stagePlacement(ref,basis,1,rows,0,storage,undefined)).rejects.toThrow();expect(data.size).toBe(0);
});
it('refuses a false saved phase and foreign/current snapshot joins',async()=>{
 const p=await stagePlacement(ref,basis,1,rows,0,storage,locks);
 await expect(checkedPlacement({...p,phase:'saved',saved:{revision:1,content_sha256:'f'.repeat(64)}},ref)).rejects.toThrow();
 await expect(checkedPlacement({...p,basis:{...basis,world_id:'foreign'}},ref)).rejects.toThrow();
 await expect(checkedPlacement({...p,unknown:true},ref)).rejects.toThrow();
});

it('persists review and before/after receipt before mutation and recovers a lost Save acknowledgment without reinsertion',async()=>{
 const {savePlacementOnPage}=await import('./workPlanPlacement');
 const initial=await stagePlacement(ref,basis,1,rows,0,storage,locks);
 let review:import('../../api/conversationWorkPlanApi').WorkPlan|null=null,insertions=0,saves=0,pageExists=false;
 const io={assertCurrent:()=>{},readReview:async()=>review,saveReview:async()=>{review={schema:'dmb_reviewed_work_plan_v1',world_id:ref.world_id,document_id:ref.document_id,conversation_id:ref.conversation_id,source_turn_id:ref.source_turn_id,source_answer_sha256:ref.source_answer_sha256,revision:1,steps:rows,dispatches:[],execution:[]};return review;},
  findSaved:async()=>pageExists?{revision:2,content_sha256:'f'.repeat(64),body_sha256:'f'.repeat(64)}:null,
  prepare:async()=>({value:'prepared',after_editor_sha256:'e'.repeat(64),after_draft_sha256:'f'.repeat(64)}),inspect:async()=>'after' as const,
  apply:()=>{const retained=JSON.parse(data.get(placementKey(ref))!);expect(retained.phase).toBe('applying');expect(retained.acknowledged_review_revision).toBe(1);expect(retained.prepared.after_draft_sha256).toBe('f'.repeat(64));insertions++;},
  save:async()=>{saves++;pageExists=true;throw new Error('lost acknowledgment');}};
 await expect(savePlacementOnPage(initial,rows,io,storage,locks)).rejects.toThrow(/lost acknowledgment/);
 const retained=(await readPlacement(ref,storage))!;expect(retained.phase).toBe('page_save_uncertain');expect(insertions).toBe(1);
 const result=await savePlacementOnPage(retained,rows,io,storage,locks);
 expect(result.placement.phase).toBe('saved');expect(result.alreadyPresent).toBe(true);expect(insertions).toBe(1);expect(saves).toBe(1);
});
it('does not overwrite newer review rows or mutate the editor after failed receipt persistence',async()=>{
 const {savePlacementOnPage}=await import('./workPlanPlacement');const initial=await stagePlacement(ref,basis,1,rows,0,storage,locks);
 let saves=0,applies=0;
 const io={assertCurrent:()=>{},readReview:async()=>({schema:'dmb_reviewed_work_plan_v1' as const,world_id:ref.world_id,document_id:ref.document_id,conversation_id:ref.conversation_id,source_turn_id:ref.source_turn_id,source_answer_sha256:ref.source_answer_sha256,revision:2,steps:[{...rows[0],text:'Newer author text'}],dispatches:[],execution:[]}),
  saveReview:async()=>{saves++;throw new Error('must not overwrite');},findSaved:async()=>null,prepare:async()=>({value:'prepared',after_editor_sha256:'e'.repeat(64),after_draft_sha256:'f'.repeat(64)}),inspect:async()=>'before' as const,apply:()=>{applies++;},save:async()=>({revision:2,content_sha256:'f'.repeat(64)})};
 await expect(savePlacementOnPage(initial,rows,io,storage,locks)).rejects.toThrow(/another tab/);expect(saves).toBe(0);expect(applies).toBe(0);
 const retained=(await readPlacement(ref,storage))!;
 const broken:PlacementStorage={getItem:storage.getItem,setItem:()=>{throw new Error('storage blocked');}};
 await expect(savePlacementOnPage(retained,rows,{...io,readReview:async()=>null},broken,locks)).rejects.toThrow(/storage blocked/);expect(applies).toBe(0);
});
