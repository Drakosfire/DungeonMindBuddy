# SURFACE: correct toy graph dogfood usability

Status: ACTIVE for the bounded renderer, projection, Surface layout and regression corrections authorized by Alan through the coordinating dot. The dot explicitly chose a separate stacked correction PR. The coordinating steward additionally authorized the narrow atomic first-World repository operation on 2026-11-10: return existing Worlds untouched, or create one fully seeded World if storage is empty, idempotently under concurrent tabs. Do not implement a non-atomic list/create/seed workaround.

## Authority, ownership and topology

- Parent: draft #2313, branch `codex/guest-after-graph-20261109`, exact `41990c0b2930668e1a1579e24b3a7d6010a38340`. This correction stacks on that commit and targets that branch; merge guest first, then re-anchor and retarget this correction. No merge or deployment authority.
- Isolated branch `codex/graph-dogfood-usability-20261110`, checkout `/media/drakosfire/Projects/.codex/2026-11-10/graph-dogfood`.
- Current remote main verified through GitHub connector on 2026-11-10: `ec649ddc1da3b663853d3c5e9122bcf75cf7afb6`. Compared with guest base `a22b77a406c6575eea7cc073139fb0774191cf50`, later main changes do not touch these product paths. Direct Git network access is unavailable; local parent object matches connector exact head. Recheck refs before publication.
- Open-PR preflight: #2313 and stale #2262 own guest composition and App guest tests; #2219 retains predecessor Surface file claims. This successor changes only its isolated correction branch; do not edit or close those prior lanes. #2308 owns storage tooling only; #2324 owns retrieval only. No active graph-renderer successor was found.
- Runtime: task-local DOM tests and production build only initially. Reserve loopback port 4182 for a later isolated browser preview after confirming it is free. Do not touch the current user dogfood tab/profile, preview port, IndexedDB or Worlds. No provider, backend, hosted graph, or deployment.

## Invariant and critique

A visitor sees an editable example graph without naming a World first; existing Worlds survive untouched. No-assistant Surface uses the available width. Background drag pans, node drag updates visually before release, zoom/fit are explicit and keyboard accessible, and assertions remain legible in a two-dimensional layout. Graph identities and semantics remain repository-owned; viewport state is presentation-only; node positions use layout CAS, never semantic mutation.

Failure cases: cancel/lost pointer capture must discard only transient movement; a drag must not also toggle selection; transformed coordinates must account for SVG scaling and pan/zoom; stale or rejected layout writes must remain visible and must not overwrite newer Worlds; empty startup must not create duplicate or half-seeded Worlds across remount/interruption/tabs; existing Worlds must not be silently seeded or replaced; prior draft guards and guest zero-hosted-request/auth boundaries remain intact.

## Exclusive write set

- `Docs/Plans/HANDOFF-SURFACE-graph-dogfood-usability.md`
- `apps/live-control-ui/src/localWorld/worldGraphCanvas/WorldGraphCanvas.tsx`
- `apps/live-control-ui/src/localWorld/worldGraphCanvas/WorldGraphCanvas.test.tsx`
- `apps/live-control-ui/src/localWorld/worldGraphCanvas/worldGraphCanvas.css`
- `apps/live-control-ui/src/localWorld/worldGraphCanvas/graphProjection.ts`
- `apps/live-control-ui/src/localWorld/worldGraphCanvas/graphProjection.test.ts`
- `apps/live-control-ui/src/localWorld/localWorldSurface/LocalWorldSurface.tsx`
- `apps/live-control-ui/src/localWorld/localWorldSurface/LocalWorldSurface.test.tsx`
- `apps/live-control-ui/src/localWorld/localWorldSurface/localWorldSurface.css`
- `apps/live-control-ui/src/App.guestEntry.test.tsx`
- `apps/live-control-ui/src/App.test.tsx` (coordinator-owned, narrow root-Surface expectation update authorized after default-discovery failure)

- `apps/live-control-ui/src/localWorld/localWorldRepository.ts`
- `apps/live-control-ui/src/localWorld/inMemoryLocalWorldRepository.ts`
- `apps/live-control-ui/src/localWorld/indexedDbLocalWorldRepository.ts`
- `apps/live-control-ui/src/localWorld/localWorldRepository.test.ts`
- `apps/live-control-ui/src/localWorld/indexedDbLocalWorldRepository.browserHarness.ts`

Within this checkout, surface worker owns the Surface/guest-test paths and the five repository-bootstrap paths immediately above. Coordinator owns renderer/projection and this handoff. No simultaneous edits. No package/lockfile, auth, API, root routing, schema, or other file changes without explicit amendment.

## Verification and delivery

Run focused graph, Surface, repository and guest boundary regressions under the per-user frontend lock; strict TypeScript and production build; inspect cumulative parent-to-head diff. Preserve cancellation, drag threshold, pointer scaling, keyboard movement, parallel/reciprocal/self-loop edges, long labels, route interruptions, drafts and existing-world regressions. Commit intended changes, run repo exact-SHA hosted verifier and full discovered diagnostic at the integrated checkpoint, validate receipts, obtain independent exact-head review, push and open this one draft stacked PR. Record passed, failed and unrun gates honestly; inherited discovered failures stay red. Prepare isolated preview only after checks, never replace the user's current session without coordination.

## Implementation checkpoint

- Atomic bootstrap uses one IndexedDB readwrite transaction across the empty-store check and complete example write; in-memory parity rechecks after its asynchronous fault hook. Existing records are returned unmodified. No schema, dependencies, or authentication changes.
- Surface opens the existing/default World directly with an editable title, places graph before notes/management, and no longer reserves an absent assistant column.
- SVG camera is responsive presentation state with background pan and explicit/keyboard zoom/fit. Node previews update edges while dragging, then issue one layout CAS on release; cancellation, lost capture, stale revisions and drag-click suppression are covered.
- Two-dimensional fallback positions, clipped arrow endpoints, readable wrapped predicate plates and full accessible predicate names preserve all assertion identities.
- Working-tree diagnostic: all localWorld and guest tests passed (147/147), TypeScript passed, production build passed. Existing bundle-size and mixed dynamic/static import warnings remain. These are diagnostics, not exact-SHA receipts.
- Desktop CUA has no browser/app surfaces and reports native pipe path unavailable. Native IndexedDB harness includes concurrency/reopen/abort/retry/existing-World tests but browser execution remains pending. No browser acceptance or user dogfood success is claimed.

- Initial independent review held one P2: opaque parallel/reciprocal/self-loop predicate plates could overlap despite distinct paths. Lane spacing now uses maximum plate dimensions projected onto the edge normal; loop plates are side-by-side. Three geometric non-overlap regressions pass, focused graph suite 44/44 and typecheck pass. Re-review remains required.
- First exact-SHA hosted verifier at `55a34865502b7210fc4b2b17839dbb653c21431b` passed 1,257 + 4 + 1 selected cases and production build with collection parity. Final-head evidence must be rerun after review corrections. Full discovered diagnostic at that checkpoint is red: 166 failures, 7,296 passing, 1 skipped; inventory failed on an incomplete SelectedWorldContext mock. One root-Surface assertion still expected the removed name-first empty screen. The steward authorized updating only that expectation and checking the exact-parent baseline for all other failures. Do not call this release-qualified.
- Follow-up review held a related P2: Fit graph omitted widened parallel predicate plates. Fit now bounds nodes, edge control hulls, and full label plates; the initial fit and explicit Fit use the same geometry. Coincident endpoints use separated loop lanes. Regressions assert plate containment in a 600×520 viewport for seven multiline reciprocal assertions, and non-overlap for coincident endpoints. Full affected suite now passes 152/152, the updated App root test passes, typecheck and production build pass as working-tree diagnostics.
- Integrated exact-SHA checkpoint `d4f47f301b30a8207c2af5107fcb3730b2afa07d`: hosted safety passes 1,260 + 4 + 1 selected cases, build, collection parity and receipt validation. Default-discovered diagnostic reports exactly the same 164 failed test IDs as exact parent `41990c0b2930668e1a1579e24b3a7d6010a38340`, with no new failures. Both inventories fail on the pre-existing missing `SELECTED_WORLD_LOCATION_CHANGED_EVENT` mock export; both remain red. Retained reports: `/tmp/graph-dogfood-d4f47-discovered-20261110/evidence.json` and `/tmp/graph-dogfood-base41990-discovered-rerun-20261110/evidence.json`. This integrated checkpoint is not final-head hosted evidence or release qualification. Final renderer corrections receive fresh hosted verification and independent exact-head review.
