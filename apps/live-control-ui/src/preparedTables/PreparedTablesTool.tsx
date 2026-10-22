import {useCallback,useEffect,useRef,useState} from 'react';
import {authenticatedApiFetch,LiveApiError} from '../api/liveApi';
import type {WorldPlayRunRecordV2} from '../api/types';
import {parseTableJson,type PreparedTable} from './tableGrammar';
import {pendingTableKey,type PreparedTablesBinding} from './preparedTablesProjection';

type Pin=Pick<WorldPlayRunRecordV2,'playable_artifact_id'|'playable_revision'|'playable_work_revision_id'|'playable_content_sha256'>;
type Command=Pin&{expected_run_revision:number;table_id:string;table_sha256:string;physical_value:number};
type Pending={id:string;body:Command};
type Table=PreparedTable&{table_sha256:string};
type Receipt={schema_version:'dmb_prepared_table_receipt_v1';world_id:string;run_id:string;command_id:string;source:Pin;source_title:string;table_id:string;table_sha256:string;table_title:string;die_sides:number;physical_value:number;row_id:string;outcome:string;recorded_at:string;expected_run_revision:number;resulting_run_revision:number};
type Inventory={run:WorldPlayRunRecordV2;source:Pin;source_title:string;can_record:boolean;tables:Table[]};
const hash=/^[0-9a-f]{64}$/;
const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const pinKeys=['playable_artifact_id','playable_revision','playable_work_revision_id','playable_content_sha256'] as const;
function samePin(a:Pin,b:Pin){return pinKeys.every(key=>a[key]===b[key]);}
function validPin(pin:Pin){return pin&&uuid.test(pin.playable_artifact_id)&&uuid.test(pin.playable_work_revision_id)&&Number.isSafeInteger(pin.playable_revision)&&pin.playable_revision>0&&hash.test(pin.playable_content_sha256);}
function validCommand(p:Pending){return p&&uuid.test(p.id)&&validPin(p.body)&&Number.isSafeInteger(p.body.expected_run_revision)&&p.body.expected_run_revision>0&&Number.isSafeInteger(p.body.physical_value)&&/^table:[a-z0-9][a-z0-9._-]{0,127}$/.test(p.body.table_id)&&hash.test(p.body.table_sha256);}
function validateRun(value:WorldPlayRunRecordV2,run:WorldPlayRunRecordV2){
  if(!value||value.schema_version!=='dmb_world_play_run_record_v2'||value.world_id!==run.world_id||value.run_id!==run.run_id||!validPin(value)||!Number.isSafeInteger(value.run_revision)||value.run_revision<1||!value.progress||typeof value.progress.notes_by_element_id!=='object')throw new Error('Invalid saved session response');
}
function validateReceipt(r:Receipt,run:WorldPlayRunRecordV2,p?:Pending){
  if(!r||r.schema_version!=='dmb_prepared_table_receipt_v1'||r.world_id!==run.world_id||r.run_id!==run.run_id||!uuid.test(r.command_id)||!validPin(r.source)||!hash.test(r.table_sha256)||typeof r.outcome!=='string'||typeof r.table_title!=='string'||typeof r.source_title!=='string'||typeof r.recorded_at!=='string'||!Number.isSafeInteger(r.physical_value)||!Number.isSafeInteger(r.expected_run_revision)||r.resulting_run_revision!==r.expected_run_revision+1||typeof r.row_id!=='string')throw new Error('Invalid recorded roll response');
  if(p&&(r.command_id!==p.id||!samePin(r.source,p.body)||r.expected_run_revision!==p.body.expected_run_revision||r.table_id!==p.body.table_id||r.table_sha256!==p.body.table_sha256||r.physical_value!==p.body.physical_value))throw new Error('Recorded roll does not match the submitted command');
}
async function call(path:string,init:RequestInit={}){
  const {response}=await authenticatedApiFetch(path,{...init,cache:'no-store'});
  const value=await response.json();
  if(!response.ok)throw new LiveApiError(typeof value.detail==='string'?value.detail:'Table request failed',response.status);
  return value;
}

export function PreparedTablesTool({run,blocked,onHeld,onRun}:PreparedTablesBinding){
  const [inventory,setInventory]=useState<Inventory|null>(null),[tableId,setTableId]=useState(''),[value,setValue]=useState('');
  const [history,setHistory]=useState<Receipt[]>([]),[before,setBefore]=useState<number|null>(null),[historyLoaded,setHistoryLoaded]=useState(false);
  const [pending,setPending]=useState<Pending|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState<string|null>(null),[storageBlocked,setStorageBlocked]=useState(false);
  const live=useRef(true),sending=useRef(false),generation=useRef(0);
  const props=useRef({run,blocked,onHeld,onRun});props.current={run,blocked,onHeld,onRun};
  const key=pendingTableKey(run.world_id,run.run_id);
  const base=`/api/live/world-play-runs/v2/${encodeURIComponent(run.run_id)}/prepared-tables`;
  const query=`world_id=${encodeURIComponent(run.world_id)}`;
  useEffect(()=>{live.current=true;return()=>{live.current=false;generation.current++}},[]);
  const refresh=useCallback(async()=>{
    const turn=++generation.current;
    try{
      const next:Inventory=await call(`${base}?${query}`);
      validateRun(next.run,run);
      if(!validPin(next.source)||!samePin(next.source,next.run)||typeof next.can_record!=='boolean'||typeof next.source_title!=='string'||!Array.isArray(next.tables))throw new Error('Invalid saved table inventory');
      for(const table of next.tables){const {table_sha256,...definition}=table;parseTableJson(JSON.stringify(definition));if(!hash.test(table_sha256))throw new Error('Invalid table identity');}
      if(!live.current||turn!==generation.current)return;
      setInventory(next);setTableId(prior=>next.tables.some(t=>t.table_id===prior)?prior:next.tables[0]?.table_id??'');
      // A read cannot silently advance the host's scene/progress or overwrite drafts.
    }catch(cause){if(live.current&&turn===generation.current)setError(cause instanceof Error?cause.message:String(cause));}
  },[base,query,run.run_id,run.world_id]);
  useEffect(()=>{
    try{const raw=localStorage.getItem(key);if(raw){const saved=JSON.parse(raw) as Pending;if(!validCommand(saved))throw new Error('Unreadable pending table command');setPending(saved);setTableId(saved.body.table_id);setValue(String(saved.body.physical_value));onHeld(true);}else onHeld(false);}
    catch{setStorageBlocked(true);setError('Browser recovery data could not be read. Keep it intact and resolve it before recording another roll.');onHeld(true);}
    void refresh();
  },[key,refresh]);
  const send=async(retry=false)=>{
    if(sending.current||props.current.blocked||storageBlocked)return;
    const table=inventory?.tables.find(t=>t.table_id===tableId);
    let command=pending;
    if(!retry){
      if(pending||!inventory?.can_record||!table)return;
      if(inventory.run.run_revision!==props.current.run.run_revision||!samePin(inventory.source,props.current.run)){setError('Session changed. Refresh the saved preparation before submitting.');return;}
      if(!/^\d+$/.test(value)||!Number.isSafeInteger(Number(value))||Number(value)<1||Number(value)>table.die_sides){setError(`Enter an integer from 1 to ${table.die_sides}.`);return;}
      command={id:crypto.randomUUID(),body:{...inventory.source,expected_run_revision:inventory.run.run_revision,table_id:table.table_id,table_sha256:table.table_sha256,physical_value:Number(value)}};
    }
    if(!command)return;
    const submitted=command;
    const raw=JSON.stringify(submitted);
    const turn=generation.current;
    const current=()=>live.current&&turn===generation.current;
    const locked=async<T,>(action:()=>T):Promise<T>=>{
      if(!navigator.locks)throw new Error('Browser locking is required for safe roll recovery.');
      return navigator.locks.request(key,()=>{
        if(!current())throw new Error('This table view has closed.');
        return action();
      });
    };
    sending.current=true;setBusy(true);setError(null);
    let sent=false;
    try{
      await locked(()=>{
        const stored=localStorage.getItem(key);
        if(retry ? stored!==raw : stored!==null)throw new Error('Another view changed the pending roll. Reopen Prepared tables to recover it.');
        if(!retry)localStorage.setItem(key,raw);
        setPending(submitted);props.current.onHeld(true);
      });
      if(!current())return;
      sent=true;
      const result=await call(`${base}/commands/${submitted.id}?${query}`,{method:'PUT',body:JSON.stringify(submitted.body)});
      validateReceipt(result.receipt,run,submitted);validateRun(result.run,run);
      if(result.run.run_revision<result.receipt.resulting_run_revision)throw new Error('Receipt revision exceeds saved session');
      await locked(()=>{
        if(localStorage.getItem(key)!==raw)throw new Error('Pending roll changed in another view. Its recovery copy was retained.');
        // Admit the host response before releasing its exact recovery command.
        props.current.onRun(result.run);
        localStorage.removeItem(key);setPending(null);props.current.onHeld(false);
        setHistory(prior=>[result.receipt,...prior.filter(r=>r.command_id!==result.receipt.command_id)]);
        setInventory(prior=>prior?{...prior,run:result.run}:prior);
      });
    }catch(cause){
      if(!current())return;
      if(!retry&&sent&&cause instanceof LiveApiError&&cause.status>=400&&cause.status<500&&![408,429].includes(cause.status)){
        try{
          await locked(()=>{
            if(localStorage.getItem(key)!==raw)throw new Error('Another view changed recovery.');
            localStorage.removeItem(key);setPending(null);props.current.onHeld(false);
          });
          setError(`${cause.message}. Your entered value is retained; refresh before a new submission.`);setInventory(null);
        }catch{setStorageBlocked(true);props.current.onHeld(true);setError('Another view changed recovery. Its saved command was retained. Reopen Prepared tables.');}
      }else{
        setError(sent?'The save outcome is unknown. Retry the exact saved command to recover its receipt.':(cause instanceof Error?cause.message:String(cause)));
        if(!sent){setStorageBlocked(true);let retained=true;try{retained=localStorage.getItem(key)!==null;}catch{/* Fail closed if storage is unreadable. */}props.current.onHeld(retained);}
      }
    }finally{if(current()){sending.current=false;setBusy(false);}}
  };
  const readHistory=async(older=false)=>{
    const turn=generation.current;
    try{
      const page=await call(`${base}/receipts?${query}${older&&before?`&before=${before}`:''}`);
      if(!Array.isArray(page.receipts)||!(page.next_before===null||Number.isSafeInteger(page.next_before)))throw new Error('Invalid receipt page');
      page.receipts.forEach((r:Receipt)=>validateReceipt(r,run));
      if(!live.current||turn!==generation.current)return;
      setHistory(prior=>older?[...prior,...page.receipts.filter((r:Receipt)=>!prior.some(p=>p.command_id===r.command_id))]:page.receipts);setBefore(page.next_before);setHistoryLoaded(true);
    }catch(cause){if(live.current&&turn===generation.current)setError(cause instanceof Error?cause.message:String(cause));}
  };
  const table=inventory?.tables.find(t=>t.table_id===tableId);
  return <section aria-label="Prepared tables"><h2>Prepared tables</h2><p>Enter a physical roll to record an outcome from this session’s saved preparation.</p>
    {inventory?<p>From {inventory.source_title}</p>:null}
    {blocked?<p role="status">Save or resolve your session changes before recording a roll.</p>:null}
    {error?<p role="alert">{error}</p>:null}
    <button disabled={busy||Boolean(pending)} onClick={()=>{setError(null);void refresh()}}>Refresh saved preparation</button>
    {inventory?.tables.length===0?<p>No prepared tables in this session’s saved preparation. Author a typed table in Plan Markdown before starting a new session.</p>:null}
    {inventory?.tables.length?<><label>Table<select value={tableId} disabled={Boolean(pending)||busy} onChange={e=>setTableId(e.target.value)}>{inventory.tables.map(t=><option key={t.table_id} value={t.table_id}>{t.title} · d{t.die_sides}</option>)}</select></label>
      <label>Physical roll<input inputMode="numeric" value={value} disabled={Boolean(pending)||busy} onChange={e=>setValue(e.target.value)}/></label>
      {!pending?<button disabled={blocked||busy||storageBlocked||!inventory.can_record} onClick={()=>void send()}>Record outcome</button>:null}
      {!inventory.can_record?<p>Reopen this session to record another outcome.</p>:null}
      {table?<details><summary>Table entries</summary><table><tbody>{table.rows.map(r=><tr key={r.row_id}><th>{r.min===r.max?r.min:`${r.min}–${r.max}`}</th><td>{r.outcome}</td></tr>)}</tbody></table></details>:null}</>:null}
    {pending?<><p role="status">A saved command is awaiting confirmation. Its table and value are frozen.</p><button disabled={busy||blocked||storageBlocked} onClick={()=>void send(true)}>Retry saved command</button></>:null}
    <button disabled={busy} onClick={()=>void readHistory()}>Show recorded outcomes</button>
    {historyLoaded&&history.length===0?<p>No recorded outcomes yet.</p>:null}
    <ol>{history.map(r=><li key={r.command_id}><strong>{r.table_title} · {r.physical_value} on d{r.die_sides}</strong><p>{r.outcome}</p><small>From {r.source_title} · {new Date(r.recorded_at).toLocaleString()}</small><details><summary>Receipt details</summary><pre>{JSON.stringify(r,null,2)}</pre></details></li>)}</ol>
    {before?<button onClick={()=>void readHistory(true)}>Earlier outcomes</button>:null}
  </section>;
}
