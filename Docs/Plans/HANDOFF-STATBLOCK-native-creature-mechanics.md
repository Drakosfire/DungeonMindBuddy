# STATBLOCK: native creature mechanics selection

ACTIVE under the operator's References/statblock goal and PRIME design authority.
Branch codex/native-creature-mechanics from7bbdaa98dc8dbd73c1573a4a457c818d29d9a859;
reuse buddy-context-loop. Source is parallel-independent of ADVERSARY2239 (no
shared write paths); delivery is serial;2239 is merged7bbdaa98 and delivered APIe4ca114/schema133.
No live mutation during implementation. Existing Play2172/2104 holds remain;
this changes creature/mechanics selection, not Play retrieval or execution.

Outcome: one native Core read view supplies existing creature selection and
verification for World mechanics association and encounter assembly. Replace the
classic managed projection at these callers; no new Graph store or admission
policy. Core admits assertions; Buddy's consumer recognizes the current published character/creature and authored
NPC classifications as actor eligibility and retains exact name/identity witnesses.
Do not invent a threat classification, infer kind from names, relabel the new ooze,
or publish any new facts in this slice. Native threat publication and explicit
successor-version association remain separate goal requirements.

The view reads a pinned native revision through the existing shared read context.
Only Core-admitted classification/name assertions build choices. Expose partial
coverage honestly; missing unrelated records do not invalidate an admitted choice.
New association/preview still requires the observed head, exact selected fields,
current World binding, draft CAS, accepted mechanics proof and exact DMS bytes.
Encounter Save independently verifies new identities from their pinned revision.
Existing saved actors remain offline and unchanged. Same-key association replay
returns the original record before external reads. No schema/data rewrite, provider
calls, ingestion, publication or new provenance/compatibility authority.

Expected writes: this handoff and predecessor HANDOFF-STATBLOCK-shared-edit-host.md;
services/world_creature_selection.py, world_mechanics_associations.py,
combat_mechanics.py, combat_encounters.py; routes/world_mechanics_associations.py;
UI api/worldMechanicsTypes.ts, api/liveApi.ts,
statblocks/WorldMechanicsAssociationPanel.tsx, combat/CombatEncounterAssembly.tsx;
owning tests test_world_mechanics_associations.py, test_combat_exact_world_mechanics.py,
test_live_combat_encounters.py, test_combat_direct_mechanics.py, test_native_world_creature_selection.py;
UI statblocks/WorldMechanicsAssociationPanel.test.tsx,
combat/CombatEncounterAssembly.test.tsx, api/worldMechanicsApi.test.ts;
.github/workflows/world-ownership-core.yml to lint the new test and exercise the affected native/HTTP boundary suite.
Stop/split if another capability or contract is required. No App/guest/LocalWorld,
writer/evaluator, migration133 or ADVERSARY source lease edits.

Verify actual Core/WK fixture admission, unsupported/missing classification,
name ambiguity, partial coverage, binding/head changes and foreign pins. Preserve
HTTP append/replay/conflict and real APP CAS tests, offline actor conservation,
exact DMS tamper refusal, UI retained requests/stale reads and both consumers.
Run TypeScript/build, cumulative independent review and CI. Deliver through a
separate guarded API/UI integration after owning gates; preserve old failures.

Predecessor2238 merged66a89f06 and delivered UI91d9eb62e. All265 owner tests,
source/integration/recipe reviews and7CI passed. Served native Chrome proves the
same editor and unsent portrait prompt survive Toolbox/full-reader/Back. API8008,
schema131 and retained state were conserved. The real Corrupted Edge ooze draft
5685d7a8-2728-4e5f-be7b-7f376829551e now has saved DMS mechanics and generated
portrait successor rev_dda9582a88ad4724997306791736975b. That is not yet a native
Graph threat, and no completed-node/conversation-integration claim is made.

Discovery checkpoint: the anticipated identity suite is test_live_combat_encounters; direct-mechanics also exercises the same optional native identity. Their fixture-only updates remain this one boundary replacement. No adoption/Run mechanics behavior is changed.

Retained-data checkpoint: initial single dnd5e:npc eligibility produced zero choices despite1403entities/6100admitted assertions. Current recap publication uses dungeonbuddy:character and dungeonbuddy:creature; authored declarations also support dnd5e:npc. The consumer now admits those three exact classes, with actual Core fixtures for all three. No name inference, classification rewriting or new semantic profile is required. Retain the failed probe and counts.

Implementation validation:83 backend cases and42 UI/API cases pass; TypeScript/production build and new-code lint pass. Actual retained Elderwyld read yields132 selectable actors (119characters,13creatures), with current C1/C2/shared witnesses and exact selection verification. This is an unserved candidate read, not a deployment/association claim. Initial fixture/auth/status mismatches and the zero-choice mapping probe are retained. Source code implements no new Graph writes or mechanics-version contract. Independent review/CI and guarded delivery remain pending.
