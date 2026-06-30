# Session 24 Projection Question Review Stub

## q:s24-opening-state

Question: What is the exact situation as Session 25 opens?

Required nodes: thread_refugee_plan, thread_short_rest_watch, loc_north_gate, threat_meat_goo_ground_sink, npc_grobnok
Expected evidence refs: evidence:s24-hybrid-friendly-fire-coordinated-tripod-kill, evidence:s24-meat-piles-goo-refugee-rest-plan, evidence:s24-caelynn-grobnok-rockie-talkie
Must include: Immediate battle ended; Full night has fallen; Ephanna/Stafl/Baergrom are at the wall above the gate for watch and short rest; Others are checking town and planning for Edge refugees; Meat piles turned to goo and sank underground; Grobnok callback and Lysandra rockie-talkie link are pending
Must not claim: long_rest_complete; refugees_resolved; goo_destroyed; grobnok_lysandra_link_complete
Fixture graph supports it: yes
Manual reviewer notes: TODO

## q:s24-refugee-problem

Question: What do I need to remember about the Edge refugees before I roleplay the next scene?

Required nodes: group_edge_refugees, thread_refugee_plan, loc_edge
Expected evidence refs: evidence:s24-meat-piles-goo-refugee-rest-plan, evidence:s24-caelynn-grobnok-rockie-talkie
Must include: The refugees from Edge still need a plan; Screening, housing, admission, safety, and taint status are unresolved; Edge remains connected to the crisis
Must not claim: refugees_safe; refugees_tainted; refugees_housed; refugees_admitted; refugees_rejected
Fixture graph supports it: yes
Manual reviewer notes: TODO

## q:s24-wall-risk

Question: Is the north wall damaged, and what caused it?

Required nodes: status_north_wall_damage, loc_north_wall, threat_meat_hybrids, threat_golem_like_creature, threat_giant_sewer_monsters
Expected evidence refs: evidence:s24-stafl-golem-commanding-shout-caelynn-cleanse, evidence:s24-wall-damage-golem-fire-weakness, evidence:s24-sewer-wall-sticky-gel-baergrom-bonogo-kill
Must include: A hybrid reached the wall and chipped away the foundation; The golem dashed to the wall ready to break it down; A sewer monster climbed onto the wall; Structural integrity remains unresolved
Must not claim: wall_collapsed; wall_breached; wall_safe; wall_repaired
Fixture graph supports it: yes
Manual reviewer notes: TODO

## q:s24-meat-goo

Question: What happened when they tried to burn the remains?

Required nodes: threat_meat_goo_ground_sink, loc_battlefield_outside_gate
Expected evidence refs: evidence:s24-meat-piles-goo-refugee-rest-plan
Must include: Karsemine and Ephanna try to burn remaining meat piles; Firebolt/Bonfire cause piles to turn to goo and get sucked underground; This remains an unresolved threat or hook
Must not claim: goo_destroyed; goo_purified; threat_solved
Fixture graph supports it: yes
Manual reviewer notes: TODO

## q:s24-monster-mechanics

Question: What monster mechanics have been revealed that I should carry forward?

Required nodes: threat_tripod_meat_monsters, threat_flying_meatwings, threat_meat_hybrids, threat_golem_like_creature, threat_giant_sewer_monsters
Expected evidence refs: evidence:s24-hybrid-ogonob-firebolt-first-charm, evidence:s24-tripod-wakes-wide-meatwing-charm, evidence:s24-wall-damage-golem-fire-weakness, evidence:s24-sewer-wall-sticky-gel-baergrom-bonogo-kill, evidence:s24-ephanna-impaled-tripod-sleep-final-assault-setup
Must include: Tripods have ignitable gases/flesh and can impale/pull with launched spikes; Meatwings compel targets toward consuming monsters and can prevent direct attacks; Hybrids can attack and damage the wall/foundation; Golem is immune to poison/charm and weak to fire; Sewer monsters climb walls, ooze sticky gel, and can spray poison on death
Must not claim: unseen_monster_abilities; exact_statblock; exact_cr
Fixture graph supports it: yes
Manual reviewer notes: TODO

## q:s24-chip-caelynn

Question: When I click Caelynn, what should the projection show?

Required nodes: pc_caelynn, npc_lysandra_ironveil, npc_grobnok, thread_rockie_talkie_bridge, threat_flying_meatwings
Expected evidence refs: evidence:s24-stafl-golem-commanding-shout-caelynn-cleanse, evidence:s24-hybrid-friendly-fire-coordinated-tripod-kill, evidence:s24-caelynn-grobnok-rockie-talkie
Must include: Charmed then cleansed by Lysandra; Magic Missile against meatwings and final tripod attack; Caelynn called Grobnok about Edge and Mireward Reach; Adjacency to Lysandra, Grobnok, rockie-talkie bridge, Edge, Mireward Reach, meatwings, and final tripod event
Must not claim: session_local_identity_as_final_architecture; rockie_link_complete
Fixture graph supports it: yes
Manual reviewer notes: TODO

## q:s24-chip-refugees

Question: When I click Edge refugees, what should I see?

Required nodes: group_edge_refugees, thread_refugee_plan, loc_edge
Expected evidence refs: evidence:s24-meat-piles-goo-refugee-rest-plan
Must include: Session 24 evidence that something needs to be done with refugees from Edge; Unresolved status for screening, housing, admission, and taint; Adjacency to Edge and town/refugee planning team
Must not claim: refugees_safe; refugees_tainted; refugees_admitted
Fixture graph supports it: yes
Manual reviewer notes: TODO

## q:s24-chip-goo

Question: When I click meat goo sinking underground, what should I see?

Required nodes: threat_meat_goo_ground_sink, loc_battlefield_outside_gate
Expected evidence refs: evidence:s24-meat-piles-goo-refugee-rest-plan
Must include: Attempted burning caused meat piles to turn to goo and get sucked underground; This is unresolved; Adjacency to battlefield, Karsemine, Ephanna, and future investigation
Must not claim: goo_destroyed; goo_purified; destination_known
Fixture graph supports it: yes
Manual reviewer notes: TODO

## q:s24-chip-wall

Question: When I click the north wall, what should I see?

Required nodes: loc_north_wall, status_north_wall_damage, threat_meat_hybrids, threat_golem_like_creature, threat_giant_sewer_monsters, thread_short_rest_watch
Expected evidence refs: evidence:s24-stafl-golem-commanding-shout-caelynn-cleanse, evidence:s24-wall-damage-golem-fire-weakness, evidence:s24-sewer-wall-sticky-gel-baergrom-bonogo-kill, evidence:s24-meat-piles-goo-refugee-rest-plan
Must include: Hybrid foundation damage; Golem wall-breaking pressure; Sewer monster climbed onto wall and sticky gel made movement difficult; Watch/rest team remains above the gate; Structural integrity unresolved
Must not claim: wall_breached; wall_collapsed; wall_safe
Fixture graph supports it: yes
Manual reviewer notes: TODO

## q:s24-high-risk

Question: Which graph items should be high-risk or frictioned before approval?

Required nodes: status_north_wall_damage, thread_refugee_plan, threat_meat_goo_ground_sink, thread_edge_status, thread_rockie_talkie_bridge
Expected evidence refs: evidence:s24-wall-damage-golem-fire-weakness, evidence:s24-meat-piles-goo-refugee-rest-plan, evidence:s24-caelynn-grobnok-rockie-talkie
Must include: Wall safety/structural integrity; Refugee screening/admission/housing; Meat goo destination and consequence; Exact Edge status; Grobnok-Lysandra link completion; Exact resources/HP/slot state
Must not claim: bulk_approve_safe; these_are_canon
Fixture graph supports it: yes
Manual reviewer notes: TODO

## q:s24-proposed-writes

Question: What proposed writes would this preview generate?

Required nodes: thread_refugee_plan, threat_meat_goo_ground_sink, status_north_wall_damage, thread_grobnok_callback
Expected evidence refs: evidence:s24-hybrid-friendly-fire-coordinated-tripod-kill, evidence:s24-meat-piles-goo-refugee-rest-plan, evidence:s24-caelynn-grobnok-rockie-talkie
Must include: Pending battle resolution write; Pending monster mechanics updates; Pending unresolved hooks for meat goo, wall damage, refugees, Edge status, Grobnok callback, and rockie-talkie bridge; All proposed writes remain pending manual review
Must not claim: approved_writes; canon_promotion; corpus_mutation
Fixture graph supports it: yes
Manual reviewer notes: TODO

## q:s24-adjacent-session-need

Question: Which Session 23 facts should the projection pull in to make Session 24 make sense?

Required nodes: group_edge_refugees, loc_edge, loc_north_gate, threat_tripod_meat_monsters, threat_flying_meatwings, threat_golem_like_creature, threat_giant_sewer_monsters, npc_lysandra_ironveil
Expected evidence refs: None
Must include: Only focused prior context needed for continuity: Edge refugees/refugee origin, north gate setup, enemy wave identities, and Lysandra/Mireward context; Avoid broad Session 23 recap flooding
Must not claim: session_23_full_summary_required; unbounded_prior_session_dump
Fixture graph supports it: yes
Manual reviewer notes: TODO

## q:s24-clean-control

Question: What happened with Baergrom's crossbow?

Required nodes: pc_baergrom
Expected evidence refs: evidence:s24-bonogo-panic-sewer-split-baergrom-jam
Must include: Baergrom readies his crossbow, it jams, he throws it down, grabs a short bow, loads an arrow, and shoots the hybrid in the head
Must not claim: unrelated_baergrom_backstory; weapon_permanently_destroyed
Fixture graph supports it: yes
Manual reviewer notes: TODO

## q:s24-unsafe-exact-counts

Question: How many meatwings were left at the end?

Required nodes: threat_flying_meatwings
Expected evidence refs: evidence:s24-tripod-wakes-wide-meatwing-charm, evidence:s24-stafl-golem-commanding-shout-caelynn-cleanse, evidence:s24-wall-damage-golem-fire-weakness
Must include: The source does not preserve a reliable exact final meatwing count; The immediate battle ends, but exact remaining meatwing count should not be fabricated
Must not claim: exact_final_meatwing_count
Fixture graph supports it: yes
Manual reviewer notes: TODO

## q:s24-unsafe-refugee-taint

Question: Are the refugees definitely tainted by the meat horror?

Required nodes: group_edge_refugees, thread_refugee_plan
Expected evidence refs: evidence:s24-meat-piles-goo-refugee-rest-plan
Must include: The recap does not resolve the refugees' taint or screening status; Treat it as a pending triage risk, not a fact
Must not claim: refugees_definitely_tainted; refugees_definitely_clear
Fixture graph supports it: yes
Manual reviewer notes: TODO

## q:s24-unsafe-grobnok-link

Question: Can Grobnok now talk directly to Lysandra?

Required nodes: thread_rockie_talkie_bridge, npc_grobnok, npc_lysandra_ironveil
Expected evidence refs: evidence:s24-caelynn-grobnok-rockie-talkie
Must include: Caelynn attempts to connect Grobnok's rockie-talkie with Lysandra’s; The recap says this will take some time; The direct link is not complete in the source
Must not claim: link_complete; grobnok_can_now_talk_to_lysandra
Fixture graph supports it: yes
Manual reviewer notes: TODO

## q:s24-unsafe-goo-destroyed

Question: Did burning the meat piles solve the goo problem?

Required nodes: threat_meat_goo_ground_sink
Expected evidence refs: evidence:s24-meat-piles-goo-refugee-rest-plan
Must include: No. The attempted burning caused the piles to turn to goo and sink underground; This creates or preserves an unresolved risk rather than solving it
Must not claim: burning_solved_problem; goo_destroyed; goo_purified
Fixture graph supports it: yes
Manual reviewer notes: TODO
