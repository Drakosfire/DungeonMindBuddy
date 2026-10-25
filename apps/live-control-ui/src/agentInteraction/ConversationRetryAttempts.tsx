import {useEffect,useRef,useState} from 'react';
import {readRetryAttempts,type TurnRetryContext} from '../api/conversationRetryApi';
import type {LibraryTurn} from '../api/conversationLibraryApi';
import {BuddyContextTraceLoader} from '../planSurface/components/BuddyContextTraceLoader';

/** Read-only previous physical attempts; a preview is never a new execution control. */
export function ConversationRetryAttempts({context}:{context:TurnRetryContext}){
 const key=JSON.stringify([context.world_id,context.conversation_id,context.turn_id,context.root_id,context.ordinal]);
 const current=useRef(key);current.current=key;
 const [rows,setRows]=useState<LibraryTurn[]>([]),[cursor,setCursor]=useState<number|null>(null);
 const [loading,setLoading]=useState(false),[error,setError]=useState('');
 const loaded=useRef(false),busy=useRef(false);
 useEffect(()=>{current.current=key;loaded.current=false;busy.current=false;setRows([]);setCursor(null);setError('');setLoading(false);return()=>{current.current='';};},[key]);
 async function load(older=false){
  if(busy.current||!older&&loaded.current)return;
  const owner=key;busy.current=true;setLoading(true);setError('');
  try{
   const page=await readRetryAttempts(context.world_id,context.conversation_id,context.turn_id,older?cursor??undefined:undefined);
   if(current.current!==owner)return;
   if(page.turns.some(t=>!t.retry_context||t.retry_context.root_id!==context.root_id||t.retry_context.ordinal>=context.ordinal))throw new Error('Earlier attempts differ from this request.');
   setRows(prior=>older?[...page.turns,...prior]:page.turns);setCursor(page.next_before_sequence);loaded.current=true;
  }catch(reason){if(current.current===owner)setError(reason instanceof Error?reason.message:'Earlier attempts are unavailable.');}
  finally{if(current.current===owner){busy.current=false;setLoading(false);}}
 }
 if(!context.ordinal)return null;
 return <details onToggle={e=>{if(e.currentTarget.open)void load();}}><summary>Previous attempts · {context.ordinal}</summary>
  {loading&&<p role="status">Loading previous attempts…</p>}
  {error&&<p role="alert">{error}<button type="button" disabled={loading} onClick={()=>void load()}>Retry history read</button></p>}
  {cursor!==null&&<button type="button" disabled={loading} onClick={()=>void load(true)}>Earlier attempts</button>}
  {rows.map(turn=><article key={turn.turn_id}><h4>Attempt {(turn.retry_context?.ordinal??0)+1} · {turn.status}</h4>
   {turn.assistant_text&&<p>{turn.assistant_text}</p>}
   <AttemptTrace context={context} turnId={turn.turn_id}/>
  </article>)}
 </details>;
}
function AttemptTrace({context,turnId}:{context:TurnRetryContext;turnId:string}){
 const [open,setOpen]=useState(false);
 return <details onToggle={e=>setOpen(e.currentTarget.open)}><summary>Trace</summary>{open&&<BuddyContextTraceLoader enabled worldId={context.world_id} conversationId={context.conversation_id} turnId={turnId}/>}</details>;
}
