import { downloadBlob } from "../shared/downloadBlob";
import {readConversationName,readConversationTurns,readExportTurns,verifyExportTurns,type ConversationSummary,type LibraryTurn} from '../api/conversationLibraryApi';
import {getWorldAgentTurnContextTrace,getWorldAgentTurnPrompt} from '../api/liveApi';
import type {BuddyPromptEvidence} from '../api/buddyContextTraceTypes';

export type ConversationExportFormat='readable'|'diagnostic';
export interface ConversationExportFile {filename:string;mime:string;content:string}
const errorText=(error:unknown)=>error instanceof Error?error.message:'Retained material is unavailable.';
const sameConversation=(a:ConversationSummary,b:ConversationSummary)=>a.world_id===b.world_id&&a.conversation_id===b.conversation_id
 &&a.turn_count===b.turn_count&&a.name_revision===b.name_revision&&a.title===b.title&&a.status===b.status&&a.updated_at===b.updated_at;

/** Collect every physical turn through the existing read-only library, including retries. */
export async function collectConversationExport(world:string,id:string,format:ConversationExportFormat,checkOwner:()=>void,signal?:AbortSignal):Promise<ConversationExportFile>{
 signal?.throwIfAborted();checkOwner();const startedAt=new Date().toISOString();const meta=await readConversationName(world,id,signal);signal?.throwIfAborted();checkOwner();
 const {turns, pages}=await readAllTurns(world,id,meta.turn_count,checkOwner,signal);
 const diagnostics=[];
 const collectDiagnostic = async (turn: LibraryTurn) => {
  signal?.throwIfAborted();checkOwner();
  try{
   const trace=await getWorldAgentTurnContextTrace(world,turn.turn_id,signal);signal?.throwIfAborted();checkOwner();
   if(trace.schema!=='dmb_agent_turn_context_trace_response_v1'||trace.world_id!==world||trace.turn_id!==turn.turn_id||!Array.isArray(trace.attempts)
     ||trace.attempts.some(t=>t.schema!=='dmb_turn_context_trace_v1'||t.world_id!==world||t.conversation_id!==id||t.turn_id!==turn.turn_id))throw new Error('Trace differs from the exported conversation turn.');
   const prompts:({trace_id:string;provider_attempt_id:string;evidence:BuddyPromptEvidence}|{trace_id:string;provider_attempt_id:string;unavailable:string})[]=[];
   for(const attempt of trace.attempts)for(const reference of attempt.observations){
    if(reference.kind!=='prompt_reference')continue;
    signal?.throwIfAborted();checkOwner();
    try{
     const evidence=await getWorldAgentTurnPrompt(world,turn.turn_id,attempt.trace_id,reference.provider_attempt_id,signal);signal?.throwIfAborted();checkOwner();
     if(evidence.schema!=='dmb_agent_prompt_evidence_v1'||evidence.world_id!==world||evidence.conversation_id!==id||evidence.turn_id!==turn.turn_id
       ||evidence.trace_id!==attempt.trace_id||evidence.attempt!==attempt.attempt||evidence.reference.provider_attempt_id!==reference.provider_attempt_id
       ||evidence.reference.evidence_id!==reference.evidence_id||evidence.reference.payload_sha256!==reference.payload_sha256
       ||evidence.reference.payload_utf8_bytes!==reference.payload_utf8_bytes)throw new Error('Prompt differs from its captured trace reference.');
     const body=JSON.parse(evidence.payload_json);if(!body||typeof body!=='object'||Array.isArray(body))throw new Error('Captured prompt is malformed.');
     prompts.push({trace_id:attempt.trace_id,provider_attempt_id:reference.provider_attempt_id,evidence});
    }catch(error){signal?.throwIfAborted();checkOwner();prompts.push({trace_id:attempt.trace_id,provider_attempt_id:reference.provider_attempt_id,unavailable:errorText(error)});}
   }
   return {turn_id:turn.turn_id,trace,prompts,prompt_capture:prompts.length?'See each captured payload or unavailable reason.':'No retained prompt references; exact prompts unavailable.',...(!trace.attempts.length?{unavailable:'No retained trace attempts.'}:{})};
  }catch(error){signal?.throwIfAborted();checkOwner();return {turn_id:turn.turn_id,unavailable:errorText(error)};}
 };
 if (format === 'diagnostic') {
  const concurrency = 2;
  for (let start = 0; start < turns.length; start += concurrency) {
   diagnostics.push(...await Promise.all(turns.slice(start, start + concurrency).map(collectDiagnostic)));
  }
 }
 for (const {before, page_sha256, next_before_sequence, legacyTurns} of pages) {
  signal?.throwIfAborted();checkOwner();
  if (page_sha256 === null) {
   const page = await readConversationTurns(world, id, before, signal);
   if (page.next_before_sequence !== next_before_sequence
    || JSON.stringify(page.turns) !== JSON.stringify(legacyTurns)) {
    throw new Error('A reply changed during export. Retry to collect the latest saved reply.');
   }
  } else {
   await verifyExportTurns(world, id, {page_sha256, next_before_sequence}, before, signal);
  }
  signal?.throwIfAborted();checkOwner();
 }
 const after=await readConversationName(world,id,signal);signal?.throwIfAborted();checkOwner();
 if(!sameConversation(meta,after))throw new Error('The conversation changed during export. Retry to collect its latest history.');
 const finishedAt=new Date().toISOString();
 if(format==='diagnostic')return {filename:`buddy-conversation-${id}-diagnostic.json`,mime:'application/json',content:JSON.stringify({
  conversation:meta,collection_started_at:startedAt,collection_finished_at:finishedAt,
  scope:'All retained physical turns, including retry attempts. Read-only capture over this interval; running turns and incomplete traces may change. Page-object entries are references, not full editable page contents.',
  turns,diagnostics,
 },null,2)};
 return {filename:`buddy-conversation-${id}.md`,mime:'text/markdown;charset=utf-8',content:readable(meta,turns,startedAt,finishedAt)};
}
async function readAllTurns(world:string,id:string,count:number,checkOwner:()=>void,signal?:AbortSignal){
 const turns:LibraryTurn[]=[],ids=new Set<string>(),sequences=new Set<number>();let before:number|undefined;
 const pages: {before?: number; page_sha256: string | null; next_before_sequence: number | null; legacyTurns?: LibraryTurn[]}[] = [];
 do {
  const page = pages[0]?.page_sha256 === null
   ? {...await readConversationTurns(world, id, before, signal), page_sha256: null}
   : await readExportTurns(world, id, before, signal);signal?.throwIfAborted();checkOwner();
  if(page.world_id!==world||page.conversation_id!==id)throw new Error('Transcript differs from the selected conversation.');
  for(const turn of page.turns){
   if(ids.has(turn.turn_id)||sequences.has(turn.sequence)||turn.sequence<1||(before!==undefined&&turn.sequence>=before))throw new Error('Transcript pagination repeated or skipped its ordering boundary.');
   ids.add(turn.turn_id);sequences.add(turn.sequence);
   turns.push(turn);
  }
  const next=page.next_before_sequence;
  if(next!==null&&(!page.turns.length||next!==Math.min(...page.turns.map(t=>t.sequence))||(before!==undefined&&next>=before)))throw new Error('Transcript pagination did not advance.');
  pages.push({before, page_sha256: page.page_sha256, next_before_sequence: next, legacyTurns: page.page_sha256 === null ? page.turns : undefined});
  before=next??undefined;
 }while(before!==undefined);
 turns.sort((a,b)=>a.sequence-b.sequence);
 if(sequences.size!==count||!Array.from(sequences).every(sequence=>Number.isInteger(sequence)&&sequence<=count))throw new Error('The complete retained transcript could not be confirmed. Retry export.');
 return {turns, pages};
}
function readable(meta:ConversationSummary,turns:LibraryTurn[],start:string,end:string){
 const lines=[`# ${meta.title}`,'',`World: ${meta.world_id}`,`Conversation: ${meta.conversation_id}`,`Status: ${meta.status}`,`Collected: ${start} → ${end}`,'',
 'All retained physical turns, including earlier retry attempts. Running replies may change. Page objects are referenced below; their complete editable contents live on their source pages. Prompts and traces are available through diagnostic export.',''];
 for(const turn of turns){
  lines.push(`## Turn ${turn.sequence} · ${turn.status}`,'',`Turn ID: ${turn.turn_id}`);
  if(turn.retry_context)lines.push(`Request lineage: ${turn.retry_context.root_id} · attempt ${turn.retry_context.ordinal+1}${turn.retry_context.successor_id?' · superseded by '+turn.retry_context.successor_id:''}`);
  lines.push('','### You','',turn.user_text,'','### Buddy','',turn.assistant_text??'No saved reply text.');
  const object=turn.reply_object;
  if(object?.kind==='questions')lines.push('','Clarifying questions:',...object.questions.map((question,i)=>`${i+1}. ${question.text}`));
  if(object){const url='/build?'+new URLSearchParams({world:object.source.world_id,documentId:object.source.document_id});
   if(object.kind==='page_object')lines.push('',`Page object: ${object.object_kind} (reference only).`);
   lines.push('',`Source page: ${url}`);
  }
  lines.push('');
 }
 return lines.join('\n');
}
export function downloadConversationExport(file:ConversationExportFile){
 downloadBlob(new Blob([file.content], { type: file.mime }), file.filename);
}
