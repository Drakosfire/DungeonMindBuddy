# Build contextual layout controls

Status: ACTIVE for draft PR publication. Alan authorized the bounded implementation on November 16, 2026, then explicitly requested “Get it reviewed and pushed.” Push this lane and create or reuse one draft PR. Do not merge, deploy, claim release qualification, touch real World data, or communicate with external agents. This publication authorization supersedes the earlier local-only stop; product scope and write ownership are unchanged.

## Outcome and topology
Serial successor to merged composer #3689, #3690, #3697 and #3711. One independently reviewable presentation change: replace the permanent composer testing toolbar with opt-in, contextual controls while preserving all existing layout operations and persistence. Do not add layout capabilities or change durable contracts.

Base: origin/main 0e12798d4858c565d526a3da645e30b4c6ff2897. Branch: codex/build-contextual-layout-20261116. Isolated checkout: /home/drakosfire/Projects/build-contextual-layout-20261116. November 16 amendment recheck: all 64 listed open PR heads were fetched and filename diffs checked; no overlap with pageComposer, MarkdownCanvas, BuildReferenceCapability or buildBuildSurfaceInteractionPublication paths. The new main delta only affects unrelated replay presentation. Recheck before expanding ownership. Older composer handoffs still say ACTIVE but their named PRs are merged; this successor owns only the UI paths below, not their old storage leases.

## Design authority and invariants
Read Docs/Design/ui-language/DESIGN-interaction-layer-language.md, Docs/Design/ARCHITECTURE-surface-interaction-layer.md and the composer specification at 56507b4cc47241be61a1d27fbd53a87e5d3a7421:Docs/Backlog/DESIGN-build-page-composer.md. Cheap chrome, expensive current work; publish into shared Edit capabilities instead of another persistent toolbar.

Writing/reading has no layout toolbar. Normal caret placement must not reveal row settings. Explicit row/image handle selection opens a compact anchored menu; layout creation remains discoverable through the existing block/shared Edit path. Details stay closed until asked. Preserve keyboard and tap discoverability, semantic order, actual table editing, image identity, undo, existing line modes, responsive stacking, draft and save contracts. No hover-triggered actions.

Failure critique: outside clicks must not restore trigger focus over the intended paragraph caret; Escape may restore trigger focus without scrolling. Opening/dismissing at viewport bottom must not shift the reading position or collapse an intended native text selection. Do not copy the agent-coupled ContextualAgentMenu blindly. Never act on stale/destroyed/read-only editors or stale selected objects. Do not lose existing row/image operations while hiding controls.

## Expected exclusive write lease
- This handoff and truthful predecessor settlement in HANDOFF-BUILD-page-composer-row.md, HANDOFF-BUILD-page-composer-controls.md and HANDOFF-BUILD-page-image-text.md.
- apps/live-control-ui/src/tiptap/pageComposer/ UI modules, CSS and existing PageRow.test.tsx (not presentation schema/mappers).
- apps/live-control-ui/src/markdownCanvas/MarkdownCanvas.tsx and directly owning existing test.
- apps/live-control-ui/src/buildSurface/reference/buildBuildSurfaceInteractionPublication.ts and its existing test, only if necessary for shared Edit discovery.
- apps/live-control-ui/src/buildSurface/reference/BuildReferenceCapability.tsx and its existing BuildReferenceCapability.test.tsx, strictly to bind shared Edit layout discovery to the current editor/session and reject stale invocations. This two-file lease amendment is approved by the designing steward within the same polish outcome.
Return for a bounded lease amendment if any further host/publication path is required. No backend, schema, lockfile, runtime config, Plan, agent features, or missing artwork repair.

## Isolation and validation
Keep existing fixture15489 and API18089, operator/API8000 and all live/retained Worlds untouched. Allocate new local ports only after checking occupancy, and disposable fixture state only. No paid calls. Use known-good saved artwork; Edge missing thumbnails are a separate unresolved symptom.

First focused editor tests and typecheck/build; then exact-commit hosted verifier and one meaningful full discovered diagnostic per AGENTS, respecting the global frontend lock and external evidence filesystem. Retain inherited red failures and exact source evidence. Browser witness: long fixture target near viewport bottom, open/dismiss controls, type directly into next paragraph, multiline selection, keyboard/Escape, narrow viewport, row resize/undo, image text options, save/cold reopen and unchanged semantic Markdown for presentation-only edits. Report missing evidence honestly. Independent review remains separate; no merge authority.


## Local implementation checkpoint — November 16

The persistent composer toolbar is replaced with explicit row/image handles and a viewport-clamped popover. Shared Edit → Page layout retains one/two/three-column row creation and Text on image. Existing shared Edit undo/redo and selected-row move/unwrap/resize/history operations remain available. Row and image details start closed. Outside pointer/focus dismissal does not restore the handle; Escape restores it without scrolling and cancels an uncommitted height field. Editor/session and selected-object guards reject stale, destroyed or read-only targets. No schema, mapper or persistence contract changed.

Forty-five focused cases and typecheck passed as working-tree diagnostics. Browser witness used synthetic staged artwork, a uniquely owned disposable application-state database, preview15490/API18090 and the existing source API paths. It passed shared Edit creation, bottom-of-viewport open/Escape scroll stability, outside-click caret typing, multiline native selection, keyboard resizing/undo/redo, row settings, narrow tap/stacking, image text controls and save/cold reopen with exact Markdown equality for a layout-only change. The synthetic fixture was canonicalized to avoid the existing exporter's trailing-space normalization. Original15489/18089 and operator8000 were untouched. No provider calls or live World writes.

Evidence root: `/home/drakosfire/Projects/.codex/buddy-check.0L1Dpx`. Browser script/result/log and PNGs are retained there. Exact-commit verifier destinations are `hosted` and `discovered` under that root; their reports, rather than this checkpoint, determine final qualification. At this checkpoint, independent review and human acceptance were pending and publication was not authorized. The later review and publication status is recorded below; merge and deployment remain unauthorized.


## Review cycle 1 correction — silent editability

Independent review held `777dca90464c8ead04eada8542d3573ca9049633`: production `setEditable(value, false)` suppresses Tiptap update notifications, leaving contextual handles visible. The correction observes ProseMirror PluginView editability changes without dispatching document transactions. NodeViews hide/show handles and separators immediately; read-only transitions cancel divider previews, dismiss open popups and refresh shared Edit availability. Initial read-only mounting and silent re-enable are covered.

Working-tree verification: 49 affected cases and typecheck passed. The client-only browser witness covers row/image popups, initial read-only mount, both silent transition directions and cancellation of a live divider gesture with zero document transactions. Evidence: `silent-editability-proof.mjs`, `silent-editability-result.json`, `silent-editability.log` under the existing evidence root. New exact-head verifier outputs use `fix-hosted` and `fix-discovered`; original exact-commit verifier evidence remains retained. Re-review was required against the correction commit and subsequently passed as recorded below. This correction itself added no publication or merge authority.


## Reviewed source and draft publication — November 16

Independent review cycle 2 passed exact runtime head `ea95d7a10dd01a4cf62b9edb2d312d7cdce79a15`. Evidence: `/home/drakosfire/Projects/.codex/buddy-check.0L1Dpx/independent-cycle2-result.json`. The independent browser witness confirmed both row/image silent false/true transitions, no transition transactions, unchanged document JSON, Escape focus and 390px popup fit. The earlier cycle-1 HOLD is resolved by the correction at this head; human product acceptance remains separate.

Exact reviewed-source verification: 49 affected cases passed; hosted suite 1,406 passed with successful build and validated evidence in `fix-hosted/evidence.json`. Full discovery at that same SHA remains red: 7,831 passed, 151 inherited failures, 2 pending; build passed. No new failures or missing cases, and the two collection discrepancies match the retained diagnostic of the identical base source tree. Exact IDs, environment, source, results and comparisons remain in `fix-discovered/evidence.json`, `fix-discovery-comparison.json` and `fix-collection-comparison.json` under the evidence root. This is not release qualification or a fabricated hosted check.

Publication re-anchor: current main `a042251d3ce0007a43cd21952f6bf16cc2271ef6`; 65 open PR heads fetched and checked, with no overlap against this lane's changed paths. Main's two new commits affect artwork access and CI test classification. Preserve reviewed base `0e12798d4858c565d526a3da645e30b4c6ff2897` and reviewed runtime code; no rebase or runtime change is part of draft publication. This handoff-only amendment records Alan's publication authority and completed review. The PR must distinguish the reviewed runtime SHA from this documentation-only publication head and retain exact-source evidence provenance. Re-anchor and verify the eventual integrated source before any separately authorized merge.
