import {useEffect,useRef,useState} from 'react';
import {useSelectedWorld} from '../selectedWorld/SelectedWorldContext';
import type {ExactRunCandidateProjection} from '../api/exactRunCandidateProjectionApi';
import {getRecapNativeReviews,type RecapNativeReview} from '../api/recapNativeReviewApi';
import {admitRecapSource,resumeRecapSource,type NativeRecapSourceStatus,type RecapSourceTarget} from '../api/nativeRecapSourceApi';
import {assertNativeMergePlan,prepareNativeMerge,confirmNativeMerge,type NativeMergePlan,type NativeMergeRequest} from '../api/recapNativePublicationApi';
import {mergeIdentity,recapMergeSelections,sameMergeContext} from './recapMergeSelections';

export function mergeRecoveryKey(p:ExactRunCandidateProjection) {
 return 'dmb:native-recap-merge:v1:'+JSON.stringify([p.managedWorldId,p.nativeWorldId,p.bindingVersion,p.runId,p.runRevision,p.sourceRevisionId,p.candidateSha256,p.spanIndexSha256]);
}
function retain(key:string,plan:NativeMergePlan,submitted:boolean) {
 const raw=JSON.stringify({plan,submitted});localStorage.setItem(key,raw);
 if(localStorage.getItem(key)!==raw)throw new Error('The exact confirmation could not be saved. Nothing was sent.');
}
function restore(key:string,p:ExactRunCandidateProjection) {
 try {
  const raw=localStorage.getItem(key);if(!raw)return {plan:null,submitted:false,error:null};
  const saved=JSON.parse(raw);assertNativeMergePlan(saved.plan,p);
  if(typeof saved.submitted!=='boolean')throw new Error();
  return {plan:saved.plan,submitted:saved.submitted,error:null};
 } catch {return {plan:null,submitted:true,error:'The saved confirmation could not be verified. It remains preserved; do not start another merge.'};}
}
export function RecapNativeMerge(props:{projection:ExactRunCandidateProjection;onClose:()=>void}) {
 const world=useSelectedWorld();
 if(world.kind!=='managed'||world.worldId!==props.projection.managedWorldId)return null;
 return <MergeConfirmation key={mergeRecoveryKey(props.projection)} {...props}/>;
}
function MergeConfirmation({projection:p,onClose}:{projection:ExactRunCandidateProjection;onClose:()=>void}) {
 const key=mergeRecoveryKey(p),saved=useRef(restore(key,p)).current;
 const [plan,setPlan]=useState<NativeMergePlan|null>(saved.plan),[submitted,setSubmitted]=useState(saved.submitted);
 const [busy,setBusy]=useState(false),[status,setStatus]=useState(''),[error,setError]=useState<string|null>(saved.error),[done,setDone]=useState(false),[refused,setRefused]=useState(false);
 const [sourceRecovery,setSourceRecovery]=useState<{target:RecapSourceTarget;status:NativeRecapSourceStatus}|null>(null);
 const alive=useRef(true),lock=useRef(false),dialog=useRef<HTMLDivElement>(null);
 useEffect(()=>{alive.current=true;const focus=document.activeElement;dialog.current?.focus();return()=>{alive.current=false;if(focus instanceof HTMLElement&&focus.isConnected)focus.focus();};},[]);
 async function read() {
  if(!p.nodes.length)throw new Error('There are no projected objects to merge.');
  const batches:string[][]=[];for(let i=0;i<p.nodes.length;i+=32)batches.push(p.nodes.slice(i,i+32).map(n=>n.candidateNodeId));
  const results=await Promise.all(batches.map(ids=>getRecapNativeReviews(p,ids)));
  if(results.some(r=>!sameMergeContext(results[0],r)))throw new Error('The World changed during its check. Reopen Merge.');
  return results;
 }
 function checkIdentities(reviews:RecapNativeReview[]) {
  for(const n of p.nodes){const r=reviews.find(r=>r.native_context.selections.some(s=>s.candidate_node_id===n.candidateNodeId));if(!r)throw new Error('World comparison is incomplete.');mergeIdentity(p,r,n.candidateNodeId);}
 }
 async function merge() {
  if(lock.current||done||saved.error||refused)return;lock.current=true;setBusy(true);setError(null);
  try {
   let exact=plan;
   if(!exact) {
    if(sourceRecovery) {
     setStatus('Recovering the saved source request…');
     const recovered=await resumeRecapSource(sourceRecovery.target,sourceRecovery.status);if(!alive.current)return;
     if(recovered.state!=='admitted'||!recovered.admission_committed||recovered.opening.state!=='verified') {
      setSourceRecovery({...sourceRecovery,status:recovered});throw new Error('The source request remains incomplete. Recover the saved source request before publication.');
     }
     setSourceRecovery(null);
    }
    setStatus('Checking the reviewed candidate…');let reviews=await read();if(!alive.current)return;
    checkIdentities(reviews);
    const first=reviews[0],admission=first.native_context.source_admission;
    if(admission.state!=='admitted'||admission.opening_state!=='verified') {
     setStatus('Saving source evidence…');
     const match=/^session-([1-9]\d*)$/.exec(p.sessionId);if(!match)throw new Error('The saved session is invalid.');
     const target:RecapSourceTarget={managedWorldId:p.managedWorldId,nativeWorldId:p.nativeWorldId,bindingVersion:p.bindingVersion,campaignId:p.campaignId,session:Number(match[1]),sourceArtifactId:p.sourceArtifactId,sourceRevisionId:first.source_revision_id,contentSha256:p.sourceSha256.slice(7)};
     const admitted=await admitRecapSource(target);if(!alive.current)return;
     if(admitted.state!=='admitted'||!admitted.admission_committed||admitted.opening.state!=='verified'){setSourceRecovery({target,status:admitted});throw new Error('Source admission is incomplete. Recover the saved source request before publication.');}
     reviews=await read();if(!alive.current)return;
     const current=reviews[0].native_context.source_admission;
     if(current.state!=='admitted'||current.run_id!==admitted.run_id||current.opening_state!=='verified'||reviews.some(r=>r.source_revision_id!==first.source_revision_id))throw new Error('Source verification changed. Nothing was published.');
    }
    const current=reviews[0],source=current.native_context.source_admission;
    if(source.state!=='admitted'||source.opening_state!=='verified')throw new Error('Source evidence is not verified.');
    const request:NativeMergeRequest={managed_world_id:p.managedWorldId,campaign_id:p.campaignId,run_id:p.runId,expected_run_revision:p.runRevision,candidate_sha256:p.candidateSha256.slice(7),source_admission_run_id:source.run_id,expected_parent_revision_id:current.native_context.revision_id,expected_source_authority_epoch:current.native_context.source_authority_epoch,selections:recapMergeSelections(p,reviews)};
    setStatus('Preparing the reviewed changes…');exact=await prepareNativeMerge(p,request,current.source_revision_id);
    retain(key,exact,false);if(!alive.current)return;setPlan(exact);
   }
   retain(key,exact,true);setSubmitted(true);setStatus('Merging into the World Graph…');
   await confirmNativeMerge(p,exact);if(alive.current){setDone(true);setStatus('Merged and verified.');}
  } catch(e) {
   if(alive.current){const code=(e as {code?:string})?.code;setRefused(['candidate_review_expired','candidate_parent_stale','candidate_source_authority_stale'].includes(code??''));setError(e instanceof Error?e.message:'Merge could not be completed.');}
  } finally {lock.current=false;if(alive.current)setBusy(false);}
 }
 return <div style={{position:'fixed',inset:0,zIndex:10000,background:'rgba(0,0,0,.6)',display:'grid',placeItems:'center'}} onKeyDown={e=>{
  if(e.key==='Escape'&&!busy){e.preventDefault();onClose();}
  if(e.key==='Tab'){if(busy){e.preventDefault();return;}const buttons=dialog.current?.querySelectorAll<HTMLButtonElement>('button:not(:disabled)');if(buttons?.length){const first=buttons[0],last=buttons[buttons.length-1];if(e.shiftKey&&(document.activeElement===first||document.activeElement===dialog.current)){e.preventDefault();last.focus();}else if(!e.shiftKey&&(document.activeElement===last||document.activeElement===dialog.current)){e.preventDefault();first.focus();}}}
 }}>
  <div ref={dialog} role="dialog" aria-modal="true" aria-labelledby="merge-title" aria-describedby="merge-summary" tabIndex={-1} className="module-panel" style={{width:'min(480px,calc(100vw - 32px))',maxHeight:'85vh',overflow:'auto',padding:24,background:'var(--panel-bg, #171e2b)'}}>
   <h2 id="merge-title">{done?'Merged':submitted?'Recover merge?':'Merge into the World Graph?'}</h2>
   <p id="merge-summary">{plan?"The previously prepared selection is retained for exact confirmation and recovery.":<>{p.nodes.length} nodes and {p.edges.length} relationships from the projected source you reviewed will be merged, with source evidence, as GM-only provisional claims for this session.</>}</p>
   {!plan?<p>Unique exact-name identities will be reused. New names create objects; ambiguous matches stop the merge. Unprojected narrative beats remain held.</p>:null}
   {submitted&&!done?<p>The exact confirmation is retained. Retry uses that same request, so a lost response does not create a second merge.</p>:null}
   {status?<p role="status">{status}</p>:null}{error?<p role="alert">{error}{refused?' This preview is stale or expired; its packet is preserved. Resolve its state before starting another merge.':''}</p>:null}
   <div style={{display:'flex',gap:12,justifyContent:'flex-end'}}>
    <button type="button" disabled={busy} onClick={onClose}>{done?'Done':'Cancel'}</button>
    {!done?<button type="button" className="primary" disabled={busy||!!saved.error||refused} onClick={()=>void merge()}>{busy?'Merging…':submitted?'Recover merge':sourceRecovery?'Recover source and merge':'Merge'}</button>:null}
   </div>
  </div>
 </div>;
}
