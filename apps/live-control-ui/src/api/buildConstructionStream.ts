import type {WorldBuildAgentTurnRequestV1, WorldPlanAgentTurnResponse} from './types';
import type {BuildProposalBasis} from './buildDocumentProposalApi';

export interface BuildConstructionProgress {
  schema:'dmb_build_construction_v1'; action_id:string; reservation_sha256:string;
  conversation_id:string; basis:BuildProposalBasis;
  origin:{client_turn_id:string;durable_turn_id:string;turn_attempt:number;broker_operation_id:string;arguments_sha256:string};
  provider_attempt_id:string; sequence:number; status:'building'|'incomplete'|'ready'; markdown:string;
}
export class ConstructionStreamError extends Error {
  constructor(public status:number,public detail:unknown){super('The saved request needs checking.');}
}
function normalized(value:unknown):unknown{
  if(Array.isArray(value))return value.map(normalized);
  if(value&&typeof value==='object')return Object.fromEntries(Object.entries(value)
    .filter(([,v])=>v!==undefined).sort(([a],[b])=>a.localeCompare(b)).map(([k,v])=>[k,normalized(v)]));
  return value;
}
const stable=(value:unknown):string=>JSON.stringify(normalized(value));

/** One POST, one terminal. Missing transport output is uncertainty, never a retry. */
export async function readBuildConstructionStream(response:Response, request:WorldBuildAgentTurnRequestV1,
  onProgress:(progress:BuildConstructionProgress)=>void, assertCurrent:()=>void=()=>undefined):Promise<WorldPlanAgentTurnResponse> {
  if(!response.headers.get('content-type')?.startsWith('text/event-stream')||!response.body)
    throw new Error('The reply stream is unavailable. Check the saved request.');
  const reader=response.body.getReader();const decoder=new TextDecoder('utf-8',{fatal:true});
  let buffer='';let sequence=0;let identity:string|null=null;
  const capability=request.build_write_capability;
  function progress(value:unknown){
    if(!capability||!value||typeof value!=='object')return;
    const p=value as BuildConstructionProgress;
    if(p.schema!=='dmb_build_construction_v1'||p.action_id!==capability.idempotency_key
      ||p.conversation_id!==capability.conversation_id||stable(p.basis)!==stable(capability.basis)
      ||p.origin?.client_turn_id!==request.turn_id||typeof p.origin?.durable_turn_id!=='string'
      ||!Number.isSafeInteger(p.origin.turn_attempt)||p.origin.turn_attempt<1
      ||typeof p.origin.broker_operation_id!=='string'||!p.origin.broker_operation_id
      ||!/^[a-f0-9]{64}$/.test(p.origin.arguments_sha256)||!/^[a-f0-9]{64}$/.test(p.reservation_sha256)
      ||typeof p.provider_attempt_id!=='string'||!p.provider_attempt_id
      ||!Number.isSafeInteger(p.sequence)||p.sequence<=sequence||typeof p.markdown!=='string'
      ||!['building','incomplete','ready'].includes(p.status))return;
    const next=stable([p.action_id,p.reservation_sha256,p.origin,p.provider_attempt_id]);
    if(identity!==null&&next!==identity)return;
    identity=next;sequence=p.sequence;
    // A retired view cannot interrupt the durable command's final reconciliation.
    try{onProgress(p);}catch{/* Preview is observation only. */}
  }
  try{
    while(true){
      const chunk=await reader.read();assertCurrent();
      buffer=(buffer+decoder.decode(chunk.value,{stream:!chunk.done})).replace(/\r\n/g,'\n');
      let end:number;
      while((end=buffer.indexOf('\n\n'))>=0){
        const frame=buffer.slice(0,end);buffer=buffer.slice(end+2);
        const data=frame.split('\n').filter(line=>line.startsWith('data:')).map(line=>line.slice(5).trimStart()).join('\n');
        if(!data)continue;
        const event=JSON.parse(data) as Record<string,unknown>;
        if(event.schema!=='dmb_build_turn_stream_v1'||event.client_turn_id!==request.turn_id)
          throw new Error('The reply stream belongs to another request. Check its saved outcome.');
        if(event.kind==='construction'){progress(event.progress);continue;}
        if(event.kind==='error'&&Number.isSafeInteger(event.status))throw new ConstructionStreamError(event.status as number,event.detail);
        if(event.kind==='result'&&event.response&&typeof event.response==='object')return event.response as WorldPlanAgentTurnResponse;
        throw new Error('The reply stream was invalid. Check the saved request.');
      }
      if(chunk.done)throw new Error('The reply stream stopped. Check the saved request before retrying.');
    }
  }finally{
    try{await reader.cancel();}catch{/* Cleanup cannot replace an already observed outcome. */}
    reader.releaseLock();
  }
}
