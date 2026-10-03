# HANDOFF — DEMO: Plan navigation shell

**Status:** ACTIVE — PR #886 is re-anchored on current main and remains a draft; browser geometry witness is still pending.
**Owner:** DEMO.
**Base:** Buddy `origin/main@8dc639f06e05cf1809f42ecaba4c791ef21af66b` (merged #889).
**Branch/worktree:** `codex/demo-plan-nav-shell` at `/tmp/demo-plan-nav-reanchor-20261003` (isolated writable clone for the authorized re-anchor).
**PR topology:** parallel-independent from RAKE’s recap-local presentation lane; no shared paths or runtime. One implementation PR: `DEMO: stabilize Plan navigation and Edit shell`.

## 2026-10-03 lease settlement

PRIME merged the World Plan save-fidelity guard as #889 at
`8dc639f06e05cf1809f42ecaba4c791ef21af66b` and directed DEMO to re-anchor #886.
The frozen product head was
`935bf04c48ff7ca0b45b8d08f4f4f433107d5fac`; its three product commits are now
rebased onto the exact #889 merge. The Plan page changes retain the original
navigation-shell/title scope, and the #889 save guard remains in the base.
This replaces the earlier temporary Page-path transfer. The branch remains a
draft and is not accepted or merge-ready: the required desktop/mobile browser
geometry witness is outstanding. Do not merge the frozen pre-rebase head.

## Blocked action and reproduction

On the Elderwyld Plan document `9811d105-b075-4674-8358-0111bd458ce2`, DOGFOOD reports that opening Edit shifts the workspace and primary navigation, the panel starts below the top edge, and node search is not discoverable. I have not changed or used the live route. Source inspection found a fixed `--app-chrome-top` fallback (5.5rem/8rem/10.5rem) while navigation and context can wrap; this is a candidate geometry cause to validate in the isolated browser witness, not a live-confirmed diagnosis.

The current Plan toolbar already registers `World Graph objects` in the EditHost with its panel open by default. Preserve that existing Graph search location and make it discoverable through the composed shell; do not add a second search or navigation contract.

DOGFOOD also reports repeated Plan identity on saved document `d96904d1-d20d-4b78-8d22-c2c84d81cdc3`: the selector, a large `WORLD PLAN`/title/draft-help heading, the Edit frame identity, and the document content repeat the same context. Keep the document content and one canonical accessible page title; keep the World/document selector and its existing actions in the composed context bar; remove the redundant visible page heading/kicker and shorten the save guidance; do not repeat the selected title in the canvas frame. The rapid-scroll papyrus flash is a separate, lower-priority finding and is excluded.

## Invariant

The primary navbar and surface context/subnav stay horizontally stable when Edit opens. The Plan workspace below that shared chrome reserves exactly the docked EditHost width and starts at the rendered chrome boundary. Navigation/context wrapping may change the measured drawer top, but must not move the navbar or leave a stale offset after the header scrolls above the viewport. Tools and inspectors remain within their host bounds and do not cover the chrome. On narrow screens Edit overlays the workspace, which retains its full width. The document’s canonical content and accessible page title remain; redundant visible page-level and canvas-frame titles are removed, while the context bar carries the World/document selector and existing actions. Save/local-draft meaning stays visible and accurate. Existing route, World/document identity, graph and navigation contracts remain unchanged.

## Exclusive write lease

Modify only the paths needed from this allowlist:

- `apps/live-control-ui/src/chrome/AppChrome.tsx`
- `apps/live-control-ui/src/chrome/AppChrome.test.tsx`
- `apps/live-control-ui/src/chrome/AppChrome.surfaceInteraction.test.tsx`
- `apps/live-control-ui/src/surfaceInteraction/editHost/EditHost.tsx`
- `apps/live-control-ui/src/surfaceInteraction/editHost/EditHost.test.tsx`
- `apps/live-control-ui/src/styles.css` — AppChrome/EditHost shell selectors only
- `apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx` — original shell/tool/title scope only; preserve the #889 save guard in the base and do not change its save-safety behavior
- `apps/live-control-ui/src/planSurface/PlanSurfacePage.test.tsx` — original shell/context assertions only; save-guard coverage is in the base and is outside this PR's change
- `apps/live-control-ui/src/planSurface/WorldPlanEditHost.integration.test.tsx`
- `apps/live-control-ui/src/planSurface/PlanSurfaceGraphInformation.integration.test.tsx` — repair its AppChrome provider harness and assert the existing projection-backed EditHost search remains discoverable; no Graph/product behavior changes
- `apps/live-control-ui/src/ui/VisualContract.stories.tsx` — the existing `EditHostDockResponsive` fixture only; add the production `WorldPlanSurfaceContext` contribution and required providers without changing product/runtime behavior
- `apps/live-control-ui/tests/ui-visual.pw.ts` — assert stable nav/context geometry, desktop workspace-only inset, Edit containment, and mobile overlay/full-width behavior for the existing mounted EditHost dock story
- this handoff

PRIME approved the Graph integration harness path and, on 2026-10-03, the two visual-fixture paths above as test-only lease extensions. They do not authorize a new product surface or runtime behavior.

The current remote main includes #884 (`4509433ce6758f1c852afed68cf18a10d5ae7cb0`), #885 (`1ded2275349f4e9ada1b67a6ab4f6061f9c2465e`), and #889 (`8dc639f06e05cf1809f42ecaba4c791ef21af66b`). PR #885 changed only `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/IronVeilHouse.md`. The 2026-10-03 GitHub audit found 13 open PRs: #886, #887, #869, #865, #844, #826, #798, #763, #781, #761, #760, #764, and #765. No other open PR changes this handoff's leased paths. #865 conversation files remain excluded. `apps/live-control-ui/src/planSurface/planSurface.css` is exclusively leased to RAKE and will not be edited. RAKE’s concurrent recap lane owns the nine paths named in its activation message: IngestionModule and test, WorldGraphRecapProjection and test, GraphReviewAuthorNodeDrawer/Host, PublishedRecapLocalAuthoring and test, and `planSurface.css`, plus its handoff. No shared port, database, provider or runtime is leased here; DOGFOOD owns live UI 5202/API 7866 and its current route/draft.

## Required verification and acceptance

- Mounted tests at the AppChrome and real World Plan/EditHost boundary prove measured shared chrome bounds, stable navigation/context composition, Edit open/close, one canonical accessible page title, concise local-save guidance, and no repeated visible title in the canvas frame. The Graph objects/search panel is covered at its existing mounted projection boundary with an actual Graph projection; do not assert it from a fixture that does not provide that projection.
- Browser geometry at desktop 1280×800 and narrow 390×844 checks Edit open and closed, header/context and workspace alignment, Edit width/top/bottom against the shared shell, inspector/tool containment and absence of horizontal overflow. Graph search discoverability is covered at the mounted projection integration boundary. Use the mounted `EditHostDockResponsive` story with the production World Plan context component and no API/DB/live data. Never change DOGFOOD’s route or draft.
- Run focused AppChrome, EditHost, PlanSurfacePage, WorldPlan EditHost integration and PlanSurfaceShell tests. Preserve inherited failures explicitly.

## Current verification state

- RAKE DUTY compared current main `8dc639f06e05cf1809f42ecaba4c791ef21af66b` with frozen #886 head `935bf04c48ff7ca0b45b8d08f4f4f433107d5fac` using the same eight-file cohort. Main had 169 passed/17 failed; the frozen head had 171 passed/13 failed. The same 13 failures were present on both refs. Main had four additional failures in `PlanSurfaceGraphInformation.integration.test.tsx`; #886's `PeekRegionProvider` wrapper repairs those four. #889 did not change the 13 shared failures.
- After re-anchoring, the eight-file run at the current product head first had 174 passed/13 failed. I then repaired the in-lease `AppChrome.surfaceInteraction.test.tsx` harnesses by wrapping them in the required `PeekRegionProvider`. The rerun completed with 185 passed/2 failed. All 11 AppChrome surface-interaction cases now pass. The projection-backed Graph integration tests pass 4/4, including the `Find objects` search assertion.
- The two remaining failures are in `PlanSurfaceShell.test.tsx`, which is outside this handoff's write lease. `bridges the exact managed Plan editor into reviewed Agent composition without direct save` cannot find button `Open` at line 413; `creates and reopens prep in the verified managed World without a C2 packet` cannot find button `Open` at line 3514. They also failed on the frozen head and current main. No change was made to that test or product path; PRIME must transfer or extend the lease before either is edited.
- `git diff --check` passes. `rtk tsc --noEmit --pretty false -p tsconfig.app.json` reports one error in an unchanged file outside this lease: `src/statblocks/publication/ThreatPublicationPanel.tsx(553,77): error TS2503: Cannot find namespace 'JSX'.` The approved visual TypeScript check reports no errors for `VisualContract.stories.tsx` or `tests/ui-visual.pw.ts`.
- The isolated static visual fixture at `/tmp/demo-plan-nav-shell-fixture/index.html` is not an AppChrome witness. Initial in-app navigation to `http://127.0.0.1:18765/` timed out after 31.392 seconds; blank-tab creation and `getState()` calls timed out after 33.049 and 31.698 seconds, with no denial reason in their tool results. Host `curl -I` returned HTTP 200. The mounted Ladle story now includes the production World Plan surface context, and `tests/ui-visual.pw.ts` contains the approved geometry assertions. The in-app browser attempt to open `http://127.0.0.1:5184/?story=visual-contract--edit-host-dock-responsive&mode=preview` returned `net::ERR_BLOCKED_BY_CLIENT`. The Ladle/Vite server also reported that `/tmp/demo-plan-nav-shell-deps/node_modules/@ladle/react/typings-for-build/app/index.html` was outside its serving allowlist. A later `rtk npm run ui:visual -- --grep 'keeps Plan chrome stable'` attempt exited 127 because `playwright` is absent from the isolated dependency link. An offline install in a separate `/tmp` directory failed with `ENOTCACHED` for React metadata; installing the cached package tarballs separately failed with `EROFS` when npm tried to write to the home cache. No screenshot or browser geometry was obtained; no alternate browser, endpoint or route was tried. No DOGFOOD UI/API port or route was used.
- DOGFOOD’s live route and draft were not opened or changed.

No API, schema, graph/state mutation, Plan conversation, Canvas package, shared contract redesign or runtime restart is in scope. If the fix needs a path outside this lease, return the exact path and reason to PRIME before editing it.
