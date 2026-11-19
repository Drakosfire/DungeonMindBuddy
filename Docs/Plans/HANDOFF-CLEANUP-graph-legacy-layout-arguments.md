# CLEANUP: remove obsolete Graph layout test arguments

ACTIVE under the standing cleanup goal's implementation, review and merge
authority. Serial one PR; branch `codex/graph-legacy-layout-arguments`, base
`4955eb7be7a60b48eb0ceeee6d4fc273d01b76e5`; reused isolated checkout.

Exclusive writes: this brief and
`apps/live-control-ui/src/localWorld/worldGraphCanvas/graphProjection.test.ts`.
Current PR paths and55pinned handoffs have no matching lease. Remove only two
legacy position-map arguments passed to the solver's options slot. Keep the
previous-map geometry comparisons, all assertions and solver/API unchanged.

Verify full exact-source frontend diagnostics before/after, identical case
inventory/results except timing, affected projection cases, hosted/build and
evidence validation; disclose inherited failures. Independently review exact head
before merge. No backend, inventory, workflow, provider, DB or deployment changes.
Use the global frontend lock; no competing Vitest run. No release qualification.

Predecessor#4167 merged4955eb7b and retired two historical reports with exact Git
recovery. This test-caller cleanup grants no original disposition count credit.
