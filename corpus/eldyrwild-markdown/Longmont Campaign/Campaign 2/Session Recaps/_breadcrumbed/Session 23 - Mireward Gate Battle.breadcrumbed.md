---
schema: dmb_recap_breadcrumbs_v1
source_recap_path: "Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 23 - Mireward Gate Battle.md"
campaign:
  title: "Longmont Campaign"
  campaign_number: 2
  campaign_id: longmont-c2
session:
  number: 23
  title: "Session 23 - Mireward Gate Battle"
  document_class: play
  canon_layer: campaign
  temporal_scope: session_specific
  origin_session: 23
  last_updated_session: 23
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
    - slug: sara_mirathorn_operator
      route: "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/"
      aliases_in_recap:
        - "Frank"
    - slug: thrin_branchborn
      route: "Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/"
      aliases_in_recap:
        - "Thrin"
        - "Thrin of the Branchborn"
        - "Mother of Broken Branches"
    - slug: brin_holloway
      route: "Elderwyld/Cities and Towns/Mireward/NPCs/brin_holloway/"
    - slug: lysandro_ironveil
      route: "Elderwyld/Cities and Towns/Mireward/NPCs/lysandro_ironveil/"
    - slug: orric_tane
      route: "Elderwyld/Cities and Towns/Mireward/NPCs/orric_tane/"
  locations:
    - slug: Mirathorn
      route: "Elderwyld/Cities and Towns/Mirathorn/"
    - slug: Mireward
      route: "Elderwyld/Cities and Towns/Mireward/"
  new_hub_candidates: []
unresolved_open_questions: []
counts_by_subject_type:
  indexed_entities:
    parties: 1
    pcs: 6
    npcs: 6
    locations: 2
    new_hub_candidates: 0
  inline_tags:
    PC: 45
    NPC: 17
    Location: 3
    Party: 0
    NewHubCandidate: 0
  unresolved_open_questions: 0
---
# Session 23 Recap

On top of the wall is a well dressed man in his mid 50s with an old worn military coat over his fine clothes. He is instructing the other “guards” on how to open and close the gate so that the group of heroes can enter the town. Lysandra is surprised to see her father wearing the old uniform, because he is not a military man, but he explains that he was having trouble organizing the town after they received the message from the north.[NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/][NPC][Elderwyld/Cities and Towns/Mireward/NPCs/lysandro_ironveil/] He explains that not long before the group arrived a messenger arrived with a dire message from Edge, the town to the north on the outskirts of the Swamp. The messenger claimed the town was under siege from horrific monsters and that a group of survivors were leaving for Mireward Reach, but no one had arrived. After such a long stretch of peace, and no other recent word from the town, people had lost interest and grown complacent.

Lysandra quickly reads the message to the group, which sounds exactly like the monsters they faced in Mirathorn; slimy monsters and flying meat creatures along with changes to people’s eyes.[NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/][Location][Elderwyld/Cities and Towns/Mirathorn/] Now she is trying to decide what they should do next, help out her hometown or go directly north to help Edge.[NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/] After a brief discussion, she decides they need to speak with the town leader.[NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/] They all head to the Inn where they can clearly hear lots of voices before they even open the doors. Inside they find the common room packed with people, all shouting over one another until one loud and clear voice silences the rest.

Another well dressed man, most likely a former merchant around the same age as Lysandro, addresses the crowd. As mayor, Orik Tane can easily command the room.[NPC][Elderwyld/Cities and Towns/Mireward/NPCs/orric_tane/] He agrees with the crowd that he is not certain if the danger is real, but they have never received a message like this before.[NPC][Elderwyld/Cities and Towns/Mireward/NPCs/orric_tane/] The problem is if there is a real threat, who from the town will be able to go and help fight. That’s when the door swings open again and six very experienced adventurers enter. And, as shocked as the crowd is to see this new group, they are more shocked to see “little” Lysandra with them.[NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/] Without wasting any time with greetings and formalities, she quickly explains the mission they are on from Mirathorn and how the group has fought back these same monsters before.[NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/][Location][Elderwyld/Cities and Towns/Mirathorn/] Instead of relief, this causes more concern as most of the people here believed that the threat was overblown.

Suddenly everyone can hear yelling and a loud bell ringing coming from outside. A very tired and very scared boy slams open the door. Through his heavy breathing he explains that shadows are coming from the Reach to the north gate. Without hesitation Stafl casts Celestial Revelation and flies up and out of the Inn to the top of the north gate.[PC][Longmont Campaign/Campaign 2/PCs/stafl/] People are stunned into silence, now fully aware that this new group is fully in charge of the situation. Stafl casts Light on a crossbow bolt and fires it out onto the road coming to the gate.[PC][Longmont Campaign/Campaign 2/PCs/stafl/] With the dim light he created he can make out lots of shadows, anywhere from twenty to one hundred.[PC][Longmont Campaign/Campaign 2/PCs/stafl/] Then there is a banging on the gate below. Before anyone can react they hear voices yelling “they’re coming, let us in”.

Ephanna rushes to the gate, but protests just letting the people in.[PC][Longmont Campaign/Campaign 2/PCs/ephanna/] They are able to determine that there are around fifty people in this group, much less than what they started out with when they evacuated to Mireward. A clear leader of the group steps forward, Brin Holloway, a cook from Edge, who quickly tells how they all narrowly escaped as the town was surrounded and overrun by horrible meat monsters.[NPC][Elderwyld/Cities and Towns/Mireward/NPCs/brin_holloway/] Ephanna explains that they will need to see the eyes of each person before they can enter, something Brin says he knows what they are looking for.[PC][Longmont Campaign/Campaign 2/PCs/ephanna/][NPC][Elderwyld/Cities and Towns/Mireward/NPCs/brin_holloway/] But before they can start this plan, Kasemine can feel the ground rumble, dirt vibrating as something big, or many things, approach the town.[PC][Longmont Campaign/Campaign 2/PCs/karsemine/] She quickly climbs to the top of the wall and with her dark vision can just make out multiple forms, some huge, slowly approaching.[PC][Longmont Campaign/Campaign 2/PCs/karsemine/]

Stafl quickly forms a plan.[PC][Longmont Campaign/Campaign 2/PCs/stafl/] He instructs the survivors to follow the wall around the city and to find the south gate and wait there.[PC][Longmont Campaign/Campaign 2/PCs/stafl/] Inside he tells the guards to watch the people, but to not let them in until the town is secure. The rest of the group joins Stafl and Karsemine on the wall to begin forming a plan. Bonogo throws some ball bearings down in front of the gate while Karsemine casts Spike Growth in a 20 foot area  providing difficult terrain and large spiky thorns along the road.[PC][Longmont Campaign/Campaign 2/PCs/bonogo/][PC][Longmont Campaign/Campaign 2/PCs/karsemine/] They can see the group of large shadows enter the tangle of thorns, but then stop. The rest of the shadows behind start to go around the area as the others back up, all while taking piercing damage from the thorns. Now that the shadows are within 120 feet Ephanna can finally see the group of terrifying creatures: two giant tripod meat monsters, a golem like creature, a swarm of flying meatwing monsters, two meat hybrid monsters and two of the sewer monsters they fought in Mirathorn.[PC][Longmont Campaign/Campaign 2/PCs/ephanna/][Location][Elderwyld/Cities and Towns/Mirathorn/]

Karsemine and Ephanna are first to plan their attack.[PC][Longmont Campaign/Campaign 2/PCs/karsemine/][PC][Longmont Campaign/Campaign 2/PCs/ephanna/] Karesmine steadies her bow, waiting for the creatures to get within range, while Ephanna casts Hunger of Hadar on a point in their path.[PC][Longmont Campaign/Campaign 2/PCs/karsemine/][PC][Longmont Campaign/Campaign 2/PCs/ephanna/] Now any creature inside will be blinded and take cold and acid damage, however the rest of the team cannot see into the magical sphere as well. Now Bonogo, Thrin and Baergrom all ready themselves, but also hold their attack until the monsters are in range.[PC][Longmont Campaign/Campaign 2/PCs/bonogo/][NPC][Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/][PC][Longmont Campaign/Campaign 2/PCs/baergrom/] The two sewer monsters are caught inside the sphere of darkness and take both cold and acid damage as they end their attack still inside.

The terrifying tripod creatures, 15 feet tall, bulbous and covered in skulls, sink their legs into the ground and then rip off a part of their body and launch it at the wall. Both land just short, but then transform into more small meat monsters. Now within range, Karsemine shoots one of them with her bow, while Baergrom attempts to shoot the other with his crossbow, but misses.[PC][Longmont Campaign/Campaign 2/PCs/karsemine/][PC][Longmont Campaign/Campaign 2/PCs/baergrom/] Thrin kills the other with a shot from his bow.[NPC][Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/] The flying meat creatures take cold damage, but then quickly fly out of the sphere and closer to the wall. Bonogo fires an arrow at the flying monsters and gets a kill.[PC][Longmont Campaign/Campaign 2/PCs/bonogo/] Stafl gives a potion with Bless to Bonogo then also kills a flying creature with his crossbow.[PC][Longmont Campaign/Campaign 2/PCs/stafl/][PC][Longmont Campaign/Campaign 2/PCs/bonogo/] The golem moves closer to the wall, but due to its slow movement, takes cold and acid damage and remains inside the sphere of darkness.

Lysandra steps forward and uses her Commanding Shout and commands Karsemine, Bonogo and Baergrom to take another shot at the flying monsters.[NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/][PC][Longmont Campaign/Campaign 2/PCs/karsemine/][PC][Longmont Campaign/Campaign 2/PCs/bonogo/][PC][Longmont Campaign/Campaign 2/PCs/baergrom/] Karesmine and Bonogo both land hits, but Baergrom misses again.[PC][Longmont Campaign/Campaign 2/PCs/karsemine/][PC][Longmont Campaign/Campaign 2/PCs/bonogo/][PC][Longmont Campaign/Campaign 2/PCs/baergrom/] Caelynn, channeling magic, casts Snowball on a group of enemies, dealing cold damage to one of the tripod creatures and two more flying monsters.[PC][Longmont Campaign/Campaign 2/PCs/caelynn/] Finally, the disgusting meat hybrid creatures trudge forward, but not before taking cold damage from Ephanna’s spell.

Back on the wall, Karsemine uses her Hunter’s Mark on one of the tripod creatures, allowing her to learn its weaknesses and resistances.[PC][Longmont Campaign/Campaign 2/PCs/karsemine/] She discovers valuable information for her team - the creatures are resistant to poison, but weak to fire.[PC][Longmont Campaign/Campaign 2/PCs/karsemine/] With this new information she takes aim again with her bow, but misses the shot.[PC][Longmont Campaign/Campaign 2/PCs/karsemine/] Ephanna uses Eldritch Blast on two of the flying meatwings, killing both, then summons Ogonob who jumps over the wall and attacks the small summoned meat monster.[PC][Longmont Campaign/Campaign 2/PCs/ephanna/] After delivering a killing blow, it dashes father out away from the wall and closer to the approaching horde then, using Fey step, creates a cube of darkness around itself. Bonogo and Thrin both fire off arrows, but miss their targets.[PC][Longmont Campaign/Campaign 2/PCs/bonogo/][NPC][Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/] Baergorm fires his crossbow, hitting and killing one of the flying meatwings.[PC][Longmont Campaign/Campaign 2/PCs/baergrom/]

The giant sewer creatures both lumber closer to the wall, again taking damage from Ephanna’s spell. The equally giant tripod creatures move closer still, then again throw new meat monsters at the attackers on the wall. The first one falls short, hits the wall, then becomes a new flying meatwing. The second finds its target, hitting Caelynn directly in the face, dealing damage and creating another meatwing.[PC][Longmont Campaign/Campaign 2/PCs/caelynn/] The creature then flies up, ready to attack Caelynn again, but creates a perfect opportunity for Lysandra and Karsemine to strike.[PC][Longmont Campaign/Campaign 2/PCs/caelynn/][NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/][PC][Longmont Campaign/Campaign 2/PCs/karsemine/] Karsemine quickly lunges out as the first one flies by and kills it before it can attack.[PC][Longmont Campaign/Campaign 2/PCs/karsemine/] Lysandra, leaping off the half wall and making an incredible jump straight up, misses her attack, but follows through to kill the second monster with a swift slice.[NPC][Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/]

Meanwhile, the other six remaining meatwings from the horde move within range of the wall and begin to cast some sort of charm. Both Bonogo and Ephanna no longer feel compelled to attack the meatwings.[PC][Longmont Campaign/Campaign 2/PCs/bonogo/][PC][Longmont Campaign/Campaign 2/PCs/ephanna/] Stafl, seeing the incredible attacks from Karsemine, casts Bardic Inspiration on her, then casts Sleep on one of the tripod creatures.[PC][Longmont Campaign/Campaign 2/PCs/stafl/][PC][Longmont Campaign/Campaign 2/PCs/karsemine/] The lone golem continues its slow march toward the wall while taking additional cold damage.

Along the wall the heroes can feel magic and the static of electricity building. Caelynn, furious after the barrage of attacks, lines herself up and unleashes a devastating lightning bolt along the line of attackers, dealing massive damage to a group of meatwings, a meat hybrid and one of the tripods.[PC][Longmont Campaign/Campaign 2/PCs/caelynn/] Will this be enough to turn the tide of battle, or will Mireward Reach be overrun?