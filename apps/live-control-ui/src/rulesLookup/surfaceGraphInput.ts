const isRecord = (v: unknown): v is Record<string, unknown> => v !== null && typeof v === 'object' && !Array.isArray(v);
const hasExactKeys = (v: unknown, keys: string[]): v is Record<string, unknown> => isRecord(v) && Object.keys(v).length === keys.length && keys.every(k => Object.prototype.hasOwnProperty.call(v, k));
const isDigest = (v: unknown): v is string => typeof v === 'string' && /^[a-f0-9]{64}$/.test(v);
const isStringList = (v: unknown): v is string[] => Array.isArray(v) && v.every(i => typeof i === 'string' && !!i.trim());
const isSortedUniqueStringList = (v: unknown, max: number): v is string[] => isStringList(v) && v.length <= max && v.every((i, n) => !n || v[n-1]! < i);

/** Shared Graph envelope; each surface supplies its actual packet schema and accounting kinds. */
export function isSurfaceGraphInput(
  value: { graph_authority: unknown; graph_packet: unknown; assembled_input: unknown },
  worldId: string,
  packetSchema: 'dmb_plan_world_graph_packet_v1' | 'dmb_play_world_graph_packet_v1',
  sourceKinds: readonly string[],
): boolean {
  const authority = value.graph_authority;
  if (!hasExactKeys(authority, [
    "managed_world_id", "native_world_id", "binding_version", "scope_mode", "campaign_id", "admissibility_version", "graph_revision",
  ])
    || authority.managed_world_id !== worldId
    || typeof authority.native_world_id !== "string" || !authority.native_world_id.trim()
    || !Number.isSafeInteger(authority.binding_version) || (authority.binding_version as number) < 1
    || authority.scope_mode !== "world" || authority.campaign_id !== null
    || typeof authority.admissibility_version !== "string" || !authority.admissibility_version.trim()
    || typeof authority.graph_revision !== "string" || !authority.graph_revision.trim()) return false;

  const packet = value.graph_packet;
  if (!hasExactKeys(packet, [
    "schema", "packet_serializer_version", "selection_policy_version", "evidence_sufficiency_policy_version",
    "retrieval_packet_sha256", "candidate_assertion_ids", "candidate_relationship_ids", "candidate_evidence_ref_ids",
    "retrieval_status", "evidence_sufficiency_status", "result_limit", "coverage_status", "truncated", "omission_reasons",
  ])
    || packet.schema !== packetSchema
    || packet.packet_serializer_version !== "canonical-json-utf8-v1"
    || typeof packet.selection_policy_version !== "string" || !packet.selection_policy_version.trim()
    || typeof packet.evidence_sufficiency_policy_version !== "string" || !packet.evidence_sufficiency_policy_version.trim()
    || !isDigest(packet.retrieval_packet_sha256)
    || !isSortedUniqueStringList(packet.candidate_assertion_ids, 512)
    || !isSortedUniqueStringList(packet.candidate_relationship_ids, 512)
    || !isSortedUniqueStringList(packet.candidate_evidence_ref_ids, 1024)
    || !["complete", "empty"].includes(String(packet.retrieval_status))
    || !["sufficient", "insufficient"].includes(String(packet.evidence_sufficiency_status))
    || !Number.isSafeInteger(packet.result_limit) || (packet.result_limit as number) < 0
    || !["complete", "incomplete"].includes(String(packet.coverage_status))
    || typeof packet.truncated !== "boolean"
    || !isStringList(packet.omission_reasons)) return false;

  const assembled = value.assembled_input;
  if (!hasExactKeys(assembled, [
    "assembler_version", "budget_policy_version", "provider_model_name", "provider_model_version", "tokenizer_name",
    "tokenizer_version", "provider_envelope_input_tokens", "output_token_reserve", "context_window_limit",
    "packet_disposition", "packet_disposition_reason", "dispatched_packet_sha256", "dispatched_assertion_ids",
    "dispatched_relationship_ids", "dispatched_evidence_ref_ids", "source_token_accounting", "included_history",
    "assembled_input_sha256",
  ])
    || !["included", "omitted_insufficient"].includes(String(assembled.packet_disposition))
    || !(assembled.packet_disposition_reason === null || assembled.packet_disposition_reason === "insufficient_evidence")
    || typeof assembled.assembler_version !== "string" || !assembled.assembler_version.trim()
    || typeof assembled.budget_policy_version !== "string" || !assembled.budget_policy_version.trim()
    || typeof assembled.provider_model_name !== "string" || !assembled.provider_model_name.trim()
    || typeof assembled.provider_model_version !== "string" || !assembled.provider_model_version.trim()
    || typeof assembled.tokenizer_name !== "string" || !assembled.tokenizer_name.trim()
    || typeof assembled.tokenizer_version !== "string" || !assembled.tokenizer_version.trim()
    || !Number.isSafeInteger(assembled.provider_envelope_input_tokens) || (assembled.provider_envelope_input_tokens as number) < 0
    || !Number.isSafeInteger(assembled.output_token_reserve) || (assembled.output_token_reserve as number) < 0
    || !Number.isSafeInteger(assembled.context_window_limit) || (assembled.context_window_limit as number) < 1
    || (assembled.provider_envelope_input_tokens as number) + (assembled.output_token_reserve as number) > (assembled.context_window_limit as number)
    || !isDigest(assembled.assembled_input_sha256)
    || !isSortedUniqueStringList(assembled.dispatched_assertion_ids, 512)
    || !isSortedUniqueStringList(assembled.dispatched_relationship_ids, 512)
    || !isSortedUniqueStringList(assembled.dispatched_evidence_ref_ids, 1024)
    || !Array.isArray(assembled.source_token_accounting)
    || assembled.source_token_accounting.length > 128
    || !assembled.source_token_accounting.every((entry) => hasExactKeys(entry, ["source_kind", "source_id", "input_tokens"])
      && sourceKinds.includes(String(entry.source_kind))
      && typeof entry.source_id === "string" && Boolean(entry.source_id.trim())
      && Number.isSafeInteger(entry.input_tokens) && (entry.input_tokens as number) >= 0)
    || !Array.isArray(assembled.included_history)
    || assembled.included_history.length > 64
    || !assembled.included_history.every((entry) => hasExactKeys(entry, ["turn_id", "answer_sha256"])
      && typeof entry.turn_id === "string" && Boolean(entry.turn_id.trim()) && isDigest(entry.answer_sha256))) return false;

  const packetAssertionIds = new Set(packet.candidate_assertion_ids as string[]);
  const packetRelationshipIds = new Set(packet.candidate_relationship_ids as string[]);
  const packetEvidenceIds = new Set(packet.candidate_evidence_ref_ids as string[]);
  const dispatchedAssertions = assembled.dispatched_assertion_ids as string[];
  const dispatchedRelationships = assembled.dispatched_relationship_ids as string[];
  const dispatchedEvidence = assembled.dispatched_evidence_ref_ids as string[];
  if (dispatchedAssertions.some((id) => !packetAssertionIds.has(id))
    || dispatchedRelationships.some((id) => !packetRelationshipIds.has(id))
    || dispatchedEvidence.some((id) => !packetEvidenceIds.has(id))) return false;

  if (packet.truncated && packet.coverage_status !== "incomplete") return false;
  if (packet.retrieval_status === "empty" && (packet.candidate_assertion_ids.length > 0
    || packet.candidate_relationship_ids.length > 0 || packet.candidate_evidence_ref_ids.length > 0
    || packet.evidence_sufficiency_status !== "insufficient")) return false;
  if (packet.evidence_sufficiency_status === "insufficient"
    ? assembled.packet_disposition !== "omitted_insufficient"
      || assembled.packet_disposition_reason !== "insufficient_evidence"
      || assembled.dispatched_packet_sha256 !== null
      || assembled.dispatched_assertion_ids.length > 0
      || assembled.dispatched_relationship_ids.length > 0
      || assembled.dispatched_evidence_ref_ids.length > 0
    : assembled.packet_disposition !== "included"
      || assembled.packet_disposition_reason !== null
      || !isDigest(assembled.dispatched_packet_sha256)
      || packet.evidence_sufficiency_status !== "sufficient") return false;

  return true;
}
