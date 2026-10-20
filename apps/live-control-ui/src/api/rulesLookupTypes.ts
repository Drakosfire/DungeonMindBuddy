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
