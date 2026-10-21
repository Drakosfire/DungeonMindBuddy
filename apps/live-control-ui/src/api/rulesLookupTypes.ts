export interface RulesSource { corpus: string; available: boolean; ruleset_id?: string; title?: string; coverage?: string; unit_count?: number }
export interface RulesCatalog { schema: 'dmb_rules_catalog_v1'; sources: RulesSource[] }
export interface RulesCitation {
  citation_id: string; corpus: string; ruleset_id: string; unit_id: string; text_sha256: string;
  section: string; source_title: string; source_uri: string; source_sha256: string;
  page_fingerprint: string; pdf_page_index: number; printed_page: number | null;
}
export interface RulesHit extends RulesCitation { excerpt: string; excerpt_start: number; excerpt_end: number; excerpt_complete: boolean }
export interface RulesLookupPacket {
  schema: 'dmb_rules_lookup_packet_v1'; corpus: string; ruleset_id: string; query_id: string; normalized_query: string;
  status: 'evidence' | 'no_evidence'; coverage: string; coverage_status: 'limited'; hits: RulesHit[]; additional_matches: boolean;
}
export interface RulesPassage extends RulesCitation { schema: 'dmb_rules_passage_v1'; text: string; attribution: string }


export interface RulesPassageTarget {
  worldId: string; conversationId: string; turnId: string; attempt: number;
  supportId: string; supportSha256: string;
}
export interface RulesStoredSupport {
  schema: 'dmb_rules_support_v1'; support_id: string; corpus_sha256: string; ruleset_id: string;
  unit_id: string; full_text_sha256: string; excerpt_start: number; excerpt_end: number;
  excerpt_text: string; excerpt_sha256: string; source_title: string; section: string;
  source_uri: string; source_sha256: string; page_fingerprint: string;
  pdf_page_index: number; printed_page: number | null;
}
export interface RulesHistoricalPassage {
  schema: 'dmb_rules_historical_passage_v1'; world_id: string; conversation_id: string;
  turn_id: string; accepted_attempt: number; support: RulesStoredSupport; support_sha256: string;
}


export interface RulesSupportRef { support_id: string; support_sha256: string }
export interface RulesAnswerSegment {
  ordinal: number; domain: 'base' | 'rules_claim' | 'rules_context'; text_start: number; text_end: number;
  base_segment_index: number | null; rules_claim_id: string | null; rules_context_id: string | null;
  category: 'interpretation' | 'gap' | 'connective' | null; support_refs: RulesSupportRef[];
}
export interface RulesAcceptedBinding {
  schema: 'dmb_rules_accepted_binding_v1'; world_id: string; conversation_id: string; turn_id: string;
  corpus_sha256: string; ruleset_id: string; accepted_turn_revision: number; product_attempt: number;
  execution_id: string; producing_provider_attempt_id: string; request_envelope_sha256: string;
  composition_sha256: string; assistant_text_sha256: string; base_text_sha256: string | null;
  base_disposition: 'absent' | 'approved' | 'unclaimed'; segment_map: RulesAnswerSegment[];
  support_table: (RulesSupportRef & { source_label: string })[]; graph_used: boolean;
}
export interface RulesAnswerContext {
  schema: 'dmb_agent_rules_answer_context_v1'; accepted_binding: RulesAcceptedBinding; accepted_binding_sha256: string;
  base_context: import('./types').WorldPlanAgentPlanContextV2 | import('./types').WorldBuildKnowledgeContextV1 | import('./types').WorldPlayAgentContextV1 | null;
}
