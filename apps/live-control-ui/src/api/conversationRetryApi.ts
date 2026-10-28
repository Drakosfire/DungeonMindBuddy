import type {AuthoredGraphReferencesV1} from './types';
import {isAuthoredGraphReferences} from '../agentInteraction/authoredGraphReferences';
import {authenticatedApiFetch,LiveApiError} from './liveApi';
interface TurnRetryContextBase {
 world_id:string;conversation_id:string;turn_id:string;revision:number;root_id:string;
 predecessor_id:string|null;successor_id:string|null;ordinal:number;eligible:boolean;
 reason:'ready'|'not_terminal'|'unknown_outcome'|'existing_result'|'reviewed_step'|'retried'|'inactive'|'unverified';
}
export type TurnRetryContext=TurnRetryContextBase&({schema?:never;authored_references?:never}|{schema:'dmb_turn_retry_context_row_v2';authored_references:AuthoredGraphReferencesV1});
export const retryUuid=(v:unknown):v is string=>typeof v==='string'&&/^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$/i.test(v);
const exact=(v:unknown,keys:string[]):v is Record<string,any>=>!!v&&typeof v==='object'&&!Array.isArray(v)&&Object.keys(v).length===keys.length&&keys.every(k=>Object.hasOwn(v,k));
export function decodeRetryContext(value:unknown,world:string,conversation:string,turn:string):TurnRetryContext|null {
 if(value===null)return null;
 if(!exact(value,['world_id','conversation_id','turn_id','revision','root_id','predecessor_id','successor_id','ordinal','eligible','reason',...(value&&typeof value==='object'&&'schema' in value?['schema','authored_references']:[])])
  ||('schema' in value&&(value.schema!=='dmb_turn_retry_context_row_v2'||!isAuthoredGraphReferences(value.authored_references,world)))
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

export interface DiscussionRetryInput {
 schema:'dmb_build_retained_discussion_retry_input_v1';world_id:string;conversation_id:string;turn_id:string;
 revision:number;pointer_revision:number;surface_instance_id:string;message:string;client_work_state:'saved_clean'|'saved_dirty';
 snapshot:import('./types').WorldBuildDraftSnapshotV1;snapshot_sha256:string;authored_references:AuthoredGraphReferencesV1|null;
}
export async function readDiscussionRetryInput(world:string,conversation:string,turn:string,revision:number):Promise<DiscussionRetryInput>{
 if(!retryUuid(conversation)||!retryUuid(turn)||!Number.isSafeInteger(revision)||revision<1)throw new Error('Select a saved failed request.');
 const {response}=await authenticatedApiFetch('/api/live/agent/worlds/'+encodeURIComponent(world)+'/conversations/'+conversation+'/turns/'+turn+'/discussion-retry-input?'+new URLSearchParams({revision:String(revision)}),{cache:'no-store'});
 const v=await response.json();
 if(!response.ok)throw new LiveApiError(typeof v.detail==='string'?v.detail:'The original request context is unavailable.',response.status);
 const sha=(x:unknown):x is string=>typeof x==='string'&&/^[a-f0-9]{64}$/.test(x);
 if(!exact(v,['schema','world_id','conversation_id','turn_id','revision','pointer_revision','surface_instance_id','message','client_work_state','snapshot','snapshot_sha256','authored_references'])
  ||v.schema!=='dmb_build_retained_discussion_retry_input_v1'||v.world_id!==world||v.conversation_id!==conversation||v.turn_id!==turn||v.revision!==revision
  ||!Number.isSafeInteger(v.pointer_revision)||v.pointer_revision<1||typeof v.surface_instance_id!=='string'||!v.surface_instance_id.trim()
  ||!['saved_clean','saved_dirty'].includes(v.client_work_state)||typeof v.message!=='string'||!v.message.trim()||!sha(v.snapshot_sha256)
  ||!(v.authored_references===null||isAuthoredGraphReferences(v.authored_references,world))
  ||!exact(v.snapshot,['schema','world_id','document_id','registry_revision','content_sha256','visibility','draft_markdown','draft_sha256','editor_sha256','draft_generation'])
  ||v.snapshot.schema!=='dmb_build_draft_snapshot_v1'||v.snapshot.world_id!==world||typeof v.snapshot.document_id!=='string'||!v.snapshot.document_id.trim()
  ||!Number.isSafeInteger(v.snapshot.registry_revision)||v.snapshot.registry_revision<1||!['internal','player_safe'].includes(v.snapshot.visibility)
  ||typeof v.snapshot.draft_markdown!=='string'||![v.snapshot.content_sha256,v.snapshot.draft_sha256,v.snapshot.editor_sha256].every(sha)
  ||!Number.isSafeInteger(v.snapshot.draft_generation)||v.snapshot.draft_generation<0)throw new Error('The retained request context differs from its saved attempt.');
 const {canonical}=await import('../shared/sourcePassageProtocol');
 const digest=async(text:string)=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text))),b=>b.toString(16).padStart(2,'0')).join('');
 if(await digest(canonical(v.snapshot))!==v.snapshot_sha256||await digest(v.snapshot.draft_markdown)!==v.snapshot.draft_sha256)throw new Error('The retained working draft failed its identity check.');
 return v as DiscussionRetryInput;
}
