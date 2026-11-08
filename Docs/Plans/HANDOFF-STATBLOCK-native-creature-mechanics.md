# STATBLOCK: native creature mechanics selection

ACTIVE under the operator's References/statblock goal and PRIME design authority.
Branch codex/native-creature-mechanics from66a89f06ca3c43d876fce516cee07b0fd4463522;
reuse buddy-context-loop. Source is parallel-independent of ADVERSARY2239 (no
shared write paths); delivery is serial after its qualified reader-fence delivery.
No live mutation during implementation. Existing Play2172/2104 holds remain;
this changes creature/mechanics selection, not Play retrieval or execution.

Outcome: one native Core read view supplies existing creature selection and
verification for World mechanics association and encounter assembly. Replace the
classic managed projection at these callers; no new Graph store or admission
policy. Core admits assertions; Buddy's consumer recognizes the existing supported
NPC classification as actor eligibility and retains exact name/identity witnesses.
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
test_combat_world_identity.py, test_native_world_creature_selection.py;
UI statblocks/WorldMechanicsAssociationPanel.test.tsx,
combat/CombatEncounterAssembly.test.tsx, api/worldMechanicsApi.test.ts;
.github/workflows/world-ownership-core.yml only to include the new owning test.
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
