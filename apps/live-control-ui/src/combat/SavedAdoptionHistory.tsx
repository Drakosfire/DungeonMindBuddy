import {useEffect,useRef,useState} from 'react';
import {inspectCombatMechanicsAdoption,listCombatMechanicsAdoptions} from './combatApi';
import {verifyInspectedAdoption} from './CombatMechanicsAdoptionRecovery';
import type {MechanicsAdoptionOutcome} from './combatTypes';
import type {RunEncounterScope} from './runEncountersApi';

/** Read-only receipt inspection, deliberately separate from command recovery. */
export function SavedAdoptionHistory({worldId,encounterId,scope,onInspected}:{worldId:string;encounterId:string;scope?:RunEncounterScope;onInspected:(outcome:MechanicsAdoptionOutcome)=>void}){
 const epoch=useRef(0),[busy,setBusy]=useState(false),[message,setMessage]=useState('');
 const [receipts,setReceipts]=useState<MechanicsAdoptionOutcome['receipt'][]|null>(null),[next,setNext]=useState<string|null>(null);
 const [opened,setOpened]=useState<MechanicsAdoptionOutcome|null>(null);
 useEffect(()=>()=>{epoch.current++;},[]);
 async function load(before:string|null=null){
  const current=++epoch.current;setBusy(true);setMessage('');
  try{
   const page=await listCombatMechanicsAdoptions(worldId,encounterId,before,scope);if(current!==epoch.current)return;
   if(before&&page.receipts.some(row=>receipts?.some(prior=>prior.operation_id===row.operation_id)))throw new Error('Saved adoption history repeated a receipt. Reload its first page.');
   setReceipts(previous=>before?[...(previous??[]),...page.receipts]:page.receipts);setNext(page.next_before_operation_id);
  }catch(error){if(current===epoch.current)setMessage(String(error));}
  finally{if(current===epoch.current)setBusy(false);}
 }
 async function inspect(receipt:MechanicsAdoptionOutcome['receipt']){
  const current=++epoch.current;setBusy(true);setMessage('');setOpened(null);
  try{
   const outcome=await inspectCombatMechanicsAdoption(worldId,encounterId,receipt.operation_id,scope);if(current!==epoch.current)return;
   if(!outcome)throw new Error('The saved adoption is unavailable.');
   verifyInspectedAdoption(receipt,outcome);setOpened(outcome);onInspected(outcome);
  }catch(error){if(current===epoch.current)setMessage(String(error));}
  finally{if(current===epoch.current)setBusy(false);}
 }
 return <details><summary>Saved adoptions</summary>
  <p>Inspect earlier choices without changing this encounter. Saved receipts are historical examples.</p>
  <button type="button" disabled={busy} onClick={()=>void load()}>Load saved adoptions</button>
  {receipts?.length===0&&<p>No adoption receipts are saved for this encounter. Mechanics copied from preparation do not count as an adoption in this session.</p>}
  {receipts&&<ul>{receipts.map(receipt=><li key={receipt.operation_id}>
   <button type="button" disabled={busy} onClick={()=>void inspect(receipt)}>{receipt.state==='applied'?'Inspect applied version':'Inspect canceled choice'} · {receipt.source.revision_id} · {new Date(receipt.created_at).toLocaleString()}</button>
  </li>)}</ul>}
  {next&&<button type="button" disabled={busy} onClick={()=>void load(next)}>More saved adoptions</button>}
  {opened&&<section aria-label="Saved adoption inspection">
   <p>{opened.receipt.state==='applied'?`Existing adoption · encounter version ${opened.receipt.committed_revision}`:'Canceled choice · no actors changed'}</p>
   <p>Exact saved version: {opened.receipt.source.revision_id}</p>
   <ul>{opened.receipt.transitions.map(actor=><li key={actor.actor_id}>{actor.actor_id} · AC policy: {actor.ac_policy} · HP policy: {actor.hp_policy}</li>)}</ul>
   {opened.advanced_since_apply&&<p>This encounter has newer changes. The receipt describes the earlier adoption.</p>}
   <p>Inspection changed no tracker values or pending recovery. The current Plan identifies where you inspected this receipt, not when the original adoption happened.</p>
  </section>}
  {message&&<p role="status">{message}</p>}
 </details>;
}
