import {authenticatedApiFetch,LiveApiError} from './liveApi';
export interface ConversationSummary{conversation_id:string;world_id:string;title:string;name_revision:number;status:'active'|'archived';turn_count:number;created_at:string;updated_at:string}
export interface LibraryPage{schema:'dmb_conversation_library_v1';world_id:string;status:'all'|'archived';items:ConversationSummary[];next_before:string|null}
export interface LibraryTurn{turn_id:string;sequence:number;status:string;user_text:string;assistant_text:string|null}
export interface LibraryTurns{schema:'dmb_conversation_library_turns_v1';world_id:string;conversation_id:string;turns:LibraryTurn[];next_before_sequence:number|null}
const uuid=(v:unknown):v is string=>typeof v==='string'&&/^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$/i.test(v);
const path=(world:string)=>'/api/live/agent/worlds/'+encodeURIComponent(world)+'/conversations';
async function read(url:string,init?:RequestInit){
 const {response}=await authenticatedApiFetch(url,{...init,cache:'no-store',headers:{'Content-Type':'application/json'}});const value=await response.json();
 if(!response.ok)throw new LiveApiError(typeof value.detail==='string'?value.detail:'Conversation library is unavailable.',response.status);
 return value;
}
function summary(value:any,world:string):ConversationSummary{
 if(!value||!uuid(value.conversation_id)||value.world_id!==world||typeof value.title!=='string'||!value.title.trim()||value.title.length>320
  ||!Number.isInteger(value.name_revision)||value.name_revision<0||!['active','archived'].includes(value.status)
  ||!Number.isInteger(value.turn_count)||value.turn_count<0||!Number.isFinite(Date.parse(value.created_at))||!Number.isFinite(Date.parse(value.updated_at)))throw new Error('Conversation name has a different owner or invalid metadata.');
 return value;
}
export async function listConversations(world:string,status:'all'|'archived',before?:string){
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
 if(value.schema!=='dmb_conversation_library_turns_v1'||value.world_id!==world||value.conversation_id!==id||!Array.isArray(value.turns)||value.turns.length>50
  ||!(value.next_before_sequence===null||Number.isInteger(value.next_before_sequence)&&value.next_before_sequence>0))throw new Error('Transcript differs from the selected conversation.');
 let last=0;for(const t of value.turns){if(!uuid(t.turn_id)||!Number.isInteger(t.sequence)||t.sequence<=last||(before!==undefined&&t.sequence>=before)||typeof t.user_text!=='string'||typeof t.status!=='string'||!(t.assistant_text===null||typeof t.assistant_text==='string'))throw new Error('Transcript order or content is invalid.');last=t.sequence;}
 return value as LibraryTurns;
}
