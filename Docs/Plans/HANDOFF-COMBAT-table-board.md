# COMBAT — table-ready encounter board

## Authority and lane

MERGED in #3968 as `e088f7b0e6b48928bc9e26cfdc34045043abec62`.
The source write lease is released to the consuming stat-editing slice. Reviewed
head `e72044c87ca9939dbcc8f4105afb0fb52ef374e7` has three distinct-head formal
review cycles across this slice; supplemental evidence audits add no cycle.
Standalone and actual shared projection components passed the synthetic-API
browser checks; exact-head inherited-red verification and its limits are below.
The immutable merged UI is served locally on owned port5218, proxying to the
existing UI's actual API8001. Real-data readiness remains pending: the existing
API reader rejects a PDF saved-mechanics snapshot that current main validates.
Read-only validation proved both retained Elderwyld records valid with current
models. The running compatibility runtime lacks merged reader correction #3797;
no saved values/digests, shared API process, or live schema were changed.

Historical activation:

ACTIVE: the operator explicitly authorized implementation in the current Combat
goal on 2026-11-18: “Do implement it, you will build this in the goal”. This is
design/stewardship and implementation authority. The operator subsequently updated
the goal to authorize Bugbot review, merging accepted slices, and local deployment.
This does not authorize production deployment or edits to retained live encounters.
Base: fetched origin/main `d172aef9cd44df1bcdfe0102ee8c08f645511de1`.
The initial discovery snapshot was `809767895`; branch allocation used the fetched
successor `d172aef9c` (hosted prompt authorization, outside this slice).
Branch: `codex/combat-table-board`. Checkout:
`/home/drakosfire/Projects/.codex/fc67/DungeonMindBuddy`.
Topology: serial; one implementation PR for this slice. No parent PR. The flexible
mechanics successor waits for this PR to merge; the integrated journey successor
waits for flexible mechanics. The full goal is not complete when this slice lands.

## Outcome and boundary

Make the existing shared roster a table-ready running board: compact readable
participants, obvious current/next turns, groups preserving individual state,
explicit defeated/return-to-action controls, notes/status editing, and exact
statblock inspection outside narrow name cells. Move occasional setup/adoption
controls out of the running roster's primary visual path while retaining access.
Use the existing draft/save/recovery owners. No backend/schema changes here.

Expected exclusive writes: this handoff; shared
`apps/live-control-ui/src/surface/modules/CombatRosterModule.tsx` and its tests;
`apps/live-control-ui/src/combat/combatRoster.css`, `CombatSurfacePage.css`,
`CombatMechanicsInspection.tsx` and its tests; new narrowly scoped board components
and interaction tests under `apps/live-control-ui/src/combat/`. Read other paths.
The required inventory guard exposed the new table test as unclassified. Steward
amendment: `ci/test-classification.json` is leased for exactly the additive
`apps/live-control-ui/src/combat/CombatRosterTable.test.tsx` fast-lane entry.
The existing CI local-verifier, Projects-allocation and HOSTED explorer leases
reserve their exact other test entries; none is edited or transferred. This is
required test metadata within the same capability, not a selector/command change.
Verify exact open-PR path overlap before source edits and amend/transfer ownership
explicitly if necessary. Shared routing, authorization, mechanics adoption and
producer contracts are outside this slice.

Fresh relevant PR census: #3668 changes absent proficiency bonus handling in
adoption; #3824 integrates hosted authorization including scene/run encounter
routes. Build #3893/#3902/#3911/#3913/#3915/#3918 consume saved mechanics/Combat
handoff. Preserve their contracts; this lane does not adopt their unmerged code.
Historical shared-surface continuity and reopen leases are SETTLED/released.

Runtime ownership: no uncoordinated server, database, ports or output replacement.
Local delivery is authorized after verification, review, and checking runtime
ownership/collisions; pin the exact target and rollback before rollout.
5202 was inspected read-only; never use its retained encounters as disposable
fixtures. Browser verification must use synthetic isolated state and a separately
allocated port after checking collisions. Keep verification outputs external on
the repository-required verified Projects filesystem. No provider calls required.

## Invariants and failure cases

- Roster identity/order and active/round-start identity survive presentation
  grouping, collapse and statblock inspection. Never group by display name alone.
- Defeated units remain retained and editable; restoring participation must not
  invent healing or rewrite their source mechanics. Zero HP is not universal death.
- Shared Plan/Play hosts keep exact encounter scope, prepared/run separation,
  Web Lock ownership, local draft recovery and compare-and-swap save behavior.
- Inspection renders the actor's exact retained snapshot, never current/latest.
  Replacing/removing an actor or switching encounters cannot display stale rules.
- Setup remains reachable by keyboard and on narrow viewports; collapse must not
  hide an active actor without a clear summary and route to it.
- Mutations remain subject to existing replacement/adoption/recovery locks.
  Presentation refactoring must not create bypasses or silently autosave.

## Design evidence

Browser inspection of current 5202 Combat opened an existing Elderwyld rehearsal
without edits. Encounter management and mechanics adoption occupied substantial
space above the table; a two-actor encounter extended below the viewport. Actor
names wrapped narrowly. Exact mechanics expanded inside a table name cell.
The unhosted static prototype was read at
`evals/c2_live_prep/mireward-prep/combat.html` and `assets/prep.js`; browser visual
inspection remains unavailable, not claimed. Browser file access was rejected;
do not bypass that restriction. Preserve its useful interaction intent from source.

## Verification and delivery

Add focused mounted tests for group/individual edits, defeat and return, exact
inspection selection, scope changes and existing save/recovery guards. Run owning
regressions, typechecks and the required exact-SHA local hosted verifier plus a
meaningful full discovered diagnostic, honoring the shared frontend resource lock.
Retain failures and compare baselines honestly; no release qualification from a
focused sample. Inspect cumulative base-to-head diff, commit, push and open/update
the assigned PR. Obtain independent Bugbot review and resolve findings before
using the operator's explicit merge and local delivery authority.

Browser acceptance: crowded synthetic roster; readable names; current/next visible;
group collapse without losing member state; defeat/return; conditions/notes edits;
exact statblock drilldown without table expansion; save/reopen/recovery; narrow
layout and keyboard access in standalone and shared hosts. Runtime/browser claims
must identify the source actually served. Never represent live 5202 as this branch.

## Goal successors (not dispatched)

1. Flexible mechanics: editable defenses and resource tracks; versioned persistence
   and recovery; explicit resource semantics and non-D&D turn modes. Requires its
   own bounded contract and owning backend verification after predecessor merge.
2. Integrated journey: Graph-backed unit selection and statblock projection through
   preparation and running, full save/reload journey, and materially different
   synthetic-system acceptance. Keep World canon, exact mechanics, preparation and
   run state under their existing owners. Coordinate cross-owner changes explicitly.

## Implementation checkpoint — 2026-11-18

The candidate uses an eight-column board, separates exact snapshot inspection into
a native modal, renders persisted groups without reordering actors, and retains
defeated actors for explicit return without healing. Round wrapping now follows
the pinned round-start actor after initiative sorting. No backend or API changes.

Initial dirty-candidate Bugbot review found row remounts resetting staged deltas
and hidden adoption recovery locking the board. Fixed by a single stable row
parent with retained hidden rows and automatically exposing blocked adoption.
Mounted regressions cover staged delta identity across defeat/return and pinned
round boundaries. This is not exact-head review approval.

An initial working-tree focused run recorded 32 passes and one oversized-copy
Graph-selection failure. Its test mocked the retired graph projection instead of
the current native creature catalog. The owning test is repaired to mock that
catalog while retaining the oversized append refusal and unchanged-draft checks.
The unchanged-base archive reproduced that failure (26 passed, one failed).
The repaired candidate passed all 34 focused tests and the full TypeScript check.
PR #3968 is open as a draft. Its main-composed head `7132f858` received one formal
exact-head Bugbot HOLD for a sticky rail underneath AppChrome; the other findings
were resolved. The follow-up offsets the standalone rail with AppChrome's measured
`--app-chrome-top`, retaining a zero inset inside independently scrolling hosts.
The old-head verifier was cancelled while still queued, before allocating a source
checkout or running tests. Exact `3b94ee073` then received Bugbot code approval.
Its hosted run built successfully with 1,396 selected passes and 12 failures;
147 skips are excluded cases in the two existing filtered safety commands.
Its full discovered diagnostic built successfully with 7,858 passes, 174 failures
and two skips. Exact base `12f626bff` had 7,852 passes, 175 failures and the same two
skips. Independent evidence audit verified no new failed IDs or missing cases,
five new passing cases, the repaired Combat fixture, matching inherited hosted
failure messages, artifact hashes and clean source/cleanup. Both qualification
validators remain red. No full-green or collection-parity claim is made.

Standalone browser checks on that runtime source used a disposable 16-unit API
fixture and proved grouping, sticky turns, exact statblock inspection, defeat and
return without healing, notes/status, save/reload/explicit recovery, and narrow
statblock layout. This is frontend evidence, not a PostgreSQL persistence claim.
The actual Plan/Play projection harness remains to be checked. The additive
inventory correction requires renewed exact-head checks/review; no release
qualification or completed slice is claimed. Task evidence root:
`/home/drakosfire/Projects/.codex/buddy-check.LPopRI`.
