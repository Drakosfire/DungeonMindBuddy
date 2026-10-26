import {SurfaceObjectMenu} from '../SurfaceObjectMenu';
import {SurfaceNavbarIconButton} from '../../surfaceInteraction/contextHost/SurfaceNavbarIconButton';
import {useEffect,useRef,useState} from 'react';
import {SurfaceGraphReferenceInput} from '../SurfaceGraphReferenceInput';
import {isAuthoredGraphReferenceList,mergeAuthoredReferences} from '../../agentInteraction/authoredGraphReferences';
import {canonical,exact} from '../../shared/sourcePassageProtocol';
import type {AuthoredGraphReferenceV1,ConversationCollaboration} from '../../api/types';
import {getWorkPlanRecord,getWorkPlan,saveWorkPlan,planObjective,type WorkPlan,type WorkStep} from '../../api/conversationWorkPlanApi';
import {getWorkspaceDocumentSnapshot} from '../../api/liveApi';
import type {BuildComposeBridge,CapturedBuildInsertion,PreparedWorkPlanPlacement} from '../../buildSurface/buildComposeBridge';
import {SurfacePageProposal} from '../SurfacePageProposal';
import {markdownToTiptapDoc} from '../../tiptap/markdown/markdownToTiptap';
import {tiptapJsonToSemanticMarkdown} from '../../tiptap/markdown/calloutMarkdown';
import {workPlanIdentity,parseWorkPlanFence,type WorkPlanReference} from './workPlanReference';
import {placementDigest,readPlacement,stagePlacement,adoptPlacementReview,replacePlacement,changePlacement,savePlacementOnPage,placementKey,placementObjective,placementReferences,type WorkPlanPlacement} from './workPlanPlacement';
import './workPlans.css';

function contains(json:unknown,ref:WorkPlanReference):boolean{
 if(!json||typeof json!=='object')return false;
 const node=json as {type?:string;attrs?:{source?:string};content?:unknown[]};
 if(node.type==='surfaceWorkPlan'){
  try{return workPlanIdentity(parseWorkPlanFence(node.attrs?.source??''))===workPlanIdentity(ref);}catch{return false;}
 }
 return node.content?.some(child=>contains(child,ref))??false;
}
/** Chat carries only this compact locator. The editable review is portalled onto the page. */
export function StagedWorkPlan({worldId,documentId,conversationId,turnId,source,steps,objective:generatedObjective,bridge,pointerRevision,disabled,onVisible}:{
 worldId:string;documentId:string;conversationId:string;turnId:string;source:string;
 steps:Extract<ConversationCollaboration,{kind:'plan'}>['steps'];objective?:string;bridge:BuildComposeBridge|null;
 pointerRevision:number;disabled:boolean;onVisible:()=>void;
}){
 const [reference,setReference]=useState<WorkPlanReference|null>(null),[placement,setPlacement]=useState<WorkPlanPlacement|null>(null);
 const [captured,setCaptured]=useState<CapturedBuildInsertion|null>(null),[rows,setRows]=useState<WorkStep[]>([]);
 const [objective,setObjective]=useState(generatedObjective??'');
 const [reviewToAdopt,setReviewToAdopt]=useState<Extract<WorkPlan,{schema:'dmb_reviewed_work_plan_v3'}>|null>(null);
 const [rootReferences,setRootReferences]=useState<AuthoredGraphReferenceV1[]|undefined>();
 const [error,setError]=useState<string|null>(null),[stale,setStale]=useState(false),[busy,setBusy]=useState(false),[inPage,setInPage]=useState(false);
 const [refresh,setRefresh]=useState(0);const picker=useRef<AbortController|null>(null);
 const scope=JSON.stringify([worldId,documentId,conversationId,turnId,source,bridge!==null,pointerRevision]);
 const epoch=useRef({scope,bridge,value:0});if(epoch.current.scope!==scope||epoch.current.bridge!==bridge)epoch.current={scope,bridge,value:epoch.current.value+1};
 const current=useRef({scope,epoch:epoch.current.value,disabled,bridge});current.current={scope,epoch:epoch.current.value,disabled,bridge};
 useEffect(()=>()=>{current.current={...current.current,scope:'retired'};picker.current?.abort();},[]);
 function assertCurrent(start=current.current){if(current.current.scope!==start.scope||current.current.epoch!==start.epoch||current.current.disabled||current.current.bridge!==start.bridge)throw new Error('The page or active conversation changed. Your plan is retained.');}
 function noteKey(ref:WorkPlanReference){return 'dmb:surface-work-plan-notes:v1:'+workPlanIdentity(ref);}
 function writeNotes(p:WorkPlanPlacement,next:WorkStep[],outcome:string,roots=rootReferences){
  const bytes=JSON.stringify({schema:roots===undefined?'dmb_surface_plan_notes_v2':'dmb_surface_plan_notes_v3',command_id:p.command_id,rows:next,objective:outcome,...(roots===undefined?{}:{root_references:roots})});
  sessionStorage.setItem(noteKey(p.reference),bytes);if(sessionStorage.getItem(noteKey(p.reference))!==bytes)throw new Error('Plan edits could not be retained locally.');
 }
 function retain(next:WorkStep[],nextObjective=objective,roots=rootReferences){
  const normalized=roots===undefined?next:next.map(row=>({...row,references:row.references??[]}));
  if(roots!==undefined)for(const row of normalized)mergeAuthoredReferences(roots,row.references??[]);
  setRows(normalized);setObjective(nextObjective);setRootReferences(roots);if(!reference||!placement)return;try{writeNotes(placement,normalized,nextObjective,roots);}
 catch{setError('These edits could not be retained locally. Copy them before reloading.');}}
 useEffect(()=>{
  let active=true;setCaptured(null);setError(null);setStale(false);setReference(null);setPlacement(null);setReviewToAdopt(null);
  void (async()=>{
   const ref:WorkPlanReference={schema:'dmb_surface_work_plan_ref_v1',world_id:worldId,document_id:documentId,conversation_id:conversationId,source_turn_id:turnId,source_answer_sha256:await placementDigest(source),title:'Work plan'};
   const retained=await readPlacement(ref);if(!active)return;setReference(ref);setPlacement(retained);
   if(!retained)return;let restored=retained.rows;let restoredObjective=placementObjective(retained)??'';let restoredRoots=placementReferences(retained);
   const bytes=sessionStorage.getItem(noteKey(ref));if(bytes){const notes=JSON.parse(bytes);
    const retired=retained.retired_placements.find(item=>item.command_id===notes.command_id)?.review_snapshot;
    const basis=notes.command_id===retained.command_id?{rows:retained.rows,objective:placementObjective(retained),roots:placementReferences(retained)}:retired?{rows:retired.rows,objective:retired.objective,roots:retired.root_references}:null;
    const aware=notes.schema==='dmb_surface_plan_notes_v3';
    if(!exact(notes,['schema','command_id','rows',...(notes.schema==='dmb_surface_plan_notes_v1'?[]:['objective']),...(aware?['root_references']:[])])
     ||!['dmb_surface_plan_notes_v1','dmb_surface_plan_notes_v2','dmb_surface_plan_notes_v3'].includes(String(notes.schema))
     ||!basis||!Array.isArray(notes.rows)||notes.rows.length!==basis.rows.length
     ||!notes.rows.every((row:WorkStep,i:number)=>exact(row,['step_id','text','selected','kind',...(aware?['references']:[])])&&row.step_id===basis.rows[i].step_id&&typeof row.text==='string'&&typeof row.selected==='boolean'&&['discuss','prepare_insertion'].includes(row.kind)))
      throw new Error('Earlier local plan edits need comparison. Their bytes were left untouched.');
    let noteRoots=basis.roots;
    if(aware){
     if(!isAuthoredGraphReferenceList(notes.root_references,worldId)||!notes.rows.every((row:WorkStep)=>isAuthoredGraphReferenceList(row.references,worldId)))throw new Error('Invalid retained Graph context.');
     for(const row of notes.rows)mergeAuthoredReferences(notes.root_references,row.references);
     noteRoots=notes.root_references;
    }
    const noteRows=aware?notes.rows:notes.rows.map((row:WorkStep)=>({...row,...(noteRoots===undefined?{}:{references:basis.rows.find(saved=>saved.step_id===row.step_id)?.references??[]})}));
    const noteObjective=notes.schema==='dmb_surface_plan_notes_v1'?basis.objective:notes.objective;
    if(!(noteObjective===null||typeof noteObjective==='string'))throw new Error('Invalid retained expected outcome.');
    if(notes.command_id!==retained.command_id){
     if(canonical(noteRows)!==canonical(basis.rows)||noteObjective!==basis.objective||canonical(noteRoots)!==canonical(basis.roots))throw new Error('Earlier local edits differ from the retained predecessor. Compare both copies.');
    }else{
     restoredRoots=noteRoots;restored=noteRows;restoredObjective=noteObjective??'';
     if(retained.prepared&&(canonical(restored)!==canonical(retained.rows)||restoredObjective!==placementObjective(retained)||canonical(restoredRoots)!==canonical(placementReferences(retained))))throw new Error('Check the earlier Save before changing this plan. Local edits were retained.');
    }
   }
   setRows(restored);setObjective(restoredObjective);setRootReferences(restoredRoots);
   if(bridge&&!disabled&&retained.pointer_revision===pointerRevision&&retained.phase!=='discarded'&&retained.phase!=='saved'){
    try{const anchor=await bridge.restore(retained.basis);if(active){setCaptured(anchor);onVisible();}}
    catch(reason){if(active){setStale(true);setError(reason instanceof Error?reason.message:String(reason));}}
   }
  })().catch(reason=>{if(active)setError(reason instanceof Error?reason.message:String(reason));});
  return()=>{active=false;picker.current?.abort();};
 },[scope,refresh,disabled,bridge]);
 useEffect(()=>{setInPage(false);if(reference&&bridge?.observeWorkPlan)return bridge.observeWorkPlan(reference,setInPage);},[reference,bridge,refresh]);
 useEffect(()=>{
  if(!reference)return;const changed=(event:StorageEvent)=>{if(event.key===placementKey(reference)){setStale(true);setCaptured(null);setError('This placement changed in another tab. Reload its retained state before continuing.');}};
  window.addEventListener('storage',changed);return()=>window.removeEventListener('storage',changed);
 },[reference]);
 async function findSaved(ref:WorkPlanReference){
  const saved=await getWorkspaceDocumentSnapshot(documentId);
  if(saved.record.world_id!==worldId||saved.record.document_id!==documentId||saved.record.content_status!=='committed'||saved.loaded_revision!==saved.record.revision)throw new Error('The saved page could not be verified.');
  const json=markdownToTiptapDoc(saved.markdown).doc;
  if(!contains(json,ref))return null;
  return {revision:saved.loaded_revision,content_sha256:saved.content_sha256,body_sha256:await placementDigest(tiptapJsonToSemanticMarkdown(json))};
 }
 async function choose(){
  if(!reference||!bridge?.pickWorkPlanInsertion)return;const start=current.current;setBusy(true);setError(null);
  const controller=new AbortController();picker.current=controller;
  try{
   assertCurrent(start);if(await findSaved(reference))throw new Error('This plan is already on the saved page. Open that object.');assertCurrent(start);
   onVisible();
   const next=await bridge.pickWorkPlanInsertion({signal:controller.signal,operationId:placement?.command_id??crypto.randomUUID()});assertCurrent(start);
   if(next.basis.selection)throw new Error('Choose an insertion point; a plan does not replace selected text.');
   const record=await getWorkPlanRecord({worldId,documentId,conversationId,turnId,sourceSha256:reference.source_answer_sha256});assertCurrent(start);
   const saved=record.plan,initialRoots=saved?.schema==='dmb_reviewed_work_plan_v3'?saved.root_references:record.sourceReferences.length?record.sourceReferences:undefined;
   const previous=await readPlacement(reference);assertCurrent(start);
   let nextPlacement=previous?await replacePlacement(previous,next.basis,pointerRevision):await stagePlacement(reference,next.basis,pointerRevision,saved?.steps??steps.map(step=>({...step,selected:true,step_id:crypto.randomUUID()})),saved?.revision??0,localStorage,navigator.locks,saved?planObjective(saved):generatedObjective??'',initialRoots);
   if(previous?.schema==='dmb_surface_work_plan_placement_v1'&&!previous.prepared){nextPlacement=await changePlacement(nextPlacement,p=>({...p,schema:'dmb_surface_work_plan_placement_v2',objective,expected_review_revision:saved?.revision??0,acknowledged_review_revision:null,phase:'staged'}));assertCurrent(start);}
   if(previous){nextPlacement=await changePlacement(nextPlacement,p=>({...p,...(rootReferences===undefined?{schema:'dmb_surface_work_plan_placement_v2' as const}:{schema:'dmb_surface_work_plan_placement_v3' as const,root_references:rootReferences}),objective,rows}));assertCurrent(start);writeNotes(nextPlacement,rows,objective);}
   assertCurrent(start);setPlacement(nextPlacement);setRows(previous?rows:nextPlacement.rows);setRootReferences(previous?rootReferences:placementReferences(nextPlacement));setObjective(previous?objective:saved?planObjective(saved):placementObjective(nextPlacement)??'');setCaptured(next);setStale(false);onVisible();
  }catch(reason){if(current.current.scope===start.scope)setError(reason instanceof Error?reason.message:String(reason));}
  finally{if(current.current.scope===start.scope)setBusy(false);}
 }
 async function move(position:number){
  if(!placement||!captured||!bridge)return;const start=current.current;setBusy(true);setError(null);
  try{assertCurrent(start);const anchor=await bridge.restore({...placement.basis,caret:position});assertCurrent(start);
   let next=await replacePlacement(placement,anchor.basis,pointerRevision);assertCurrent(start);
   next=await changePlacement(next,p=>({...p,...(rootReferences===undefined?{schema:'dmb_surface_work_plan_placement_v2' as const}:{schema:'dmb_surface_work_plan_placement_v3' as const,root_references:rootReferences}),objective,rows}));assertCurrent(start);writeNotes(next,rows,objective);setPlacement(next);setCaptured(anchor);
  }catch(reason){setError(reason instanceof Error?reason.message:String(reason));}finally{if(current.current.scope===start.scope)setBusy(false);}
 }
 async function save(){
  if(!reference||!placement||!bridge?.prepareWorkPlan||!bridge.applyWorkPlan)return;const start=current.current;setBusy(true);setError(null);
  const planScope={worldId,documentId,conversationId,turnId,sourceSha256:reference.source_answer_sha256};
  try{
   const result=await savePlacementOnPage<PreparedWorkPlanPlacement>(placement,rows,{
    objective,rootReferences,
    assertCurrent:()=>{assertCurrent(start);if(pointerRevision!==placement.pointer_revision)throw new Error('The conversation pointer changed. Choose a new position.');},
    readReview:async()=>{const plan=await getWorkPlan(planScope);assertCurrent(start);if(plan?.schema==='dmb_reviewed_work_plan_v3'&&(rootReferences===undefined||plan.revision!==placement.expected_review_revision))setReviewToAdopt(plan);return plan;},saveReview:(revision,reviewed,outcome,roots)=>saveWorkPlan(planScope,revision,reviewed,outcome,roots),
    findSaved:()=>findSaved(reference),prepare:async receipt=>{const anchor=await bridge.restore(receipt.basis);const prepared=await bridge.prepareWorkPlan!(anchor,receipt.reference);return {value:prepared,after_editor_sha256:prepared.afterEditorSha256,after_draft_sha256:prepared.afterDraftSha256};},
    inspect:receipt=>bridge.inspectProposal(receipt.basis,receipt.prepared!.after_editor_sha256,receipt.prepared!.after_draft_sha256),
    apply:prepared=>bridge.applyWorkPlan!(prepared),
    save:async receipt=>{await bridge.saveProposal(receipt.basis,receipt.prepared!.after_editor_sha256,receipt.prepared!.after_draft_sha256);
     const saved=await findSaved(reference);if(!saved||saved.body_sha256!==receipt.prepared!.after_draft_sha256)throw new Error('The saved page does not yet verify this insertion.');
     return {revision:saved.revision,content_sha256:saved.content_sha256};},
   });
   assertCurrent(start);setPlacement(result.placement);setInPage(true);setCaptured(null);
   if(result.placement.phase==='saved')sessionStorage.removeItem(noteKey(reference));
  }catch(reason){if(current.current.scope===start.scope){setError(reason instanceof Error?reason.message:String(reason));const retained=await readPlacement(reference).catch(()=>null);if(retained)setPlacement(retained);}}
  finally{if(current.current.scope===start.scope)setBusy(false);}
 }
 async function adoptSavedReview(){
  if(!reviewToAdopt||!placement||placement.prepared||placement.phase==='review_saving')return;
  const start=current.current,saved=reviewToAdopt;setBusy(true);setError(null);
  try{
   assertCurrent(start);const latest=await getWorkPlan({worldId,documentId,conversationId,turnId,sourceSha256:placement.reference.source_answer_sha256});assertCurrent(start);
   if(canonical(latest)!==canonical(saved))throw new Error('The saved review changed again. Check it before adopting.');
   const next=await adoptPlacementReview(placement,{rows,objective,rootReferences},saved);assertCurrent(start);
   setPlacement(next);setRows(saved.steps);setRootReferences(saved.root_references);setObjective(saved.objective);writeNotes(next,saved.steps,saved.objective,saved.root_references);setReviewToAdopt(null);
  }catch(reason){if(current.current.scope===start.scope)setError(String(reason));}
  finally{if(current.current.scope===start.scope)setBusy(false);}
 }
 const review=<section className="surface-work-plan" aria-label="Plan suggestion" contentEditable={false}>
  <header className="surface-work-plan__header"><strong>Work plan</strong><SurfaceObjectMenu label="Plan suggestion options">{placement&&<details><summary>Placement recovery</summary><pre>{JSON.stringify(placement,null,2)}</pre></details>}</SurfaceObjectMenu><button type="button" aria-label="Dismiss plan suggestion" disabled={disabled||busy||!!placement?.prepared||placement?.phase==='review_saving'} onClick={()=>{
   if(!placement)return;const start=current.current;setBusy(true);void changePlacement(placement,p=>({...p,phase:'discarded'})).then(next=>{assertCurrent(start);setPlacement(next);setCaptured(null);}).catch(reason=>{if(current.current.scope===start.scope)setError(String(reason));}).finally(()=>{if(current.current.scope===start.scope)setBusy(false);});
  }}>×</button></header>
  <label>Expected outcome<textarea aria-label="Expected outcome" value={objective} disabled={disabled||busy||!!placement?.prepared} onChange={event=>retain(rows,event.target.value)}/></label>
  <SurfaceGraphReferenceInput worldId={worldId} label="Plan Graph context" value={rootReferences??[]} disabled={disabled||busy||!!placement?.prepared} onChange={refs=>retain(rows,objective,refs)}/>
  {rows.map((row,i)=><div className="surface-work-plan__step" key={row.step_id}><label className="surface-work-plan__include"><input type="checkbox" checked={row.selected} disabled={disabled||busy||!!placement?.prepared} onChange={event=>retain(rows.map((s,j)=>j===i?{...s,selected:event.target.checked}:s))}/><span className="surface-work-plan__sr">Include step {i+1}</span></label><span className="surface-work-plan__number" aria-hidden="true">{i+1}.</span>
   <textarea aria-label={`Plan step ${i+1}`} value={row.text} disabled={disabled||busy||!!placement?.prepared} onChange={event=>retain(rows.map((s,j)=>j===i?{...s,text:event.target.value}:s))}/>
   <label className="surface-work-plan__action"><span className="surface-work-plan__sr">Action</span><select aria-label={`Plan action ${i+1}`} value={row.kind} disabled={disabled||busy||!!placement?.prepared} onChange={event=>retain(rows.map((s,j)=>j===i?{...s,kind:event.target.value as WorkStep['kind']}:s))}><option value="discuss">Discuss</option><option value="prepare_insertion">Prepare an insertion</option></select></label>
   <div className="surface-work-plan__references"><SurfaceGraphReferenceInput worldId={worldId} label={`Step ${i+1} Graph context`} value={row.references??[]} disabled={disabled||busy||!!placement?.prepared} onChange={refs=>retain(rows.map(s=>s.step_id===row.step_id?{...s,references:refs}:s),objective,rootReferences??[])}/></div>
  </div>)}
  <SurfaceNavbarIconButton icon="save" label="Save" disabled={disabled||busy||stale||!objective.trim()||!rows.length||rows.some(row=>!row.text.trim())} onClick={()=>void save()}/>
  {reviewToAdopt&&<section aria-label="Saved review comparison"><p>The saved review has Graph context. Your local version is retained.</p><p>{reviewToAdopt.objective}</p><SurfaceGraphReferenceInput worldId={worldId} label="Saved review Graph context" readOnly value={reviewToAdopt.root_references} onChange={()=>{}}/><ol>{reviewToAdopt.steps.map(row=><li key={row.step_id}>{row.text}<SurfaceGraphReferenceInput worldId={worldId} label="Saved step Graph context" readOnly value={row.references??[]} onChange={()=>{}}/></li>)}</ol><button type="button" disabled={disabled||busy||!!placement?.prepared||placement?.phase==='review_saving'} onClick={()=>void adoptSavedReview()}>Use saved review for this placement</button></section>}
  {error?<p role="alert">{error}</p>:null}
 </section>;
 return <>
  {(!captured||stale||inPage)&&placement&&<SurfaceObjectMenu label="Plan placement options"><details><summary>Placement recovery</summary><pre>{JSON.stringify(placement,null,2)}</pre></details></SurfaceObjectMenu>}
  <p>{inPage?'Plan on page.':captured&&!stale?'Plan prepared on the page.':'Plan ready for page placement.'}</p>
  {!inPage&&(!captured||stale)?<button type="button" disabled={disabled||busy||!reference||!bridge?.pickWorkPlanInsertion||placement?.phase==='review_saving'&&placement.schema!=='dmb_surface_work_plan_placement_v1'} onClick={()=>void choose()}>Place plan on page</button>:null}
  {placement?.schema==='dmb_surface_work_plan_placement_v1'&&placement.phase==='review_saving'&&!placement.prepared?<button type="button" disabled={disabled||busy} onClick={()=>void choose()}>Choose a new placement with an expected outcome</button>:null}
  {placement?.prepared&&placement.phase!=='saved'?<button type="button" disabled={disabled||busy} onClick={()=>void save()}>Check and finish Save</button>:null}
  {error&&(!captured||stale||inPage)?<p role="alert">{error}</p>:null}
  {stale?<button type="button" disabled={busy} onClick={()=>setRefresh(value=>value+1)}>Reload retained placement</button>:null}

  {captured&&!stale&&!inPage?<SurfacePageProposal editor={captured.editor} position={captured.basis.caret} editorJson={captured.editorJson}
   placementId={placement?.command_id} revealKey={1} busy={busy} focusOnReveal={false} onStale={()=>{if(!busy)setStale(true);}}
   onMove={position=>void move(position)}>{review}</SurfacePageProposal>:null}
 </>;
}
