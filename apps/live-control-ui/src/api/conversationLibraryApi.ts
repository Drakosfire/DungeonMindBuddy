import {readSavedCitationPreview,type SavedCitationPreview} from './savedCitationPreview';
import type {AuthoredReferenceInput} from './types';
import {isAuthoredReferences} from '../agentInteraction/authoredGraphReferences';
import {decodeRetryContext,type TurnRetryContext} from './conversationRetryApi';
import {authenticatedApiFetch,LiveApiError} from './liveApi';
export interface ConversationSummary{conversation_id:string;world_id:string;title:string;name_revision:number;status:'active'|'archived'|'trashed';turn_count:number;created_at:string;updated_at:string}
export interface LibraryPage{schema:'dmb_conversation_library_v1';world_id:string;status:'all'|'archived'|'trashed';items:ConversationSummary[];next_before:string|null}
export interface LibraryObjectSource{world_id:string;conversation_id:string;turn_id:string;document_id:string;surface_id:'build'}
export type LibraryReplyObject=({kind:'questions';questions:{text:string}[]}|{kind:'page_object';object_kind:'plan'|'connected_page'|'relationship'})&{source:LibraryObjectSource};
export interface LibraryTurn{authored_references?:AuthoredReferenceInput;turn_id:string;sequence:number;status:string;user_text:string;assistant_text:string|null;reply_object:LibraryReplyObject|null;retry_context:TurnRetryContext|null}
export interface LibraryTurns{schema:'dmb_conversation_library_turns_v3';world_id:string;conversation_id:string;turns:LibraryTurn[];next_before_sequence:number|null}
const uuid=(v:unknown):v is string=>typeof v==='string'&&/^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$/i.test(v);
const path=(world:string)=>'/api/live/agent/worlds/'+encodeURIComponent(world)+'/conversations';
async function read(url:string,init?:RequestInit){
 const {response}=await authenticatedApiFetch(url,{...init,cache:'no-store',headers:{'Content-Type':'application/json'}});const value=await response.json();
 if(!response.ok)throw new LiveApiError(typeof value.detail==='string'?value.detail:'Conversation library is unavailable.',response.status);
 return value;
}
function summary(value:any,world:string):ConversationSummary{
 if(!value||!uuid(value.conversation_id)||value.world_id!==world||typeof value.title!=='string'||!value.title.trim()||value.title.length>320
  ||!Number.isInteger(value.name_revision)||value.name_revision<0||!['active','archived','trashed'].includes(value.status)
  ||!Number.isInteger(value.turn_count)||value.turn_count<0||!Number.isFinite(Date.parse(value.created_at))||!Number.isFinite(Date.parse(value.updated_at)))throw new Error('Conversation name has a different owner or invalid metadata.');
 return value;
}
export async function listConversations(world:string,status:'all'|'archived'|'trashed',before?:string){
 const q=new URLSearchParams({status,limit:'25'});if(before)q.set('before',before);
 const value=await read(path(world)+'?'+q);
 if(value.schema!=='dmb_conversation_library_v1'||value.world_id!==world||value.status!==status||!Array.isArray(value.items)||value.items.length>25||!(value.next_before===null||uuid(value.next_before)))throw new Error('Conversation list differs from this World.');
 value.items.forEach((item:any)=>summary(item,world));return value as LibraryPage;
}
export async function readConversationName(world:string,id:string){const value=summary(await read(path(world)+'/'+encodeURIComponent(id)+'/name'),world);if(value.conversation_id!==id)throw new Error('Conversation name differs from the selection.');return value;}
export async function renameConversation(world:string,id:string,title:string,expected_revision:number){
 const value=summary(await read(path(world)+'/'+encodeURIComponent(id)+'/name',{method:'PUT',body:JSON.stringify({title,expected_revision})}),world);
 if(value.conversation_id!==id||value.title!==title.trim()||value.name_revision!==expected_revision+1)throw new Error('The exact name save could not be confirmed.');return value;
}
export async function readConversationTurns(world:string,id:string,before?:number){
 const q=new URLSearchParams({limit:'50'});if(before!==undefined)q.set('before_sequence',String(before));
 const value=await read(path(world)+'/'+encodeURIComponent(id)+'/turns?'+q);
 return decodeLibraryTurns(value,world,id,before);
}
export function decodeLibraryTurns(value:any,world:string,id:string,before?:number):LibraryTurns {
 if(!exactObject(value,['schema','world_id','conversation_id','turns','next_before_sequence'])||value.schema!=='dmb_conversation_library_turns_v3'||value.world_id!==world||value.conversation_id!==id||!Array.isArray(value.turns)||value.turns.length>50
  ||!(value.next_before_sequence===null||Number.isInteger(value.next_before_sequence)&&value.next_before_sequence>0))throw new Error('Transcript differs from the selected conversation.');
 let last=0;for(const t of value.turns){if(!exactObject(t,['turn_id','sequence','status','user_text','assistant_text','reply_object','retry_context',...(Object.hasOwn(t,'authored_references')?['authored_references']:[])])||!uuid(t.turn_id)||!Number.isInteger(t.sequence)||t.sequence<=last||(before!==undefined&&t.sequence>=before)||typeof t.user_text!=='string'||typeof t.status!=='string'||!(t.assistant_text===null||typeof t.assistant_text==='string'))throw new Error('Transcript order or content is invalid.');if(Object.hasOwn(t,'authored_references')&&!isAuthoredReferences(t.authored_references,world))throw new Error('Transcript reference input is invalid.');validateReplyObject(t.reply_object,world,id,t);decodeRetryContext(t.retry_context,world,id,t.turn_id);last=t.sequence;}
 return value as LibraryTurns;
}

function exactObject(value:unknown,keys:string[]):boolean{
 return !!value&&typeof value==='object'&&!Array.isArray(value)&&Object.keys(value).length===keys.length&&keys.every(k=>Object.hasOwn(value,k));
}
function validateReplyObject(value:unknown,world:string,conversation:string,turn:LibraryTurn){
 if(value===null)return;
 if(turn.status!=='completed'||!value||typeof value!=='object')throw new Error('Transcript object lacks a completed owner.');
 const obj=value as Record<string,unknown>,source=obj.source as Record<string,unknown>;
 if(!exactObject(source,['world_id','conversation_id','turn_id','document_id','surface_id'])
  ||source.world_id!==world||source.conversation_id!==conversation||source.turn_id!==turn.turn_id
  ||source.surface_id!=='build'||typeof source.document_id!=='string'||!source.document_id.trim())throw new Error('Transcript object differs from its source page.');
 if(obj.kind==='questions'&&exactObject(obj,['kind','questions','source'])&&Array.isArray(obj.questions)&&obj.questions.length
  &&obj.questions.every(q=>exactObject(q,['text'])&&typeof q.text==='string'&&q.text.trim()))return;
 if(obj.kind==='page_object'&&exactObject(obj,['kind','object_kind','source'])&&['plan','connected_page','relationship'].includes(String(obj.object_kind)))return;
 throw new Error('Transcript object is invalid.');
}

/** Existing APP reopen command and durable receipt; no second switch authority. */
export interface ResumeConversationCommand {world_id:string;conversation_id:string;command_id:string;expected_pointer_revision:number;expected_active_conversation_id:string|null}
export async function resumeConversation(command:ResumeConversationCommand){
 const value=await read(path(command.world_id)+'/'+encodeURIComponent(command.conversation_id)+'/resume',{method:'POST',body:JSON.stringify(command)});
 if(!exactObject(value,['world_id','command_id','command_kind','conversation_id','active_conversation_id','pointer_revision','recorded_at'])
  ||value.world_id!==command.world_id||value.command_id!==command.command_id||value.command_kind!=='reopen'
  ||value.conversation_id!==command.conversation_id||value.active_conversation_id!==command.conversation_id
  ||value.pointer_revision!==command.expected_pointer_revision+1||!Number.isFinite(Date.parse(value.recorded_at)))throw new Error('The saved switch could not be confirmed. Refresh conversations before trying again.');
 return value;
}

export type ConversationLifecycleOperation='trash'|'restore';
export async function changeConversationLifecycle(command:ResumeConversationCommand,operation:ConversationLifecycleOperation){
 const value=await read(path(command.world_id)+'/'+encodeURIComponent(command.conversation_id)+'/'+operation,{method:'POST',body:JSON.stringify(command)});
 const active=operation==='trash'&&command.expected_active_conversation_id===command.conversation_id?null:command.expected_active_conversation_id;
 if(!exactObject(value,['world_id','command_id','command_kind','conversation_id','active_conversation_id','pointer_revision','recorded_at'])
  ||value.world_id!==command.world_id||value.command_id!==command.command_id||value.command_kind!==operation
  ||value.conversation_id!==command.conversation_id||value.active_conversation_id!==active
  ||value.pointer_revision!==command.expected_pointer_revision+1||!Number.isFinite(Date.parse(value.recorded_at)))throw new Error('The conversation lifecycle change could not be confirmed. Refresh conversations before retrying.');
 return value;
}

export type ConversationMessage=Pick<LibraryTurn,'turn_id'|'sequence'|'status'|'user_text'|'assistant_text'>;
export interface ConversationMessages{schema:'dmb_conversation_messages_v1';world_id:string;conversation_id:string;messages:ConversationMessage[];next_before_sequence:number|null}
export async function readConversationMessages(world:string,id:string,before?:number):Promise<ConversationMessages>{
 const q=new URLSearchParams({limit:'50'});if(before!==undefined)q.set('before_sequence',String(before));
 const value=await read(path(world)+'/'+encodeURIComponent(id)+'/messages?'+q);
 if(!exactObject(value,['schema','world_id','conversation_id','messages','next_before_sequence'])||value.schema!=='dmb_conversation_messages_v1'||value.world_id!==world||value.conversation_id!==id||!Array.isArray(value.messages)||value.messages.length>50
  ||!(value.next_before_sequence===null||Number.isInteger(value.next_before_sequence)&&value.next_before_sequence>0))throw new Error('Message preview differs from the selected conversation.');
 let last=0;for(const t of value.messages){if(!exactObject(t,['turn_id','sequence','status','user_text','assistant_text'])||!uuid(t.turn_id)||!Number.isInteger(t.sequence)||t.sequence<=last||(before!==undefined&&t.sequence>=before)||!['accepted','running','completed','failed','interrupted'].includes(t.status)||typeof t.user_text!=='string'||!(t.assistant_text===null||typeof t.assistant_text==='string'))throw new Error('Message preview order or content is invalid.');last=t.sequence;}
 if(value.next_before_sequence!==null&&(!value.messages.length||value.next_before_sequence!==value.messages[0].sequence))throw new Error('Message preview cursor differs from its page.');
 return value;
}

/** Display/correlation metadata only; never a verified execution or action grant. */
export interface ActiveConversationMessages {
  schema: 'dmb_active_conversation_messages_v2'; world_id: string; conversation_state: 'active' | 'absent';
  conversation_id: string | null; active_conversation_id: string | null; pointer_revision: number;
  messages: (ConversationMessage & { revision: number; idempotency_key: string; provenance: import('./types').AgentConversationTurnProvenanceV1; citation_preview: SavedCitationPreview })[];
  next_before_sequence: number | null;
}
export async function readActiveConversationMessages(world: string, before?: number, signal?: AbortSignal): Promise<ActiveConversationMessages> {
  const q = new URLSearchParams({ limit: '50' }); if (before !== undefined) q.set('before_sequence', String(before));
  const v = await read(path(world) + '/active/messages?' + q, { signal });
  if (!exactObject(v, ['schema', 'world_id', 'conversation_state', 'conversation_id', 'active_conversation_id', 'pointer_revision', 'messages', 'next_before_sequence'])
    || v.schema !== 'dmb_active_conversation_messages_v2' || v.world_id !== world || !['active', 'absent'].includes(v.conversation_state)
    || !Number.isSafeInteger(v.pointer_revision) || v.pointer_revision < 0 || !Array.isArray(v.messages) || v.messages.length > 50
    || (v.conversation_state === 'active' ? !uuid(v.conversation_id) || v.active_conversation_id !== v.conversation_id
      : v.conversation_id !== null || v.active_conversation_id !== null || v.messages.length !== 0 || v.next_before_sequence !== null)) throw new Error('Active message page has a different owner.');
  let last = 0; for (const t of v.messages) {
if (!exactObject(t, ['turn_id', 'sequence', 'status', 'user_text', 'assistant_text', 'revision', 'idempotency_key', 'provenance', 'citation_preview'])
      || !uuid(t.turn_id) || !uuid(t.idempotency_key) || !Number.isSafeInteger(t.revision) || t.revision < 1 || !Number.isSafeInteger(t.sequence) || t.sequence <= last
      || before !== undefined && t.sequence >= before || !['accepted', 'running', 'completed', 'failed', 'interrupted'].includes(t.status)
      || typeof t.user_text !== 'string' || !(t.assistant_text === null || typeof t.assistant_text === 'string') || t.provenance?.world_id !== world) throw new Error('Active message metadata is invalid.');
    t.citation_preview=t.status==='completed'?readSavedCitationPreview(t.citation_preview,world,t.provenance.surface_id,t.assistant_text):null;
    last = t.sequence;
}
  if (!(v.next_before_sequence === null || v.messages.length > 0 && v.next_before_sequence === v.messages[0].sequence)) throw new Error('Active message cursor differs from its page.');
  return v;
}
