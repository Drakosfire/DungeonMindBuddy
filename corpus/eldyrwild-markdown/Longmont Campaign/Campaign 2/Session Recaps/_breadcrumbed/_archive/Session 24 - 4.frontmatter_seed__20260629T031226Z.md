---
schema: dmb_recap_breadcrumbs_v1
source_recap_path: "Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 24 - 4.md"
campaign:
  title: "Longmont Campaign"
  campaign_number: 2
  campaign_id: longmont-c2
session:
  number: 24
  title: "Session 24 - 4"
  document_class: play
  canon_layer: campaign
  temporal_scope: session_specific
  origin_session: 24
  last_updated_session: 24
  source_class: observed_session_recap
breadcrumb_semantics:
  purpose: "Machine-facing session memory index over normalized recap prose."
  placement_rule: "Place tags immediately after the source-derived span that should route to that hub."
  selectivity_rule: "Tag durable actions, discoveries, relationships, location-state changes, collective decisions, and unresolved durable entities; do not tag every mere mention."
  source_boundary: "The canonical source recap remains the prose source of truth and is not edited by this file."
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
        - "the group"
        - "the party"
        - "the team"
      routing_policy: "Tag party spans only for collective decisions, travel beats, or end-of-session forks."
  pcs:
    - slug: baergrom
      route: "Longmont Campaign/Campaign 2/PCs/baergrom/"
    - slug: bonogo
      route: "Longmont Campaign/Campaign 2/PCs/bonogo/"
    - slug: caelynn
      route: "Longmont Campaign/Campaign 2/PCs/caelynn/"
    - slug: ephanna
      route: "Longmont Campaign/Campaign 2/PCs/ephanna/"
    - slug: karsemine
      route: "Longmont Campaign/Campaign 2/PCs/karsemine/"
    - slug: stafl
      route: "Longmont Campaign/Campaign 2/PCs/stafl/"
  npcs:
    - slug: captain_lysandra_ironveil
      route: "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/"
      aliases_in_recap:
        - "Lysandra"
        - "the captain"
    - slug: thrin_branchborn
      route: "Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/"
      aliases_in_recap:
        - "Thrin"
        - "Thrin of the Branchborn"
        - "Mother of Broken Branches"
  locations:
    - slug: Mireward
      route: "Elderwyld/Cities and Towns/Mireward/"
  new_hub_candidates: []
unresolved_open_questions: []
counts_by_subject_type:
  indexed_entities:
    parties: 1
    pcs: 6
    npcs: 2
    locations: 1
    new_hub_candidates: 0
  inline_tags:
    PC: 0
    NPC: 0
    Location: 0
    Party: 0
    NewHubCandidate: 0
  unresolved_open_questions: 0
---

### Session 24 - 4 — frontmatter seed only
