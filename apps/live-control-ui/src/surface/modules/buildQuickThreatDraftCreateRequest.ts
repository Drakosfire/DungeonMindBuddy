import type { CreateThreatDraftRequestV1 } from "../../api/types";

/** Dogfood defaults for required ThreatDraft fields the workbench form does not expose. */
export function buildQuickThreatDraftCreateRequest(input: {
  name: string;
  description: string;
  targetCr?: string;
}): CreateThreatDraftRequestV1 {
  const name = input.name.trim();
  const description = input.description.trim();
  const targetCr = input.targetCr?.trim() || null;
  return {
    world_id: "world_eldyrwild",
    campaign_id: "campaign_longmont_c2",
    focus: { session: null, prep_label: "statblock-workbench-quick-create" },
    name,
    description,
    threat_kind: "creature",
    intended_roles: [],
    tags: ["workbench-quick-create"],
    generation_intent: {
      ruleset: { system: "dnd5e", edition: "2024" },
      target_cr: targetCr,
      must_include: [],
      must_avoid: [],
    },
    encounter_context: {
      party_level: null,
      party_size: null,
      terrain_notes: [],
    },
    graph_context_snapshot: {
      graph_revision_id: "rev_workbench_quick_create",
      selected_node_ids: ["node_workbench_placeholder"],
      admitted_source_anchor_ids: ["anchor_workbench_placeholder"],
    },
    created_by: "gm-workbench",
  };
}
