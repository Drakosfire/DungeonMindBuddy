# CI: await the actual encounter observation

Status: ACTIVE. PRIME owns one serial prerequisite slice from verified main
 a22b77a406c6575eea7cc073139fb0774191cf50 on branch
codex/ci-encounter-observation-wait in the existing buddy-context-loop checkout.
No unmerged parent. Retirement PR2312 remains frozen at933f440c until this slice
is qualified and merged; then re-anchor that PR before its own review and gates.
Merge order: this assertion repair, then the re-anchored retirement. No runtime,
provider, database, dependency or service changes. Recovery hold stays binding.

## Required invariant and scope

PlanSceneEncounter's existing positive test must observe the acknowledged tour
reading with the exact saved Plan pin, encounter identity, revision and digest.
Finding the child Combat DOM does not imply that its effect has reported roster
state and the parent has rendered EncounterTourObservation. Use the already
imported waitFor for this existing assertion, with all expected fields unchanged.
Keep the default timeout, all recovery/foreign/stale checks and production code.
No sleep, mock acknowledgement, skipped test, retry exemption or weakened proof.

Only writes: this handoff and apps/live-control-ui/src/combat/PlanSceneEncounter.test.tsx,
limited to the existing acknowledged-observation assertion. Inspected active
CI2298 and Surface2313 paths do not overlap it; CI2288 retains infrastructure
ownership. No other test, manifest, frozen command fixture or runtime file changes.

## Evidence and gates

Original full933f440c diagnostic:7433 cases/165 failures. Current parenta22b77a:
7443/164; retirement accounts for ten passing removed cases but not the extra
assertion. Three focused alternating parent/candidate pairs all pass10/10; they
do not establish suite-level parity. Preserve those failures and raw reports in
Projects/.buddy/evidence/reference-play-sheet-*; do not call the extra failure
inherited solely because oldc12 also exhibited it.

Verify the one-line cumulative code diff and unchanged expected proof fields.
Run owning tests and exact-head hosted/build plus full discovered qualification
under the shared lock, retaining inherited red diagnostics and investigating new
failures. Obtain independent exact-head Bugbot review, commit/push/open the owning
PR and merge under standing PRIME authority only after applicable source gates.
This is a verification prerequisite, not product/tour implementation or delivery.
