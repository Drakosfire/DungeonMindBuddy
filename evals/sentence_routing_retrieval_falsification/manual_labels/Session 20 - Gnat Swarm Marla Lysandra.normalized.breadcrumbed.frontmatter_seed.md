---
schema: dmb_recap_breadcrumbs_v1
source_recap_path: "Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 20 - Gnat Swarm Marla Lysandra.md"
campaign:
  title: "Longmont Campaign"
  campaign_number: 2
  campaign_id: longmont-c2
session:
  number: 20
  title: "Session 20 - Gnat Swarm Marla Lysandra"
  document_class: play
  canon_layer: campaign
  temporal_scope: session_specific
  origin_session: 20
  last_updated_session: 20
  source_class: observed_session_recap
breadcrumb_semantics:
  purpose: "Machine-facing session memory index: inline labels mark source-aligned recap spans with durable retrieval value for agentic planning, live-play querying, hub routing, or proposed hub review."
  placement_rule: "Place tags immediately after the source-derived span that should route to that hub."
  selectivity_rule: "Do not tag every mere mention; tag table-significant actions, discoveries, relationship beats, location-state changes, reputation beats, collective decisions, affected groups, and unresolved durable entities."
  multi_hub_rule: "When one span has durable value for multiple hubs, append multiple tags to that same span."
  source_boundary: "This is a derivative retrieval/index artifact. The canonical source recap remains the prose source of truth and is not edited by this file."
  hub_status_rule: "Existing hubs route to corpus-relative hub folders or dossier files; durable subjects without a hub use NewHubCandidate with a proposed route."
  downstream_use: "Future agents should use this artifact to find relevant recap evidence and hub routes without rereading the whole recap when planning or enriching live-game interactions."
inline_tag_grammar:
  pc: "[PC][corpus-relative hub route]"
  npc: "[NPC][corpus-relative hub route]"
  location: "[Location][corpus-relative hub route]"
  party: "[Party][corpus-relative or proposed party hub route]"
  new_hub_candidate: "[NewHubCandidate][proposed corpus-relative route]"
entity_index:
  parties:
    questionable_company:
      slug: questionable_company
      display_name: "Questionable Company"
      hub_status: proposed
      proposed_route: "Longmont Campaign/Campaign 2/Parties/questionable_company/"
      default_members: [baergrom, bonogo, caelynn, ephanna, karsemine, stafl]
      aliases_in_recap:
        - "Questionable Company"
        - "the heroes"
        - "the group"
        - "the team"
        - "the rest of the team"
        - "the rest of the group"
        - "the others"
      routing_policy: "Use the Party breadcrumb only when the span has durable retrieval value for the party as a collective actor, witness, decision-maker, reputation target, or affected group. Do not tag every generic group/heroes/team sentence merely because the party is probably present. If specific PCs are acting separately, tag those PCs instead. If any PC is explicitly elsewhere, do not infer all-six participation from group language unless the sentence clearly says so."
  pcs:
    - slug: baergrom
      route: "Longmont Campaign/Campaign 2/PCs/baergrom/"
      inline_tag_count: 0
      note: "Session roster member; not named directly in this recap prose."
    - slug: bonogo
      route: "Longmont Campaign/Campaign 2/PCs/bonogo/"
    - slug: caelynn
      route: "Longmont Campaign/Campaign 2/PCs/caelynn/"
    - slug: ephanna
      route: "Longmont Campaign/Campaign 2/PCs/ephanna/"
    - slug: karsemine
      route: "Longmont Campaign/Campaign 2/PCs/karsemine/"
      aliases_in_recap: ["Karesmine"]
    - slug: stafl
      route: "Longmont Campaign/Campaign 2/PCs/stafl/"
  npcs:
    - slug: captain_lysandra_ironveil
      route: "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/"
    - slug: marla_brambleback
      route: "Elderwyld/Cities and Towns/Mossford/NPCs/marla_brambleback/"
    - slug: sara_mirathorn_operator
      route: "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/"
    - slug: sheriff_roderic_marr
      route: "Elderwyld/Cities and Towns/Mossford/NPCs/sheriff_roderic_marr/"
    - slug: stacey_brambleback
      route: "Elderwyld/Cities and Towns/Mossford/NPCs/stacey_brambleback/"
    - slug: stuart
      route: "Elderwyld/Cities and Towns/Mossford/NPCs/stuart/"
    - slug: thrin_branchborn
      route: "Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/"
  locations:
    - slug: mirathorn
      route: "Elderwyld/Cities and Towns/Mirathorn/"
    - slug: mossford
      route: "Elderwyld/Cities and Towns/Mossford/"
    - slug: migrating_forest
      route: "Elderwyld/Migrating Forest/"
    - slug: stormspire_academy
      route: "Elderwyld/Cities and Towns/Mirathorn/Stormspire Academy/"
  new_hub_candidates:
    - slug: half_burned_warehouse
      subject_type: location
      proposed_route: "Elderwyld/Cities and Towns/Mossford/Mossford_Location_Dossiers/Half-Burned Warehouse.md"
      rationale: "Repeated, specific Mossford child-gang scene location; not present in Mossford dossier collection."
    - slug: professor_merril_tealeaf
      subject_type: npc
      proposed_route: "Elderwyld/Cities and Towns/Mirathorn/Stormspire Academy/NPCs/professor_merril_tealeaf/"
      rationale: "Recurring Stormspire/Tealeaf contact for Caelynn; no dedicated hub found."
    - slug: voices_tower_blueprint
      subject_type: location
      proposed_route: "Elderwyld/Unknown Sites/Voices Tower/"
      rationale: "Lysandra draws a top-down tower blueprint under cult-like influence; no existing exact hub found."
unresolved_open_questions:
  - subject: half_burned_warehouse
    question: "Should the half-burned warehouse be promoted as a Mossford location dossier, or folded into an existing Mossford district dossier such as Dense Worker Housing?"
    proposed_route: "Elderwyld/Cities and Towns/Mossford/Mossford_Location_Dossiers/Half-Burned Warehouse.md"
  - subject: professor_merril_tealeaf
    question: "Should Professor Tealeaf receive a dedicated NPC hub under Stormspire Academy, or remain surfaced through Caelynn/Sara timelines and Stormspire prose?"
    proposed_route: "Elderwyld/Cities and Towns/Mirathorn/Stormspire Academy/NPCs/professor_merril_tealeaf/"
  - subject: voices_tower_blueprint
    question: "What canonical location route should own Lysandra's tower blueprint and voices clue once the site is identified?"
    proposed_route: "Elderwyld/Unknown Sites/Voices Tower/"
counts_by_subject_type:
  indexed_entities:
    parties: 1
    pcs: 6
    npcs: 7
    locations: 4
    new_hub_candidates: 3
  inline_tags:
    PC: 0
    NPC: 0
    Location: 0
    Party: 0
    NewHubCandidate: 0
  unresolved_open_questions: 3
---

### Session 20 (normalized) — frontmatter seed only
