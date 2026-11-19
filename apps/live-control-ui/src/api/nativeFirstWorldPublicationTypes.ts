import type {FirstWorldDisposition, FirstWorldGraphPlan} from './types';

// Product envelopes use camelCase. Nested generic Core contracts retain snake_case.
export type NativeDomainContractRef = {domain_id: string; domain_revision: string; descriptor_sha256: string};
export type NativeSemanticProfileRef = {profile_id: string; profile_revision: string; descriptor_sha256: string};
export interface NativeFirstWorldExistingBinding {
  reviewedEvidenceRefId: string;
  proof: {schema_version: 'dm_native_utf8_span_v1'; span_id: string; source_revision_id: string;
    evidence_ref_id: string; start_byte: number; end_byte: number; slice_sha256: string};
  sourceRevision: {schema_version: 'dm_source_revision_v2'; source_revision_id: string; source_artifact_id: string;
    content_sha256: string; body_storage: string; locator: string | null; created_at: string};
  evidenceRole: 'support' | 'context';
  /** Proof creation epoch, not the current sourceAuthorityEpoch freshness observation. */
  proofAuthorityEpoch: number;
  originKind: 'admission' | 'extension'; originOperationId: string;
  originReceiptSha256: string; introducedRevisionId: string;
}
export interface NativeFirstWorldSourceStage {
  admissionState: 'absent' | 'admitted'; admissionId: string; admissionReceiptSha256: string | null;
  nativeSourceArtifactId: string | null; nativeSourceRevisionId: string | null; wholeDocumentEvidenceRefId: string | null;
  documentId: string; sourceRootRelpath: string; documentRevision: number; documentUpdatedAt: string; bodySha256: string;
  origin: {namespace: string; object_id: string; revision_id: string};
  genesisInitializationId: string; genesisCreatedAt: string; headRevisionId: string | null;
  headProfileRef: NativeSemanticProfileRef | null; sourceAuthorityEpoch: number;
  extensionId: string; profileTransitionId: string; existingBindings: NativeFirstWorldExistingBinding[];
}
export interface NativeFirstWorldPlan extends Omit<FirstWorldGraphPlan, 'schema' | 'campaignScope' | 'sessionScope'> {
  schema: 'dmb_native_first_world_plan_v1'; runRevision: number; campaignScope: string; sessionScope: null;
  compilerIntentJson: string; compilerIntentSha256: string;
  domainContractRef: NativeDomainContractRef; targetProfileRef: NativeSemanticProfileRef;
  sourceStage: NativeFirstWorldSourceStage; publicationId: string; preparedBy: string;
  createdAt: string; expiresAt: string; policy: 'dmb_native_first_world_compiler_v1'; token: string;
}
export type FirstWorldRetainedPlan = NativeFirstWorldPlan | FirstWorldGraphPlan;
export type NativeFirstWorldPrepareRequest = {schema: 'dmb_native_first_world_prepare_request_v1'; runId: string; decisions: FirstWorldDisposition[]};
export type NativeFirstWorldConfirmRequest = {schema: 'dmb_native_first_world_confirm_request_v1'; plan: NativeFirstWorldPlan};
export type HistoricalFirstWorldConfirmRequest = {schema: 'dmb_first_world_graph_confirm_request_v1'; plan: FirstWorldGraphPlan};
export type FirstWorldPublicationRequest = NativeFirstWorldConfirmRequest | HistoricalFirstWorldConfirmRequest;
export interface NativeFirstWorldReceipt {
  schema: 'dmb_native_first_world_confirm_v1'; outcome: 'initialized' | 'already_initialized' | 'activation_pending';
  worldId: string; planId: string; planDigest: string; decisionDigest: string;
  sourceArtifactId: string; sourceRevisionId: string; contributionId: string;
  nativeContributionId: string; nativeWorldId: string; publicationId: string; committedRevisionId: string;
  appliedAssertionCount: number; acceptedAssertionIds: string[]; rejectedAssertionIds: string[];
  nativePublication: {
    publication_receipt: {space_id: string; publication_id: string; published_revision_id: string; [key: string]: unknown};
    prospective_result: {space_id: string; publication_id: string; published_revision_id: string; [key: string]: unknown};
    [key: string]: unknown;
  };
  activationStatus: 'active' | 'pending'; sourceStatus: 'available' | 'unavailable' | 'unknown'; recovered: boolean; warnings: string[];
}
export interface HistoricalFirstWorldReceipt {
  schema: 'dmb_historical_first_world_receipt_v1'; worldId: string; nativeWorldId: string;
  planId: string; planDigest: string; activationStatus: 'historical_only';
  historicalReceipt: {world_id: string; source_plan_id: string; source_plan_sha256: string; [key: string]: unknown};
}
export type FirstWorldPublicationReceipt = NativeFirstWorldReceipt | HistoricalFirstWorldReceipt;
