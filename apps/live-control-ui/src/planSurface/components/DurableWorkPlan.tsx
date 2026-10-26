import {SurfaceNavbarIconButton} from '../../surfaceInteraction/contextHost/SurfaceNavbarIconButton'
import {SurfaceGraphReferenceInput} from '../../surface/SurfaceGraphReferenceInput'
import {isAuthoredGraphReferenceList,mergeAuthoredReferences} from '../../agentInteraction/authoredGraphReferences'
import type {AuthoredGraphReferenceV1,ReviewedStepReference} from '../../api/types'
import {useEffect,useRef,useState,type ReactNode} from 'react'
import {getWorkPlan,saveWorkPlan,continueWorkPlan,planObjective,type WorkPlan,type WorkStep,type WorkDispatch,type WorkPlanScope,type WorkExecution} from '../../api/conversationWorkPlanApi'
export type WorkPlanToolbarControls={add:ReactNode;save:ReactNode}
export type ReviewedRow={text:string;include:boolean;kind?:'discuss'|'prepare_insertion'}
export function DurableWorkPlan({scope,disabled,onContinue,renderDraft,saveLabel="Save reviewed plan",renderResult,continuationDisabled=false,beginContinuation,renderToolbar}:{renderToolbar?:(controls:WorkPlanToolbarControls)=>ReactNode;continuationDisabled?:boolean;beginContinuation?:(plan:WorkPlan)=>()=>boolean;saveLabel?:string;renderResult?:(execution:WorkExecution)=>ReactNode;scope:WorkPlanScope;disabled:boolean;onContinue:(plan:WorkPlan,dispatch:WorkDispatch,reference:ReviewedStepReference|null)=>void;renderDraft:(save:(rows:ReviewedRow[])=>Promise<void>,busy:boolean)=>ReactNode}){
 const [plan,setPlan]=useState<WorkPlan|null>(null),[steps,setSteps]=useState<WorkStep[]>([]),[loaded,setLoaded]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState<string|null>(null)
 const [objective,setObjective]=useState('')
 const [rootReferences,setRootReferences]=useState<AuthoredGraphReferenceV1[]|undefined>(undefined)
 const [staleDraft,setStaleDraft]=useState(false),[blockedDraft,setBlockedDraft]=useState(false)
 const identity=JSON.stringify([scope.worldId,scope.conversationId,scope.turnId,scope.source??{sha256:scope.sourceSha256,documentId:scope.documentId}]);const current=useRef<string|null>(null)
 const lifecycle=useRef({identity,disabled,continuationDisabled,epoch:0});
 if(lifecycle.current.identity!==identity||lifecycle.current.disabled!==disabled||lifecycle.current.continuationDisabled!==continuationDisabled)
  lifecycle.current={identity,disabled,continuationDisabled,epoch:lifecycle.current.epoch+1};
 const draftKey=`dmb:reviewed-plan-edit:v1:${identity}`;const edited=useRef(false)
 function retain(next:WorkStep[],nextObjective=objective,nextReferences=rootReferences){
  const refs=nextReferences,rows=refs===undefined?next:next.map(row=>({...row,references:row.references??[]}));
  if(refs!==undefined)for(const row of rows)mergeAuthoredReferences(refs,row.references??[]);
  edited.current=true;setSteps(rows);setObjective(nextObjective);setRootReferences(refs);if(blockedDraft)return;
  try{sessionStorage.setItem(draftKey,JSON.stringify({schema:refs===undefined?'dmb_reviewed_plan_edit_v2':'dmb_reviewed_plan_edit_v3',identity,base_revision:plan?.revision,steps:rows,objective:nextObjective,...(refs===undefined?{}:{root_references:refs})}))}catch{setError('These plan edits could not be retained locally. Keep a copy before reloading.')}
 }
 function saveReview(revision:number,rows:WorkStep[],outcome:string){return rootReferences===undefined?saveWorkPlan(scope,revision,rows,outcome):saveWorkPlan(scope,revision,rows,outcome,rootReferences)}
 function restore(p:WorkPlan){
  try{
   const raw=sessionStorage.getItem(draftKey);if(!raw)return p.steps
   const v=JSON.parse(raw);if(!['dmb_reviewed_plan_edit_v1','dmb_reviewed_plan_edit_v2','dmb_reviewed_plan_edit_v3'].includes(v.schema)||v.schema!=='dmb_reviewed_plan_edit_v1'&&typeof v.objective!=='string'||v.identity!==identity||!Array.isArray(v.steps)||!v.steps.every((s:WorkStep)=>s&&typeof s.step_id==='string'&&typeof s.text==='string'&&typeof s.selected==='boolean'&&['discuss','prepare_insertion'].includes(s.kind)))throw new Error('Invalid local plan copy')
   if(v.schema==='dmb_reviewed_plan_edit_v3'){if(!isAuthoredGraphReferenceList(v.root_references,scope.worldId)||!v.steps.every((row:WorkStep)=>isAuthoredGraphReferenceList(row.references,scope.worldId)))throw new Error('Invalid local Graph reference copy');for(const row of v.steps)mergeAuthoredReferences(v.root_references,row.references);setRootReferences(v.root_references)}else if(v.steps.some((row:WorkStep)=>row.references!==undefined))throw new Error('Unversioned local Graph references');
   setObjective(v.schema!=='dmb_reviewed_plan_edit_v1'?v.objective:'');edited.current=true;if(v.base_revision!==p.revision){setStaleDraft(true);setError('The saved plan changed. Your local edits were restored; compare them before saving.')}
   // A pre-reference local copy edits wording/selection, not unseen saved Graph context.
   return v.schema!=='dmb_reviewed_plan_edit_v3'&&p.schema==='dmb_reviewed_work_plan_v3'
    ?v.steps.map((row:WorkStep)=>({...row,references:p.steps.find(saved=>saved.step_id===row.step_id)?.references??[]})):v.steps as WorkStep[]
  }catch{setBlockedDraft(true);setError('Local plan edits could not be restored; their bytes were left untouched.');return p.steps}
 }
 function adopted(p:WorkPlan){setStaleDraft(false);setBlockedDraft(false);setPlan(p);setSteps(p.steps);setObjective(planObjective(p));setRootReferences(p?.schema==='dmb_reviewed_work_plan_v3'?p.root_references:undefined);edited.current=false;try{sessionStorage.removeItem(draftKey)}catch{setError('The saved plan is durable, but this tab could not clear its older local copy.')}}
 useEffect(()=>{let active=true;current.current=identity;setLoaded(false);setError(null);void getWorkPlan(scope).then(p=>{if(active){setPlan(p);setObjective(planObjective(p));setRootReferences(p?.schema==='dmb_reviewed_work_plan_v3'?p.root_references:undefined);setSteps(p?restore(p):[]);setLoaded(true)}}).catch(e=>{if(active)setError(String(e))});return()=>{active=false;current.current=null}},[identity])
 async function run(action:()=>Promise<void>){setBusy(true);setError(null);try{await action()}catch(e){if(current.current===identity)setError(e instanceof Error?e.message:String(e))}finally{if(current.current===identity)setBusy(false)}}
 async function saveDraft(rows:ReviewedRow[]){await run(async()=>{const p=await saveReview(0,rows.map(r=>({step_id:crypto.randomUUID(),text:r.text,selected:r.include,kind:r.kind??'discuss'})),objective);if(current.current===identity)adopted(p)})}
 const changed=!!plan&&(JSON.stringify(steps)!==JSON.stringify(plan.steps)||objective!==planObjective(plan)||JSON.stringify(rootReferences)!==JSON.stringify(plan.schema==='dmb_reviewed_work_plan_v3'?plan.root_references:undefined))
 const locked=(id:string)=>!!plan?.dispatches.some(d=>d.step_id===id)
 useEffect(()=>{
  if(!plan||!plan.execution.some(x=>['awaiting_dispatch','accepted','running'].includes(x.status)))return
  let active=true
  const timer=setInterval(()=>{void getWorkPlan(scope).then(p=>{if(active&&current.current===identity&&p){if(edited.current&&p.revision!==plan.revision)setStaleDraft(true);setPlan(p);if(!edited.current){setSteps(p.steps);setObjective(planObjective(p));setRootReferences(p.schema==='dmb_reviewed_work_plan_v3'?p.root_references:undefined)}}}).catch(e=>{if(active)setError(String(e))})},2000)
  return()=>{active=false;clearInterval(timer)}
 },[identity,plan?.revision,plan?.execution.map(x=>x.status).join(',')])
 function edit(id:string,update:Partial<WorkStep>){retain(steps.map(s=>s.step_id===id?{...s,...update}:s))}
 const addControl=<SurfaceNavbarIconButton icon="new" label="Add step" disabled={!plan||disabled||busy} onClick={()=>retain([...steps,{step_id:crypto.randomUUID(),text:'',selected:true,kind:'discuss'}])}/>;
 const saveControl=<SurfaceNavbarIconButton icon="save" label={saveLabel} disabled={!plan||disabled||busy||staleDraft||blockedDraft||!changed||!objective.trim()||steps.some(s=>!s.text.trim())} onClick={()=>{if(!plan)return;const saved=plan;void run(async()=>{const p=await saveReview(saved.revision,steps,objective);if(current.current===identity)adopted(p)})}}/>;
 return <section className="surface-work-plan-review" aria-label="Saved work plan">
  {renderToolbar?.({add:addControl,save:saveControl})}
  {error&&<p role="alert">{error}</p>}
  {error&&!plan&&<button type="button" disabled={busy} onClick={()=>{void run(async()=>{const p=await getWorkPlan(scope);if(current.current===identity){setPlan(p);setObjective(planObjective(p));setRootReferences(p?.schema==='dmb_reviewed_work_plan_v3'?p.root_references:undefined);setSteps(p?restore(p):[]);setLoaded(true)}})}}>Reload saved plan</button>}
  {!loaded?<p role="status">Opening saved plan…</p>:!plan?<><label>Expected outcome<textarea aria-label="Expected outcome" value={objective} disabled={disabled||busy} onChange={e=>setObjective(e.target.value)}/></label>{renderDraft(saveDraft,busy)}</>:<>
   {disabled?<p><strong>Expected outcome</strong><br/>{objective||'Not specified in this plan.'}</p>:<label>Expected outcome<textarea aria-label="Expected outcome" value={objective} disabled={busy} onChange={e=>retain(steps,e.target.value)}/></label>}
   <SurfaceGraphReferenceInput worldId={scope.worldId} label="Plan Graph context" value={rootReferences??[]} disabled={disabled||busy} onChange={refs=>retain(steps,objective,refs)}/>
   {!planObjective(plan)&&<p>Add an expected outcome and Save before continuing a new step.</p>}
   {staleDraft&&<><p role="alert">The saved review changed. Compare before saving these edits.</p><details><summary>Latest saved review</summary><p>Expected outcome: {planObjective(plan)||'Not specified'}</p><SurfaceGraphReferenceInput worldId={scope.worldId} label="Latest saved plan Graph context" value={plan.schema==='dmb_reviewed_work_plan_v3'?plan.root_references:[]} disabled onChange={()=>{}}/><ol>{plan.steps.map(s=><li key={s.step_id}>{s.selected?'Selected':'Deferred'} · {s.text}<SurfaceGraphReferenceInput worldId={scope.worldId} label="Latest saved step Graph context" value={s.references??[]} disabled onChange={()=>{}}/></li>)}</ol></details><button type="button" disabled={disabled||busy} onClick={()=>{setStaleDraft(false);setError(null);retain(steps)}}>Use these edits against the latest review</button></>}
   {blockedDraft&&<button type="button" disabled={disabled||busy} onClick={()=>adopted(plan)}>Use saved plan and replace unreadable local copy</button>}
   {steps.map((s,i)=>{const executions=plan.execution.filter(x=>x.step_id===s.step_id),last=executions.at(-1),status=last?.status??(s.selected?'pending':'deferred');const body=<>
    {!locked(s.step_id)&&<label className="surface-work-plan__include"><input type="checkbox" checked={s.selected} disabled={disabled||busy||locked(s.step_id)} onChange={e=>edit(s.step_id,{selected:e.target.checked})}/><span className="surface-work-plan__sr">Include step {i+1}</span></label>}
    <textarea aria-label={`Saved step ${i+1}`} value={s.text} disabled={disabled||busy||locked(s.step_id)} onChange={e=>edit(s.step_id,{text:e.target.value})}/>
    <label className="surface-work-plan__action"><span className="surface-work-plan__sr">Action</span><select aria-label={`Saved action ${i+1}`} value={s.kind} disabled={disabled||busy||locked(s.step_id)} onChange={e=>edit(s.step_id,{kind:e.target.value as WorkStep['kind']})}><option value="discuss">Discuss</option><option value="prepare_insertion">Prepare an insertion</option></select></label>
    {!locked(s.step_id)&&<SurfaceNavbarIconButton className="surface-work-plan__remove" icon="remove" label={`Remove step ${i+1}`} disabled={disabled||busy||steps.length<=1} title={steps.length<=1?'A plan needs at least one step':`Remove step ${i+1}`} onClick={()=>retain(steps.filter(row=>row.step_id!==s.step_id))}/>}
    <div className="surface-work-plan__references"><SurfaceGraphReferenceInput worldId={scope.worldId} label={`Step ${i+1} Graph context`} value={s.references??[]} disabled={disabled||busy||locked(s.step_id)} onChange={refs=>retain(steps.map(row=>row.step_id===s.step_id?{...row,references:refs}:row),objective,rootReferences??[])}/></div>
    <p className="surface-work-plan__status" role="status">{status==='completed'?'Reply received':status==='prepared'?'Suggestion prepared · review and Save on the page':status==='awaiting_dispatch'?'Ready to resume the same request':status==='needs_attention'?'Result needs attention':status}</p>
    {last?.result?.kind==='reply'&&<div className="surface-work-plan__result">{renderResult?renderResult(last):<p>{last.result.text}</p>}</div>}
    {executions.length>1&&<details><summary>Previous continuations · {executions.length-1}</summary>{executions.slice(0,-1).map(x=><p key={x.command_id}>{x.status} · {x.turn_id??'not admitted'}</p>)}</details>}
    <button className="surface-work-plan__continue" type="button" disabled={disabled||continuationDisabled||busy||changed||staleDraft||blockedDraft||(!planObjective(plan)&&status!=='awaiting_dispatch')||!s.selected||['accepted','running','completed','prepared','needs_attention'].includes(status)} onClick={()=>{void run(async()=>{const admitted=beginContinuation?.(plan)??(()=>true),epoch=lifecycle.current.epoch;
     if(disabled||continuationDisabled||!admitted())throw new Error('Save and open the current page before continuing.');
     const response=await continueWorkPlan(scope,plan,s.step_id,crypto.randomUUID());if(current.current!==identity)return;
     if(lifecycle.current.epoch!==epoch||!admitted())throw new Error('The page or conversation changed. The reserved step was retained; refresh results before explicitly resuming.');
     adopted(response.plan);onContinue(response.plan,response.dispatch,response.reference)})}}>{status==='awaiting_dispatch'?'Resume step':status==='failed'||status==='interrupted'?'Try step again':'Continue step'}</button>
   </>;
    return status==='completed'?<details className="surface-work-plan__finished" key={s.step_id}><summary><span>{i+1}. {s.text}</span><span className="surface-work-plan__badge">Reply received</span></summary><div className="surface-work-plan__step">{body}</div></details>:<div className="surface-work-plan__step" key={s.step_id}><span className="surface-work-plan__number" aria-hidden="true">{i+1}.</span>{body}</div>;
   })}
   {!renderToolbar&&<>{addControl}{' '}{saveControl}{' '}</>}
   <button type="button" disabled={busy||changed} onClick={()=>{void run(async()=>{const p=await getWorkPlan(scope);if(p&&current.current===identity)adopted(p)})}}>Refresh results</button>
  </>}
 </section>
}
