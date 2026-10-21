import { useEffect, useRef, useState } from 'react';
import { correctExactRunEvidence, getExactRunReviewPackage } from '../api/extractPromoteApi';
import type { ExactRunEvidenceCorrectionResponse, ExactRunEvidenceQuoteCorrection, ExactRunReviewPackage,
  ExtractionRunRecord, GraphReviewHandoffPayload, WorkspaceDocumentRecord } from '../api/types';
import { GraphReviewExactRunProjection } from '../planSurface/graphReviewWorkbench/GraphReviewExactRunProjection';
import { GraphReviewWorldbuildingPublication } from '../planSurface/graphReviewWorkbench/GraphReviewWorldbuildingPublication';
import { exactRunCorrectionDigest } from '../api/exactRunCorrectionIdentity';
import { useSelectedWorld } from '../selectedWorld/SelectedWorldContext';

type CorrectionRequest = { parentRunId: string; parentCandidateSha256: string; corrections: ExactRunEvidenceQuoteCorrection[] };
type Props = { document: WorkspaceDocumentRecord; currentRevision: number; run: ExtractionRunRecord;
  handoff: GraphReviewHandoffPayload; sourceContentSha256: string; onClose: () => void;
  onDerivedRun: (receipt: ExactRunEvidenceCorrectionResponse, expectedDigest: string, isCurrent: () => boolean) => Promise<void>; onBusyChange: (busy: boolean) => void };
const digest = (value: unknown) => typeof value === 'string' && /^(?:sha256:)?[a-f0-9]{64}$/.test(value)
  ? value.replace(/^sha256:/, '') : null;
const message = (reason: unknown) => reason instanceof Error ? reason.message : 'This exact review could not be loaded.';

function validCorrection(value: unknown, review: ExactRunReviewPackage, run: ExtractionRunRecord): value is CorrectionRequest {
  if (!value || typeof value !== 'object') return false;
  const request = value as CorrectionRequest;
  if (request.parentRunId !== run.run_id || !digest(request.parentCandidateSha256)
    || digest(request.parentCandidateSha256) !== digest(run.components?.candidate_graph?.sha256)
    || !Array.isArray(request.corrections) || !request.corrections.length) return false;
  const seen = new Set<string>();
  return request.corrections.every(change => {
    if (!change || !Number.isInteger(change.evidenceIndex) || change.evidenceIndex < 0
      || !Number.isInteger(change.quoteIndex) || change.quoteIndex < 0 || typeof change.replacementQuote !== 'string'
      || !change.replacementQuote.trim()) return false;
    const evidence = review.assertions.find(item => item.assertionId === change.assertionId)?.evidence[change.evidenceIndex];
    const key = JSON.stringify([change.assertionId, change.evidenceIndex, change.quoteIndex]);
    if (seen.has(key) || !evidence || evidence.sourceArtifactId !== review.sourceArtifactId
      || evidence.sourceSpanRefId !== change.sourceSpanRefId || evidence.anchorQuotes[change.quoteIndex] !== change.originalQuote
      || !evidence.invalidAnchorQuotes?.includes(change.originalQuote)) return false;
    seen.add(key); return true;
  });
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

function ExactReview({ document, currentRevision, run, handoff, sourceContentSha256, worldId, onClose, onDerivedRun, onBusyChange, isScopeCurrent }: Props & {worldId:string; isScopeCurrent: () => boolean}) {
  const [review, setReview] = useState<ExactRunReviewPackage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);
  const [correcting, setCorrecting] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [correctionError, setCorrectionError] = useState<string | null>(null);
  const alive = useRef(true), lock = useRef(false);
  const key = 'dmb.buildEvidenceCorrection.v1:' + JSON.stringify([worldId,document.document_id,run.run_id,run.components?.candidate_graph?.sha256]);
  const [recovery, setRecovery] = useState<unknown>(() => {
    try { const saved = localStorage.getItem(key); return saved ? JSON.parse(saved) : null; }
    catch { return {unavailable:true}; }
  });
  useEffect(() => {
    alive.current = true;
    return () => { alive.current = false; onBusyChange(false); };
  }, [onBusyChange]);
  useEffect(() => { onBusyChange(correcting || confirming); }, [correcting,confirming,onBusyChange]);
  useEffect(() => {
    let current = true; setReview(null); setError(null);
    void getExactRunReviewPackage(run.run_id).then(result => {
      if (!current) return;
      if (run.status !== 'reviewable' || run.source_domain !== 'worldbuilding'
        || handoff.document_id !== document.document_id || handoff.extraction_run_id !== run.run_id
        || handoff.source_artifact_id !== run.source_artifact_id
        || result.schema !== 'dmb_extract_promote_exact_run_review_v1' || result.runId !== run.run_id
        || result.sourceDomain !== 'worldbuilding' || result.sourceArtifactId !== run.source_artifact_id
        || result.worldId !== worldId || !digest(sourceContentSha256) || digest(result.sourceRevisionId) !== digest(sourceContentSha256)
        || (run.lineage?.parent_run_id && result.derivedFromRunId !== run.lineage.parent_run_id)) {
        throw new Error('The review does not match this saved document, run, source revision and World.');
      }
      setReview(result);
    }).catch(reason => { if(current) setError(message(reason)); });
    return () => {current = false;};
  }, [run, handoff, document.document_id, sourceContentSha256, worldId, reload]);

  const recoveryValid = review !== null && validCorrection(recovery, review, run);
  async function submit(corrections?: ExactRunEvidenceQuoteCorrection[]) {
    if (!review || lock.current || confirming) return;
    const request: unknown = corrections ? {parentRunId:run.run_id,parentCandidateSha256:run.components?.candidate_graph?.sha256,corrections} : recovery;
    if (!validCorrection(request, review, run)) {setCorrectionError('The saved correction does not match this exact source. No request was sent.'); return;}
    let encoded: string;
    try { encoded = JSON.stringify(request); localStorage.setItem(key, encoded); }
    catch {setCorrectionError('The correction could not be saved for recovery. No request was sent.'); return;}
    setRecovery(request); lock.current = true; setCorrecting(true); setCorrectionError(null);
    try {
      const expectedDigest = await exactRunCorrectionDigest(request);
      if (!alive.current || !isScopeCurrent()) return;
      const result = await correctExactRunEvidence(request);
      if (!alive.current) return;
      await onDerivedRun(result, expectedDigest, () => alive.current && isScopeCurrent());
      if (!alive.current || !isScopeCurrent()) return;
      if (localStorage.getItem(key) === encoded) localStorage.removeItem(key);
      if (alive.current) setRecovery(null);
    } catch(reason) {if (alive.current) setCorrectionError(`${message(reason)} The source is unchanged; retry the saved correction to recover its child run.`);}
    finally {lock.current = false; if(alive.current) setCorrecting(false);}
  }
  function abandon() {
    try {localStorage.removeItem(key);setRecovery(null);setCorrectionError(null);}
    catch {setCorrectionError('The saved correction could not be cleared.');}
  }
  return <section className="build-run-review" aria-label="Review extracted knowledge">
    <header><h2>Review extracted knowledge · {document.title}</h2><button type="button" disabled={correcting || confirming} onClick={onClose}>Close review</button></header>
    <p>{document.title}.
      {currentRevision !== handoff.document_revision ? ' This review uses earlier saved text; the editor has newer changes.' : ' Your document remains editable above.'}</p>
    {error && <><p role="alert">{error}</p><button type="button" onClick={()=>setReload(n=>n+1)}>Retry review read</button></>}
    {!review && !error && <p role="status">Reading this exact extraction run…</p>}
    {review && <>
      {recovery !== null && !recoveryValid && <p role="alert">Saved correction details are unavailable or do not match this run. <button type="button" onClick={abandon}>Abandon saved request</button></p>}
      <GraphReviewExactRunProjection review={review} showSource={false}
        correctionEnabled={review.inspectionStatus === 'invalid_evidence' && !!digest(run.components?.candidate_graph?.sha256)}
        correctionPending={correcting} recoveryPending={recovery !== null} correctionError={correctionError}
        correctionRecoveryAvailable={recoveryValid} recoveryChanges={recoveryValid ? (recovery as CorrectionRequest).corrections : []}
        onCorrectEvidence={changes=>void submit(changes)} onRetryCorrection={()=>void submit()} onAbandonCorrection={abandon} />
      {review.inspectionStatus === 'ready' && <GraphReviewWorldbuildingPublication review={review} onConfirmInFlightChange={setConfirming} />}
    </>}
  </section>;
}
