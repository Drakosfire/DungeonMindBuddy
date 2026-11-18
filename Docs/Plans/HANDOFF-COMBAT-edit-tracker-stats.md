# COMBAT — edit tracked defenses and maximum HP

## Authority, lane and outcome

MERGED as #3975 at `15a288044cb1946821b960f156ecbf8c918d549e`; source lease
released to HANDOFF-COMBAT-persistent-statblock.md. Exact reviewed head
`1d64c1205c8cfe10226f40202d95ea59288051d4` passed 54 focused checks and typecheck.
Independent code/evidence review approved bounded acceptance: exact-base discovered
7864/174/2 versus head7867/174/2, no new failed IDs or missing case occurrences,
both builds passed. Hosted1396/12 with 147 excluded skips; all failures inherited.
Full validators and discovered collection parity remain red, not release-qualified.
Disposable browser Save/Revert/recovery, numeric/text/unset overrides and unchanged
source/sibling checks passed. Live runtime readiness remains pending below.

Original authority: under the operator's Combat implementation goal and explicit review,
accepted-slice merge and local deployment authority. The root is the assigned
Combat designing/implementing steward. This is a revised serial slice after
#3968, merged `e088f7b0e6b48928bc9e26cfdc34045043abec62`.
Base: that fetched main commit. Branch: `codex/combat-edit-tracker-stats`.
Checkout: `/home/drakosfire/Projects/.codex/fc67/DungeonMindBuddy`.
No unmerged parent. One open Combat implementation PR at a time.

A GM can change AC and maximum HP on an existing participant, including manual
descriptive values, using the same owned draft, Save, Revert and recovery path as
HP, temporary HP and initiative. These are encounter overrides; exact source
mechanics stay immutable and inspectable. Do not clamp current HP, heal, defeat
or advance a unit as a side effect of editing its maximum or defense.

This slice does not complete the goal. System-neutral statistics/resources,
manual ordering and non-D&D pacing, persistent nonmodal exact-sheet projection,
and the full integrated real-runtime Graph/Plan/Play journey remain required.

## Scope and ownership

Expected exclusive writes: this handoff and truthful predecessor settlement in
`HANDOFF-COMBAT-table-board.md`; shared
`apps/live-control-ui/src/surface/modules/CombatRosterModule.tsx` and its tests;
`apps/live-control-ui/src/combat/combatRoster.css` only if the new fields need
layout adjustments. No new schema, source/provenance contract, API, migration,
provider calls, root routing or authorization change.

Relevant open work checked: #3668 owns source proficiency projection in
`combatMinimums.ts` and `services/combat_mechanics.py`, both read-only here.
#3824 is the hosted integration draft. Build variant handoff/review PRs remain
source consumers; no producer paths are touched.

## Why the profile successor waits

The database explicitly checks the v1 ruleset/draft schema identifiers. A genuine
versioned system-neutral profile needs an additive constraint migration, alongside
v1-preserving models, recovery and preparation/session cloning. Current main has
head0160. Open #3877 reserves0161, on `codex/hosted-play-progress`, current pinned
head `ec87ac17e4af4c27dbfdbc1d8f4c341e09d679b7`, and depends on #3875 first.
Do not create a competing migration head or silently relabel expanded data as v1.
The profile migration remains BLOCKED on that schema ownership/sequence being
settled; no profile implementation lane or migration number is allocated here.
The detailed steward draft is retained in the task evidence directory as
`flexible-profile-design-draft.md`; adopt a fresh bounded handoff before dispatch.

## Invariants and critique

- All edits travel through `updateEntity`/`updateDraft`, existing Web Lock and
  synchronous recovery retention. Replacement, unresolved recovery and adoption
  locks must disable the new controls exactly like other actor edits.
- Empty values stay unset; descriptive values remain descriptive. Respect existing
  numeric/string bounds and avoid silently converting descriptive values to zero.
- Changing AC/max HP does not modify the exact statblock, association, sibling,
  current HP, temporary HP, notes, status or turn/round pointer.
- Save acknowledgements preserve later edits; unknown Save retains its exact
  request. Revert/recovery retain their existing explicit owner and scope.
- Legacy persisted records and source snapshot digests are unchanged by reading.

## Verification and delivery

Mounted tests prove numeric and descriptive edits, unsetting, disabled replacement
controls, unchanged source/sibling/current HP, and exact Save/Revert/recovery.
Use existing classified tests; preserve inventory validity. Inspect cumulative
diff, run type/build and the required isolated exact-SHA hosted/discovered checks
under the shared lock. Compare inherited failures with exact baseline evidence;
retain red qualification and every real error. Independent exact-head Bugbot
judgment precedes merge and coordinated local delivery.

Browser evidence uses disposable records first. The accepted immutable UI on5218
is separate from this development branch and must not hot-load in-flight work.
API8001 and existing UI5202 remain read-only during this implementation. Real-data
rollout has an inherited runtime-reader compatibility gate: existing API source
under `buddy-check.XuK5ht/runtime-3962-compatible` omits the merged #3797 PDF
coordinate/digest reader correction. Both stored Elderwyld encounters validate
with current main models inside a read-only transaction. Preserve their exact
bytes/digests and coordinate runtime adoption rather than repairing stored data.
No live schema/encounter changes are authorized by this slice.

Task evidence root: `/home/drakosfire/Projects/.codex/buddy-check.LPopRI`.

## Implementation checkpoint

AC and maximum HP now use the owned actor draft update path. Whole numeric values
remain numeric, descriptive values remain text, and blank values are unset.
Lowering a maximum never changes current HP; Heal now also preserves a current
value above that maximum rather than reducing it. New controls inherit the same
replacement/adoption/recovery disablement as the existing actor fields.

Working-candidate diagnostics: 53 focused roster/table/inspection/recovery tests
pass, full TypeScript checks pass, and all1,555 test files classify successfully.
Coverage includes unchanged source mechanics/sibling/current HP, descriptive and
unset saves, Revert and explicit local recovery. Exact-head checks, independent
review and browser acceptance for this slice remain pending.

Bugbot HOLD on `86ba537c5` found that a descriptive fractional maximum such as
`"10.5"` could be parsed into invalid fractional HP during healing. The repair
keeps those values opaque to integer healing arithmetic and explains that manual
text maxima do not provide a numeric healing cap. A mounted HP10/max`"10.5"`/Heal1
regression retains the text and saves integer HP11. Earlier source evidence is
retained. Repaired working-candidate diagnostics pass all 54 focused tests and
the full TypeScript check; repaired exact-head verification and review remain
required.
