import {SurfaceObjectMenu} from '../SurfaceObjectMenu';
import {useEffect,useRef,useState} from 'react';
import {DurableWorkPlan} from '../../planSurface/components/DurableWorkPlan';
import {useWorkPlanHost} from './WorkPlanHost';
import {workPlanBelongsTo,workPlanIdentity,type WorkPlanReference} from './workPlanReference';
import {readPlacement,placementKey,PLACEMENT_CHANGED,type WorkPlanPlacement} from './workPlanPlacement';
import './workPlans.css';

/** One projection of the existing APP plan, never a second executor. */
export function SurfaceWorkPlan({reference,onTitleChange}:{reference:WorkPlanReference;onTitleChange?:(title:string)=>void}){
  const host=useWorkPlanHost(),root=useRef<HTMLElement|null>(null),[observed,setObserved]=useState<string|null>(null);
  const [checkedIdentity,setCheckedIdentity]=useState<string|null>(null);
  const [receipt,setReceipt]=useState<WorkPlanPlacement|null>(null),[receiptError,setReceiptError]=useState<string|null>(null);
  const identity=workPlanIdentity(reference),belongs=!!host&&workPlanBelongsTo(reference,host);
  useEffect(()=>{
    if(!belongs||!root.current)return;
    if(typeof IntersectionObserver==='undefined'){setObserved(identity);return;}
    const observer=new IntersectionObserver(entries=>{if(entries.some(entry=>entry.isIntersecting)){setObserved(identity);observer.disconnect();}});
    observer.observe(root.current);return()=>observer.disconnect();
  },[identity,belongs]);
  useEffect(()=>{
    if(!belongs)return;let active=true;let generation=0;
    const load=()=>{const own=++generation;void readPlacement(reference).then(p=>{if(active&&own===generation){setReceipt(p);setReceiptError(null);setCheckedIdentity(identity);}}).catch(reason=>{if(active&&own===generation)setReceiptError(String(reason));});};
    const storage=(event:StorageEvent)=>{if(event.key===placementKey(reference))load();};
    const changed=(event:Event)=>{if((event as CustomEvent).detail===identity)load();};
    load();window.addEventListener('storage',storage);window.addEventListener(PLACEMENT_CHANGED,changed);
    return()=>{active=false;window.removeEventListener('storage',storage);window.removeEventListener(PLACEMENT_CHANGED,changed);};
  },[identity,belongs]);
  if(!host||!workPlanBelongsTo(reference,host))return <section className="surface-work-plan" aria-label="Work plan">
    <strong>{reference.title}</strong><p>This plan belongs to its original page. Open that page to inspect it.</p>
  </section>;
  const placementPending=!!receipt&&receipt.phase!=='saved'&&receipt.phase!=='discarded';
  const editable=checkedIdentity===identity&&!receiptError&&!placementPending&&host.editable&&!host.busy&&host.activeConversationId===reference.conversation_id&&host.conversationId===reference.conversation_id;
  return <section ref={root} className="surface-work-plan" aria-label="Work plan" contentEditable={false}>
    <header><strong>{reference.title}</strong><SurfaceObjectMenu label="Plan options">{receipt&&<details><summary>Placement recovery</summary><pre>{JSON.stringify(receipt,null,2)}</pre></details>}</SurfaceObjectMenu></header>
    {editable&&onTitleChange?<label>Plan title<input aria-label="Plan title" defaultValue={reference.title} onBlur={event=>{
      const title=event.currentTarget.value.trim();if(title&&title!==reference.title)onTitleChange(title);else event.currentTarget.value=reference.title;
    }}/></label>:null}
    {receiptError?<p role="alert">{receiptError}</p>:null}
    {placementPending?<p role="status">Check the page Save before continuing. <button type="button" onClick={()=>host.openReply?.(reference.source_turn_id)}>Check Save</button></p>:null}

    {!editable&&!placementPending?<p>Open the original active conversation to edit or continue this plan.
      {host.openConversation?<button type="button" onClick={()=>host.openConversation!(reference.conversation_id)}>Open conversation</button>:null}</p>:null}
    {observed===identity?<DurableWorkPlan scope={{worldId:reference.world_id,documentId:reference.document_id,conversationId:reference.conversation_id,turnId:reference.source_turn_id,sourceSha256:reference.source_answer_sha256}}
      disabled={!editable} continuationDisabled={host.canContinue===false} beginContinuation={host.beginContinuation} saveLabel="Save" onContinue={host.onContinue}
      renderResult={execution=>execution.turn_id&&host.openReply?<button type="button" onClick={()=>host.openReply!(execution.turn_id!)}>View reply</button>:<p>Reply available in the original conversation.</p>}
      renderDraft={()=><p>The referenced review is unavailable. Open its original conversation to check it.</p>}/>:<p>Open this plan to load its steps.</p>}
  </section>;
}
