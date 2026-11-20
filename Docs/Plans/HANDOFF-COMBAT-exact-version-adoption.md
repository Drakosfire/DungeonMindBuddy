# COMBAT — explicit exact mechanics adoption

## SETTLED serial implementation authority

PRIME's completed serial slice B under the operator-selected connected
scene/encounter/manual revision goal. Base/live
`a6684f1aedff28b46a32770dc32b08b60bfb5bae`, existing buddy-context-loop checkout,
branch `codex/combat-exact-version-adoption`. Fresh open-PR census found no competing
runtime lane. Architecture critique turn `01a16628-609a-72d1-9a6b-ee9763b45ad5`
is adopted, with the closures below. PRIME activates this exact lease after resolving
its stated design gaps; no operator permission gate remains.
One implementation PR, not a separate status/design PR; no new environment.

## Predecessor and owning boundaries

#1619 immutable manual revision Save and #1620 shared coherent maximum-HP editor
are merged/live. Real retained-tool UI proved original AC13/HP16, armor successor
AC16/HP16, then a validated immutable HP28 successor with matching3d8+15 formula,
old/new reopen, local edit reload recovery and post-Save protected restart. All
four encounters, both World associations and158 agent turns remained identical;
no AI call. Latest restart preserved1760 APP rows, all native rows,79 product files,
17 frozen components. Full Conks/Sheep connected acceptance remains open.

DMS owns immutable exact resources; no producer/API changes. Buddy owns explicit
actor selection, self-contained encounter snapshots and transactional adoption
receipts. APP0049/native0017/Core617635c/DMSf95e remain current until a reviewed
additive APP migration. No World association, source draft acceptance, Graph,
scene link, Plan/Run ownership or AI mutation in B.

## Proposed contract

- Start from a clean saved encounter, select one or more existing actor IDs and
  choose an exact saved mechanics version from the owned World draft. Existing
  actors must carry the same logical statblock/contract/ruleset. Preserve their
  names, source/World identities, team/order/initiative, turn/round/group membership,
  temp HP, conditions, notes and defeated status. Other actors/fights stay unchanged.
- Enumerate the existing metadata-only World/draft/version catalog. Preview uses
  original acceptance or committed revision proof from slice A and one exact DMS
  read, never latest/name matching or inherited acceptance of descendants.
- Introduce a versioned saved-mechanics snapshot with original acceptance anchor,
  optional successor revision receipt, exact locator/resource/digest. Retain old
  immutable snapshot readers. Ordinary generic encounter Save continues refusing
  snapshot replacement and cannot forge a new adopted actor/snapshot.
- Explicit per-actor tracker choices: keep AC or adopt the shown primary numeric
  AC; keep current/max HP, or adopt shown max plus preserve current HP, clamp it
  to the new maximum, or reset to full. Preserve temp HP in every choice. Explain
  that preserve may leave current HP above max. Clamp rejects descriptive/missing
  current HP; reset is an explicit heal. No fractional/implicit reconciliation.
  Defaults preserve all tracked values; show old/new values and affected actors.
- Command binds operation UUID, World/encounter, expected encounter revision,
  exact draft/version selection, actor IDs/base snapshot digests and policies.
  Server verifies exact mechanics before a short APP transaction; no external IO
  inside the transaction. Under operation-key lock, replay/body-conflict check and
  encounter CAS commit actor changes and a metadata receipt atomically. Store no
  duplicate full definition/encounter in the receipt. No partial multi-actor apply.
- Replay must inspect the receipt before DMS/Graph access. Acknowledgment contains
  receipt plus current encounter; later encounter revisions are explicitly reported
  and never replaced with an old result. Protect the original submitted body/key.
- Shared Combat component owns the same interaction on all surfaces. Require no
  dirty/pending/recoverable encounter save before adoption. Retain pending adoption
  by browser writer/World/encounter, block competing controls and fence late responses.
  Unknown outcome requires explicit same-key recovery, never automatic repost or
  absence-GET unlock. Define safe cancellation or a proven stale-CAS release before
  activation; an in-flight preflight must never commit after UI releases its intent.

## Expected write lease upon activation

This handoff; HANDOFF-STATBLOCK-hp-edit-consistency.md,
HANDOFF-COMBAT-scene-encounter-revision.md and Docs/Roadmaps/ROADMAP-demo.md settlement;
APP combat_encounters/types.py, service.py, new adoption.py; new additive migration
20261022_0050_combat_mechanics_adoption.py; existing server services/combat_mechanics.py,
services/statblock_saved_revision.py only for a public exact-source resolver,
routes/combat_encounters.py; UI combat/combatTypes.ts, combatApi.ts,
new CombatMechanicsAdoption.tsx and its test/recovery helper, shared
surface/modules/CombatRosterModule.tsx and its existing test; new
 tests/test_combat_mechanics_adoption.py and
 tests/application_state/test_combat_mechanics_adoption_postgres.py;
existing tests/test_combat_exact_world_mechanics.py/test_combat_direct_mechanics.py
if the new union requires affected assertions. No generated DTO/lockfile/old migration,
DMS, authoring, scene or unrelated routing edits. Amend before expanding.

## Verification and acceptance

Actual HTTP+APP/DMS boundary tests: exact source proof, same-family/type/ruleset and
World ownership, immutable originals, selected subset only, all tracker policies,
non-numeric and lower-max consequences, preservation of all other fields, generic
Save bypass rejection, stale/concurrent CAS, same-key changed intent, offline replay,
unknown/cancellation ordering and transaction rollback. UI tests: explicit preview
and chosen actors/policies, dirty-draft protection, exact pending recovery/remount,
late/foreign acknowledgment rejection and shared host continuity. Typecheck/build.
Independent exact cumulative Bugbot review then PRIME merge/protected rollout.
Ordinary retained mechanics encounter: adopt HP28 successor for one actor, preserve
sibling/other fight, run meaningful tracker changes, reload/restart/reopen exact
snapshot with DMS unavailable read proof where practical. Full connected Conks first,
Sheep generality, J1–J6 twice and all remaining goal acceptance stay open.

## Adopted critique closures

Distinct saved-revision snapshot origin, exact World/draft/original anchor and
append-only per-actor before/after snapshot digest transitions. Associated actors
must match their historical exact association receipt/target, not a mutable current
slot; Graph-head advancement alone does not rewrite/invalidate historical identity.
No same-name selection, no incompatible/manual actor widening. All selected actors
must qualify or the complete command is refused.

One additive APP terminal operation table stores applied/canceled metadata receipts.
Cancel receives the exact original request and hashes the same scope/body; under
operation-key lock it returns applied if commit won, otherwise inserts a canceled
fence. Later preflights observe the fence before CAS. Applied/canceled replay and
operation-ID receipt reads precede DMS lookup; a same-key changed body conflicts.
Receipt includes committed revision, exact target locator, per-actor old/new snapshot
digests, explicit policies and before/after tracker values. Response separates
current encounter revision and an advanced-since-apply flag. No historical restore.

Primary AC is the typed default profile, else first profile; missing numeric value
refuses AC adoption only. HP max is typed fixed_value or producer-rounded typed dice
average, never parsed from prose. Preserve keeps null/descriptive HP; clamp requires
integer current HP and uses min(current,new_max); reset leaves defeated/temp HP/
conditions untouched and preview warns about a defeated actor at full HP. Existing
700KiB full-draft validation remains the fan-out guard; refusal is atomic. Add large
resource multi-actor overflow regression. No new character/token/history cap.

UI pending body/key is retained per browser-writer/World/encounter before dispatch;
explicit Retry/Cancel use that exact intent. Only verified applied/canceled receipt
unlocks; no missing GET inference. Existing dirty drafts/recovery are never cleared
to enter adoption. Source/version editor can be opened from the shared adoption
panel; it remains separate from explicit adoption and retains its local drafts.
Lease amendment: new UI CombatMechanicsAdoptionRecovery.ts helper/test if needed;
new APP adoption_types.py for closed request/receipt models; historical association
lookup lives read-only inside new adoption service, no association writer change.

Lease amendment before edit: scripts/generate_combat_recovery_schema.py and generated
UI combat/combatRecoverySchema.json must include the new snapshot resource in the
existing strict owner-derived recovery schema; tests/test_combat_recovery_schema.py
remains the parity gate. This is a current contract update, not a compatibility path.
Architecture's closure response is adopted: historical association predecessor chain
is checked, operation UUID globally unique, Cancel never means rollback. Required
race witnesses cover paused preflight/cancel and commit-before-cancel, separate
transaction same/different-key contention, and historical slot advancement.

Proof reads are operation-local and deduplicated: one exact producer read for a
selected version regardless of actor count; shared historical association rows and
saved-revision proofs are reused within the short APP transaction. Every actor's
individual target/locator/digest checks still run. Replay uses zero producer reads.

## Consuming settlement — #1621

Reviewed head `6bd4641aae344f670d7ae0d335eb19f9b21f2c85`, one independent Bugbot
cycle, merged/live `0cea62670164ded25646d0686693022b851ad220`, APP0050. The runtime
write lease is released. Independent verification covered31 backend/schema and48
mounted UI/recovery tests. Ordinary retained synthetic UI adopted AC16/HP28 for one
actor while preserving HP10/temp7/Prone/note and its sibling. Subsequent turns saved
first HP12, second HP11/current, revision4; protected API restart and ordinary
reload reopened that exact state. Other encounters, associations, revision proofs
and agent turns remained unchanged. No AI call. Full scene ownership/Conks/Sheep
acceptance remains open; the consuming contract is HANDOFF-COMBAT-scene-template.md.
