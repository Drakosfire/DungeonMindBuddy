import type { WorldAgentConversationHistoryTurn } from "../api/types";

export function isUnansweredFailure(turn: WorldAgentConversationHistoryTurn): boolean {
  return (turn.lifecycle_status === "failed" || turn.lifecycle_status === "interrupted")
    && !turn.assistant_text?.trim();
}

/** Display grouping only. This never authorizes replay or changes retained history. */
export function matchingQuestion(left: WorldAgentConversationHistoryTurn, right: WorldAgentConversationHistoryTurn): boolean {
  return left.user_text === right.user_text
    && left.provenance.world_id === right.provenance.world_id
    && left.provenance.surface_id === right.provenance.surface_id
    && left.provenance.primary_work.object_id === right.provenance.primary_work.object_id;
}

export function groupConversationAttempts<T>(items: readonly T[], turnFor: (item: T) => WorldAgentConversationHistoryTurn | null,
  breaksAfter: ReadonlySet<number> = new Set()): Array<{item:T;previous:T[]}> {
  const groups: Array<{item:T;previous:T[]}> = [];
  for(const item of items){
    const last=groups.at(-1), prior=last ? turnFor(last.item) : null, current=turnFor(item);
    const barrier=prior && current && [...breaksAfter].some(sequence=>sequence>=prior.sequence && sequence<current.sequence);
    if(last && prior && current && isUnansweredFailure(prior) && matchingQuestion(prior,current)
      && current.sequence===prior.sequence+1 && !barrier){
      groups[groups.length-1]={item,previous:[...last.previous,last.item]};
    }else groups.push({item,previous:[]});
  }
  return groups;
}
