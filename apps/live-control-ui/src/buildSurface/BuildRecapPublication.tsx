import {useEffect,useMemo,useRef,useState} from 'react';
import type {ExactRunReviewPackage,ExtractionRunRecord,ExtractPromotePrepareResponse} from '../api/types';
import {prepareExtractPromote} from '../api/extractPromoteApi';
import {GraphReviewExtractPromoteSheet} from '../planSurface/graphReviewWorkbench/GraphReviewExtractPromoteSheet';
import {GraphReviewCommittedProjectionPanel} from '../planSurface/graphReviewWorkbench/GraphReviewCommittedProjectionPanel';
import {GraphReviewLiveStateProvider} from '../planSurface/graphReviewWorkbench/GraphReviewLiveStateContext';
import {exactRunBindingKey,type GraphReviewCommittedBinding} from '../planSurface/graphReviewWorkbench/graphReviewCommittedAuthority';

import {assertRecapPrepared, recapPublicationScope, readRecapPublicationRecovery, saveRecapPublicationRecovery, setAsideRecapPublication} from './buildRecapPublicationRecovery';

/** Hosts existing Recap prepare/confirm/receipt owners without the Ingest workbench. */
export function BuildRecapPublication({review,run,worldId,onBusy}:{review:ExactRunReviewPackage;run:ExtractionRunRecord;worldId:string;onBusy:(busy:boolean)=>void}){
  const [epoch,setEpoch]=useState(0);
  return <RecapPublication key={recapPublicationScope(review,run,worldId)+epoch} onReset={()=>setEpoch(n=>n+1)} review={review} run={run} worldId={worldId} onBusy={onBusy}/>;
}
function RecapPublication({review,run,worldId,onBusy,onReset}:{review:ExactRunReviewPackage;run:ExtractionRunRecord;worldId:string;onBusy:(busy:boolean)=>void;onReset:()=>void}){
  const scope=recapPublicationScope(review,run,worldId);
  const [saved]=useState(()=>{
    try{return {recovery:readRecapPublicationRecovery(scope,run,review,worldId),error:null};}
    catch(reason){return {recovery:null,error:reason instanceof Error?reason.message:'Saved publication is unavailable.'};}
  });
  const [prepared,setPrepared]=useState<ExtractPromotePrepareResponse|null>(saved.recovery?.prepared??null);
  const [visible,setVisible]=useState(true);
  const [canReprepare,setCanReprepare]=useState(saved.recovery?.assertionIds==null||saved.recovery?.canReprepare===true);
  const [preparing,setPreparing]=useState(false),[confirming,setConfirming]=useState(false),[error,setError]=useState<string|null>(saved.error);
  const alive=useRef(true),lock=useRef(false);
  useEffect(()=>{alive.current=true;return()=>{alive.current=false;onBusy(false);};},[onBusy]);
  useEffect(()=>{onBusy(preparing||confirming);},[preparing,confirming,onBusy]);
  const binding=useMemo<GraphReviewCommittedBinding>(()=>{
    const identity={runId:run.run_id,sourceArtifactId:run.source_artifact_id,campaignId:run.campaign_id??null,sessionId:run.session_id??null};
    return {kind:'exact_run',key:exactRunBindingKey(identity),...identity};
  },[run.run_id,run.source_artifact_id,run.campaign_id,run.session_id]);
  async function prepare(){
    if(lock.current||prepared||saved.error||review.promotable===false)return;
    lock.current=true;setPreparing(true);setError(null);
    try{
      const result=await prepareExtractPromote({runId:run.run_id,managedWorldId:worldId});
      if(!alive.current)return;
      assertRecapPrepared(result,run,review,worldId);
      saveRecapPublicationRecovery({schema:'dmb_build_recap_publication_recovery_v1',scope,prepared:result,assertionIds:null,selectionIds:null,canReprepare:true});
      setPrepared(result);
    }catch(reason){if(alive.current)setError(reason instanceof Error?reason.message:'Could not prepare reviewed changes.');}
    finally{lock.current=false;if(alive.current)setPreparing(false);}
  }
  return <section aria-label="Recap acceptance"><h3>Review changes for your World</h3>
    {review.promotable===false?<p>{review.promotableReason??'This extraction needs review before it can be accepted.'}</p>:null}
    {!prepared&&<button type="button" disabled={preparing||!!saved.error||review.promotable===false} onClick={()=>void prepare()}>
      {preparing?'Preparing changes…':'Prepare changes for review'}</button>}
    {error&&<p role="alert">{error}</p>}
    {prepared&&canReprepare&&<button disabled={preparing||confirming} onClick={()=>{
      try{const value=readRecapPublicationRecovery(scope,run,review,worldId);if(!value)throw new Error('Saved proposal is unavailable.');
        setAsideRecapPublication(value);onReset();}
      catch(reason){setError(reason instanceof Error?reason.message:'Could not retain the previous proposal.');}
    }}>Set aside proposal and prepare again</button>}
    {prepared&&!visible&&<button onClick={()=>setVisible(true)}>Reopen saved publication review</button>}
    {saved.recovery?.assertionIds&&<p>The original publication request is saved. Recover its result by retrying that exact confirmation; no new selection will be sent.</p>}
    {prepared&&<div hidden={!visible}><GraphReviewLiveStateProvider campaignId={run.campaign_id??''} sessionId={run.session_id??''} liveRun={null}
      committedBinding={binding} committedWorldId={(run.lineage?.world_campaign_ingest_context as Record<string,any>)?.native_world_id} compareError={null} selection={null} onSelectSelection={()=>undefined}>
      <GraphReviewExtractPromoteSheet prepared={prepared} onClose={()=>setVisible(false)} onConfirmInFlightChange={setConfirming}
        recoveryAssertionIds={saved.recovery?.assertionIds} initialSelectionIds={saved.recovery?.selectionIds}
        onSelectionChange={selectionIds=>saveRecapPublicationRecovery({schema:'dmb_build_recap_publication_recovery_v1',scope,prepared,selectionIds,assertionIds:null,canReprepare:true})}
        onBeforeConfirm={assertionIds=>{
          saveRecapPublicationRecovery({schema:'dmb_build_recap_publication_recovery_v1',scope,prepared,assertionIds,selectionIds:assertionIds,canReprepare:false});setCanReprepare(false);
        }}
        onConfirmRejected={code=>{if(code==='governed_write_stale_parent'){
          try{const value=readRecapPublicationRecovery(scope,run,review,worldId);if(!value)return;
            saveRecapPublicationRecovery({...value,canReprepare:true});setCanReprepare(true);}
          catch(reason){setError(reason instanceof Error?reason.message:'Could not save rejection recovery.');}
        }}}/>
      <GraphReviewCommittedProjectionPanel/>
    </GraphReviewLiveStateProvider></div>}
  </section>;
}
