import type { NativeAssertion } from "./nativeGraphInspection";
import type {AuthoredReferenceInput} from './types'
/** APP-STATE context-trace consumer shape. Observations grant no evidence authority. */
export interface WorldAgentTurnContextTraceResponse {
  schema: 'dmb_agent_turn_context_trace_response_v1'
  world_id: string
  turn_id: string
  attempts: BuddyTurnContextTrace[]
}
export interface BuddyTraceRoute {
  route_id: string; world_id: string; graph_revision: string
  node_id?: string | null; anchor_id?: string | null; evidence_ref_id?: string | null
  source_artifact_id?: string | null; source_revision_id?: string | null; content_sha256?: string | null
}
export interface BuddyTraceMaterial {
  item_id: string; state: 'model_context' | 'retrieval_route'
  role: 'user' | 'assistant' | 'source' | 'fact'; text?: string | null
  route?: BuddyTraceRoute | null; source_read_event_id?: string | null
  source_reads: { source_read_id: string; content_sha256: string }[]
  historical_source_reads?: BuddyHistoricalSourceReference[]
}
export interface BuddyHistoricalSourceReference {
  schema: 'dmb_trace_historical_source_ref_v1'; world_id: string; conversation_id: string
  turn_id: string; attempt: number; trace_id: string; source_read_event_id: string
  source_read_id: string; content_sha256: string
}
export interface BuddyHistoricalSourcePassageResponse {
  schema: 'dmb_agent_historical_source_passage_v1'
  reference: BuddyHistoricalSourceReference
  passage: BuddyTraceSourcePassage
}
interface Observation { sequence: number; elapsed_ms: number }
interface GraphLimits {
  max_nodes?: number | null; max_relationships?: number | null
  max_claims?: number | null; max_source_anchors?: number | null
}
export type BuddyTraceGraphRequest =
  | (GraphLimits & { operation: 'search'; query_text: string; seed_node_ids: string[] })
  | (GraphLimits & { operation: 'object'; target_node_id: string })
  | (GraphLimits & { operation: 'neighborhood'; seed_node_ids: string[]; depth: 1 | 2 })
  | { operation: 'support'; target_node_id: string; max_source_anchors?: number | null }
  | { operation: 'observations'; observation_ids: string[]; max_bytes: number }
export interface BuddyTraceGraphCounts { nodes: number; relationships: number; claims: number; evidence_refs: number }
export interface BuddyTraceGraphResult {
  outcome: 'enough' | 'partial' | 'truncated' | 'empty' | 'denied' | 'unavailable'
  graph_revision: string; coverage_status: 'complete' | 'incomplete'; projection_status: 'complete' | 'limited'
  nodes: { node_id: string; label: string; kind: string }[]
  relationships?: { relationship_id: string; source_node_id: string; target_node_id: string }[]
  discovery_relationship_ids?: string[]
  neighborhood_replay?: {
    hops: { relationship_id: string; from_node_id: string; to_node_id: string }[]
    object_limit_pruned_ids: string[]
    object_limit_pruned_count: number
  }
  relationship_ids: string[]; claim_ids: string[]; evidence_ref_ids: string[]
  returned_counts: BuddyTraceGraphCounts; total_counts: BuddyTraceGraphCounts; omission_codes: string[]
}
export interface BuddyTraceSourcePassage extends Observation {
  kind: 'source_passage' | 'source_passage_reuse'; origin_turn_id?: string; origin_attempt?: number; origin_read_event_id?: string; origin_provider_attempt_id?: string; source_read_event_id: string; read_call_id: string
  world_id: string; graph_revision: string; source_read_id: string; anchor_id: string
  evidence_ref_id: string; source_artifact_id: string; source_revision_id: string; source_name?: string | null
  line_start: number | null; line_end: number | null; outcome: 'enough' | 'partial' | 'truncated'
  returned_chars: number; content_sha256: string; text: string
}
export type BuddyAuthoredTraceEvent = {event_id:string;sequence:number} & (
  | {kind:'build_authored_references_captured_v1';references:AuthoredReferenceInput;read_graph_revision:string;turn_id:string;conversation_id:string;attempt:number;submitted_intent_fingerprint:string}
  | {kind:'build_authored_reference_authorized_v1';capture_event_id:string;node_id:string;arguments_sha256:string}
  | {kind:'build_authored_reference_read_v1';capture_event_id:string;authorization_event_id:string;node_id:string;operation_event_ids:string[];source_read_event_ids:string[];returned_node_ids:string[];outcome:'read'|'read_partial'|'source_gap'}
  | {kind:'build_authored_provider_inclusion_v1';capture_event_id:string;references_sha256:string;source_read_event_ids:string[];provider_attempt_id:string;envelope_sha256:string;material_sha256:string}
)
export type BuddyTraceObservation =
  | (Observation & {kind:'authored_graph_reference_v1';execution_event:BuddyAuthoredTraceEvent})
  | (Observation & { kind: 'context_snapshot'; stage: 'before' | 'after'; materials: BuddyTraceMaterial[]; snapshot_kind?: 'provider_input' | 'provider_response' | 'validated_answer' | 'compaction_input' | 'compaction_output' | null; comparison_id?: string | null })
  | (Observation & { kind: 'context_decision'; action: 'retrieved' | 'retained' | 'expanded' | 'compacted' | 'pruned'; item_ids: string[]; reason_code: string; policy_version: string })
  | (Observation & { kind: 'graph_tool'; tool_name: 'expand_graph_retrieval'; execution_event_id: string; request_arguments_sha256: string; result_packet_sha256: string; scope_mode: 'campaign' | 'world'; campaign_id: string | null; revision_pin: string; request: BuddyTraceGraphRequest; result: BuddyTraceGraphResult; duration_ms?: number | null })
  | BuddyTraceSourcePassage
  | BuddyTracePromptReference
  | (Observation & { kind: 'provider_call'; provider_attempt_id?: string | null; provider: string; model: string; outcome: 'authorized' | 'response_received' | 'denied' | 'failed' | 'unknown'; input_tokens?: number | null; output_tokens?: number | null; input_upper_bound?: number | null; input_estimator?: string | null; duration_ms?: number | null })
  | (Observation & { kind: 'failure'; code: string; phase: string; stage?: string | null; diagnostic_id?: string | null; diagnostic_sha256?: string | null; exception_type?: string | null; cause_type?: string | null })
export interface BuddyTurnContextTrace {
  schema: 'dmb_turn_context_trace_v1'; trace_id: string; world_id: string
  conversation_id: string; turn_id: string; attempt: number; execution_start_sequence: number
  started_at: string; closed_at: string | null; terminal_status: 'completed' | 'failed' | 'interrupted' | null
  capture_status: 'recording' | 'complete' | 'incomplete'; capture_failure_code: string | null
  observations: BuddyTraceObservation[]
  writer_evidence_sequences?: number[] | null
  effective_retrieval_selections?: { sequence: number; controller_attempt_id: string; operation: 'select_candidates' | 'discover_more' | 'finish_retrieval'; selected_count: number }[] | null
  graph_replay_order?: Record<string, number> | null
  native_discovery_replay?: {
    revision_id: string
    seed_ids: string[]
    labels: Record<string, string>
    hops: { relationship_id: string; from_node_id: string; to_node_id: string }[]
  } | null
  retrieval_exclusion_steps?: {
    sequence: number
    candidates: { handle: string; label: string; kind: string }[]
    total: number
  }[] | null
  native_assertion_steps?: {
    sequence: number; revision_id: string; assertion_ids: string[]; subject_ids: string[]
    assertion_ids_by_subject?: Record<string, string[]>
    related_labels?: Record<string, string>
    subject_labels?: Record<string, string>; subject_kinds?: Record<string, string>
    unavailable_count: number; writer_evidence: boolean
  }[] | null
}

export interface BuddyReplayNativeAssertionResponse {
  schema: 'dmb_replay_native_assertion_v1'; world_id: string; turn_id: string; trace_id: string
  sequence: number; revision_id: string
  assertion: { assertion_id: string; subject_entity_id: string; predicate: string; value: unknown; metadata?: NativeAssertion["metadata"] }
  excerpts: { evidence_ref_id: string; text: string }[]
}

export interface BuddyTracePromptReference extends Observation {
  kind: 'prompt_reference'; evidence_id: string; provider_attempt_id: string
  provider: string; model: string; api_mode: string; serializer_version: string
  payload_sha256: string; payload_utf8_bytes: number
}
export interface BuddyPromptEvidence {
  schema: 'dmb_agent_prompt_evidence_v1'; world_id: string; conversation_id: string
  turn_id: string; trace_id: string; attempt: number
  reference: BuddyTracePromptReference; payload_json: string
}


export interface BuddyReplayAssertionResponse {
  schema: 'dmb_replay_assertion_v1'
  world_id: string
  turn_id: string
  trace_id: string
  sequence: number
  scope: { managed_world_id: string; revision_id: string; scope_mode: 'campaign' | 'world'; campaign_id: string | null }
  assertion: { assertion_id: string; subject_entity_id: string; predicate: string; value: unknown }
}
