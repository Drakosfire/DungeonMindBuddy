# COMBAT — side-based turn pacing

ACTIVE under the operator's Combat design/implementation/review/accepted-merge
and local-delivery assignment. Root owns this bounded design. Serial successor
to #4008, merged83013db27115007435b586cf657c39119a47b60a. Base is that exact fetched
main; branch codex/combat-side-turns in the existing isolated fc67 checkout. No
unmerged parent and no other open Combat implementation PR. Spotlight pacing and
real-runtime delivery remain required successors; this slice is not goal completion.

## Outcome and boundary

Choose side-based pacing when creating a manual profile, assign participants to
named sides, choose who acts within the active side, mark a participant's turn
finished, and explicitly pass to another side. Ordered/optional-round encounters
retain their exact persisted shapes and behavior. This is one vertical capability:
profile validation, reference safety, initialization, rendering and recovery must
agree before persisted side turns are exposed. No automatic action economy,
initiative rolls, damage interpretation, profile conversion or canon mutation.

This lane exclusively expects writes to:
- APP combat_encounters/{manual_profiles,manual_encounters}.py;
  play/session_encounters.py for existing manual initialization; new migration
  migrations/versions/20261118_0164_side_combat_pacing.py.
- Client combat/{ManualCombatTypes,ManualCombatState,validateCombatRecovery}.ts;
  ManualCombatProfileForm.tsx, ManualCombatEditor.tsx, ManualCombatRosterTable.tsx;
  a new ManualCombatSides.tsx within combat; combatRoster.css; generated
  combatRecoverySchema.json and its existing generator only if required.
- Existing owning manual profile/record/persistence/HTTP/recovery/editor/Plan/Play
  tests, new focused side state/component tests, relevant cross-language fixtures,
  ci/contracts.json and ci/test-classification.json for actual owning coverage.
- This handoff and truthful predecessor settlement in
  HANDOFF-COMBAT-manual-profile.md. If an owning API/access/session-preview file
  must change, explicitly amend this bounded contract before editing it.

Legacy v1 DTOs/rulesets/serialization, hosted authorization routes, main.py, provider
producers (including open #3668 combat_mechanics.py), shared routing/lockfiles and
operator runtime/data remain read-only. Existing public route paths stay unchanged.

## Design and failure critique

Manual profile pacing adds a discriminated `side` variant with no required round
counter. Persist a `side` turn with active_side_id, active_actor_id and unique
acted_actor_ids. The last list records only this side's current phase, not a rules
engine or a global action budget. The UI calls it "Took a turn"; the GM may
explicitly choose "Act again". Never derive participation or turn eligibility
from a resource label, zero, a status or source statblock.

- Active side must reference this encounter; active actor must be in action and
  belong to that side. With no active side, actor/acted references are empty.
  Acted references must be unique, existing and assigned to the active side;
  an out-of-action actor may retain its marker until the side is explicitly passed.
- Start selects the first named side. Pass cycles the stable side list, clears
  active actor and phase markers, and does not skip empty sides implicitly. An
  empty side remains visible with an explanation and explicit Pass control.
  A direct side selection is also explicit and resets phase markers. No rounds
  are inferred from cycling back to the first side.
- Choose an in-action actor on this side to act; Finish marks it and clears the
  actor selection. Choosing an actor already marked is explicit Act again and
  clears its prior marker. Stable roster order is presentation within the side,
  not initiative. UI makes the difference from ordered pacing clear.
- Defeat/out-of-action clears an active actor without advancing the side or
  healing anyone; return does not grant a fresh marker. Moving an actor to another
  side clears its old active/acted references atomically. Removing an actor prunes
  references/groups. Removing the active side unassigns its members and resets
  side turn selection rather than silently choosing another side.
- Sides are independent of collapsible display groups. Current actor remains
  visible through a collapsed group; source projection follows actor identity.
  Unassigned participants keep all their data and can be assigned explicitly.
- Immutable profile mode must match turn kind at APP and recovery boundaries.
  Save cannot replace the pinned mode. Template capture preserves preparation;
  materialization mints fresh side/actor/group IDs, remaps memberships and resets
  active side/actor/phase markers. Existing ordered/v1 initialization is unchanged.
- Exact pending Save retry, retained later edits, bounded JSON/profile storage,
  World/run/principal/CAS, source immutability and unknown recovery refusal stay
  with their existing owners. No second draft owner or alternate persistence path.

## Migration and runtime sequencing

Main's sole head after #4008 is0163. Audit of current published assignments and
open PR metadata found no0164 reservation; PRIME was explicitly notified of the
next reader fence and asked to flag any existing collision. Root adopts0164 after
0163 within this bounded Combat assignment; no reply or elapsed-time approval is
claimed. Re-anchor before editing/merging and resolve any actual overlapping lease.
The new fence admits new pacing readers without rewriting old records or widening
existing JSONB byte limits. Follow existing forward-recovery fences; do not
silently downgrade to a reader that cannot decode persisted side profiles/history.
Never renumber an applied operator migration or migrate operator/live stores.

Shared API8001/UI5202 and preview5218 remain untouched. Prior rehearsal8018/5219
is stopped; check exclusive availability before reuse. The task-owned PostgreSQL
container buddy-combat-manual-fc67 at loopback33073 remains available with unique
disposable template/clones only. External scratch/evidence stays under the verified
Projects UUID48fa5d10-fe99-4557-9fc9-d8a2a4b41ac8 and shared frontend resource lock.

## Validation and completion

Pure profile/record/state tests must prove matching mode, invalid/stale side and
acted references, no duplicate markers, empty side pass, defeat/return, assignment
changes and removal, exact ordered/v1 controls and canonical preimages. Actual
APP/HTTP/PostgreSQL tests must prove create/cold Save/CAS/rollback and Plan capture
→ materialization/remapping → live Save/reopen/isolation with source retained.
Client boundary tests must exercise semantic recovery, pending Save and later
edits, side management, groups and projection in the shared hosts. Run repository
exact-SHA backend and hosted/discovered frontend standards with honest exact-base
failure/case/message comparison; independent exact-head review precedes merge.

Browser acceptance must use actual routes/APP disposable DBs, synthetic providers
clearly identified, and exact source: non-D&D side encounter, at least three sides
including empty/unassigned units, crowded groups, arbitrary action selection,
explicit Act again/Finish/Pass, defeat/return without marker reset, field/status/
note changes, source projection, Save/reload/recovery and Plan/Play separation at
wide/narrow sizes. A focused route harness is valid boundary evidence but does not
replace the full goal's real product startup/local delivery acceptance.
