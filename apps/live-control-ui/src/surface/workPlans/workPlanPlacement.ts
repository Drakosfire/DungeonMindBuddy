import type {AuthoredGraphReferenceV1} from '../../api/types';
import {isAuthoredGraphReferenceList,mergeAuthoredReferences} from '../../agentInteraction/authoredGraphReferences';
import type {BuildProposalBasis} from '../../api/buildDocumentProposalApi';
import {planObjective,type WorkPlan,type WorkStep} from '../../api/conversationWorkPlanApi';
import {canonical,exact} from '../../shared/sourcePassageProtocol';
import {parseWorkPlanReference,workPlanFence,workPlanIdentity,type WorkPlanReference} from './workPlanReference';

export const PLACEMENT_CHANGED='dmb-work-plan-placement-change';
export type PlacementPhase='staged'|'review_saving'|'review_saved'|'applying'|'page_save_uncertain'|'saved'|'discarded';
export interface PlacementTransaction {
  apply_id:string;before_editor_sha256:string;after_editor_sha256:string;before_draft_sha256:string;after_draft_sha256:string;
}
interface RetiredPlacement {
  command_id:string;basis:BuildProposalBasis;reference:WorkPlanReference;reference_markdown:string;reference_sha256:string;
  review_snapshot?:{rows:WorkStep[];objective:string|null;root_references?:AuthoredGraphReferenceV1[];schema:WorkPlanPlacement['schema'];phase:PlacementPhase;expected_review_revision:number;acknowledged_review_revision:number|null};
  prepared:PlacementTransaction|null;disposition:'superseded_unresolved'|'superseded_unapplied';
}
interface PlacementBase {
  reference:WorkPlanReference;command_id:string;basis:BuildProposalBasis;
  pointer_revision:number;reference_markdown:string;reference_sha256:string;rows:WorkStep[];
  expected_review_revision:number;acknowledged_review_revision:number|null;prepared:PlacementTransaction|null;
  phase:PlacementPhase;saved:{revision:number;content_sha256:string}|null;retired_placements:RetiredPlacement[];
}
export type WorkPlanPlacement = PlacementBase & ({schema:'dmb_surface_work_plan_placement_v1'}|{schema:'dmb_surface_work_plan_placement_v2';objective:string}|{schema:'dmb_surface_work_plan_placement_v3';objective:string;root_references:AuthoredGraphReferenceV1[]});
export const placementObjective=(p:WorkPlanPlacement)=>p.schema!=='dmb_surface_work_plan_placement_v1'?p.objective:null;
export const placementReferences=(p:WorkPlanPlacement)=>p.schema==='dmb_surface_work_plan_placement_v3'?p.root_references:undefined;
export type PlacementStorage=Pick<Storage,'getItem'|'setItem'>;
export type PlacementLocks=Pick<LockManager,'request'>;
const digest=/^[a-f0-9]{64}$/;
const uuid=/^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$/;
const integer=(value:unknown,min=0):value is number=>typeof value==='number'&&Number.isSafeInteger(value)&&value>=min;
export async function placementDigest(text:string):Promise<string>{
  return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text))),byte=>byte.toString(16).padStart(2,'0')).join('');
}
export const placementKey=(ref:WorkPlanReference)=>'dmb:surface-work-plan-placement:v1:'+workPlanIdentity(ref);
export const placementLockKey=(ref:WorkPlanReference)=>'dmb:surface-work-plan-placement:'+JSON.stringify([ref.world_id,ref.document_id]);
function validBasis(value:unknown,ref:WorkPlanReference):value is BuildProposalBasis{
  if(!value||typeof value!=='object'||Array.isArray(value))return false;
  const v=value as Record<string,unknown>;
  const allowed=['world_id','document_id','registry_revision','content_sha256','visibility','draft_sha256','caret','draft_generation','selection_generation','editor_sha256','selection'];
  return Object.keys(v).every(key=>allowed.includes(key))&&v.world_id===ref.world_id&&v.document_id===ref.document_id
    &&integer(v.registry_revision,1)&&typeof v.content_sha256==='string'&&digest.test(v.content_sha256)
    &&['internal','player_safe'].includes(String(v.visibility))&&typeof v.draft_sha256==='string'&&digest.test(v.draft_sha256)
    &&typeof v.editor_sha256==='string'&&digest.test(v.editor_sha256)&&integer(v.caret)&&integer(v.draft_generation)&&integer(v.selection_generation)
    &&(v.selection===undefined||v.selection===null);
}
function validRows(value:unknown,world?:string,roots?:AuthoredGraphReferenceV1[]):value is WorkStep[]{
  if(!Array.isArray(value)||!value.length)return false;
  const ids=new Set<string>();
  return value.every(row=>{
    if(!exact(row,['step_id','text','selected','kind',...(roots===undefined?[]:['references'])])||typeof row.step_id!=='string'||!uuid.test(row.step_id)||ids.has(row.step_id)
      ||typeof row.text!=='string'||!row.text.trim()||typeof row.selected!=='boolean'||!['discuss','prepare_insertion'].includes(String(row.kind)))return false;
    if(roots!==undefined){if(!isAuthoredGraphReferenceList(row.references,world))return false;try{mergeAuthoredReferences(roots,row.references);}catch{return false;}}
    ids.add(row.step_id);return true;
  });
}
function validTransaction(value:unknown,basis:BuildProposalBasis):value is PlacementTransaction{
  return exact(value,['apply_id','before_editor_sha256','after_editor_sha256','before_draft_sha256','after_draft_sha256'])
    &&typeof value.apply_id==='string'&&uuid.test(value.apply_id)
    &&['before_editor_sha256','after_editor_sha256','before_draft_sha256','after_draft_sha256'].every(key=>typeof value[key]==='string'&&digest.test(value[key] as string))
    &&value.before_editor_sha256===basis.editor_sha256&&value.before_draft_sha256===basis.draft_sha256
    &&value.before_editor_sha256!==value.after_editor_sha256&&value.before_draft_sha256!==value.after_draft_sha256;
}
async function validReference(ref:unknown,markdown:unknown,sha:unknown,owner:WorkPlanReference):Promise<boolean>{
  try{
    const parsed=parseWorkPlanReference(JSON.stringify(ref));
    return workPlanIdentity(parsed)===workPlanIdentity(owner)&&typeof markdown==='string'&&markdown===workPlanFence(parsed)
      &&typeof sha==='string'&&sha===await placementDigest(markdown);
  }catch{return false;}
}
function validReviewSnapshot(v:NonNullable<RetiredPlacement['review_snapshot']>,world:string):boolean{
 const aware=v.schema==='dmb_surface_work_plan_placement_v3';
 return exact(v,['rows','objective','schema','phase','expected_review_revision','acknowledged_review_revision',...(aware?['root_references']:[])])
  &&['dmb_surface_work_plan_placement_v1','dmb_surface_work_plan_placement_v2','dmb_surface_work_plan_placement_v3'].includes(v.schema)
  &&integer(v.expected_review_revision)&&(v.acknowledged_review_revision===null||integer(v.acknowledged_review_revision,1))
  &&['staged','review_saving','review_saved','applying','page_save_uncertain','saved','discarded'].includes(v.phase)
  &&(v.objective===null||typeof v.objective==='string')&&(!aware||isAuthoredGraphReferenceList(v.root_references,world))
  &&validRows(v.rows,world,aware?v.root_references:undefined);
}
/** Never repair retained bytes into apparent success. */
export async function checkedPlacement(value:unknown,owner:WorkPlanReference):Promise<WorkPlanPlacement>{
  if(!exact(value,['schema','reference','command_id','basis','pointer_revision','reference_markdown','reference_sha256','rows','expected_review_revision','acknowledged_review_revision','prepared','phase','saved','retired_placements',...(value&&typeof value==='object'&&'schema' in value&&['dmb_surface_work_plan_placement_v2','dmb_surface_work_plan_placement_v3'].includes(String(value.schema))?['objective',...(value.schema==='dmb_surface_work_plan_placement_v3'?['root_references']:[])]:[])])
    ||!['dmb_surface_work_plan_placement_v1','dmb_surface_work_plan_placement_v2','dmb_surface_work_plan_placement_v3'].includes(String(value.schema))||value.schema!=='dmb_surface_work_plan_placement_v1'&&typeof value.objective!=='string'||value.schema==='dmb_surface_work_plan_placement_v3'&&!isAuthoredGraphReferenceList(value.root_references,owner.world_id)||typeof value.command_id!=='string'||!uuid.test(value.command_id)
    ||!validBasis(value.basis,owner)||!integer(value.pointer_revision,1)||!validRows(value.rows,owner.world_id,value.schema==='dmb_surface_work_plan_placement_v3'?value.root_references as AuthoredGraphReferenceV1[]:undefined)
    ||!integer(value.expected_review_revision)||!(value.acknowledged_review_revision===null||integer(value.acknowledged_review_revision,1))
    ||!['staged','review_saving','review_saved','applying','page_save_uncertain','saved','discarded'].includes(String(value.phase))
    ||!(value.prepared===null||validTransaction(value.prepared,value.basis))||!Array.isArray(value.retired_placements)
    ||!await validReference(value.reference,value.reference_markdown,value.reference_sha256,owner))throw new Error('The retained plan placement needs recovery; its bytes were left untouched.');
  const p=value as unknown as WorkPlanPlacement;
  if((['applying','page_save_uncertain','saved'].includes(p.phase)!==(p.prepared!==null))
    ||(['review_saved','applying','page_save_uncertain','saved'].includes(p.phase)&&p.acknowledged_review_revision===null)
    ||(p.phase==='saved')!==(p.saved!==null)
    ||p.saved!==null&&(!exact(p.saved,['revision','content_sha256'])||!integer(p.saved.revision,p.basis.registry_revision)||!digest.test(p.saved.content_sha256)))
    throw new Error('The retained placement phase differs from its receipt.');
  const commands=new Set([p.command_id]);
  for(const entry of p.retired_placements){
    if(!exact(entry,['command_id','basis','reference','reference_markdown','reference_sha256','prepared','disposition',...(entry.review_snapshot?['review_snapshot']:[])])
      ||entry.review_snapshot!==undefined&&!validReviewSnapshot(entry.review_snapshot,owner.world_id)
      ||typeof entry.command_id!=='string'||!uuid.test(entry.command_id)||commands.has(entry.command_id)||!validBasis(entry.basis,owner)
      ||!await validReference(entry.reference,entry.reference_markdown,entry.reference_sha256,owner)
      ||!(entry.prepared===null||validTransaction(entry.prepared,entry.basis))
      ||!['superseded_unresolved','superseded_unapplied'].includes(String(entry.disposition))
      ||(entry.disposition==='superseded_unresolved')!==(entry.prepared!==null))throw new Error('The earlier plan placement differs from its retained receipt.');
    commands.add(entry.command_id);
  }
  return p;
}
export async function readPlacement(ref:WorkPlanReference,storage:PlacementStorage=localStorage):Promise<WorkPlanPlacement|null>{
  const bytes=storage.getItem(placementKey(ref));
  if(bytes===null)return null;
  return checkedPlacement(JSON.parse(bytes),ref);
}
async function persist(p:WorkPlanPlacement,storage:PlacementStorage){
  await checkedPlacement(p,p.reference);
  const bytes=JSON.stringify(p),key=placementKey(p.reference);
  storage.setItem(key,bytes);
  if(storage.getItem(key)!==bytes)throw new Error('Plan placement storage did not retain the exact receipt. Nothing else was authorized.');
  if(typeof window!=='undefined')window.dispatchEvent(new CustomEvent(PLACEMENT_CHANGED,{detail:workPlanIdentity(p.reference)}));
}
export async function withPlacementLock<T>(ref:WorkPlanReference,action:()=>Promise<T>,locks:PlacementLocks|undefined=navigator.locks):Promise<T>{
  if(!locks)throw new Error('Safe page placement needs browser tab coordination. Your plan is retained.');
  return locks.request(placementLockKey(ref),async()=>action());
}
/** Lock BEFORE the first read/write, so a new tab cannot replace an uncertain attempt. */
export async function stagePlacement(ref:WorkPlanReference,basis:BuildProposalBasis,pointerRevision:number,rows:WorkStep[],expectedRevision=0,
  storage:PlacementStorage=localStorage,locks:PlacementLocks|undefined=navigator.locks,objective:string|null=null,rootReferences?:AuthoredGraphReferenceV1[]):Promise<WorkPlanPlacement>{
  return withPlacementLock(ref,async()=>{
    const existing=await readPlacement(ref,storage);
    if(existing)return existing;
    const markdown=workPlanFence(ref);
    const created:WorkPlanPlacement={...(rootReferences!==undefined?{schema:'dmb_surface_work_plan_placement_v3' as const,objective:objective??'',root_references:rootReferences}:objective===null?{schema:'dmb_surface_work_plan_placement_v1' as const}:{schema:'dmb_surface_work_plan_placement_v2' as const,objective}),reference:ref,command_id:crypto.randomUUID(),basis,
      pointer_revision:pointerRevision,reference_markdown:markdown,reference_sha256:await placementDigest(markdown),rows:rootReferences===undefined?rows:rows.map(row=>({...row,references:row.references??[]})),
      expected_review_revision:expectedRevision,acknowledged_review_revision:null,prepared:null,phase:'staged',saved:null,retired_placements:[]};
    await persist(created,storage);return created;
  },locks);
}
/** Every mutation compares the full old receipt, not just its still-shared command ID. */
export async function changePlacement(expected:WorkPlanPlacement,change:(current:WorkPlanPlacement)=>WorkPlanPlacement,
  storage:PlacementStorage=localStorage,locks:PlacementLocks|undefined=navigator.locks):Promise<WorkPlanPlacement>{
  return withPlacementLock(expected.reference,async()=>{
    const current=await readPlacement(expected.reference,storage);
    if(!current||canonical(current)!==canonical(expected))throw new Error('This plan placement changed in another tab. Inspect it before continuing.');
    const next=change(current);
    if(next.command_id!==current.command_id||workPlanIdentity(next.reference)!==workPlanIdentity(current.reference)
      ||canonical(next.basis)!==canonical(current.basis)||next.pointer_revision!==current.pointer_revision
      ||current.prepared!==null&&(canonical(next.prepared)!==canonical(current.prepared)||next.reference_sha256!==current.reference_sha256||canonical(next.rows)!==canonical(current.rows)||placementObjective(next)!==placementObjective(current)||canonical(placementReferences(next))!==canonical(placementReferences(current)))
      ||canonical(next.retired_placements)!==canonical(current.retired_placements))throw new Error('A new placement requires explicit predecessor retention.');
    await persist(next,storage);return next;
  },locks);
}
/** Explicit re-placement preserves uncertain predecessor bytes before changing the current basis. */
export async function replacePlacement(expected:WorkPlanPlacement,basis:BuildProposalBasis,pointerRevision:number,
  storage:PlacementStorage=localStorage,locks:PlacementLocks|undefined=navigator.locks):Promise<WorkPlanPlacement>{
  return withPlacementLock(expected.reference,async()=>{
    const current=await readPlacement(expected.reference,storage);
    if(!current||canonical(current)!==canonical(expected)||(current.phase==='saved'||current.phase==='review_saving'&&current.schema!=='dmb_surface_work_plan_placement_v1'))
      throw new Error('Check the current placement and review outcome before choosing a new position.');
    if(current.schema==='dmb_surface_work_plan_placement_v1'&&current.prepared)throw new Error('Check and finish the earlier legacy page Save before changing its outcome or placement.');
    const previous:RetiredPlacement={command_id:current.command_id,basis:current.basis,reference:current.reference,
      reference_markdown:current.reference_markdown,reference_sha256:current.reference_sha256,prepared:current.prepared,review_snapshot:{rows:current.rows,objective:placementObjective(current),schema:current.schema,...(current.schema==='dmb_surface_work_plan_placement_v3'?{root_references:current.root_references}:{}),phase:current.phase,expected_review_revision:current.expected_review_revision,acknowledged_review_revision:current.acknowledged_review_revision},
      disposition:current.prepared?'superseded_unresolved':'superseded_unapplied'};
    const next:WorkPlanPlacement={...current,command_id:crypto.randomUUID(),basis,pointer_revision:pointerRevision,
      prepared:null,saved:null,phase:current.acknowledged_review_revision?'review_saved':'staged',retired_placements:[...current.retired_placements,previous]};
    await persist(next,storage);return next;
  },locks);
}

/** A single explicit Save holds the document lock across its review/page joins. */
export async function placementSession<T>(ref:WorkPlanReference,action:(session:{read:()=>Promise<WorkPlanPlacement|null>;change:(expected:WorkPlanPlacement,next:WorkPlanPlacement)=>Promise<WorkPlanPlacement>})=>Promise<T>,
 storage:PlacementStorage=localStorage,locks:PlacementLocks|undefined=navigator.locks):Promise<T>{
 return withPlacementLock(ref,async()=>{
  let active=true;
  const assertActive=()=>{if(!active)throw new Error('This placement session has ended.');};
  try{return await action({read:()=>{assertActive();return readPlacement(ref,storage);},change:async(expected,next)=>{
   assertActive();const current=await readPlacement(ref,storage);
   if(!current||canonical(current)!==canonical(expected)||next.command_id!==current.command_id
     ||canonical(next.basis)!==canonical(current.basis)||next.pointer_revision!==current.pointer_revision
     ||workPlanIdentity(next.reference)!==workPlanIdentity(ref)||canonical(next.retired_placements)!==canonical(current.retired_placements)
     ||current.prepared!==null&&(canonical(next.prepared)!==canonical(current.prepared)||next.reference_sha256!==current.reference_sha256||canonical(next.rows)!==canonical(current.rows)||placementObjective(next)!==placementObjective(current)||canonical(placementReferences(next))!==canonical(placementReferences(current))))
    throw new Error('The retained placement changed. Inspect it before continuing.');
   await persist(next,storage);return next;
  }});}finally{active=false;}
 },locks);
}

export interface PlacementPageIO<Prepared> {
 objective?:string;
 rootReferences?:AuthoredGraphReferenceV1[];
 assertCurrent:()=>void;
 readReview:()=>Promise<import('../../api/conversationWorkPlanApi').WorkPlan|null>;
 saveReview:(revision:number,rows:WorkStep[],objective:string,rootReferences?:AuthoredGraphReferenceV1[])=>Promise<import('../../api/conversationWorkPlanApi').WorkPlan>;
 findSaved:()=>Promise<{revision:number;content_sha256:string;body_sha256:string}|null>;
 prepare:(placement:WorkPlanPlacement)=>Promise<{value:Prepared;after_editor_sha256:string;after_draft_sha256:string}>;
 inspect:(placement:WorkPlanPlacement)=>Promise<'before'|'after'|'changed'>;
 apply:(prepared:Prepared)=>void;
 save:(placement:WorkPlanPlacement)=>Promise<{revision:number;content_sha256:string}>;
}
/** Explicit author Save only. No generation/dispatch is available to this owner. */
export async function savePlacementOnPage<T>(expected:WorkPlanPlacement,rows:WorkStep[],io:PlacementPageIO<T>,
 storage:PlacementStorage=localStorage,locks:PlacementLocks|undefined=navigator.locks):Promise<{placement:WorkPlanPlacement;alreadyPresent:boolean}>{
 return placementSession(expected.reference,async session=>{
  let current=await session.read();
  if(!current||canonical(current)!==canonical(expected)||current.phase==='discarded')throw new Error('The placement changed. Inspect its current state before saving.');
  io.assertCurrent();
  async function verifyAcknowledgedReview(placement:WorkPlanPlacement){
   const plan=await io.readReview();io.assertCurrent();
   if(!plan||plan.revision!==placement.acknowledged_review_revision||canonical(plan.steps)!==canonical(placement.rows)||placementObjective(placement)!==(plan.schema==='dmb_reviewed_work_plan_v1'?null:plan.objective)||canonical(placementReferences(placement))!==canonical(plan.schema==='dmb_reviewed_work_plan_v3'?plan.root_references:undefined)
    ||plan.world_id!==placement.reference.world_id||plan.document_id!==placement.reference.document_id
    ||plan.conversation_id!==placement.reference.conversation_id||plan.source_turn_id!==placement.reference.source_turn_id
    ||plan.source_answer_sha256!==placement.reference.source_answer_sha256)
    throw new Error('The acknowledged plan review changed. The earlier placement is retained; compare the reviews before continuing.');
  }
  if(current.prepared)await verifyAcknowledgedReview(current);
  const existing=await io.findSaved();io.assertCurrent();
  if(existing){
   if(current.prepared&&existing.body_sha256===current.prepared.after_draft_sha256){
    await verifyAcknowledgedReview(current);
    current=await session.change(current,{...current,phase:'saved',saved:{revision:existing.revision,content_sha256:existing.content_sha256}});
   }
   return {placement:current,alreadyPresent:true};
  }
  if(current.phase==='saved')throw new Error('The saved plan object is no longer on this page. Inspect the page before placing it again.');
  if(!current.prepared){
   const objective=io.objective??placementObjective(current)??'';
   if(!objective.trim())throw new Error('Add an expected outcome before saving this plan.');
   const roots=io.rootReferences??placementReferences(current);
   const reviewedRows=roots===undefined?rows:rows.map(row=>({...row,references:row.references??[]}));
   if(current.phase==='review_saving'&&(canonical(current.rows)!==canonical(reviewedRows)||current.schema!=='dmb_surface_work_plan_placement_v1'&&current.objective!==objective||canonical(placementReferences(current))!==canonical(roots)))throw new Error('Resolve the earlier review Save before changing these rows.');
   let plan=await io.readReview();io.assertCurrent();
   if(plan&&(plan.world_id!==current.reference.world_id||plan.document_id!==current.reference.document_id
    ||plan.conversation_id!==current.reference.conversation_id||plan.source_turn_id!==current.reference.source_turn_id
    ||plan.source_answer_sha256!==current.reference.source_answer_sha256))throw new Error('The saved review belongs to another object.');
   if(!plan&&current.acknowledged_review_revision!==null)throw new Error('The saved review is no longer available. Its placement was retained.');
   if(current.schema==='dmb_surface_work_plan_placement_v1'&&current.phase==='review_saving')throw new Error('The legacy review Save needs an explicit outcome-aware new placement. Its original receipt is retained.');
   if(plan?.schema==='dmb_reviewed_work_plan_v3'&&roots===undefined)throw new Error('This saved review now has Graph context. Compare and explicitly adopt its reference-aware review before placing it.');
   const needsPut=!plan||canonical(plan.steps)!==canonical(reviewedRows)||planObjective(plan)!==objective||canonical(plan.schema==='dmb_reviewed_work_plan_v3'?plan.root_references:undefined)!==canonical(roots);
   if(roots!==undefined&&(plan?.revision??0)!==current.expected_review_revision&&!(current.phase==='review_saving'&&!needsPut&&plan?.revision===current.expected_review_revision+1))throw new Error('The reviewed plan changed in another tab. Your Graph context and rows were retained.');
   if(needsPut&&(plan?.revision??0)!==current.expected_review_revision)throw new Error('The reviewed plan changed in another tab. Your rows were retained.');
   current=await session.change(current,{...current,...(roots===undefined?{schema:'dmb_surface_work_plan_placement_v2' as const}:{schema:'dmb_surface_work_plan_placement_v3' as const,root_references:roots}),objective,rows:reviewedRows,phase:'review_saving'});
   if(needsPut){plan=await io.saveReview(current.expected_review_revision,current.rows,objective,roots);io.assertCurrent();}
   if(!plan)throw new Error('The review Save did not return a plan.');
   if(roots!==undefined&&needsPut&&plan.revision!==current.expected_review_revision+1)throw new Error('The reference-aware review acknowledgment has a different revision. Its placement was retained.');
   if(canonical(plan.steps)!==canonical(current.rows)||planObjective(plan)!==objective||canonical(plan.schema==='dmb_reviewed_work_plan_v3'?plan.root_references:undefined)!==canonical(roots)||plan.world_id!==current.reference.world_id||plan.document_id!==current.reference.document_id
     ||plan.conversation_id!==current.reference.conversation_id||plan.source_turn_id!==current.reference.source_turn_id||plan.source_answer_sha256!==current.reference.source_answer_sha256)
    throw new Error('The acknowledged plan differs from the reviewed page object.');
   current=await session.change(current,{...current,phase:'review_saved',expected_review_revision:plan.revision,acknowledged_review_revision:plan.revision});
   const prepared=await io.prepare(current);io.assertCurrent();
   current=await session.change(current,{...current,phase:'applying',prepared:{apply_id:crypto.randomUUID(),before_editor_sha256:current.basis.editor_sha256!,before_draft_sha256:current.basis.draft_sha256,
    after_editor_sha256:prepared.after_editor_sha256,after_draft_sha256:prepared.after_draft_sha256}});
   await verifyAcknowledgedReview(current);io.assertCurrent();io.apply(prepared.value);
  }else{
   if(canonical(rows)!==canonical(current.rows)||current.schema!=='dmb_surface_work_plan_placement_v1'&&io.objective!==undefined&&current.objective!==io.objective||io.rootReferences!==undefined&&canonical(io.rootReferences)!==canonical(placementReferences(current)))throw new Error('The earlier insertion must be checked before changing this object.');
   const inspected=await io.inspect(current);io.assertCurrent();
   if(inspected==='changed')throw new Error('The page changed around the earlier insertion. Compare retained copies before explicitly choosing a new position.');
   if(inspected==='before'){
    const prepared=await io.prepare(current);io.assertCurrent();
    if(prepared.after_editor_sha256!==current.prepared.after_editor_sha256||prepared.after_draft_sha256!==current.prepared.after_draft_sha256)
     throw new Error('The prepared plan insertion differs from the retained transaction. Nothing was inserted.');
    await verifyAcknowledgedReview(current);io.apply(prepared.value);
   }
  }
  try{
   await verifyAcknowledgedReview(current);
   const saved=await io.save(current);
   await verifyAcknowledgedReview(current);
   current=await session.change(current,{...current,phase:'saved',saved});
   return {placement:current,alreadyPresent:false};
  }catch(error){
   // Keep the exact applying receipt even if this follow-up storage write fails.
   try{current=await session.change(current,{...current,phase:'page_save_uncertain',saved:null});}catch{/* Existing before/after data stays authoritative. */}
   throw error;
  }
 },storage,locks);
}

/** Explicit review adoption retains local edits and replaces the receipt in one locked write. */
export async function adoptPlacementReview(expected:WorkPlanPlacement,local:{rows:WorkStep[];objective:string;rootReferences?:AuthoredGraphReferenceV1[]},review:Extract<WorkPlan,{schema:'dmb_reviewed_work_plan_v3'}>,
 storage:PlacementStorage=localStorage,locks:PlacementLocks|undefined=navigator.locks):Promise<WorkPlanPlacement>{
 return withPlacementLock(expected.reference,async()=>{
  const current=await readPlacement(expected.reference,storage);
  if(!current||canonical(current)!==canonical(expected)||current.prepared||['saved','discarded','review_saving'].includes(current.phase))throw new Error('Check the retained placement before adopting another review.');
  const ref=current.reference;
  if(review.world_id!==ref.world_id||review.document_id!==ref.document_id||review.conversation_id!==ref.conversation_id||review.source_turn_id!==ref.source_turn_id||review.source_answer_sha256!==ref.source_answer_sha256)throw new Error('The saved review belongs to another page or response.');
  const localCopy:WorkPlanPlacement={...current,...(local.rootReferences===undefined?{schema:'dmb_surface_work_plan_placement_v2' as const}:{schema:'dmb_surface_work_plan_placement_v3' as const,root_references:local.rootReferences}),rows:local.rows,objective:local.objective};
  await checkedPlacement(localCopy,ref);
  const previous:RetiredPlacement={command_id:current.command_id,basis:current.basis,reference:ref,reference_markdown:current.reference_markdown,reference_sha256:current.reference_sha256,prepared:null,disposition:'superseded_unapplied',review_snapshot:{rows:localCopy.rows,objective:placementObjective(localCopy),schema:localCopy.schema,...(localCopy.schema==='dmb_surface_work_plan_placement_v3'?{root_references:localCopy.root_references}:{}),phase:localCopy.phase,expected_review_revision:localCopy.expected_review_revision,acknowledged_review_revision:localCopy.acknowledged_review_revision}};
  const next:WorkPlanPlacement={...current,schema:'dmb_surface_work_plan_placement_v3',command_id:crypto.randomUUID(),root_references:review.root_references,rows:review.steps,objective:review.objective,expected_review_revision:review.revision,acknowledged_review_revision:null,phase:'staged',retired_placements:[...current.retired_placements,previous]};
  await persist(next,storage);return next;
 },locks);
}
