import {useEffect,useMemo,useRef,useState} from 'react';
import type {ExactRunReviewPackage,ExtractionRunRecord,ExtractPromotePrepareResponse} from '../api/types';
import {prepareExtractPromote} from '../api/extractPromoteApi';
import {GraphReviewExtractPromoteSheet} from '../planSurface/graphReviewWorkbench/GraphReviewExtractPromoteSheet';
import {GraphReviewCommittedProjectionPanel} from '../planSurface/graphReviewWorkbench/GraphReviewCommittedProjectionPanel';
import {GraphReviewLiveStateProvider} from '../planSurface/graphReviewWorkbench/GraphReviewLiveStateContext';
import {exactRunBindingKey,type GraphReviewCommittedBinding} from '../planSurface/graphReviewWorkbench/graphReviewCommittedAuthority';

/** Hosts existing Recap prepare/confirm/receipt owners without the Ingest workbench. */
export function BuildRecapPublication({review,run,worldId,onBusy}:{review:ExactRunReviewPackage;run:ExtractionRunRecord;worldId:string;onBusy:(busy:boolean)=>void}){
  const [prepared,setPrepared]=useState<ExtractPromotePrepareResponse|null>(null);
  const [preparing,setPreparing]=useState(false),[confirming,setConfirming]=useState(false),[error,setError]=useState<string|null>(null);
  const alive=useRef(true),lock=useRef(false);
  useEffect(()=>{alive.current=true;return()=>{alive.current=false;onBusy(false);};},[onBusy]);
  useEffect(()=>{onBusy(preparing||confirming);},[preparing,confirming,onBusy]);
  const binding=useMemo<GraphReviewCommittedBinding>(()=>{
    const identity={runId:run.run_id,sourceArtifactId:run.source_artifact_id,campaignId:run.campaign_id??null,sessionId:run.session_id??null};
    return {kind:'exact_run',key:exactRunBindingKey(identity),...identity};
  },[run.run_id,run.source_artifact_id,run.campaign_id,run.session_id]);
  async function prepare(){
    if(lock.current||prepared||review.promotable===false)return;
    lock.current=true;setPreparing(true);setError(null);
    try{
      const result=await prepareExtractPromote({runId:run.run_id,managedWorldId:worldId});
      if(!alive.current)return;
      const context=run.lineage?.world_campaign_ingest_context as Record<string,unknown>|undefined;
      if(result.schema!=='dmb_extract_promote_prepare_v1'||result.runId!==run.run_id||result.worldId!==context?.native_world_id
        ||result.campaignId!==run.campaign_id||result.sessionId!==run.session_id||!result.proposalId||!result.proposalDigest||!result.parentRevisionId){
        throw new Error('The proposed changes do not match this exact Recap and World.');
      }
      setPrepared(result);
    }catch(reason){if(alive.current)setError(reason instanceof Error?reason.message:'Could not prepare reviewed changes.');}
    finally{lock.current=false;if(alive.current)setPreparing(false);}
  }
  return <section aria-label="Recap acceptance"><h3>Review changes for your World</h3>
    {review.promotable===false?<p>{review.promotableReason??'This extraction needs review before it can be accepted.'}</p>:null}
    {!prepared&&<button type="button" disabled={preparing||review.promotable===false} onClick={()=>void prepare()}>
      {preparing?'Preparing changes…':'Prepare changes for review'}</button>}
    {error&&<p role="alert">{error}</p>}
    {prepared&&<GraphReviewLiveStateProvider campaignId={run.campaign_id??''} sessionId={run.session_id??''} liveRun={null}
      committedBinding={binding} committedWorldId={(run.lineage?.world_campaign_ingest_context as Record<string,any>)?.native_world_id} compareError={null} selection={null} onSelectSelection={()=>undefined}>
      <GraphReviewExtractPromoteSheet prepared={prepared} onClose={()=>setPrepared(null)} onConfirmInFlightChange={setConfirming}/>
      <GraphReviewCommittedProjectionPanel/>
    </GraphReviewLiveStateProvider>}
  </section>;
}
