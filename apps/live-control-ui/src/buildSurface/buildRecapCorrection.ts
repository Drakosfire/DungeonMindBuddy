import type {ExactRunEvidenceCorrectionResponse,RecapEvidenceCorrectionResponse,ExactRunReviewPackage,ExtractionRunRecord} from '../api/types';
export type BuildCorrectionReceipt = ExactRunEvidenceCorrectionResponse | RecapEvidenceCorrectionResponse;
export const quoteDigest = (value: unknown): string | null => typeof value === 'string' && /^(?:sha256:)?[a-f0-9]{64}$/.test(value)
  ? value.replace(/^sha256:/,'') : null;
export const RECAP_QUOTE_DERIVATION = 'operator_recap_literal_evidence_correction_v1';
export type RecapQuoteReview = ExactRunReviewPackage & {semanticDisposition?: {version:number;state:string;basisSha256:string|null}|null};

export function assertRecapQuoteParent(run: ExtractionRunRecord, review?: ExactRunReviewPackage) {
  const context=run.lineage?.world_campaign_ingest_context as Record<string,unknown>|undefined;
  if (!context || typeof context.managed_world_id!=='string' || !context.managed_world_id.trim()
    || typeof context.native_world_id!=='string' || !context.native_world_id.trim() || context.campaign_id!==run.campaign_id
    || run.status !== 'reviewable' || run.source_domain !== 'recap' || run.profile_id !== 'recap_category_v1@1.0'
    || !run.campaign_id || !run.session_id
    || ['candidate_graph','source_artifact','source_span_index'].some(key => run.components?.[key]?.exists !== true || !quoteDigest(run.components[key].sha256))
    || (review && (review.runId !== run.run_id || review.sourceDomain !== 'recap' || review.sourceArtifactId !== run.source_artifact_id
      || review.campaignId !== run.campaign_id || review.sessionId !== run.session_id
      || quoteDigest(review.sourceRevisionId) !== quoteDigest(run.components?.source_artifact.sha256)))) {
    throw new Error('The exact Recap evidence and frozen source are unavailable for correction.');
  }
}
export function assertRecapQuoteChild(parent: ExtractionRunRecord, receipt: RecapEvidenceCorrectionResponse, child: ExtractionRunRecord) {
  assertRecapQuoteParent(parent);
  const disposition = child.lineage?.semantic_disposition as Record<string,unknown>|undefined;
  if (receipt.schema !== 'dmb_recap_evidence_correction_response_v1' || receipt.parentRunId!==parent.run_id
    || receipt.status!=='reviewable'||child.status!=='reviewable'||child.run_id!==receipt.runId||child.run_id===parent.run_id
    ||child.source_domain!=='recap'||child.source_artifact_id!==parent.source_artifact_id||child.profile_id!==parent.profile_id
    ||quoteDigest(receipt.parentCandidateSha256)!==quoteDigest(parent.components?.candidate_graph?.sha256)
    ||quoteDigest(child.components?.candidate_graph?.sha256)!==quoteDigest(receipt.candidateSha256)
    ||child.lineage?.parent_run_id!==parent.run_id||quoteDigest(child.lineage?.correction_digest)!==quoteDigest(receipt.correctionDigest)
    ||!quoteDigest(receipt.semanticBasisSha256)
    || !['held','accepted','rejected'].includes(receipt.semanticState)
    || child.lineage?.derivation !== RECAP_QUOTE_DERIVATION || child.campaign_id !== parent.campaign_id || child.session_id !== parent.session_id
    || !disposition || disposition.version !== 1 || !['held','accepted','rejected'].includes(String(disposition.state))
    || quoteDigest(disposition.basis_sha256) !== quoteDigest(receipt.semanticBasisSha256)
    || JSON.stringify(child.lineage?.world_campaign_ingest_context) !== JSON.stringify(parent.lineage?.world_campaign_ingest_context)
    || ['source_artifact','source_span_index'].some(key => child.components?.[key]?.exists !== true
      || child.components[key].uri !== parent.components?.[key]?.uri
      || quoteDigest(child.components[key].sha256) !== quoteDigest(parent.components?.[key]?.sha256))) {
    throw new Error('The corrected Recap child does not preserve its frozen source, World and semantic hold.');
  }
}
export function recapQuoteReviewBasis(run: ExtractionRunRecord, review: RecapQuoteReview) {
  assertRecapQuoteParent(run,review);
  const revision=(run as ExtractionRunRecord & {revision?:unknown}).revision;
  const disposition=run.lineage?.semantic_disposition as Record<string,unknown>|undefined;
  const projected=review.semanticDisposition;
  if (run.lineage?.derivation !== RECAP_QUOTE_DERIVATION || !Number.isSafeInteger(revision) || (revision as number)<1
    || !disposition || disposition.version!==1 || !['held','accepted','rejected'].includes(String(disposition.state))
    || !projected || projected.version!==1 || projected.state!==disposition.state
    || !quoteDigest(projected.basisSha256) || quoteDigest(disposition.basis_sha256)!==quoteDigest(projected.basisSha256)) {
    throw new Error('The corrected Recap review basis could not be verified. Reopen this exact review.');
  }
  return {revision:revision as number,candidateSha256:quoteDigest(run.components?.candidate_graph.sha256)!,
    basisSha256:quoteDigest(projected.basisSha256)!,state:projected.state};
}
