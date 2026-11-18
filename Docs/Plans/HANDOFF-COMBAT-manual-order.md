# COMBAT — arrange participants without initiative

ACTIVE under the operator's full Combat implementation/review/accepted-merge
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
