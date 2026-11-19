# COMBAT — arrange participants without initiative

MERGED as #3984 at `c67f8b8a50c5d7aab63dd983d5bf75d859710c54`; source lease
released to HANDOFF-COMBAT-profile-validation.md. Reviewed repaired head
`699749676c07ee568915f6e8a67aa83e7849fa1c` has independent code/evidence acceptance.
All41 focused checks/typecheck passed. Exact hosted1,408 selected passes/0 failures,
build/parity/validator passed. Discovered7,917/160/2 versus base7,915/160/2: two new
passes, no missing cases or new failed IDs. Paired Work Plans diagnostics resolve
the failure-depth ambiguity. All remaining failures match baseline statements and
source frames. Full discovered qualification/extra-skip parity stays red. Browser
keyboard/source/staged-input/Save/reopen proof is synthetic, not real DB readiness.

Original authority: under the operator's full Combat implementation/review/accepted-merge
authority. Serial successor to #3981, merged
`5711085fd69913111db7925027ccdede1b1e694a`; base that fetched main SHA, branch
`codex/combat-manual-order`, same isolated fc67 checkout. No unmerged parent.
One open implementation PR for this workstream. #3668 owns only mechanics
minimums/adoption work; Build and cleanup consumers do not own this write set.

Outcome: keyboard-accessible Earlier/Later commands move an in-action participant
in canonical saved order without requiring numeric initiative. Swap with the
adjacent in-action participant, leave defeated slots intact, and normalize order
values. First/last commands disable at their bounds. Defeated rows must explicitly
return to action before rearrangement. Initiative sorting remains explicit.

Exclusive writes: this handoff; truthful predecessor settlement in
HANDOFF-COMBAT-persistent-statblock.md; shared CombatRosterModule.tsx and its
existing test; combatRoster.css if needed for the small move controls. No API,
backend, schema, migration, profile, source producer, host registry or root config
writes. Existing shared API8001/UI5202/immutable5218 remain untouched; disposable
acceptance ports5217/5219 require fresh ownership checks and the global test lock.

Invariants: moving preserves current actor, round anchor and number by identity;
never heals, changes participation, source, group membership, notes or statuses.
Noncontiguous groups remain segmented instead of relocating other members. Stable
row keys preserve staged adjustments and projected source. Edits use the existing
guarded updateDraft/recovery/Save owner; replacement, adoption and unresolved
recovery disable these controls. Save acknowledgements do not erase later moves.

Validation: mounted movement/boundary/disabled tests, current/next and round-wrap
checks, source/group/value preservation, staged inputs and projection, exact Save,
Revert and explicit recovery. Browser keyboard activation and persisted reopen.
Run focused/type/inventory checks and required exact-head hosted/discovered suites
with exact-base comparison, cumulative review and independent Bugbot judgment.
Keep inherited qualification failures red. No live encounter changes.

This ordered-pacing capability does not complete configurable non-D&D profiles,
resources, sides/spotlight, real-runtime Graph integration or final acceptance.
Profile migration still respects open #3877 (its #3875 prerequisite has merged).
Task evidence/designs: `/home/drakosfire/Projects/.codex/buddy-check.LPopRI`.

## Verification checkpoint and owning test repair

Initial candidate `4444b478c49f0234593f401b23fe414573e2c111` passed 41 focused
tests, full TypeScript, inventory, and exact-head code review. Disposable browser
keyboard Enter moved the active actor while preserving round, projected source
and staged damage; Save revision11/reopen retained the new order and next actor.
Both fixture services stopped; no shared runtime or live-record changes.

Its exact hosted suite passed all 1,408 selected tests, build/parity and validator.
Full discovered reported 7,916/161/2 versus exact base
`5711085fd69913111db7925027ccdede1b1e694a` at 7,915/160/2. The two new cases pass
and no occurrences are missing, but one existing owning adoption test newly fails:
it asserted parent unlock immediately after finding a child success message.
The lock release arrives through the child's effect. Independent audit requires
waiting for actual control readiness, preserving all value/revision/source checks.
The repaired case includes a second actor and verifies move controls are disabled
during adoption and eventually enabled afterward. Product locking is unchanged.

The old-head evidence remains HOLD and retained. Repaired exact-head checks and
review are required. A Work Plans failure also reached a different statement on
base/head; pair its unchanged owning file before classifying that cause as
inherited. Full discovered qualification remains red. Evidence pointers use
`order-*-evidence-path`; do not relabel the old head as repaired-source proof.
