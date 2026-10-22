export interface CombatRulesetField {
  key: "initiative" | "armor_class" | "hit_points" | "temp_hit_points" | "conditions" | "notes";
  label: string;
  enabled: boolean;
}

export interface CombatRulesetConfig {
  schema: "dmb_combat_ruleset_v1";
  config_id: string;
  system_id: string;
  edition_id: string;
  revision: string;
  mode: "manual_tracking";
  fields: CombatRulesetField[];
  manual_defaults: Record<string, string | number | boolean | null>;
}

export interface CombatEntityProvenance {
  source: "generated_statblock_view";
  artifact_id: string;
  draft_id: string | null;
  corpus_display_path: string | null;
  corpus_file_fingerprint: string | null;
  retrieval_status: string | null;
  retrieval_verified_at: string | null;
  added_at: string;
  hydration_contract: "combat_defaults";
}

export interface CombatWorldIdentity {
  managed_world_id: string; native_world_id: string; binding_version: number;
  graph_revision_id: string; node_id: string; label: string; kind: string; role: string; campaign_scope: string | null;
}

export interface CombatEntity {
  id: string;
  name: string;
  team: "pc" | "ally" | "enemy" | "neutral";
  order: number;
  init: number | null;
  ac: number | string | null;
  hp: number | string | null;
  max_hp: number | string | null;
  temp_hp: number;
  defeated: boolean;
  notes: string;
  conditions: string[];
  tags: string[];
  statblock_path: string | null;
  statblock_artifact_id: string | null;
  statblock_title: string | null;
  corpus_fingerprint: string | null;
  source: "corpus" | "generated_pending" | "manual" | "imported";
  world_identity?: CombatWorldIdentity | null;
  provenance: CombatEntityProvenance[];
}

export interface CombatGroup {
  group_key: string;
  label: string;
  statblock_path: string | null;
  member_ids: string[];
  collapsed: boolean;
}

export interface CombatEncounterProvenance {
  source: "statblock_combat_add";
  artifact_id: string;
  added_entity_ids: string[];
  added_at: string;
}

export interface CombatEncounterDraft {
  schema: "dmb_combat_encounter_draft_v1";
  title: string;
  round: number;
  active_turn_entity_id: string | null;
  round_start_entity_id: string | null;
  queue_model: "circular_barrel_v1";
  entities: CombatEntity[];
  groups: CombatGroup[];
  provenance: CombatEncounterProvenance[];
}

export interface CombatEncounterRecord {
  encounter_id: string;
  world_id: string;
  campaign_id: string | null;
  session: number | null;
  revision: number;
  ruleset: CombatRulesetConfig;
  ruleset_digest: string;
  draft: CombatEncounterDraft;
  created_at: string;
  updated_at: string;
}

export interface CreateCombatEncounterRequest {
  title: string;
  campaign_id?: string | null;
  session?: number | null;
  ruleset_id?: string;
}

export interface AddGeneratedStatblockRequest {
  expected_revision: number;
  team: CombatEntity["team"];
  count: number;
  name_override?: string | null;
  initiative?: number | null;
  insert_after_entity_id?: string | null;
  group_key?: string | null;
  notes?: string | null;
  hp_override?: number | null;
  max_hp_override?: number | null;
}

export interface AddGeneratedStatblockResponse {
  added_entities: CombatEntity[];
  encounter: CombatEncounterRecord;
}
