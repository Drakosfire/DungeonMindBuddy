# INGEST: unify source-to-enriched-recap navigation

**Status:** ACTIVE — PRIME authorized this bounded Ingest presentation correction on 2026-10-17.
**Base:** `origin/main@c253acca3b3138fd2baddf5bb9151cdaa53f1026`.
**Branch:** `codex/ingest-source-to-enriched-review` in the existing `996b` checkout.
**Topology:** Serial; one Ingest UI PR. ARCHITECTURE reviews the exact cumulative head; PRIME retains merge and rollout authority.

## Mission

Make the Ingest path feel like one coherent workflow: write or paste a recap, choose **Process**, then work in the formatted, graph-enriched recap. Preserve the full recap and its linked node pills as the reader; this slice is not a node-only summary or a new projection.

The Ingest page already owns campaign/session selection and prior-recap loading in its local navigation. The embedded `WorldGraphRecapProjectionView` adds a second Campaign / Focus session / Load toolbar. In the Ingest call site, `onLoad` is not supplied, so Load is permanently disabled. This duplicates navigation and exposes a dead action inside the primary recap view.

Add an explicit optional prop to the shared projection view to suppress only that toolbar. Keep its default visible for other consumers such as Plan and Graph Preview; Ingest opts out because its own navigation owns this context. Keep the projected recap, node pills, authoring controls, evidence/provenance, loading/error states, and selection identity intact.

## Evidence and failure cases

- Read-only desktop inspection of a fresh 5202 tab at Session 10 showed the formatted recap with linked node pills and no visible raw Markdown syntax.
- The recap projection showed a second Campaign / Focus session / Load row. The accessibility tree exposed its Load button as disabled, matching the Ingest call site's missing `onLoad` prop.
- Ingest's own local navigation continues to expose source/campaign/session actions. The duplicate row is owned by `WorldGraphRecapProjectionView`, which is shared with other surfaces.
- Do not remove the outer Ingest navigation, hide evidence or exact-run provenance, or change how session/campaign selection, hydration, reader recovery, draft preservation, or authoring proposals work.
- Do not click Process or Load, edit/save/discard, or mutate the real Session 10 recap, source, World Graph, or database.
- The available CUA surface does not expose a viewport override. Narrow-width rendered acceptance is unavailable and must not be claimed.

## Exact write lease

- `Docs/Plans/HANDOFF-INGEST-source-to-enriched-review.md` — this bounded contract and truthful implementation/verification evidence.
- `apps/live-control-ui/src/modules/IngestionModule.tsx` — opt the Ingest reader out of the shared projection toolbar only.
- `apps/live-control-ui/src/modules/IngestionModule.test.tsx` — verify the Ingest view has one campaign/session/source-navigation owner and still renders the enriched recap.
- `apps/live-control-ui/src/planSurface/graphPreview/WorldGraphRecapProjection.tsx` — add an explicit toolbar visibility prop that defaults to visible; do not change toolbar behavior for other consumers.
- `apps/live-control-ui/src/planSurface/graphPreview/WorldGraphRecapProjection.test.tsx` — verify default-visible behavior, opt-out behavior, and continued node-bearing projection.

No CSS is initially leased. No server/API/schema/extraction/persistence, other surface, route, Graph publication, source/corpus, database, provider, runtime, environment, build-output, or 5202 service changes are authorized. If CSS or any other path becomes necessary, report the exact path and invariant to PRIME before editing it.

## Verification and acceptance

- Focused `IngestionModule.test.tsx` and `WorldGraphRecapProjection.test.tsx` suites pass, including existing identity/session-switching and reader recovery regressions.
- UI typecheck and production build pass; keep build output in the existing repository `.pytest_cache/` and prove served `apps/live-control-ui/dist` hashes are unchanged.
- `git diff --check` passes and the exact cumulative base-to-head diff stays within this lease.
- The Ingest reader no longer contains the duplicate Campaign / Focus session / disabled Load toolbar; its local navigation and prior-recap source controls remain.
- The shared projection retains its toolbar by default for Plan/Graph Preview consumers.
- The formatted recap, linked nodes, evidence/provenance, authoring entry points, and context identity remain visible/usable.
- Read-only desktop inspection of Session 10 is recorded; narrow rendered inspection is unavailable in the current CUA environment. No real Process or source/World write is used as test data.
- Open/update one PR for independent review. Do not merge it or alter 5202. The operator continues dogfooding Build; do not ask them to accept Ingest yet.

## Predecessor settlement

- PR #1349 settled `HANDOFF-INGEST-stage-clarity.md` (merge `08563087107b79c4f8e5751dd960952278a2d8f2`). Its Source ready / unrun-extraction distinction is on this base.
- PR #1362 settled `HANDOFF-INGEST-working-recap-provenance.md` (merge `5e3e566c151aee785d5eb52af8619e6dca2b2478`). Its Working recap / Published recap source labels are on this base.
- PR #1358 separately proved Process evidence persistence on PRIME's disposable database fixture. This UI slice does not repeat that database test or change the Process boundary.

## Current verification

- `apps/live-control-ui/src/modules/IngestionModule.test.tsx` and `apps/live-control-ui/src/planSurface/graphPreview/WorldGraphRecapProjection.test.tsx`: **88 tests passed**. New assertions prove Ingest has no duplicate Focus session/Load toolbar and only one Campaign control; the shared projection retains the toolbar by default; the opt-out leaves the node-bearing recap mounted. Existing route/session and reader-recovery tests remain in the run. Existing React `act(...)` warnings remain.
- The shared projection default-toolbar test includes an enabled Load callback; the current Ingest projection call omits that callback and opts out, removing the permanently disabled Load affordance without changing other consumers.
- `npm run typecheck`: passed.
- `npm run build -- --outDir ../../.pytest_cache/ingest-source-to-enriched-review-build` from `apps/live-control-ui`: passed (712 modules). Vite reports the existing large-chunk warning and notes the explicit output directory is outside project root. All `apps/live-control-ui/dist` file hashes matched before and after the build.
- Read-only desktop check on 5202 Session 10 confirmed the formatted recap and node pills remain the intended reader content; no Process/Load/edit/save action was taken. The deployed 5202 page still reflects its existing bundle, not this branch. Narrow-width rendering could not be checked because the available CUA interface has no viewport override.
- The exact five-path cumulative diff was reviewed against `origin/main@c253acca3b3138fd2baddf5bb9151cdaa53f1026`; `git diff --check` passes. No runtime, source, persistence, or graph behavior changed.
