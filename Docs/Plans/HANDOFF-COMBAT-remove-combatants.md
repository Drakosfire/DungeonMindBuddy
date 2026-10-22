# COMBAT — remove a combatant from the recoverable encounter draft

ACTIVE. PRIME owns a serial slice from21e263b7ace1de519848be66a8220196034762c9,
branch codex/combat-remove-combatants, existing buddy-context-loop checkout.
Remote/open PR census found no overlapping implementation lease. The ordinary
Sheep rehearsal accepted a source-backed Noke statblock and association, but the
shared roster exposes no way to remove the earlier manual actor before using
that snapshot. Existing APP complete-draft Save already admits actor removal.

Invariant critique: removing one actor must not leave dangling turn/group refs,
advance the round, mutate surviving mechanics identities, erase add provenance,
or bypass recovery journaling/CAS. Offer Remove on the shared row: local draft
only until Save, recoverable by Revert before Save. On active removal choose the
next surviving undefeated actor in existing circular order, or null. Clear a
removed round-start pointer, preserve other pointers and round, normalize order,
remove that ID from groups and drop empty groups. Keep surviving group identity
and historical add provenance. Existing pending-Save/recovery/storage/World guards
apply through the single updateDraft boundary. No backend schema/API changes.

Exclusive lease: this handoff; predecessor HANDOFF-BUILD-answer-coverage.md and
Docs/Roadmaps/ROADMAP-demo.md settlement; shared Surface CombatRosterModule.tsx
and its tests; tests/application_state/test_combat_encounters_postgres.py
(existing complete-draft Save boundary only). No creature source/accepted
mechanics mutation, rules changes, automatic roster replacement, new cap or
compatibility path. Plan/Play both use this same component.

Acceptance: UI removal of active/inactive/final/defeated actors preserves valid
pointers/groups/round and remaining data; Revert and explicit recover restore the
proper versions; storage failure leaves the row; pending-save guards hold. Real
disposable APP accepts cleaned omission, rejects dangling refs/stale CAS and
reopens exact saved roster. Bugbot exact cumulative review; PRIME merge; guarded
UI rollout preserves APP and product bytes. Ordinary Sheep encounter replaces
manual roster entry explicitly with source-backed snapshot and reopens same
encounter/current Play scene. Full adventure roster/J1–J6 remain open.

Predecessor #1591 merged21e263b7a after Bugbot approvedd2f22330f,109 tests and103
unchanged historical normalization cases. Guarded API delivery retained1533 APP
rows/59 product files. Fresh source-grounded Sheep question completed with no
contradictory gap; one writer,10498ms trace capture, full reload retained answer.
Its lease is released. Ordinary manual Beat/three Scene creation, focused Agent
read-aloud edit, exact saved Plan→Play, refusal note and current-scene/partial
roster reload succeeded. Original Plan revision11/hash remained unchanged by
session notes and Combat. Agent structural creation did not create cards; that
capability remains open. Source-backed Noke acceptance/association is retained;
no whole-adventure or latency acceptance is awarded.
