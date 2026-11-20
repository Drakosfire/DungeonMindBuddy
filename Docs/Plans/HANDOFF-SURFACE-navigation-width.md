# Shared navigation width

Status: DELIVERED. Source review cycle1 approved exact32f7c5a7707c846b875b76ed71511fdeb5e70eb7; merged04e44374300a985e247941fb03de6bdaa01662b3 (identical tree). UI5202 adopted index-CKtaN8p7.js, index SHA719006fd22f101ddd9f4044660f1ae6a33decf33ec3cd57f41a45a49f300d5b4; prior assets/index retained, API unchanged. Author live four-surface measurements share left20/right1385.5557/width1365.5557 with no horizontal overflow; narrow preview also matched. Independent17 shell/notes tests passed; typecheck/build author verified. Temporary5213 and redundant preview output removed after live byte comparison. Explicit operator request on 2026-10-20 to examine and standardize the navigation across Plan, Play, Ingest and Build.

## Decision and boundary

The shared app header spans the viewport with identical 20px outer gutters and a 6px top inset on every native surface. Both command navigation and the optional surface toolbar share that header. Surface content retains its own reading/workspace width. Reserve a stable root scrollbar gutter so page-scroll surfaces and bounded workspaces keep identical header edges; set the content wrapper width explicitly so lazy-loading states do not shrink it. Header height remains measured; narrow controls wrap under the existing shared rules. No fixed viewport positioning, guessed height or per-surface width override.

Move AppChrome's header outside the content-width app-wrap into the shared app-shell-layout. Keep the same mounted surface/context providers, header ref and page children. Update floating Play notes' header lookup to the common shell so dragged notes still clear actual chrome. Remove obsolete content-wrapper header selectors and Plan-only mobile Graph navigation layout overrides. Existing scroll/workspace/editor sizing remains owned by the content wrapper.

## Lane and write lease

PR topology: parallel-independent from draft Rules PR1506 at c125f3cc3c28c09c914fe410aed86d5d20e4f3b3; no behavioral dependency or overlapping writes. PRIME reuses buddy-context-loop checkout serially, branch codex/surface-nav-width from fetched origin/main 55ab48ebce184ac5fe2d952c0bdf1e0a03eb8532. Rules changes are committed/pushed before switching. Architecture reviews pinned Git heads, not mutable checkout contents.

Expected writes: this handoff; apps/live-control-ui/src/chrome/AppChrome.tsx and AppChrome.test.tsx; src/styles.css; src/playSurface/currentMoment/FloatingSceneNotes.tsx and its current owner test if affected. No backend, database, corpus, draft/notes writes or provider calls. Live UI5202 is established preview PID17085 using retained ui-dist; verify exact runtime/output lease before reviewed UI asset adoption. Temporary preview5213, owned unified exec session26941, outputs only `.pytest_cache/surface-nav-width-dist`; stop and remove redundant preview output after delivery. Keep prior live assets for open tabs/rollback. API8000 remains unchanged.

## Verification and delivery

Inspect exact cumulative diff, typecheck and current shell/notes owner checks. Browser-measure common header edges across four native surfaces and representative narrow/loaded states; check no horizontal overflow and content reading widths retained. Independent exact-head review, authorized PRIME merge, re-anchor, then build/adopt reviewed source to UI5202 and verify rendered behavior. Preserve drafts, mounted editor/undo, scene position, note data and active Buddy transport. A navbar screenshot or helper test alone does not prove those data invariants.
