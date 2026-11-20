/** Host wire metadata. None of these identifiers or prepared blobs is prompt input. */
export type Json = null | boolean | number | string | Json[] | {[key:string]:Json};
export type Packet = {[key:string]:Json};
export interface ManualSelector {
  schema:'dmb_native_manual_context_v1';managedWorldId:string;documentId:string;
  documentRevision:number;bodySha256:string;runId:string;runRevision:number;
}
export interface ManualSource {
  managedWorldId:string;nativeWorldId:string;bindingVersion:number;documentId:string;
  documentRevision:number;bodySha256:string;runId:string;runRevision:number;
  appSourceArtifactId:string;appSourceRevisionId:string;spanIndexSha256:string;
}
export interface Witness {sourceSpanRefId:string;startByte:number;endByte:number;sliceSha256:string}
export interface Endpoint {entityId:string;name:string;objectKind:string}
export type ManualOperation = {kind:'object';objectKind:string;name:string;role:string|null;aliases:string[];description:string|null}
  | {kind:'relationship';source:Endpoint;target:Endpoint;predicate:string;label:string|null;description:string|null};
export interface ManualRequest {
  schema:'dmb_native_manual_prepare_v1';source:ManualSource;operationId:string;createdAt:string;
  expectedParentRevisionId:string;expectedSourceAuthorityEpoch:number;witness:Witness;operation:ManualOperation;
}
export interface ManualContext {
  schema:'dmb_native_manual_context_result_v1';source:ManualSource;nativeSource:Packet;
  parentRevisionId:string;sourceAuthorityEpoch:number;domainContractRef:Packet;semanticProfileRef:Packet;
  manualCapability:boolean;transitionRequired:boolean;spans:Witness[];kinds:Record<string,string>;
  predicates:Record<string,{term:string;reverseEndpoints:boolean}>;
}
export interface ManualPlan {
  schema:'dmb_native_manual_plan_v1';review:ManualRequest;publication:Packet;preparedChangeJson:string;
  domainContractRef:Packet;semanticProfileRef:Packet;preparedBy:string;expiresAt:string;token:string;
}
export interface ManualReceipt {schema:'dmb_native_manual_receipt_v1';recovered:boolean;receipt:Packet}
export interface ProfileRequest {
  schema:'dmb_native_profile_transition_prepare_v1';managedWorldId:string;expectedNativeWorldId:string;
  expectedBindingVersion:number;expectedParentRevisionId:string;publicationId:string;
}
export interface ProfilePlan {
  schema:'dmb_native_profile_transition_plan_v1';managedWorldId:string;nativeWorldId:string;bindingVersion:number;
  request:Packet;parentPayloadSha256:string;migrationOriginRef:Packet|null;preparedBy:string;expiresAt:string;token:string;
}
export interface ProfileReceipt {schema:'dmb_native_profile_transition_receipt_v1';recovered:boolean;receipt:Packet}
export interface AdmissionTarget {worldId:string;documentId:string;revision:number;bodySha256:string}
