import {useEffect,useRef,useState} from 'react';
import type {ExactRunReviewPackage,ExtractionRunRecord} from '../api/types';
import {decideRecapSemantics,type RecapSemanticDecisionReceipt,type RecapSemanticDecisionRequest} from '../api/recapSemanticReviewApi';
import {recapQuoteReviewBasis,RECAP_QUOTE_DERIVATION} from './buildRecapCorrection';

type Props={run:ExtractionRunRecord;review:ExactRunReviewPackage;worldId:string;onBusy:(busy:boolean)=>void;
  isCurrent:()=>boolean;onDecided:(receipt:RecapSemanticDecisionReceipt,isCurrent:()=>boolean)=>Promise<()=>void>};
type Pending={schema:'dmb_build_recap_semantic_review_v1';scope:string;request:RecapSemanticDecisionRequest};
const message=(error:unknown)=>error instanceof Error?error.message:'The corrected interpretation could not be reviewed.';
const equal=(a:unknown,b:unknown)=>JSON.stringify(a)===JSON.stringify(b);

/** Existing semantic owner remains separate from evidence correction and World publication. */
export function BuildRecapSemanticReview(props:Props){
  if(props.run.lineage?.derivation!==RECAP_QUOTE_DERIVATION)return null;
  if(props.review.inspectionStatus!=='ready')return <p>Complete the literal evidence corrections before reviewing their interpretation.</p>;
  try{
    const basis=recapQuoteReviewBasis(props.run,props.review);
    const scope=JSON.stringify([props.worldId,props.run.run_id,props.run.source_artifact_id,
      props.review.sourceRevisionId,basis.candidateSha256,basis.basisSha256]);
    return <SemanticReview key={scope} {...props} basis={basis} scope={scope}/>;
  }catch(reason){return <p role="alert">{message(reason)}</p>;}
}
function SemanticReview({run,scope,basis,onBusy,isCurrent,onDecided}:Props&{scope:string;basis:ReturnType<typeof recapQuoteReviewBasis>}){
  const key='dmb.buildRecapSemanticReview.v1:'+scope;
  function read():Pending|null{
    const raw=localStorage.getItem(key);if(raw===null)return null;
    const value=JSON.parse(raw) as Pending,request=value?.request;
    if(value?.schema!=='dmb_build_recap_semantic_review_v1'||value.scope!==scope
      ||Object.keys(value).some(key=>!['schema','scope','request'].includes(key))
      ||!request||typeof request!=='object'||Array.isArray(request)
      ||Object.keys(request).some(key=>!['schema','expectedRevision','candidateSha256','decision','reviewDecisionRef'].includes(key))
      ||request?.schema!=='dmb_recap_semantic_decision_request_v1'||request.candidateSha256!==basis.candidateSha256
      ||!Number.isSafeInteger(request.expectedRevision)||request.expectedRevision<1
      ||![basis.revision,basis.revision-1].includes(request.expectedRevision)
      ||!['accepted','rejected'].includes(request.decision)||typeof request.reviewDecisionRef!=='string'||!request.reviewDecisionRef.trim()
      ||(request.expectedRevision!==basis.revision&&request.decision!==basis.state))throw new Error('The saved semantic decision does not match this exact corrected candidate.');
    return value;
  }
  const [saved]=useState(()=>{try{return {value:read(),error:null};}catch(reason){return {value:null,error:message(reason)};}});
  const [pending,setPending]=useState<Pending|null>(saved.value),[error,setError]=useState<string|null>(saved.error);
  const [checked,setChecked]=useState(false),[busy,setBusy]=useState(false);
  const alive=useRef(true),lock=useRef(false);
  useEffect(()=>{alive.current=true;return()=>{alive.current=false;onBusy(false);};},[onBusy]);
  async function storage<T>(action:()=>T):Promise<T>{
    if(!navigator.locks)throw new Error('This browser cannot safely retain review decisions across tabs.');
    return navigator.locks.request(key,action);
  }
  async function submit(decision?:'accepted'|'rejected'){
    if(lock.current||saved.error||!isCurrent()||(!pending&&(!checked||basis.state!=='held'||!decision)))return;
    lock.current=true;setBusy(true);onBusy(true);setError(null);
    const value:Pending=pending??{schema:'dmb_build_recap_semantic_review_v1',scope,request:{
      schema:'dmb_recap_semantic_decision_request_v1',expectedRevision:basis.revision,
      candidateSha256:basis.candidateSha256,decision:decision!,reviewDecisionRef:'build-recap-review:'+crypto.randomUUID()}};
    try{
      await storage(()=>{
        if(!alive.current||!isCurrent())throw new Error('The selected Recap changed. The original decision is retained.');
        const current=read();
        if((pending&&!equal(current,pending))||(!pending&&current!==null))throw new Error('Another saved decision is pending. Reopen this review to recover it.');
        localStorage.setItem(key,JSON.stringify(value));
      });
      if(!alive.current||!isCurrent())return;
      setPending(value);
      const receipt=await decideRecapSemantics(run.run_id,value.request,basis.basisSha256);
      if(!alive.current||!isCurrent())return;
      // Stage current-run proof; commit and recovery cleanup share one synchronous
      // storage lock callback, so remount cannot observe a half-adopted decision.
      const commit=await onDecided(receipt,()=>alive.current&&isCurrent());
      await storage(()=>{
        if(!alive.current||!isCurrent()||!equal(read(),value))throw new Error('The selected review changed. Recover the saved decision.');
        commit();localStorage.removeItem(key);
      });
      if(alive.current)setPending(null);
    }catch(reason){if(alive.current)setError(message(reason));}
    finally{lock.current=false;if(alive.current){setBusy(false);onBusy(false);}}
  }
  return <section aria-label="Review corrected Recap interpretation"><h3>Review corrected interpretation</h3>
    <p>Compare the corrected statements and their evidence above. Accepting this interpretation enables a separate World publication review.</p>
    {error&&<p role="alert">{error}</p>}
    {pending?<><p>Your exact review decision is saved. Recover it without submitting a different decision.</p>
      <button disabled={busy||!!saved.error} onClick={()=>void submit()}>{busy?'Recovering review…':'Recover saved review decision'}</button></>:
      basis.state==='held'?<><label><input type="checkbox" checked={checked} disabled={busy||!!saved.error}
        onChange={event=>setChecked(event.target.checked)}/>I reviewed the corrected statements against their source evidence.</label>
        <button disabled={!checked||busy||!!saved.error} onClick={()=>void submit('accepted')}>Accept corrected interpretation</button>
        <button disabled={!checked||busy||!!saved.error} onClick={()=>void submit('rejected')}>Reject corrected interpretation</button></>:
      <p role="status">{basis.state==='accepted'?'Corrected interpretation accepted.':'Corrected interpretation rejected. World publication remains unavailable.'}</p>}
  </section>;
}
