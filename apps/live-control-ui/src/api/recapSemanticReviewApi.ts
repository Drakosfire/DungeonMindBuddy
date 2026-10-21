import {authenticatedApiFetch} from './liveApi';
import {ExtractPromoteApiError} from './extractPromoteApi';

export interface RecapSemanticDecisionRequest {
  schema: 'dmb_recap_semantic_decision_request_v1';
  expectedRevision: number;
  candidateSha256: string;
  decision: 'accepted' | 'rejected';
  reviewDecisionRef: string;
}
export interface RecapSemanticDecisionReceipt {
  schema: 'dmb_recap_semantic_decision_response_v1';
  runId: string;
  revision: number;
  candidateSha256: string;
  state: 'accepted' | 'rejected';
  basisSha256: string;
  reviewDecisionRef: string;
  reviewerId: string;
  decidedAt: string;
}
const sha = (value: unknown): value is string => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
export function assertRecapSemanticReceipt(value: RecapSemanticDecisionReceipt, runId: string,
  request: RecapSemanticDecisionRequest, basis: string) {
  if (!value || value.schema !== 'dmb_recap_semantic_decision_response_v1' || value.runId !== runId
    || !Number.isSafeInteger(value.revision) || value.revision !== request.expectedRevision + 1
    || value.candidateSha256 !== request.candidateSha256 || value.state !== request.decision
    || value.basisSha256 !== basis || !sha(value.basisSha256)
    || value.reviewDecisionRef !== request.reviewDecisionRef || typeof value.reviewerId !== 'string' || !value.reviewerId.trim()
    || typeof value.decidedAt !== 'string' || !Number.isFinite(Date.parse(value.decidedAt))) {
    throw new Error('The review decision receipt does not match this exact corrected candidate. Recover the original request.');
  }
}
export async function decideRecapSemantics(runId: string, request: RecapSemanticDecisionRequest,
  basis: string): Promise<RecapSemanticDecisionReceipt> {
  if (Object.keys(request).some(key=>!['schema','expectedRevision','candidateSha256','decision','reviewDecisionRef'].includes(key))
    || !runId.trim() || request.schema!=='dmb_recap_semantic_decision_request_v1'
    || !Number.isSafeInteger(request.expectedRevision) || request.expectedRevision<1 || !sha(request.candidateSha256)
    || !['accepted','rejected'].includes(request.decision) || !request.reviewDecisionRef.trim() || !sha(basis)) {
    throw new Error('The exact Recap review decision request is invalid.');
  }
  const {response} = await authenticatedApiFetch(`/api/live/extract-promote/runs/${encodeURIComponent(runId)}/semantic-disposition`,
    {method:'POST',body:JSON.stringify(request)});
  let value: RecapSemanticDecisionReceipt;
  try { value = JSON.parse(await response.text()); }
  catch { throw new ExtractPromoteApiError('The review decision response could not be read. Recover the saved request.',response.status); }
  if (!response.ok) {
    const error = value as unknown as {message?:string;code?:string};
    throw new ExtractPromoteApiError(error.message ?? 'The review decision was not confirmed.',response.status,error.code ?? null);
  }
  assertRecapSemanticReceipt(value,runId,request,basis);
  return value;
}
