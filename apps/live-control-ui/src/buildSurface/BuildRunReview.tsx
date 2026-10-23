import { lazy, Suspense, useEffect, useRef, useState } from 'react';
import { correctExactRunEvidence, correctRecapRunEvidence, getExactRunReviewPackage, getWorldbuildingFrozenSpans } from '../api/extractPromoteApi';
import type { ExactRunEvidenceQuoteCorrection, ExactRunReviewPackage,
  ExtractionRunRecord, GraphReviewHandoffPayload, WorkspaceDocumentRecord, WorldbuildingEvidenceCorrectionRequest, WorldbuildingFrozenSpanCatalog } from '../api/types';
import { GraphReviewExactRunProjection } from '../planSurface/graphReviewWorkbench/GraphReviewExactRunProjection';
import { GraphReviewWorldbuildingPublication } from '../planSurface/graphReviewWorkbench/GraphReviewWorldbuildingPublication';
import {BuildRecapPublication} from './BuildRecapPublication';
import {assertRecapQuoteParent, type BuildCorrectionReceipt} from './buildRecapCorrection';
import {BuildRecapSemanticReview} from './BuildRecapSemanticReview';
import type {RecapSemanticDecisionReceipt} from '../api/recapSemanticReviewApi';
import {WorldbuildingEvidenceCorrection,validFrozenCatalog,validWorldbuildingCorrection} from './WorldbuildingEvidenceCorrection';
import { exactRunCorrectionDigest, worldbuildingEvidenceCorrectionDigest } from '../api/exactRunCorrectionIdentity';
import { useSelectedWorld } from '../selectedWorld/SelectedWorldContext';

const BuildManualKnowledge=lazy(()=>import('./BuildManualKnowledge').then(m=>({default:m.BuildManualKnowledge})));

type RecapCorrectionRequest = { parentRunId: string; parentCandidateSha256: string; corrections: ExactRunEvidenceQuoteCorrection[] };
type CorrectionRequest = RecapCorrectionRequest | WorldbuildingEvidenceCorrectionRequest;
type Props = { document: WorkspaceDocumentRecord; currentRevision: number; run: ExtractionRunRecord;
  handoff: GraphReviewHandoffPayload; sourceContentSha256: string; onClose: () => void;
  onDerivedRun: (receipt: BuildCorrectionReceipt, expectedDigest: string, isCurrent: () => boolean) => Promise<() => void>; onBusyChange: (busy: boolean) => void;
  onSemanticDecision: (receipt: RecapSemanticDecisionReceipt, isCurrent: () => boolean) => Promise<() => void> };
const digest = (value: unknown) => typeof value === 'string' && /^(?:sha256:)?[a-f0-9]{64}$/.test(value)
  ? value.replace(/^sha256:/, '') : null;
const message = (reason: unknown) => reason instanceof Error ? reason.message : 'This exact review could not be loaded.';
async function correctionStorage<T>(key:string,action:()=>T):Promise<T>{
  if(!navigator.locks)throw new Error('This browser cannot safely retain evidence corrections across tabs.');
  return navigator.locks.request(key,action);
}

function validCorrection(value: unknown, review: ExactRunReviewPackage, run: ExtractionRunRecord, catalog: WorldbuildingFrozenSpanCatalog|null): value is CorrectionRequest {
  if(run.source_domain==='worldbuilding')return validWorldbuildingCorrection(value,catalog,review);
  if (!value || typeof value !== 'object') return false;
  const request = value as RecapCorrectionRequest;
  if (request.parentRunId !== run.run_id || !digest(request.parentCandidateSha256)
    || digest(request.parentCandidateSha256) !== digest(run.components?.candidate_graph?.sha256)
    || !Array.isArray(request.corrections) || !request.corrections.length) return false;
  const seen = new Set<string>();
  const matches=request.corrections.every(change => {
    if (!change || !Number.isInteger(change.evidenceIndex) || change.evidenceIndex < 0
      || !Number.isInteger(change.quoteIndex) || change.quoteIndex < 0 || typeof change.replacementQuote !== 'string'
      || !change.replacementQuote.trim()) return false;
    const evidence = review.assertions.find(item => item.assertionId === change.assertionId)?.evidence[change.evidenceIndex];
    const key = JSON.stringify([change.assertionId, change.evidenceIndex, change.quoteIndex]);
    if (seen.has(key) || !evidence || evidence.sourceArtifactId !== review.sourceArtifactId
      || evidence.sourceSpanRefId !== change.sourceSpanRefId || evidence.anchorQuotes[change.quoteIndex] !== change.originalQuote
      || !evidence.invalidAnchorQuotes?.includes(change.originalQuote)) return false;
    if(run.source_domain==='recap'&&(change.replacementQuote!==change.replacementQuote.trim()
      ||change.replacementQuote===change.originalQuote||!evidence.paragraphText.includes(change.replacementQuote)))return false;
    seen.add(key); return true;
  });
  const invalidCount=review.assertions.reduce((total,item)=>total+item.evidence.reduce((sum,evidence)=>sum
    +evidence.anchorQuotes.filter(quote=>evidence.invalidAnchorQuotes?.includes(quote)).length,0),0);
  return matches&&(run.source_domain!=='recap'||request.corrections.length===invalidCount);
}

/** Reuses the owners' review/mutation components while the Build editor stays mounted. */
export function BuildRunReview(props: Props) {
  const world = useSelectedWorld();
  const scope = JSON.stringify([world.kind, world.kind === 'managed' ? world.worldId : null, props.document.document_id]);
  const currentScope = useRef(scope); currentScope.current = scope;
  if (world.kind !== 'managed' || !props.document.world_id || props.document.world_id !== world.worldId) {
    return <p role="status">Select this document’s verified World to review its extracted knowledge.</p>;
  }
  return <ExactReview key={JSON.stringify([world.worldId,props.document.document_id,props.run.run_id,props.sourceContentSha256])}
    {...props} worldId={world.worldId} isScopeCurrent={() => currentScope.current === scope} />;
}

function ExactReview({ document, currentRevision, run, handoff, sourceContentSha256, worldId, onClose, onDerivedRun, onBusyChange, isScopeCurrent, onSemanticDecision }: Props & {worldId:string; isScopeCurrent: () => boolean}) {
  const [manualOpen,setManualOpen]=useState(false),[manualMounted,setManualMounted]=useState(false);
  const [review, setReview] = useState<ExactRunReviewPackage | null>(null);
  const [catalog,setCatalog] = useState<WorldbuildingFrozenSpanCatalog|null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);
  const [correcting, setCorrecting] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [correctionError, setCorrectionError] = useState<string | null>(null);
  const alive = useRef(true), lock = useRef(false);
  const key = (run.source_domain==='recap'?'dmb.buildRecapEvidenceCorrection.v1:':'dmb.buildEvidenceCorrection.v2:') + JSON.stringify([worldId,document.document_id,run.run_id,run.components?.candidate_graph?.sha256]);
  const legacyKey=run.source_domain==='worldbuilding'?key.replace('dmb.buildEvidenceCorrection.v2:','dmb.buildEvidenceCorrection.v1:'):null;
  const recoveryRaw=useRef<string|null>(null),recoveryStorageKey=useRef(key);
  function readRecovery():unknown {
    try {
      const earlier=legacyKey?localStorage.getItem(legacyKey):null;
      recoveryStorageKey.current=earlier!==null?legacyKey!:key;
      const raw=earlier??localStorage.getItem(key);recoveryRaw.current=raw;
      return raw!==null?(JSON.parse(raw)??{unavailable:true}):null;
    } catch {return {unavailable:true};}
  }
  const [recovery,setRecovery]=useState<unknown>(readRecovery);
  useEffect(() => {
    alive.current = true;
    return () => { alive.current = false; onBusyChange(false); };
  }, [onBusyChange]);
  useEffect(() => { onBusyChange(correcting || confirming); }, [correcting,confirming,onBusyChange]);
  useEffect(() => {
    let current = true; setReview(null); setCatalog(null); setError(null);
    void getExactRunReviewPackage(run.run_id).then(async result => {
      const spans=run.source_domain==='worldbuilding'&&result.inspectionStatus==='invalid_evidence'?await getWorldbuildingFrozenSpans(run.run_id):null;
      if (!current) return;
      const recap=run.source_domain==='recap';
      const context=run.lineage?.world_campaign_ingest_context as Record<string,unknown>|undefined;
      if (run.status !== 'reviewable' || !['recap','worldbuilding'].includes(run.source_domain)
        || handoff.document_id !== document.document_id || handoff.extraction_run_id !== run.run_id
        || handoff.source_artifact_id !== run.source_artifact_id
        || result.schema !== 'dmb_extract_promote_exact_run_review_v1' || result.runId !== run.run_id
        || result.sourceDomain !== run.source_domain || result.sourceArtifactId !== run.source_artifact_id
        || result.worldId !== (recap?context?.native_world_id:worldId)
        || (recap&&(context?.managed_world_id!==worldId||result.campaignId!==run.campaign_id||result.sessionId!==run.session_id))
        || !digest(sourceContentSha256) || digest(result.sourceRevisionId) !== digest(sourceContentSha256)
        || (run.lineage?.parent_run_id && result.derivedFromRunId !== run.lineage.parent_run_id)) {
        throw new Error('The review does not match this saved document, run, source revision and World.');
      }
      if(run.source_domain==='worldbuilding'&&result.inspectionStatus==='invalid_evidence'&&(!spans||!validFrozenCatalog(spans,result,run,worldId)))throw new Error('The frozen source paragraphs do not match this exact extraction. Reopen its review.');
      setCatalog(spans);setReview(result);
    }).catch(reason => { if(current) setError(message(reason)); });
    return () => {current = false;};
  }, [run, handoff, document.document_id, sourceContentSha256, worldId, reload]);

  const recoveryValid = review !== null && validCorrection(recovery, review, run, catalog);
  async function submit(corrections?: ExactRunEvidenceQuoteCorrection[]|WorldbuildingEvidenceCorrectionRequest) {
    if (!review || lock.current || confirming) return;
    const request: unknown = corrections ? (run.source_domain==='worldbuilding'?corrections:{parentRunId:run.run_id,parentCandidateSha256:run.components?.candidate_graph?.sha256,corrections}) : recovery;
    if (!validCorrection(request, review, run, catalog)) {setCorrectionError('The saved correction does not match this exact source. No request was sent.'); return;}
    let encoded: string;
    lock.current=true;setCorrecting(true);setCorrectionError(null);
    try {
      if(run.source_domain==='recap')assertRecapQuoteParent(run,review);
      encoded=JSON.stringify(request);
      const persist=()=>{
        if(!alive.current||!isScopeCurrent())throw new Error('The selected correction changed before persistence.');
        if(legacyKey&&localStorage.getItem(legacyKey)!==null)throw new Error('An earlier correction request is retained. Explicitly set it aside before creating another.');
        const current=localStorage.getItem(key);
        if(current!==null&&current!==encoded)throw new Error('Another correction is retained. Reopen this review to recover it.');
        localStorage.setItem(key,encoded);
      };
      await correctionStorage(key,persist);
    } catch(reason){lock.current=false;if(alive.current){setCorrecting(false);setRecovery(readRecovery());setCorrectionError(`${message(reason)} The correction could not be saved for recovery. No request was sent.`);}return;}
    if(!alive.current||!isScopeCurrent()){lock.current=false;return;}
    recoveryStorageKey.current=key;recoveryRaw.current=encoded;setRecovery(request);
    try {
      const expectedDigest = await (run.source_domain==='worldbuilding'?worldbuildingEvidenceCorrectionDigest(request as WorldbuildingEvidenceCorrectionRequest):exactRunCorrectionDigest(request as RecapCorrectionRequest));
      if (!alive.current || !isScopeCurrent()) return;
      const result = run.source_domain==='recap' ? await correctRecapRunEvidence(request as RecapCorrectionRequest) : await correctExactRunEvidence(request as WorldbuildingEvidenceCorrectionRequest);
      if (!alive.current) return;
      const commit=await onDerivedRun(result, expectedDigest, () => alive.current && isScopeCurrent());
      const adopt=()=>{
        if(!alive.current||!isScopeCurrent()||localStorage.getItem(key)!==encoded)throw new Error('The selected correction changed. Recover its original request.');
        commit();localStorage.removeItem(key);recoveryRaw.current=null;
      };
      await correctionStorage(key,adopt);
      if (alive.current) setRecovery(null);
    } catch(reason) {if (alive.current) setCorrectionError(`${message(reason)} The source is unchanged; retry the saved correction to recover its child run.`);}
    finally {lock.current = false; if(alive.current) setCorrecting(false);}
  }
  async function abandon() {
    if(lock.current)return;
    lock.current=true;setCorrecting(true);
    try {
      const retain=()=>{
        if(!alive.current||!isScopeCurrent())throw new Error('The selected correction changed before abandonment.');
        const storageKey=recoveryStorageKey.current;
        const raw=localStorage.getItem(storageKey);
        if(raw!==recoveryRaw.current)throw new Error('The saved correction changed. Reopen its review.');
        if(raw!==null)localStorage.setItem(storageKey+':retained:'+crypto.randomUUID(),raw);
        localStorage.removeItem(storageKey);
      };
      await correctionStorage(key,retain);
      if(alive.current&&isScopeCurrent()){setRecovery(readRecovery());setCorrectionError(null);}
    }catch {if(alive.current)setCorrectionError('The saved correction could not be retained and cleared.');}
    finally {lock.current=false;if(alive.current)setCorrecting(false);}
  }
  return <section className="build-run-review" aria-label="Review extracted knowledge">
    <header><h2>Review extracted knowledge · {document.title}</h2><button type="button" disabled={correcting || confirming} onClick={onClose}>Close review</button></header>
    <p>{document.title}.
      {currentRevision !== handoff.document_revision ? ' This review uses earlier saved text; the editor has newer changes.' : ' Your document remains editable above.'}</p>
    {error && <><p role="alert">{error}</p><button type="button" onClick={()=>setReload(n=>n+1)}>Retry review read</button></>}
    {!review && !error && <p role="status">Reading this exact extraction run…</p>}
    {review && <>
      {run.source_domain==='worldbuilding'&&<><button type="button" aria-expanded={manualOpen} onClick={()=>{setManualMounted(true);setManualOpen(v=>!v);}}>Author knowledge from this source</button>
        {manualMounted&&<div hidden={!manualOpen}><Suspense fallback={<p role="status">Opening manual authoring…</p>}><BuildManualKnowledge
          worldId={worldId} document={document} run={run} handoff={handoff} review={review}
          sourceContentSha256={sourceContentSha256} isScopeCurrent={isScopeCurrent} frozenCatalog={catalog}/></Suspense></div>}</>}
      {recovery !== null && !recoveryValid && <p role="alert">{recoveryStorageKey.current===legacyKey?'An earlier correction request is retained; its retired format cannot be submitted.':'Saved correction details are unavailable or do not match this run.'} Abandoning retains the request in this browser; it does not cancel a submitted correction. <button type="button" onClick={abandon}>Abandon saved request</button></p>}
      <GraphReviewExactRunProjection review={review} showSource={false}
        correctionEnabled={run.source_domain==='recap' && review.inspectionStatus === 'invalid_evidence' && !!digest(run.components?.candidate_graph?.sha256)}
        correctionPending={correcting} recoveryPending={recovery !== null} correctionError={correctionError}
        correctionRecoveryAvailable={recoveryValid} recoveryChanges={recoveryValid ? (recovery as RecapCorrectionRequest).corrections : []}
        onCorrectEvidence={changes=>void submit(changes)} onRetryCorrection={()=>void submit()} onAbandonCorrection={abandon} />
      {run.source_domain==='worldbuilding'&&catalog&&<WorldbuildingEvidenceCorrection review={review} catalog={catalog} busy={correcting}
        recovery={recoveryValid?recovery as WorldbuildingEvidenceCorrectionRequest:null} hasRecovery={recovery!==null} error={correctionError}
        onSubmit={request=>void submit(request)} onRetry={()=>void submit()} onAbandon={()=>void abandon()}/>}
      {run.source_domain==='recap' && <BuildRecapSemanticReview run={run} review={review} worldId={worldId}
        onBusy={setConfirming} isCurrent={()=>alive.current&&isScopeCurrent()} onDecided={onSemanticDecision}/>}
      {review.inspectionStatus === 'ready' && (run.source_domain==='recap'
        ? <BuildRecapPublication review={review} worldId={worldId} run={run} onBusy={setConfirming}/>
        : <GraphReviewWorldbuildingPublication review={review} onConfirmInFlightChange={setConfirming} />)}
    </>}
  </section>;
}
