# GRAPH: full loaded bubble overview

Status: COMPLETED predecessor. Merged as #2464 at 77175b77212b35b2c2d0a0507a4ef314dea23b22 on 2026-11-12; its identical reviewed source tree was deployed to the local frontend after positive user pan feedback. Fresh hosted qualification and independent code review passed; inherited red discovery and unperformed responsive/weak-client checks remain limitations. No provider use, live graph writes or backend/data changes occurred. The following sections retain implementation history; the successor is HANDOFF-GRAPH-connected-density.md.

## 1. Outcome and PR slice

One coherent serial GRAPH implementation PR: render every loaded object and every valid real relationship in the native overview using SVG; reveal names, relationship predicates and editing affordances through semantic zoom; preserve camera, selection, native revisions, draft protection and writes. No mandatory clustering, inferred relationships, backend completeness change, Canvas/WebGL migration or extra product workflow. Search and optional focused exploration remain available.

Geometry and camera optimization are coupled to uncapping the overview and are part of the same reviewable capability. Dependency is merged #2431 at base 5d116c9d7304b8a91605ebfccf0969bdd77b5f63. Independent exact-head review and later merge authority remain separate.

## 2. Re-anchor, topology and isolation

Remote main was read through the connected GitHub API and exactly matched local origin/main at 5d116c9d7304b8a91605ebfccf0969bdd77b5f63. CLI network fetch was denied; it was not retried or bypassed. Read current committed AGENTS.md. Scanned all 51 open PR changed-file sets: historical SURFACE #2326 at b30833ede97cb4c79acf17a1fe55ff50446c7452 overlaps canvas files, as already recorded by merged #2431. It remains unchanged; current-main work preserves the newer shared canvas. No other open PR changes this lease. Root expressly assigned proceeding on current main while preserving other work.

Branch: codex/full-bubble-graph-20261111. Worktree: /home/drakosfire/Projects/.codex/full-bubble-graph-20261111/worktrees/DungeonMindBuddy. Task-owned scratch/cache/verification beneath the same root. Projects UUID 48fa5d10-fe99-4557-9fc9-d8a2a4b41ac8 and writable parent verified before allocation. No live backend, database, corpus or native persistence writes. Browser tests use an isolated fixture page or read-only real graph snapshot. Any preview port will be checked and recorded before use. Honor the shared frontend verification lock.

## 3. Failure critique and acceptance

- All loaded IDs and valid parallel/reverse/self-loop edge identities survive. Absent endpoints remain diagnostics, not invented nodes. Partial native reads retain their existing warning; all loaded does not claim all World data.
- Existing saved/pinned positions remain authoritative. Deterministic fallback layout uses real connected components and individually arranged disconnected objects; topology is presentation only. No aggregate replaces an object and no artificial edge is drawn.
- Camera changes must not rebuild graph indexes, fallback layouts or edge geometry. Semantic labels are bounded by visibility/detail rather than suppressing real edge strokes. Selection and keyboard access remain available while names are hidden.
- Fit, repeated zoom/pan/focus/overview, viewport changes, World/revision changes and draft/drag interruptions need boundary tests.
- Measure the observed 1404-object/559-edge shape and real loaded graph if safely available. Distinguish synthetic layout/React timings from real browser interaction timings and weak-client evidence. Do not claim unperformed measurements.

## 4. Expected write lease

- Docs/Plans/HANDOFF-GRAPH-full-bubble-overview.md
- Docs/Plans/HANDOFF-GRAPH-corpus-exploration.md (truthful predecessor completion only)
- apps/live-control-ui/src/localWorld/worldGraphCanvas/graphProjection.ts
- apps/live-control-ui/src/localWorld/worldGraphCanvas/graphProjection.test.ts
- apps/live-control-ui/src/localWorld/worldGraphCanvas/WorldGraphCanvas.tsx
- apps/live-control-ui/src/localWorld/worldGraphCanvas/WorldGraphCanvas.test.tsx
- apps/live-control-ui/src/localWorld/worldGraphCanvas/worldGraphCanvas.css
- apps/live-control-ui/src/nativeGraphDemo/NativeGraphDemo.tsx
- apps/live-control-ui/src/nativeGraphDemo/NativeGraphDemo.test.tsx
- apps/live-control-ui/src/localWorld/worldGraphCanvas/fullGraphOverview.benchmark.tsx (fixture-only diagnostic if needed)
- apps/live-control-ui/src/buildSurface/BuildCompose.integration.test.tsx (only the transferred prerequisite fixture repair below)

## 5. Verification and completion

Focused projection/canvas/native tests; typecheck and build; exact-SHA hosted verifier and validate; one full default-discovered diagnostic at integrated checkpoint, with baseline legacy failures retained red. Fresh locked install is a required gate, copied dependencies only diagnostic. Cumulative base-to-head diff, exact remote publication and short checks, independent exact-head review. Keep one draft PR until required qualification and review permit the authorized ship. Do not infer browser acceptance or waive a red release gate.

## 6. Retention

Task owns the worktree/scratch/cache/verification root above; retain until review and evidence acceptance. No cleanup permission is inferred and no deletion performed. Final notes inventory created/retained/removed paths and cleanup follow-up.

## Implementation checkpoint and evidence limits

The native embedded overview opts into uncapped loaded-snapshot projection. Default callers and explicit focused neighborhoods keep their existing budgets. The index/layout/edge geometry and SVG layers are independent of camera transforms; memoized bubbles avoid rerendering every label on selection. Individual types have stable colors with a text legend. Names appear at 45% zoom, predicates at 90%, and existing keyboard/inspection/edit authority remains. Saved layout wins; World-local fallback positions survive revision additions. No backend API or completeness changes.

Working-tree diagnostics: 98 focused tests across projection/canvas/native integration pass, and TypeScript passes. The synthetic 1404/559 fixture verifies all individual objects and real edge identities, cached camera geometry, stable revision positions, repeated focus/Fit/overview, and preserved native draft/placement behavior. The standalone diagnostic benchmark is excluded from ordinary test discovery; use a temporary Vitest config with include selecting fullGraphOverview.benchmark.tsx and the usual jsdom/setup configuration, under the shared lock.

Development React/jsdom CPU diagnostic (synthetic topology, not real World geometry): index+layout+projection median 1.30 ms / p95 3.29 ms (30 samples); full SVG initial mount 152 ms (one sample), camera-pan commit median 0.26 ms / p95 0.38 ms (30), zoom 0.26 ms / p95 0.32 ms (30), selection 9.47 ms / p95 10.21 ms (6). Full view contains 1404 nodes, 559 edges and 10380 SVG elements. The comparison is 512/43 on the same optimized component, not a before/after historical browser benchmark. No browser paint, frame-rate or weak-client claim follows from these timings.

Current CUA inventory is empty and opening an in-app browser returns Browser is not available: iab. Do not substitute shell-driven browser UI automation for the supported interface. Historical predecessor browser reports did not retain the real graph JSON; the localhost 5202 read endpoint refused the connection from this executor. No actual-graph browser, responsive screenshot or weak-client acceptance has been performed. Retain this as a draft experiment pending those checks. Exact-SHA aggregate verification and independent review are recorded separately in PR evidence when available.


## First review correction

Independent review of local candidate 5d954b2cadaac1f1fe2ae4bacb59007c28bb1b00 found a zoom-floor mismatch for compact full graphs: Zoom out remained enabled but could not reduce zoom below Fit. The correction uses the same smaller-of-manual-minimum-and-fit floor as the button and adds a repeated Zoom out regression. Unchanged bubbles also retain their position references during drag previews. Re-review and updated source diagnostics are required.

The required exact-SHA hosted verifier created a clean candidate checkout, then its fresh locked npm installation was denied by network policy for registry.npmjs.org. No aggregate tests ran and no clean-install qualification is claimed. Do not retry that denied install without materially new relevant authorization. Copied-dependency full discovery and production build can provide separate diagnostics, not substitute qualification.


## Accessibility correction and broader diagnostics

A second independent review identified insufficient contrast for small type labels on colored fills. Full-mode type labels now use the darker graph ink; all eight palette colors have computed normal-text contrast coverage. Person, Location and Event use distinct stable colors rather than colliding hash assignments. Keyboard labels remain independent of color.

The full default-discovered diagnostic at a087ea7a6f482b6a7038efd0f7ebb2431e78c1bd using existing dependencies completed with 7234 passes, 79 failures and one pending test; TypeScript and production build passed. Historical failure evidence is not an exact current-base comparison and collection differences remain explicit. This diagnostic is red, not clean-install or release qualification. Exact current-main baseline comparison and affected final-source checks are recorded outside this immutable checkpoint.

## Layout and interrupted-drag corrections

Independent geometry review found overlapping bubbles in the original ellipse-region layout. The replacement assigns individual 144-unit staggered slots in deterministic topology/BFS order, with disconnected individuals in a later band. New slots exclude points within 128 units of retained automatic positions. Regression coverage measures all pair distances for the 1404-object fixture, revision additions and compact graphs. The finite 0..6000 coordinate domain holds about 1927 nominal slots; larger snapshots reduce spacing rather than hide IDs, and arbitrary crowded retained positions take precedence. This experiment does not claim unlimited collision-free layout or move saved user pins.

Fit now reads persisted graph geometry independently of the active drag preview, so keyboard Fit during an unfinished connected-node drag restores the correct camera in one action without saving the drag. A component regression covers that interrupted flow.

Exact current-main copied-dependency diagnostic comparison completed: base 5d116c9d7304b8a91605ebfccf0969bdd77b5f63 has 7224 passing cases, 79 failures and one pending; candidate a087ea7a has 7234 passing cases, the identical 79 failures and one pending. No existing test changed status and no case was removed. Both have the same eight collection failures: seven pdf.worker.min.mjs?url import denials caused by the shared dependency location, plus the existing BuildCompose mock export error. Those are explicit incomplete-collection limits, not a passing full suite. The later contrast, spacing and interrupted-drag corrections require affected final-source checks and renewed review.


## Transferred collection prerequisite and integrated qualification

The CI owner explicitly transferred only BuildCompose.integration.test.tsx in
local pinned commit 231637c726dba5ddf6687e44dadd573c4d72665a on
codex/ci-buildcompose-lease-transfer, in
Docs/Plans/HANDOFF-CI-additive-fast-gate.md. It supersedes that one file lease in
PR #2298 at b1b95d839290cf85bfc8f65376806129cf41f49b; CI retains all other
paths and responsibilities. Adopt only the test-file diff from
b237a4179f3963e4c1ca0049a9a22cb307efc21d, parent
ad540611325bf0e1756654c163f2fa1acfeaba1e. This restores real selected-World
exports and committed snapshot prerequisites; every test declaration and assertion
remains unchanged. It does not repair the separate legacy Compose contract failures.

Remote main bcb50c7b05ac5a5fea287617721fbe98e0638b38 and all 52 open PR file
sets were rechecked before adoption. Only #2298 overlaps the new file, covered by
the explicit transfer. Historical #2326 is unchanged at b30833ede97cb4c79acf17a1fe55ff50446c7452
and its old canvas overlap was already reconciled by the predecessor. The new
current-main saved-statblock and source-gold changes are preserved at integration.

The user-run official verifier produced genuine fresh-install exact-source hosted
qualification for published 71a990c26552dfe2b1261d83ad402f763188ed2a: 1320 selected
cases, collection parity, type/build and clean boundaries passed; independent
artifact audit passed. Full discovery remained red at 7469 passing, 160 failing
and one pending, with the BuildCompose module export as the sole collection error.
The original receipt is retained unchanged. Those results do not qualify a later
source SHA. Reverify the transferred harness on base and candidate, retain all
legacy failures and omissions, obtain exact-source final qualification and review,
and do not treat shipping authorization as completed browser acceptance. The agent's
earlier npm network denial is not retried or bypassed.

## Browser-feedback navigation correction

Alan reported that navigating by dragging grabs nodes instead of panning. Root
assigned the bounded correction within this graph slice: full-corpus views default
to Pan graph, with an explicit Move nodes mode for layout edits. Ordinary clicks
still select. Node-origin pans do not write layout or start creation; canceled
pan/move gestures, focused-node keyboard navigation, connector ports, Fit and
World changes retain their existing safety boundaries. Legacy non-full canvas
callers keep their direct node-drag behavior. No topology, isolate filtering,
degree sizing, type mapping, naming repair or live data change belongs to this fix.

Before editing, main bcb50c7 and all 52 open PR path sets were rechecked; only
unchanged historical #2326 overlaps the already-owned canvas paths. The source
change requires new exact-head review/qualification and a refreshed preview.
Earlier caa07661 receipts remain immutable historical evidence, not a pass for the
new source. Browser feedback is not completion of browser acceptance.

Navigation review corrected capture/click handling on controlled revision and
World changes, cancellation across disabled/re-enabled editing, and pressed-mode
button hover/focus contrast. All 156 affected canvas/native tests and production
TypeScript/build pass with existing dependencies. The native integration witness
checks that panning does not alter stored positions or call native graph writes,
while explicit Move nodes still saves presentation positions. These are source
diagnostics; final exact-SHA qualification and browser recheck remain separate.
