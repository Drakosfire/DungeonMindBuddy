import type { WorldAgentConversationHistoryTurn } from "../api/types";

export function isUnansweredFailure(turn: WorldAgentConversationHistoryTurn): boolean {
  return (turn.lifecycle_status === "failed" || turn.lifecycle_status === "interrupted")
    && !turn.assistant_text?.trim();
}

/** Explicit APP lineage only; grouping never grants execution authority. */
export function groupRetryLineage<T>(items: readonly T[], contextFor: (item:T)=>WorldAgentConversationHistoryTurn["retry_context"]): Array<{item:T;previous:T[];historical?:boolean}> {
  const groups:Array<{item:T;previous:T[];historical?:boolean}>=[];
  const roots=new Map<string,number>();
  for(const item of items){
    const ctx=contextFor(item);
    if(!ctx){groups.push({item,previous:[]});continue;}
    const key=JSON.stringify([ctx.world_id,ctx.conversation_id,ctx.root_id]);
    const index=roots.get(key);
    if(index===undefined){roots.set(key,groups.length);groups.push({item,previous:[],historical:ctx.successor_id!==null});continue;}
    const group=groups[index],prior=contextFor(group.item);
    if(prior&&prior.ordinal<ctx.ordinal)groups[index]={item,previous:[...group.previous,group.item],historical:ctx.successor_id!==null};
    else group.previous.push(item);
  }
  return groups;
}

export function groupConversationAttempts<T>(items: readonly T[], turnFor: (item:T)=>WorldAgentConversationHistoryTurn|null,
 _breaksAfter:ReadonlySet<number>=new Set()) {
 const groups=groupRetryLineage(items,item=>turnFor(item)?.retry_context);
 // Preserve existing Plan/Play presentation; this slice changes ordinary Build only.
 const result:typeof groups=[];
 for(const group of groups){
  const last=result.at(-1),prior=last?turnFor(last.item):null,current=turnFor(group.item);
  const barrier=prior&&current&&[..._breaksAfter].some(n=>n>=prior.sequence&&n<current.sequence);
  if(last&&prior&&current&&prior.provenance.surface_id!=='build'&&current.provenance.surface_id!=='build'
   &&isUnansweredFailure(prior)&&prior.user_text===current.user_text&&prior.provenance.world_id===current.provenance.world_id
   &&prior.provenance.surface_id===current.provenance.surface_id&&prior.provenance.primary_work.object_id===current.provenance.primary_work.object_id
   &&current.sequence===prior.sequence+1&&!barrier)result[result.length-1]={item:group.item,previous:[...last.previous,last.item]};
  else result.push(group);
 }
 return result;
}
