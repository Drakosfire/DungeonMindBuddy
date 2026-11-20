# COMBAT — exact associated World mechanics snapshots

SETTLED. #1583 merged3f3f608650f23ba4746777fde2e4bc671db18478 and runs8000/5202.
Bugbot approvedc3ab93fc0 after fixing complete draft-capacity preflight; independently
54backend/32UI/API tests passed. Real UI created encounter06be700f-58ac-4a40-98b4-418e9ed28c14,
loaded exact associated mechanics, added two actors, applied independent HP7/16,
Prone/notes and active turn, saved and reopened after API restart. Full encounter
state equal; all1489APP rows/59product files preserved. Native head and exact
DMS identity unchanged. Shared Plan/Play hosting/recovery is the successor.

Historical scope: Architecture reviewed the contract2026-10-22; PRIME owned serial implementation.
Base b5fc320c9cad2e8958499b8419404e3323c39c81; existing buddy-context-loop checkout,
branch codex/combat-exact-world-mechanics. No competing open PR owns these paths.
Strict Graph-head equality is intentional: even unrelated head advance requires explicit
re-association before new adoption. Graph may advance after verification; this is
historical verification, not cross-service atomic currentness. Preview is read-only
and carries a digest over the complete snapshot including World/node/association identity.
Save persists only server-verified snapshots; any invalid slot refuses the whole save.
Existing snapshot reopening works with DMS/Graph unavailable.

One capability: explicitly attach proven accepted mechanics to a new World-linked
Combat actor as an immutable encounter-owned snapshot. Operational Combat and
Plan/Play embedding remain successors; no new environment or Graph writes.

Predecessor #1582 merged b5fc320c9 and runs API8000/UI5202 after Bugbot approval
of b74583cd7 (12 UI/API and19 backend tests). Ordinary Build associated accepted
Blue Lantern Keeper mechanics with existing Lantern Keeper NPC in the synthetic
receipt-continuity-rehearsal World. One APP receipt appended; Graph head and exact
DMS identity unchanged. API restart preserved1488 APP rows and59 product files;
normal Tools/history→Load creatures reopened saved association version1.

Explicit Combat preview loads one selected current association, checks managed/native
binding/version, current Graph head/node against its historical witness, and exact
DMS resource identity/integrity. Snapshot stores association UUID/version, six-field
locator and complete exact revision resource. Retain canonical text and validation
receipt; normalize resource.definition from parsed canonical text. APP validates
canonical text SHA256 and equality with stored definition, locator/resource/receipt
identity without importing runtime. Shared StatblockRenderer reads saved resource.

New-actor Save independently verifies preview contents, deduplicating reads across
copies by association. APP takes sorted World/node slot advisory locks, rechecks
current association UUID/version and exact World target, and then existing encounter
CAS. Existing actor snapshot/source identity is immutable; later saved encounter
read/edit/reopen does not refresh external mechanics. Per-copy tracker fields are
independent. Generic manual-tracking retains manual/null AC/HP; no D&D projection.
Selection/World/encounter changes invalidate late previews. New preview is explicit;
no per-keystroke/repeated-per-copy Graph or DMS reads. The host checks the complete proposed UTF-8 draft against the existing700KiB
capacity before appending snapshots; refusal preserves both prior edits and assembly
inputs. Actor count and draft byte bounds remain existing constraints; add no arbitrary new caps or compatibility path.

Exclusive expected writes: this handoff; predecessor association handoff and
Docs/Roadmaps/ROADMAP-demo.md; src/application_state/combat_encounters/{types,service}.py;
world_mechanics/service.py current-slot transaction verifier; new HTTP service
combat_mechanics.py, routes/combat_encounters.py, services/combat_encounters.py;
UI combat/{combatTypes,combatApi,CombatEncounterAssembly}.ts(x), new CombatMechanicsInspection.tsx, shared roster module
and existing statblock renderer integration; owning UI/API/HTTP/PostgreSQL tests.
No schema migration, new store, provider generation, ruleset expansion, Play writer,
accepted-ref mutation, latest lookup or old unresolved journal repair.

Verify exact preview→Save→APP persistence and snapshot tamper/foreign/stale/missing
association/head/mapping/node, slot replacement race, immutable prior identity,
manual-only compatibility, duplicate-copy read counts, late UI response/selection
ABA, no implicit stats, draft/reload/restart preservation and shared inspection.
Bugbot exact cumulative review→PRIME merge→guarded delivery on8000/5202. Actual UI
World select→load exact mechanics→multiple copies→save→reload→API restart→inspection;
prior APP rows/product files/Graph heads preserved. No full C2/J1–J6 acceptance claim.
