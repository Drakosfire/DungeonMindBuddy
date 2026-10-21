import type {ExtractionRunRecord,RecapEvidenceCorrectionResponse} from '../api/types';
import type {RecapQuoteReview} from './buildRecapCorrection';
import type {RecapSemanticDecisionReceipt} from '../api/recapSemanticReviewApi';
export const sourceHash='a'.repeat(64),candidateHash='b'.repeat(64),basisHash='c'.repeat(64),correctionHash='d'.repeat(64);
export const recapRun={schema_version:'dmb_extraction_run_v1',version:'1.0',revision:3,run_id:'child-run',source_domain:'recap',
  source_artifact_id:'source-a',status:'reviewable',profile_id:'recap_category_v1@1.0',campaign_id:'longmont-c2',session_id:'session-30',
  components:{candidate_graph:{kind:'candidate_graph',uri:'child.json',exists:true,sha256:candidateHash},
    source_artifact:{kind:'source_artifact',uri:'source.md',exists:true,sha256:sourceHash},
    source_span_index:{kind:'source_span_index',uri:'spans.json',exists:true,sha256:'e'.repeat(64)}},
  lineage:{derivation:'operator_recap_literal_evidence_correction_v1',parent_run_id:'parent-run',
    parent_candidate_sha256:'f'.repeat(64),correction_digest:correctionHash,
    world_campaign_ingest_context:{managed_world_id:'world-a',native_world_id:'native-a',campaign_id:'longmont-c2',binding_version:1},
    semantic_disposition:{version:1,state:'held',basis_sha256:basisHash}}} as ExtractionRunRecord & {revision:number};
export const recapReview:RecapQuoteReview={schema:'dmb_extract_promote_exact_run_review_v1',runId:'child-run',derivedFromRunId:'parent-run',
  sourceDomain:'recap',sourceArtifactId:'source-a',sourceRevisionId:'sha256:'+sourceHash,campaignId:'longmont-c2',sessionId:'session-30',
  worldId:'native-a',sourceProse:'Mara crossed the boardwalk.',assertions:[{assertionId:'mara',kind:'object',label:'Mara',summary:'Mara crossed the boardwalk.',
    evidence:[{sourceArtifactId:'source-a',sourceSpanRefId:'span-a',paragraphText:'Mara crossed the boardwalk.',anchorQuotes:['Mara crossed the boardwalk.']}]}],
  inspectionStatus:'ready',invalidEvidenceCount:0,promotable:false,promotableReason:'Corrected evidence awaits semantic review.',diagnostics:[],
  semanticDisposition:{version:1,state:'held',basisSha256:basisHash}};
export const quoteReceipt:RecapEvidenceCorrectionResponse={schema:'dmb_recap_evidence_correction_response_v1',runId:'child-run',parentRunId:'parent-run',
  parentCandidateSha256:'f'.repeat(64),candidateSha256:candidateHash,correctionDigest:correctionHash,status:'reviewable',semanticState:'held',semanticBasisSha256:basisHash};
export const decisionReceipt:RecapSemanticDecisionReceipt={schema:'dmb_recap_semantic_decision_response_v1',runId:'child-run',revision:4,
  candidateSha256:candidateHash,state:'accepted',basisSha256:basisHash,reviewDecisionRef:'test-decision',reviewerId:'test:gm',decidedAt:'2026-10-21T13:00:00Z'};
