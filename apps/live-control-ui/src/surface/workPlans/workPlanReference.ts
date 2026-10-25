/** Page-owned locator. Reviewed steps and execution remain with APP work_plan. */
export const WORK_PLAN_LANGUAGE='dmb-work-plan-v1';
export interface WorkPlanReference {
  schema:'dmb_surface_work_plan_ref_v1';
  world_id:string;document_id:string;conversation_id:string;source_turn_id:string;
  source_answer_sha256:string;title:string;
}
const keys=['schema','world_id','document_id','conversation_id','source_turn_id','source_answer_sha256','title'];
const uuid=/^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$/;
export function parseWorkPlanReference(raw:string):WorkPlanReference {
  const value:unknown=JSON.parse(raw);
  if(!value||typeof value!=='object'||Array.isArray(value)
    ||Object.keys(value).sort().join(',')!==[...keys].sort().join(','))throw new Error('Invalid work-plan reference fields.');
  const v=value as Record<string,unknown>;
  if(v.schema!=='dmb_surface_work_plan_ref_v1'||keys.some(key=>typeof v[key]!=='string')
    ||![v.world_id,v.document_id,v.title].every(text=>(text as string).trim().length>0)
    ||!uuid.test(v.conversation_id as string)||!uuid.test(v.source_turn_id as string)
    ||!/^[a-f0-9]{64}$/.test(v.source_answer_sha256 as string))throw new Error('Invalid work-plan reference.');
  // All admitted values are strings. Tokenize the already-valid flat JSON so
  // escaped colons/quotes inside a value cannot masquerade as object keys.
  const tokens=raw.match(/"(?:[^"\\]|\\.)*"|[{}:,]/g)??[];
  const seen=new Set<string>();
  for(let i=1;i<tokens.length-1;i+=4){
    const key=JSON.parse(tokens[i]) as string;
    if(seen.has(key))throw new Error('Duplicate work-plan reference key.');
    seen.add(key);
  }
  return {schema:'dmb_surface_work_plan_ref_v1',world_id:v.world_id as string,document_id:v.document_id as string,
    conversation_id:v.conversation_id as string,source_turn_id:v.source_turn_id as string,
    source_answer_sha256:v.source_answer_sha256 as string,title:v.title as string};
}
export function workPlanIdentity(ref:WorkPlanReference):string {
  return JSON.stringify([ref.world_id,ref.document_id,ref.conversation_id,ref.source_turn_id,ref.source_answer_sha256]);
}
export function workPlanFence(ref:WorkPlanReference):string {
  const checked=parseWorkPlanReference(JSON.stringify(ref));
  return '```'+WORK_PLAN_LANGUAGE+'\n'+JSON.stringify(checked)+'\n```';
}
export function parseWorkPlanFence(raw:string):WorkPlanReference {
  const lines=raw.split('\n');
  const open=/^ {0,3}(`{3,}|~{3,})dmb-work-plan-v1[ \t]*$/.exec(lines[0]??'');
  if(!open||!new RegExp('^ {0,3}'+open[1][0]+'{'+open[1].length+',}[ \\t]*$').test(lines.at(-1)??''))
    throw new Error('Invalid or unclosed work-plan fence.');
  return parseWorkPlanReference(lines.slice(1,-1).join('\n'));
}
export function workPlanBelongsTo(ref:WorkPlanReference,host:{worldId:string;documentId:string}):boolean {
  return ref.world_id===host.worldId&&ref.document_id===host.documentId;
}
