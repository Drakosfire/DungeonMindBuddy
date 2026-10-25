import {authenticatedApiFetch,LiveApiError} from './liveApi';
export interface TurnRetryContext {
 world_id:string;conversation_id:string;turn_id:string;revision:number;root_id:string;
 predecessor_id:string|null;successor_id:string|null;ordinal:number;eligible:boolean;
 reason:'ready'|'not_terminal'|'unknown_outcome'|'existing_result'|'reviewed_step'|'retried'|'inactive'|'unverified';
}
export const retryUuid=(v:unknown):v is string=>typeof v==='string'&&/^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$/i.test(v);
const exact=(v:unknown,keys:string[]):v is Record<string,any>=>!!v&&typeof v==='object'&&!Array.isArray(v)&&Object.keys(v).length===keys.length&&keys.every(k=>Object.hasOwn(v,k));
export function decodeRetryContext(value:unknown,world:string,conversation:string,turn:string):TurnRetryContext|null {
 if(value===null)return null;
 if(!exact(value,['world_id','conversation_id','turn_id','revision','root_id','predecessor_id','successor_id','ordinal','eligible','reason'])
  ||value.world_id!==world||value.conversation_id!==conversation||value.turn_id!==turn
  ||!retryUuid(conversation)||!retryUuid(turn)||!retryUuid(value.root_id)
  ||!Number.isSafeInteger(value.revision)||value.revision<1||!Number.isSafeInteger(value.ordinal)||value.ordinal<0
  ||!(value.predecessor_id===null||retryUuid(value.predecessor_id))||!(value.successor_id===null||retryUuid(value.successor_id))
  ||value.predecessor_id===turn||value.successor_id===turn
  ||(value.ordinal===0?(value.predecessor_id!==null||value.root_id!==turn):(value.predecessor_id===null||value.root_id===turn))
  ||!['ready','not_terminal','unknown_outcome','existing_result','reviewed_step','retried','inactive','unverified'].includes(value.reason)
  ||(value.reason==='retried'&&value.successor_id===null)||(value.successor_id!==null&&!['retried','inactive'].includes(value.reason))
  ||(value.ordinal===1&&value.predecessor_id!==value.root_id)||(value.ordinal>1&&value.predecessor_id===value.root_id)
  ||typeof value.eligible!=='boolean'||value.eligible!==(value.reason==='ready')||value.eligible&&value.successor_id!==null)
   throw new Error('Retry context differs from its saved conversation attempt.');
 return value as TurnRetryContext;
}
export async function readRetryContext(world:string,conversation:string,ids:string[],signal?:AbortSignal){
 if(!retryUuid(conversation)||!ids.length||ids.length>100||new Set(ids).size!==ids.length||!ids.every(retryUuid))throw new Error('Select distinct saved attempts.');
 const url='/api/live/agent/worlds/'+encodeURIComponent(world)+'/conversations/'+conversation+'/retry-context?'+new URLSearchParams({turn_ids:ids.join(',')});
 const {response}=await authenticatedApiFetch(url,{cache:'no-store',signal});const v=await response.json();
 if(!response.ok)throw new LiveApiError(typeof v.detail==='string'?v.detail:'Retry history is unavailable.',response.status);
 if(!exact(v,['schema','world_id','conversation_id','turns'])||v.schema!=='dmb_turn_retry_context_v1'||v.world_id!==world||v.conversation_id!==conversation||!Array.isArray(v.turns)||v.turns.length!==ids.length)throw new Error('Retry history has a different owner.');
 const rows=new Map<string,TurnRetryContext|null>();
 for(const row of v.turns){if(!exact(row,['turn_id','context'])||!ids.includes(row.turn_id)||rows.has(row.turn_id))throw new Error('Retry history has a different attempt.');rows.set(row.turn_id,decodeRetryContext(row.context,world,conversation,row.turn_id));}
 return rows;
}
export async function readRetryAttempts(world:string,conversation:string,turn:string,before?:number){
 const q=new URLSearchParams({limit:'50'});if(before!==undefined)q.set('before_sequence',String(before));
 const {response}=await authenticatedApiFetch('/api/live/agent/worlds/'+encodeURIComponent(world)+'/conversations/'+encodeURIComponent(conversation)+'/turns/'+encodeURIComponent(turn)+'/retry-attempts?'+q,{cache:'no-store'});
 const v=await response.json();if(!response.ok)throw new LiveApiError(typeof v.detail==='string'?v.detail:'Earlier attempts are unavailable.',response.status);
 const {decodeLibraryTurns}=await import('./conversationLibraryApi');return decodeLibraryTurns(v,world,conversation,before);
}
