---
schema: dmb_recap_breadcrumbs_v1
source_recap_path: "Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 21 - Drake Nest Mirathorn Call.md"
campaign:
  title: "Longmont Campaign"
  campaign_number: 2
  campaign_id: longmont-c2
session:
  number: 21
  title: "Session 21 - Drake Nest Mirathorn Call"
  document_class: play
  canon_layer: campaign
  temporal_scope: session_specific
  origin_session: 21
  last_updated_session: 21
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
        - "the group"
        - "the rest of the group"
        - "the majority"
      routing_policy: "Tag party spans only for collective decisions, travel beats, or end-of-session forks — not every generic group sentence."
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
    - slug: sara_mirathorn_operator
      route: "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/"
      note: "Frank is Sara's twin co-operator; route Frank/Mirathorn handset beats here unless a dedicated Frank hub is promoted."
    - slug: sheriff_roderic_marr
      route: "Elderwyld/Cities and Towns/Mossford/NPCs/sheriff_roderic_marr/"
    - slug: thrin_branchborn
      route: "Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/"
  locations:
    - slug: mirathorn
      route: "Elderwyld/Cities and Towns/Mirathorn/"
    - slug: mossford
      route: "Elderwyld/Cities and Towns/Mossford/"
  new_hub_candidates:
    - slug: young_drake_nest_hill
      subject_type: location
      proposed_route: "Elderwyld/Unknown Sites/Young Drake Nest Hill/"
      rationale: "Major session set-piece: iridescent young drake nest bowl with elder drakes and loot."
    - slug: edge_of_the_world
      subject_type: location
      proposed_route: "Elderwyld/Cities and Towns/Edge of the World/"
      rationale: "Sheriff rumor destination for cultist music conversion; named northbound town."
    - slug: mireward
      subject_type: location
      proposed_route: "Elderwyld/Cities and Towns/Mireward/"
      rationale: "Named next town north on the road (~5 days out per Lysandra)."
    - slug: boots_of_crowing_wings
      subject_type: item
      proposed_route: "Longmont Campaign/Campaign 2/Plot Artifacts/boots_of_crowing_wings.md"
      rationale: "Bonogo loot from drake nest human remains; mechanical item acquired this session."
    - slug: metal_slab_with_buttons
      subject_type: item
      proposed_route: "Longmont Campaign/Campaign 2/Plot Artifacts/metal_slab_with_buttons.md"
      rationale: "Unidentified tech loot from drake nest; table-significant discovery."
unresolved_open_questions:
  - subject: mirathorn_festival_resumed
    question: "Mirathorn resumed the Festival; Frank hung up; Lysandra cannot get through — is the city compromised or merely distracted?"
    proposed_route: "Elderwyld/Cities and Towns/Mirathorn/"
  - subject: swamp_vs_mirathorn_fork
    question: "Party agreed to press on to the swamp rather than turn back — S22 opening pressure."
    proposed_route: "Longmont Campaign/Campaign 2/Parties/questionable_company/"
counts_by_subject_type:
  indexed_entities:
    parties: 1
    pcs: 6
    npcs: 4
    locations: 2
    new_hub_candidates: 5
  inline_tags:
    PC: 49
    NPC: 18
    Location: 15
    Party: 4
    NewHubCandidate: 7
  unresolved_open_questions: 2
---
# Session 21 Recap

While still waiting for a response Caelynn studies the sky once again.[PC][Longmont Campaign/Campaign 2/PCs/caelynn/] She estimates that the gathering storm will arrive in about seven hours.[PC][Longmont Campaign/Campaign 2/PCs/caelynn/] The group then decides to load up the wagon and head out in hopes of beating the storm.[Party][Longmont Campaign/Campaign 2/Parties/questionable_company/] They plan to head back up the main road through town and continue north. This will give them a chance to warn the Mossford of the approaching storm and gather any supplies they might need.[Location][Elderwyld/Cities and Towns/Mossford/] Stafl and Lysandra, both in need of a good rest, lay down in the back of the wagon, using this time to recharge while they travel.[PC][Longmont Campaign/Campaign 2/PCs/stafl/][NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/] Caelynn prepares some tea while the rest of the supplies are loaded in the wagon. As the wagon approaches town it is clear that they are having a celebration. Stafl begins to shout, in rhyme, to the crowd about the storm.[PC][Longmont Campaign/Campaign 2/PCs/stafl/] He is quickly approached by the sheriff, who is not happy about the news during the celebration.[PC][Longmont Campaign/Campaign 2/PCs/stafl/][NPC][Elderwyld/Cities and Towns/Mossford/NPCs/sheriff_roderic_marr/] It also becomes clear he is not a fan of signing, or rhyming in general.[NPC][Elderwyld/Cities and Towns/Mossford/NPCs/sheriff_roderic_marr/] He warns the group about rumors coming from a town to the north about cultists using music to convert others.[NPC][Elderwyld/Cities and Towns/Mossford/NPCs/sheriff_roderic_marr/][NewHubCandidate][Elderwyld/Cities and Towns/Edge of the World/] The town, called Edge of the World, is about a one week trip to reach.[NewHubCandidate][Elderwyld/Cities and Towns/Edge of the World/] They warn the sheriff about tainted meat and Karsemine uses her Thaumaturgy to show them what to look for when people begin to change.[NPC][Elderwyld/Cities and Towns/Mossford/NPCs/sheriff_roderic_marr/][PC][Longmont Campaign/Campaign 2/PCs/karsemine/]

They continue on north with Karsemine and Caelynn keeping an eye out for high ground for a place to stop for the night. While on this short trip everyone is able to relax and have a short rest. Because of their timing leaving the town and their navigation skills, the wagon is able to make it far enough north to just hit the very edge of the storm and only get soaked. They are able to see the sheen of magic as the rain pools up and instead of the usual petrichor the rain smells savory. Karsemine and Caelynn spot a good camping spot on the top of a conical hill.[PC][Longmont Campaign/Campaign 2/PCs/karsemine/][PC][Longmont Campaign/Campaign 2/PCs/caelynn/] They leave the wagon and the animals at the bottom and make their way up until they reach a giant bowl of water surrounded by a grove of trees. From this position they can see out along the plains for a fairly long distance. After conferring with Lysandra, they determine that they are 3 days from Mirathorn and the next little town north along the road will be Mireward, about 5 days out.[NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/][Location][Elderwyld/Cities and Towns/Mirathorn/][NewHubCandidate][Elderwyld/Cities and Towns/Mireward/] Everyone gets comfortable, sentries are posted, and they get a peaceful night’s rest. After another uneventful night, the group grabs their belongings and begins to walk back down to the wagon. As soon as they start Bonogo sees a huge double rainbow.[PC][Longmont Campaign/Campaign 2/PCs/bonogo/] Thrin is so excited to see it that he thanks the group again for taking him out of the forest.[NPC][Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/] Bonogo is convinced that there is something on the next hill over where the rainbow appears to end.[PC][Longmont Campaign/Campaign 2/PCs/bonogo/] Ephanna reminds him of an old Fey legend about making promises under a rainbow.[PC][Longmont Campaign/Campaign 2/PCs/ephanna/] The group decides to make a short detour to the hill Bonogo thinks the rainbow ended on.[Party][Longmont Campaign/Campaign 2/Parties/questionable_company/][PC][Longmont Campaign/Campaign 2/PCs/bonogo/] What they find at the bottom of the hill is a very old trail covered in thick brush. After only a brief discussion about continuing, the group slashes their way up the trail.

Karsemine, always keeping a sharp eye on her surroundings, is the first to notice something just off the trail.[PC][Longmont Campaign/Campaign 2/PCs/karsemine/] She picks up an iridescent scale, still warm to the touch.[PC][Longmont Campaign/Campaign 2/PCs/karsemine/] She shows it to Caelynn to make an arcana check, but she can’t tell anything about it.[PC][Longmont Campaign/Campaign 2/PCs/karsemine/][PC][Longmont Campaign/Campaign 2/PCs/caelynn/] As the group continues up the path the number of scales laying around continues to grow until it becomes obvious something is up ahead. Karsemine becomes very nervous about reaching the top and finding something waiting.[PC][Longmont Campaign/Campaign 2/PCs/karsemine/] While Caelynn creates Good Berries for everyone, Karemine scouts ahead.[PC][Longmont Campaign/Campaign 2/PCs/caelynn/][PC][Longmont Campaign/Campaign 2/PCs/karsemine/] The top of the hill is again shaped like a giant bowl, just as before, but this time instead of water this bowl is filled with detritus and the horrible smell of decay. Karsemine sneaks back to the group and warns them that something is definitely living here.[PC][Longmont Campaign/Campaign 2/PCs/karsemine/] Bonogo does not want to leave without taking a look himself, so Karsemine casts Pass Without a Trace and they both sneak back up.[PC][Longmont Campaign/Campaign 2/PCs/bonogo/][PC][Longmont Campaign/Campaign 2/PCs/karsemine/] They slowly make their way back through the remaining brush to the lip of the bowl and suddenly Bonogo is overwhelmed with the scent of reptiles.[PC][Longmont Campaign/Campaign 2/PCs/bonogo/] Down below on the floor of the bowl they can see a large amount of winged reptiles, between 40 and 50, and the remains of countless animal corpses along with human corpses with some remaining gear. The reptiles appear to be the size of a very large dog and their iridescent scales make them appear to be covered in rainbows. Despite the danger, Bonogo is convinced the “treasure” is on the human remains and tells the rest of the group that this is a big score waiting to be picked up.[PC][Longmont Campaign/Campaign 2/PCs/bonogo/]

As the group spends the next few minutes deciding what to do next, the majority want to leave right away, suddenly a large group of the reptiles fly up and away. Karsemine is able to tell now that they are young drakes.[PC][Longmont Campaign/Campaign 2/PCs/karsemine/][Location][Elderwyld/Unknown Sites/Young Drake Nest Hill/] Based on their size five of these would be a tough battle for the group, so it doesn't look good if they are caught fighting the whole nest.[Location][Elderwyld/Unknown Sites/Young Drake Nest Hill/] Bonogo decides now is a good time to check again on how many remained in the nest.[PC][Longmont Campaign/Campaign 2/PCs/bonogo/][Location][Elderwyld/Unknown Sites/Young Drake Nest Hill/] What he finds is nine young drakes remain, but he also discovers two large elder drakes and seven more sitting on smaller nests.[PC][Longmont Campaign/Campaign 2/PCs/bonogo/][Location][Elderwyld/Unknown Sites/Young Drake Nest Hill/] Because of the spell from Karsemine he is able to sneak even closer without being seen.[PC][Longmont Campaign/Campaign 2/PCs/bonogo/][PC][Longmont Campaign/Campaign 2/PCs/karsemine/][Location][Elderwyld/Unknown Sites/Young Drake Nest Hill/] He is able to find a few valuable things right away: a metal slab with buttons and a pair of beat-up old boots.[PC][Longmont Campaign/Campaign 2/PCs/bonogo/][NewHubCandidate][Longmont Campaign/Campaign 2/Plot Artifacts/metal_slab_with_buttons.md][NewHubCandidate][Longmont Campaign/Campaign 2/Plot Artifacts/boots_of_crowing_wings.md][Location][Elderwyld/Unknown Sites/Young Drake Nest Hill/] He decides not to push his luck further and heads back to the group.[PC][Longmont Campaign/Campaign 2/PCs/bonogo/] He is disappointed in the loot until he tries on the boots and discovers that they are the Boots of Crowing Wings.[PC][Longmont Campaign/Campaign 2/PCs/bonogo/][NewHubCandidate][Longmont Campaign/Campaign 2/Plot Artifacts/boots_of_crowing_wings.md] They allow him additional jumping distance.[PC][Longmont Campaign/Campaign 2/PCs/bonogo/][NewHubCandidate][Longmont Campaign/Campaign 2/Plot Artifacts/boots_of_crowing_wings.md] Back at the wagon the sky still looks good, but Caelynn can feel the storm starting to build and Ephanna feels a strange magic forming.[PC][Longmont Campaign/Campaign 2/PCs/caelynn/][PC][Longmont Campaign/Campaign 2/PCs/ephanna/] The group decides that it is best to find a spot quickly where they can make any sort of shelter from the storm.[Party][Longmont Campaign/Campaign 2/Parties/questionable_company/] They continue up the path until they reach the next small hill. Again they leave the wagon and hike half way up the hill before finding a suitable spot. Thrin shows his craftiness by helping to create a shelter from the surrounding trees.[NPC][Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/]

Stafl is on first watch, with little happening, until the sky darkens further and he can just make out a huge swarm of wings.[PC][Longmont Campaign/Campaign 2/PCs/stafl/] Ephanna takes the next watch, and the only notable thing that happens is they find a strangely flat rock, which they put into their pack.[PC][Longmont Campaign/Campaign 2/PCs/ephanna/] Shortly after sunrise Caelynn decides to call Mirathorn again.[PC][Longmont Campaign/Campaign 2/PCs/caelynn/][Location][Elderwyld/Cities and Towns/Mirathorn/] After a pause she is finally connected with Frank, who sounds very hung over.[PC][Longmont Campaign/Campaign 2/PCs/caelynn/][NPC][Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/][Location][Elderwyld/Cities and Towns/Mirathorn/] He apologizes to her, telling Caelynn that the city resumed the Festival and it was a long night.[PC][Longmont Campaign/Campaign 2/PCs/caelynn/][NPC][Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/][Location][Elderwyld/Cities and Towns/Mirathorn/] She is very upset at the news about the festival, but before she can tell Frank he abruptly hangs up on her.[PC][Longmont Campaign/Campaign 2/PCs/caelynn/][NPC][Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/][Location][Elderwyld/Cities and Towns/Mirathorn/] Now she is devastated.[PC][Longmont Campaign/Campaign 2/PCs/caelynn/] And things don’t appear to be improving. In need of a friend, she approaches Lysandra to tell her what just happened, but Lysandra doesn’t appear to notice that Caelynn is barely holding back tears.[PC][Longmont Campaign/Campaign 2/PCs/caelynn/][NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/] Frustrated, Caelynn turns and walks away to gather her things.[PC][Longmont Campaign/Campaign 2/PCs/caelynn/] Lysandra then notices Ephanna talking with her while she is brewing some tea.[NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/][PC][Longmont Campaign/Campaign 2/PCs/ephanna/] She takes the chance to approach Caelynn again and asks for some tea and finally notices the state that Caelynn is in.[NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/][PC][Longmont Campaign/Campaign 2/PCs/caelynn/] Now it's Lysandra’s turn to burst into tears.[NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/] After collecting herself, she tells Caelynn that she has done a little investigation into the person they spoke about back in the city and how she finally sees how much the group does for her.[NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/][PC][Longmont Campaign/Campaign 2/PCs/caelynn/] Again Caelynn turns and walks away, clearly not ready to talk.[PC][Longmont Campaign/Campaign 2/PCs/caelynn/]

Ephanna moves in to speak with Lysandra and tell her about the earlier call to Mirathorn.[PC][Longmont Campaign/Campaign 2/PCs/ephanna/][NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/][Location][Elderwyld/Cities and Towns/Mirathorn/] Lysandra decides to make a call herself, but does not even get an answer.[NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/][Location][Elderwyld/Cities and Towns/Mirathorn/] Something seems wrong back at the city, but they cannot know for sure.[Location][Elderwyld/Cities and Towns/Mirathorn/] Now the group must decide: continue on their mission to the swamp, or turn back and see what is happening at the city. After a brief discussion, they agree to press on to the swamp.[Party][Longmont Campaign/Campaign 2/Parties/questionable_company/]
