import { authenticatedApiFetch, LiveApiError } from "./liveApi";
import type { ExactRunCandidateProjection } from "./exactRunCandidateProjectionApi";

export type ReviewSourceAdmission = { state: "not_found" } | {
  state: "reserved" | "dispatching" | "admitted" | "unknown" | "conflict" | "unavailable";
  run_id: string; run_revision: number; opening_state: "not_checked" | "verified" | "unavailable" | "integrity_error";
  failure_code: string | null;
};
export type ReviewSupportOpening = { status: "unavailable" } | {
  status: "available"; source_artifact_id: string; source_revision_id: string; body_sha256: string;
  span_start_byte: number; span_end_byte: number; span_text: string;
};
export interface RecapNativeReview {
  source_revision_id: string;
  native_context: {
    revision_id: string; source_authority_epoch: number;
    domain_contract_ref: { domain_id: string; domain_revision: string; descriptor_sha256: string };
    semantic_profile_ref: { profile_id: string; profile_revision: string; descriptor_sha256: string };
    source_admission: ReviewSourceAdmission;
    source_evidence: Array<{ evidence_ref_id: string; evidence_role: "support"; opening: ReviewSupportOpening }>;
    selections: Array<{ candidate_node_id: string; status: string; search_is_advisory: true;
      alternatives: Array<{ entity_id: string; identity_approved: false; status: string }> }>;
  };
}
const record = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null && !Array.isArray(v);
const text = (v: unknown): v is string => typeof v === "string" && !!v.trim();
const integer = (v: unknown): v is number => Number.isSafeInteger(v) && Number(v) >= 0;
const digest = (v: unknown): v is string => typeof v === "string" && /^[a-f0-9]{64}$/.test(v);
const uuid = (v: unknown): v is string => typeof v === "string" && /^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/i.test(v);
function invalid(): never { throw new LiveApiError("This comparison no longer matches the selected candidate. Reload saved work.", 0); }

/** Display/scope guards only. The existing server and Core own source acceptance. */
export async function getRecapNativeReview(projection: ExactRunCandidateProjection, nodeId: string, signal?: AbortSignal): Promise<RecapNativeReview> {
  // Capture dispatched scalar coordinates; never reinterpret a late response using changed props.
  const p = { runId: projection.runId, revision: projection.runRevision, status: projection.runStatus,
    source: projection.sourceArtifactId, sourceHash: projection.sourceSha256.slice(7),
    candidateHash: projection.candidateSha256.slice(7), spanHash: projection.spanIndexSha256.slice(7),
    world: projection.managedWorldId, native: projection.nativeWorldId, binding: projection.bindingVersion,
    campaign: projection.campaignId, session: projection.sessionId };
  if (p.status !== "reviewable" || ![p.runId, p.source, p.world, p.native, p.campaign, p.session, nodeId].every(text)
      || !integer(p.revision) || p.revision < 1 || !integer(p.binding) || p.binding < 1
      || ![projection.sourceSha256, projection.candidateSha256, projection.spanIndexSha256].every(v => /^sha256:[a-f0-9]{64}$/.test(v))
      || !projection.nodes.some(n => n.candidateNodeId === nodeId)) invalid();
  const { response } = await authenticatedApiFetch(`/api/live/extract-promote/runs/${encodeURIComponent(p.runId)}/selection-context`, {
    method: "POST", cache: "no-store", headers: { "Content-Type": "application/json" }, ...(signal ? { signal } : {}),
    body: JSON.stringify({ schema: "dmb_ingest_native_review_request_v2", expected_run_revision: p.revision,
      expected_candidate_sha256: p.candidateHash, expected_source_sha256: p.sourceHash,
      expected_span_index_sha256: p.spanHash, expected_world_id: p.world,
      node_ids: [nodeId], edge_ids: [], inspect_source_support: true }),
  });
  let body: unknown;
  try { body = JSON.parse(await response.text()); }
  catch (reason) {
    if (reason instanceof LiveApiError) throw reason;
    throw new LiveApiError(`World comparison response was not JSON (HTTP ${response.status}).`, response.status);
  }
  if (!response.ok) {
    const detail = record(body) && record(body.detail) ? body.detail : body;
    throw new LiveApiError(record(detail) && text(detail.message) ? detail.message : "World comparison could not be opened.", response.status,
      { code: record(detail) && text(detail.code) ? detail.code : null });
  }
  if (!record(body) || body.schema !== "dmb_ingest_native_review_context_v2" || body.run_id !== p.runId || body.run_revision !== p.revision
      || body.source_artifact_id !== p.source || !uuid(body.source_revision_id) || body.source_sha256 !== p.sourceHash
      || body.candidate_sha256 !== p.candidateHash || body.span_index_sha256 !== p.spanHash || !record(body.scope)
      || body.scope.managed_world_id !== p.world || body.scope.native_world_id !== p.native || body.scope.binding_version !== p.binding
      || body.scope.campaign_id !== p.campaign || body.scope.session_id !== p.session
      || !Array.isArray(body.selected_node_ids) || body.selected_node_ids.length !== 1 || body.selected_node_ids[0] !== nodeId
      || !Array.isArray(body.selected_edge_ids) || body.selected_edge_ids.length !== 0 || !record(body.native_context)) invalid();
  const native = body.native_context;
  if (!text(native.revision_id) || !integer(native.source_authority_epoch) || native.identity_approval !== false || native.semantic_support_verified !== false
      || !record(native.domain_contract_ref) || ![native.domain_contract_ref.domain_id, native.domain_contract_ref.domain_revision].every(text)
      || !digest(native.domain_contract_ref.descriptor_sha256) || !record(native.semantic_profile_ref)
      || ![native.semantic_profile_ref.profile_id, native.semantic_profile_ref.profile_revision].every(text) || !digest(native.semantic_profile_ref.descriptor_sha256)
      || !record(native.source_admission) || !Array.isArray(native.source_evidence) || !Array.isArray(native.selections)) invalid();
  const admission = native.source_admission;
  if (admission.state !== "not_found" && (!['reserved', 'dispatching', 'admitted', 'unknown', 'conflict', 'unavailable'].includes(String(admission.state))
      || !uuid(admission.run_id) || !integer(admission.run_revision) || admission.run_revision < 1
      || !['not_checked', 'verified', 'unavailable', 'integrity_error'].includes(String(admission.opening_state))
      || !(admission.failure_code === null || text(admission.failure_code)))) invalid();
  if (native.source_evidence.length && (admission.state !== "admitted" || admission.opening_state !== "verified")) invalid();
  for (const row of native.source_evidence) {
    if (!record(row) || !text(row.evidence_ref_id) || row.evidence_role !== "support" || !record(row.opening)) invalid();
    const opened = row.opening;
    if (opened.status !== "unavailable" && (opened.status !== "available" || ![opened.source_artifact_id, opened.source_revision_id].every(text)
        || opened.body_sha256 !== p.sourceHash || !integer(opened.span_start_byte) || !integer(opened.span_end_byte)
        || opened.span_end_byte <= opened.span_start_byte || !text(opened.span_text))) invalid();
  }
  if (new Set(native.source_evidence.map(row => row.evidence_ref_id)).size !== native.source_evidence.length) invalid();
  for (const selection of native.selections) {
    if (!record(selection) || !text(selection.candidate_node_id) || !text(selection.status) || selection.search_is_advisory !== true || !Array.isArray(selection.alternatives)
        || selection.alternatives.some(a => !record(a) || !text(a.entity_id) || !text(a.status) || a.identity_approved !== false)) invalid();
  }
  if (native.selections.filter(s => s.candidate_node_id === nodeId).length !== 1) invalid();
  return body as unknown as RecapNativeReview;
}
