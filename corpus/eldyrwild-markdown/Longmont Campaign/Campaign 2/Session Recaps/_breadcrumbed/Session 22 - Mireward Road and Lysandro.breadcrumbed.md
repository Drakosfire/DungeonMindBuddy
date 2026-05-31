---
schema: dmb_recap_breadcrumbs_v1
source_recap_path: "Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 22 - Mireward Road and Lysandro.md"
campaign:
  title: "Longmont Campaign"
  campaign_number: 2
  campaign_id: longmont-c2
session:
  number: 22
  title: "Session 22 - Mireward Road and Lysandro"
  document_class: play
  canon_layer: campaign
  temporal_scope: session_specific
  origin_session: 22
  last_updated_session: 22
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
    PC: 40
    NPC: 28
    Location: 10
    Party: 3
    NewHubCandidate: 0
  unresolved_open_questions: 2
---
# Session 22 Recap

The group turns their focus to the Reach; the vast Golden Fields to the north. If they decide to continue on, their destination is Mireward.[Location][Elderwyld/Cities and Towns/Mireward/] If they decide to turn around, it's a multiday journey back to Mirathorn.[Location][Elderwyld/Cities and Towns/Mirathorn/] The first thing to do is break their camp and head back to the wagon. The trail is damp from the rain and a magical sheen lies everywhere. In the distance to the west another storm appears to be building and there is a constant feeling of an approaching storm.

After another failed attempt to contact Mirathorn by rockie-talkie, the group decides they need to come up with a plan to contact someone in the city they can trust.[Location][Elderwyld/Cities and Towns/Mirathorn/][Party][Longmont Campaign/Campaign 2/Parties/questionable_company/] After some debate, they decide they should send a message to Professor Tealeaf, assuming the Wizard’s College is the least likely to be affected by anything nefarious happening, and an encoded message to Grobnok in case the message gets intercepted.[NPC][Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/] The group decides on a spoken and written message about the problems they have had contacting the city and for someone there to contact them back.[Party][Longmont Campaign/Campaign 2/Parties/questionable_company/] They send off a silver raven knowing that it would take the rest of the day for it to arrive.

With nothing left to do for Mirathorn, the group loads up the wagon and continues north, all the while a gigantic storm from the west appears to be merging with a storm coming from the south.[Location][Elderwyld/Cities and Towns/Mirathorn/] Most of the day is spent quietly traveling. Thrin asks Ephanna whether or not the forest can lie, which he is informed it does, while this breaks Caelynn out of her silent contemplation long enough to comment that people lie too; with a glance towards Lysandra.[NPC][Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/][PC][Longmont Campaign/Campaign 2/PCs/ephanna/][PC][Longmont Campaign/Campaign 2/PCs/caelynn/][NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/] While walking along the wagon Karsemine notices something odd happening when birds fly over: something is wrong with the reflections in the puddles.[PC][Longmont Campaign/Campaign 2/PCs/karsemine/] It appears that the reflections are somewhat delayed, anything reflected in the shimmering water is a second late.

The group continues on when they see a cloud of dust as something is moving fast in their direction. They soon encounter a young rider on a horse at top speed. She slows long enough to say that they cannot stop unless they have food for her horse so that she can continue on. The horse has clearly been running at full speed for a long time and could use a short break. Caeylynn conjures some Good Berries for the horse and fetches some water.[PC][Longmont Campaign/Campaign 2/PCs/caelynn/] Stafl immediately recognizes the soldier’s uniform of the Elderwild Reach, the same uniform he wore before leaving and joining this group.[PC][Longmont Campaign/Campaign 2/PCs/stafl/] The woman introduces herself as Private Hester and she is carrying a sealed tube in her hand with reports for Mirathorn.[Location][Elderwyld/Cities and Towns/Mirathorn/] Lysandra requests a report right away.[NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/] Hester tells her of reports of mysterious music and people walking into the swamp, none of them responding when stopped.[NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/] Karsemine shows her the glassy eyes they have seen countless times, and Hester is even more worried that something very bad is happening.[PC][Longmont Campaign/Campaign 2/PCs/karsemine/] She scoffs when Lysandra tells her the group is headed there to take care of the problem, saying they would need a much bigger party.[NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/] Before turning to take off again, she tells Lysandra to speak to Commander Vale before heading into the swamp.[NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/]

Karsemine begins to look for a good place to camp, but can't help wondering more about the mysterious puddles.[PC][Longmont Campaign/Campaign 2/PCs/karsemine/] She asks Caelynn for help and she casts Detect Magic using her Whisper Bottle.[PC][Longmont Campaign/Campaign 2/PCs/karsemine/][PC][Longmont Campaign/Campaign 2/PCs/caelynn/] Magic seems to be coming from everywhere, but she is able to see that the magic in the puddle is from conjuration.[PC][Longmont Campaign/Campaign 2/PCs/caelynn/] Caelynn takes a small vial with her and Karsemine pokes the puddle with a stick.[PC][Longmont Campaign/Campaign 2/PCs/caelynn/][PC][Longmont Campaign/Campaign 2/PCs/karsemine/] Just then Bonogo leaps over them both and lands in the puddle, splashing everyone with water.[PC][Longmont Campaign/Campaign 2/PCs/bonogo/] They hold their breath waiting for something to change, but nothing else happens. So they continue to the next hill, looking for a good place to stop for the night.

While sitting around the fire, Stafl uses Identify on the vial and isn't able to tell much except that no one should drink it.[PC][Longmont Campaign/Campaign 2/PCs/stafl/] After another arcana check, it appears the magic is some sort of bleed from another plane of existence and something is conjuring it. They are even more concerned about the effect this will have on the flora and fauna in the area. Suddenly Ephanna can hear a muffled voice coming from the rockie-talkie.[PC][Longmont Campaign/Campaign 2/PCs/ephanna/] They can just make out the code phrase before they realize it is Grobnok.[NPC][Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/] What follows is not a great update from the city. Grobnok took the rockie-talkie from Frank after it appears he has been compromised and he has not seen Sara recently.[NPC][Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/] The council was not able to find all the corrupted meat in time and now there is a full blown outbreak once again.[Location][Elderwyld/Cities and Towns/Mirathorn/] The decimated city guard is further reduced by the corruption so the council had no other option but to hire mercenaries. He and Tealeaf are working together to regain some control, which is mostly working.[NPC][Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/] The council instructs the group to continue on to the swamp where they believe this problem originates.[Party][Longmont Campaign/Campaign 2/Parties/questionable_company/] Finally, he tells them he will be the only one contacting the group going forward and will do his best to call each evening.[NPC][Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/]

The group sits quietly near the fire until they are assaulted by gnats, except for Thrin, and they turn in early.[NPC][Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/] Karsemine takes first watch.[PC][Longmont Campaign/Campaign 2/PCs/karsemine/] The night is quiet until she starts to hear a rhythmic sound on the wind coming from the north.[PC][Longmont Campaign/Campaign 2/PCs/karsemine/] Stafl takes the next watch, and except for a pair of eyes that turns out to be a fox, his shift is quiet.[PC][Longmont Campaign/Campaign 2/PCs/stafl/] Ephanna is the last watch and as the sun starts to rise so does a strange mist, with a familiar savory flavor.[PC][Longmont Campaign/Campaign 2/PCs/ephanna/] With no call from Grobnok the group packs up and begins the walk back to the wagons.[NPC][Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/] Caelynn checks on the weather and it is very clear that a major storm is coming.[PC][Longmont Campaign/Campaign 2/PCs/caelynn/] Where the two storms are meeting it appears to be hazy, but Caelynn quickly determines it is a huge hail storm.[PC][Longmont Campaign/Campaign 2/PCs/caelynn/] She directs the group to get moving and to be on the lookout for any place to shelter.[PC][Longmont Campaign/Campaign 2/PCs/caelynn/]

The ride is much more pleasant as both Lysandra and Caelynn are in much better moods.[NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/][PC][Longmont Campaign/Campaign 2/PCs/caelynn/] Having a goal and helping the group really boosted morale. Lysandra opens up to Ephanna about how poorly she is handling the mission she has been given.[NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/][PC][Longmont Campaign/Campaign 2/PCs/ephanna/] She is upset with how difficult it is to keep Mirathorn out of trouble, but is determined to get back to being the group leader.[NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/][Location][Elderwyld/Cities and Towns/Mirathorn/] After a nice stretch of peaceful travel, one by one the each member realizes they are humming some sort of song. Even more, they are all humming the same song. Karesmine identifies it as the rhythm she heard the night before, and Ephanna figures out it is the song they all heard the Dustwalker perform at the festival.[PC][Longmont Campaign/Campaign 2/PCs/karsemine/][PC][Longmont Campaign/Campaign 2/PCs/ephanna/] Up ahead, at the fork in the road, is a small building and a sign indicating Mireward 20 miles north.[Location][Elderwyld/Cities and Towns/Mireward/]

The small building turns out to be an abandoned restaurant specializing in meat on a stick. Karsemine takes a quick look around and judges that the place was only recently abandoned, no more than a week ago.[PC][Longmont Campaign/Campaign 2/PCs/karsemine/] The chalkboard menu out front has been hastily erased and now simply reads “headed south, north wrong”. Inside the group finds a small sink, dishes neatly put away, and a trapdoor leading to a small storage area. Here they only find a jar with a few skewers with old graying meat. Returning outside, Caelynn takes another look at the weather and decides they may not be able to beat the storm north, so they decide to take shelter in the building.[PC][Longmont Campaign/Campaign 2/PCs/caelynn/] Karsemine uses her survival skills to reinforce the structure so that the animals are protected as well.[PC][Longmont Campaign/Campaign 2/PCs/karsemine/] Just in time as an incredible wall of hail smashes into the building and the surrounding area. For several minutes no one can hear anything except for the roar of the storm, then it quickly starts to fade as it moves on.

The sun is starting to get low, but the group thinks they can make it to Mireward around 10 o'clock.[Location][Elderwyld/Cities and Towns/Mireward/] As they once again pack up the wagon they assess the damage the storm left. Besides the trees being shredded, all else seems ok, until, not long after they left, Karsemine hears a distinctive sound: knocking on a door.[PC][Longmont Campaign/Campaign 2/PCs/karsemine/] Even with her dark vision and her scouting skills, she is unable to find the source of the noise, and in fact cannot find anything that would have a door.[PC][Longmont Campaign/Campaign 2/PCs/karsemine/]

While she is out scouting, Ephanna gets another call from Grobnok.[PC][Longmont Campaign/Campaign 2/PCs/ephanna/][NPC][Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/] He airs his frustration at having to help the city instead of partying at the festival, and says things are not getting better.[NPC][Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/] There is an uneasy truce between the mercenaries and the “meat heads”, but the “meat heads” have become more vocal and open in the recruitment for the Shepherd. And worse still, a gnome was found within the city to have the shimmering eyes, something that previously only happened to humans who became infected.[Location][Elderwyld/Cities and Towns/Mirathorn/] Stafl then argues with Grobnok about their effectiveness in dealing with the cultists before hanging up the rockie-talkie and giving it to Lysandra.[PC][Longmont Campaign/Campaign 2/PCs/stafl/][NPC][Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/][NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/] Then, not fully trusting her, or anyone from the city, takes it back and gives it to Caelynn.[PC][Longmont Campaign/Campaign 2/PCs/stafl/][NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/][PC][Longmont Campaign/Campaign 2/PCs/caelynn/]

That's when Stalf casts Suggestion on Lysandra, intending to find out her motivations.[PC][Longmont Campaign/Campaign 2/PCs/stafl/][NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/] He asks her to tell him her true intentions, to which she responds that her goal is to keep the team focused on going to the swamp and destroying the source of the cult.[PC][Longmont Campaign/Campaign 2/PCs/stafl/][NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/] It is well into the night when they spot a wall in the darkness and can just make out a person standing guard at the top. He demands that the group stop and to identify themselves. Stafl casts Light so he can more clearly see the group of heroes.[PC][Longmont Campaign/Campaign 2/PCs/stafl/] Karsemine, thinking of Lysanrda’s new found leadership, says our leader should step forward.[PC][Longmont Campaign/Campaign 2/PCs/karsemine/][NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/] But Bonogo, believing that she means him, steps forward with a simple hello.[PC][Longmont Campaign/Campaign 2/PCs/bonogo/][NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/] The man’s eyes grow big as he scans the rest of the group.

“Is that little Lysandra?” he asks.[NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/] “No dad, it’s Lieutenant Lysandra now”.[NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/] And that is how they all met her father Lysandro.[NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/]