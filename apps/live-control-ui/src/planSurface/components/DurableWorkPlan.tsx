import {useEffect,useRef,useState,type ReactNode} from 'react'
import {getWorkPlan,saveWorkPlan,continueWorkPlan,type WorkPlan,type WorkStep,type WorkDispatch,type WorkPlanScope} from '../../api/conversationWorkPlanApi'
export type ReviewedRow={text:string;include:boolean;kind?:'discuss'|'prepare_insertion'}
export function DurableWorkPlan({scope,disabled,onContinue,renderDraft}:{scope:WorkPlanScope;disabled:boolean;onContinue:(plan:WorkPlan,dispatch:WorkDispatch)=>void;renderDraft:(save:(rows:ReviewedRow[])=>Promise<void>,busy:boolean)=>ReactNode}){
 const [plan,setPlan]=useState<WorkPlan|null>(null),[steps,setSteps]=useState<WorkStep[]>([]),[loaded,setLoaded]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState<string|null>(null)
 const [staleDraft,setStaleDraft]=useState(false),[blockedDraft,setBlockedDraft]=useState(false)
 const identity=JSON.stringify([scope.worldId,scope.conversationId,scope.turnId,scope.source]);const current=useRef<string|null>(null)
 const draftKey=`dmb:reviewed-plan-edit:v1:${identity}`;const edited=useRef(false)
 function retain(next:WorkStep[]){edited.current=true;setSteps(next);if(blockedDraft)return;try{sessionStorage.setItem(draftKey,JSON.stringify({schema:'dmb_reviewed_plan_edit_v1',identity,base_revision:plan?.revision,steps:next}))}catch{setError('These plan edits could not be retained locally. Keep a copy before reloading.')}}
 function restore(p:WorkPlan){
  try{
   const raw=sessionStorage.getItem(draftKey);if(!raw)return p.steps
   const v=JSON.parse(raw);if(v.schema!=='dmb_reviewed_plan_edit_v1'||v.identity!==identity||!Array.isArray(v.steps)||!v.steps.every((s:WorkStep)=>s&&typeof s.step_id==='string'&&typeof s.text==='string'&&typeof s.selected==='boolean'&&['discuss','prepare_insertion'].includes(s.kind)))throw new Error('Invalid local plan copy')
   edited.current=true;if(v.base_revision!==p.revision){setStaleDraft(true);setError('The saved plan changed. Your local edits were restored; compare them before saving.')}
   return v.steps as WorkStep[]
  }catch{setBlockedDraft(true);setError('Local plan edits could not be restored; their bytes were left untouched.');return p.steps}
 }
 function adopted(p:WorkPlan){setStaleDraft(false);setBlockedDraft(false);setPlan(p);setSteps(p.steps);edited.current=false;try{sessionStorage.removeItem(draftKey)}catch{setError('The saved plan is durable, but this tab could not clear its older local copy.')}}
 useEffect(()=>{let active=true;current.current=identity;setLoaded(false);setError(null);void getWorkPlan(scope).then(p=>{if(active){setPlan(p);setSteps(p?restore(p):[]);setLoaded(true)}}).catch(e=>{if(active)setError(String(e))});return()=>{active=false;current.current=null}},[identity])
 async function run(action:()=>Promise<void>){setBusy(true);setError(null);try{await action()}catch(e){if(current.current===identity)setError(e instanceof Error?e.message:String(e))}finally{if(current.current===identity)setBusy(false)}}
 async function saveDraft(rows:ReviewedRow[]){await run(async()=>{const p=await saveWorkPlan(scope,0,rows.map(r=>({step_id:crypto.randomUUID(),text:r.text,selected:r.include,kind:r.kind??'discuss'})));if(current.current===identity)adopted(p)})}
 const changed=!!plan&&JSON.stringify(steps)!==JSON.stringify(plan.steps)
 const locked=(id:string)=>!!plan?.dispatches.some(d=>d.step_id===id)
 useEffect(()=>{
  if(!plan||!plan.execution.some(x=>['awaiting_dispatch','accepted','running'].includes(x.status)))return
  let active=true
  const timer=setInterval(()=>{void getWorkPlan(scope).then(p=>{if(active&&current.current===identity&&p){if(edited.current&&p.revision!==plan.revision)setStaleDraft(true);setPlan(p);if(!edited.current)setSteps(p.steps)}}).catch(e=>{if(active)setError(String(e))})},2000)
  return()=>{active=false;clearInterval(timer)}
 },[identity,plan?.revision,plan?.execution.map(x=>x.status).join(',')])
 function edit(id:string,update:Partial<WorkStep>){retain(steps.map(s=>s.step_id===id?{...s,...update}:s))}
 return <section aria-label="Saved work plan">
  {error&&<p role="alert">{error}</p>}
  {error&&!plan&&<button type="button" disabled={busy} onClick={()=>{void run(async()=>{const p=await getWorkPlan(scope);if(current.current===identity){setPlan(p);setSteps(p?restore(p):[]);setLoaded(true)}})}}>Reload saved plan</button>}
  {!loaded?<p role="status">Opening saved plan…</p>:!plan?renderDraft(saveDraft,busy):<>
   <h4>Reviewed plan</h4>
   {staleDraft&&<><p role="alert">The saved review changed. Compare before saving these edits.</p><details><summary>Latest saved steps</summary><ol>{plan.steps.map(s=><li key={s.step_id}>{s.selected?'Selected':'Deferred'} · {s.text}</li>)}</ol></details><button type="button" disabled={disabled||busy} onClick={()=>{setStaleDraft(false);setError(null);retain(steps)}}>Use these edits against the latest review</button></>}
   {blockedDraft&&<button type="button" disabled={disabled||busy} onClick={()=>adopted(plan)}>Use saved plan and replace unreadable local copy</button>}
   {steps.map((s,i)=>{const executions=plan.execution.filter(x=>x.step_id===s.step_id),last=executions.at(-1),status=last?.status??(s.selected?'pending':'deferred');return <div key={s.step_id}>
    <label><input type="checkbox" checked={s.selected} disabled={disabled||busy||locked(s.step_id)} onChange={e=>edit(s.step_id,{selected:e.target.checked})}/> Include step {i+1}</label>
    <textarea aria-label={`Saved step ${i+1}`} value={s.text} disabled={disabled||busy||locked(s.step_id)} onChange={e=>edit(s.step_id,{text:e.target.value})}/>
    <label>Action <select aria-label={`Saved action ${i+1}`} value={s.kind} disabled={disabled||busy||locked(s.step_id)} onChange={e=>edit(s.step_id,{kind:e.target.value as WorkStep['kind']})}><option value="discuss">Discuss</option><option value="prepare_insertion">Prepare an insertion</option></select></label>
    <p role="status">{status==='completed'?'Reply received':status==='prepared'?'Suggestion prepared · review and Save on the page':status==='awaiting_dispatch'?'Ready to resume the same request':status==='needs_attention'?'Result needs attention':status}</p>
    {last?.result?.kind==='reply'&&<p>{last.result.text}</p>}
    {executions.length>1&&<details><summary>Previous continuations · {executions.length-1}</summary>{executions.slice(0,-1).map(x=><p key={x.command_id}>{x.status} · {x.turn_id??'not admitted'}</p>)}</details>}
    <button type="button" disabled={disabled||busy||changed||staleDraft||blockedDraft||!s.selected||['accepted','running','completed','prepared','needs_attention'].includes(status)} onClick={()=>{void run(async()=>{const response=await continueWorkPlan(scope,plan,s.step_id,crypto.randomUUID());if(current.current!==identity)return;adopted(response.plan);onContinue(response.plan,response.dispatch)})}}>{status==='awaiting_dispatch'?'Resume step':status==='failed'||status==='interrupted'?'Try step again':'Continue step'}</button>
   </div>})}
   <button type="button" disabled={disabled||busy} onClick={()=>retain([...steps,{step_id:crypto.randomUUID(),text:'',selected:true,kind:'discuss'}])}>Add step</button>{' '}
   <button type="button" disabled={disabled||busy||staleDraft||blockedDraft||!changed||steps.some(s=>!s.text.trim())} onClick={()=>{void run(async()=>{const p=await saveWorkPlan(scope,plan.revision,steps);if(current.current===identity)adopted(p)})}}>Save reviewed plan</button>{' '}
   <button type="button" disabled={busy||changed} onClick={()=>{void run(async()=>{const p=await getWorkPlan(scope);if(p&&current.current===identity)adopted(p)})}}>Refresh results</button>
  </>}
 </section>
}
