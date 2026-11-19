# COMBAT — keep exact statblocks beside the encounter

MERGED as #3981 at `5711085fd69913111db7925027ccdede1b1e694a`; source lease
released to HANDOFF-COMBAT-manual-order.md. Reviewed head
`d1d7bb58f2c58469185cbf13232fadd7a732411b` has independent code/evidence acceptance.
Final42 focused tests/typecheck passed. Exact hosted1408 selected passes/0 failures,
147 filtered skips, build/parity and validator passed. Discovered7907/162/2 versus
exact base7902/162/2: five added passes, no missing cases or new failed IDs. Both
builds passed. A differing Work Plans failure depth reproduced identically in a
paired exact-source diagnostic, independently audited against Git blobs. Full
discovered qualification/extra-skip parity remains red; no release qualification.
Browser proof and remaining real-runtime/profile requirements are retained below.

Original authority: under the operator's Combat goal and renewed explicit review/accepted-PR
merge authority. Serial successor to #3975, merged
`15a288044cb1946821b960f156ecbf8c918d549e`; no unmerged parent. Branch
`codex/combat-persistent-statblock`, same isolated fc67 checkout, base that fetched
main SHA. Existing shared API8001/UI5202 and immutable preview5218 stay untouched.
Disposable browser services use5217/5219 only after checking ownership and the
global frontend verification lock.

Outcome: select a participant's exact saved statblock and keep it readable while
editing the encounter. Wide layouts place it beside the roster; narrow hosts
stack it without putting source content inside the table's horizontal scroller.
The existing quick modal remains available. Standalone, Plan and Play share this
implementation. No latest-source lookup or source mutation is introduced.

Exclusive writes: this handoff, truthful predecessor settlement in
HANDOFF-COMBAT-edit-tracker-stats.md; CombatRosterModule.tsx and its existing test;
combat/CombatRosterWorkspace.tsx and its test; CombatMechanicsInspection.tsx and
its test if necessary to share the exact renderer; combatRoster.css; one new test
classification entry in ci/test-classification.json. No API, backend, migration,
Graph/mechanics producer, host registry or authorization writes. Open #3668 owns
combatMinimums/service adoption work and remains read-only. Build variant work is
a source consumer and has no lease on these UI paths.

Selection is local presentation state resolved by actor identity against the
current draft, never a copied snapshot. Key the workspace by World, encounter and
run/scene scope. Removal, loss of source and scope replacement retire projection;
defeat and group collapse preserve individual state and selected source. Explicit
mechanics adoption shows the accepted replacement snapshot. Opening/closing does
not remount rows or erase staged damage/heal values. The nonmodal complementary
region has labeled controls, no focus trap, and a sensible keyboard focus return.

Verification: mounted exact-source/no-fetch tests; edits with a projection open;
stable staged inputs; source replacement/removal/scope cleanup; keyboard focus;
responsive browser acceptance through actual standalone and Plan/Play components.
Run type/build, inventory and required isolated exact-SHA hosted/discovered checks
with exact-base failure/case comparison and independent Bugbot judgment. Keep
inherited failures and collection parity red; no release-green claim.

System-neutral profile/resources/pacing, migration sequencing behind #3877/#3875,
and real Graph/runtime readiness remain required goal outcomes. The shared API's
missing merged #3797 reader fix remains a separate gate; no live data repair or
shared process restart is authorized by this UI lease. Design/evidence retained
under `/home/drakosfire/Projects/.codex/buddy-check.LPopRI`.

## Implementation and browser checkpoint

The shared workspace resolves the selected source from the live draft, preserves
row ancestry, and returns close focus to its visible trigger or workspace. Quick
modal inspection reuses the same deferred exact renderer. A ResizeObserver
publishes the turn rail's actual height; panel sticky offset, scroll margin and
available height account for that rail and standalone chrome. Container queries
provide side-by-side projection in sufficiently wide standalone/tool hosts and a
stacked source panel at390px. No fixed turn-rail height assumption remains.

Initial42 focused tests and full typecheck passed. Browser iteration found and
fixed a narrow-layout source header hidden under wrapped turn controls. Repaired
standalone acceptance showed readable header/Close controls at390px, exact source
AC15/HP68 beside edited tracker AC20/HP9, staged damage7 surviving open/close, and
Save revision9. Actual shared Plan/Play host components against disposable HTTP
fixtures showed PlanHP8 saved revision10 and independent PlayHP57 revision5; Plan
reopen retained8 and no projected selection from the prior scope. The Plan wide
toolbox keeps the exact source beside editable rows. Both disposable services
stopped; existing APIs/UI and live data unchanged. Screenshots are retained as
combat-persistent-source-wide.jpg, combat-persistent-source-narrow.jpg and
combat-plan-persistent-source.jpg in the current conversation visualization root.
These are synthetic transport/client-host proofs, not real PostgreSQL or the full
governed Graph journey. Final focused/type checks, exact-head full suites and
independent exact-head judgment remain pending at this checkpoint.
