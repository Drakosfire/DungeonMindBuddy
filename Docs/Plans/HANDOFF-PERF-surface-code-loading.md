# Surface and tool code follows activation

**Status:** ACTIVE; PRIME owns this bounded frontend-foundation implementation.
**Base:** d154de4d3e9643b5159c53d9aaaa99a2019e5794, branch codex/surface-code-loading, existing buddy-context-loop checkout.
**Topology:** serial successor to accepted history-demand; no overlapping active code-loading lane found in open PRs.

## Invariant and failure critique

Ship surface and projection-renderer code on activation, preserving the existing App providers, route identity keys, one persistent conversation controller, draft and pending recovery ownership. Module-level deferred component identities must remain stable across ordinary rerenders. A loading or failed chunk must render local accessible status/retry content; it must not suspend/unmount the surrounding providers or change selected World, route, tool binding, or data. Retry may recreate only a failed deferred child. No route redirects, schema, admission, prompt, dispatch, dependency or backward compatibility changes.

## Exclusive expected write lease

- This handoff.
- apps/live-control-ui/src/ui/deferredComponent.tsx and its test: shared local Suspense/error retry wrapper.
- apps/live-control-ui/src/App.tsx: defer owned surface/editor/shell renderer imports, retain provider order and controller identity.
- apps/live-control-ui/src/planSurface/projection/{Plan,Ingest}ProjectionCatalogRegistration.tsx: defer heavy renderer modules while retaining registration/binding validation.
- projectionCatalogRegistrations.test.tsx and LegacyProjectionHostAdapter.test.tsx under the projection directory: await actual deferred renderer readiness while retaining catalog identity and binding assertions.
- Existing App.test.tsx, App.commandAccepted.test.tsx, App.surfaceInteraction.test.tsx and test/appNavigation.test.tsx only if assertions need to await actual route readiness; never remove behavior coverage.

Verify helper load/failure/retry/state lifetime and real App/navigation/catalog owner tests. Build production chunks and inspect initial static closure plus activated surface/tool requests; compare against current 2,619,090 raw / 717,192 gzip eager JS. No claim of target-laptop acceptance from host measurements. Inspect cumulative diff, get exact-head independent review, merge, adopt reviewed assets on owned 5202 with protected17 JSON state unchanged and retained Document/Cards scene and Buddy draft/recovery behavior. Prior assets stay available for active tabs. Temporary probes/tabs are cleaned up. Read payload/list bounds, further heavy conversation/tool/trace/editor splits, launcher sizing, user+Agent Rules lookup and native Combat remain outstanding.

## Pre-review evidence

TypeScript and Vite production build pass; cumulative source/test diff inspected and diff check clean. The 10-file App/navigation/catalog/helper cohort reports 116 passed / 9 inherited failures. Exact-base in-memory Vite transforms reproduce the same five App/navigation and four catalog failures; none is newly introduced. Readiness assertions now await deferred inspector/reference/renderers; the campaign-switch test explicitly waits for the lookup to begin before proving its late result is retired. Three new wrapper tests prove activation-only loading, prop/state retention, pending-load sibling draft retention and failed-load retry without remounting the surrounding owner.

Production manifest: initial static JS closure contains exactly one entry, index-CZEw9clC.js, 1,359,390 raw bytes / Vite-reported 387,900 gzip bytes versus accepted 2,619,090 raw / 717,192 gzip. Approximately 48.1% raw and 45.9% gzip reduction; this is code distribution evidence, not cold-start/INP improvement. Separate route/tool chunks include Plan, Play, Build, Ingest, Tiptap, statblocks, ingestion and diagnostics. Native acceptance remains pending reviewed merge/adoption. Conversation controller code is still eager; later splitting must preserve its transport/recovery lifetime.
