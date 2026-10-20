# Surface and tool code follows activation

**Status:** COMPLETE; accepted on 5202, write lease released. Full frontend-foundation goal remains active.
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

## Review, merge and 5202 acceptance

Architecture ReviewCycle1 source-approved exact b711d1f30b936c5b344f59570d3bc3ce31abc6eb in chat; independent cohort35passed/4reportedbaselinecatalogfailures, no blocking finding. PR1487 merged08a2ae057ea759482ffcd72d50c41a477f9ea7a3; re-anchored before adoption. Owned PID17085/API unchanged; served index-CZEw9clC.js, indexSHA2564ecd0b6afa303f06a2f31d3ae4ab0a6b7ef945a38609d58aa7b8e34f2fd0de11, prior product assets retained.

Native six-second host measurements: Index1JS/1,359,390raw/387,904encoded with no route/tool chunks; initialCSS155,279raw vs397,142. Activated total JS: Plan13chunks/1,695,479raw; Play6/1,530,410; Build11/1,578,394; Ingest13/1,764,754. All rendered; Plan Document/Cards retained Journey north, and real Plan Buddy unsent draft survived close/reopen before restoration to the original empty composer. Existing saved recovery remained active; no provider request was sent. No editor/controller identity was moved; existing user-tab assets retained.

Controlled native browser fixture built from the exact reviewed wrapper demonstrated delayed load→local failure→retry→current World-B binding while retaining the sibling draft. This is a controlled loader test, not a network404cache recovery guarantee. All17protected canonical JSON responses unchanged before/after. Private receipts surface-loading-* retained in established experiment state. Owned temporary tabs, HTML and fixture assets removed; no runtime/API restart. Screenshot API unavailable; evidence uses renderedDOM/native request metadata. Measurements are current-host/warm-cache, not older-laptop latency/INP/RAM proof. Architecture acknowledged reported acceptance with these limits. This backward-looking settlement travels with the next dependent trace implementation.
