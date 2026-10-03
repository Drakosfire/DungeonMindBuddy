# HANDOFF — DEMO: Plan navigation shell

**Status:** FROZEN — PR #886 remains a draft at product head `935bf04c48ff7ca0b45b8d08f4f4f433107d5fac`; Page path lease transferred 2026-10-03.
**Owner:** DEMO.
**Base:** Buddy `origin/main@1ded2275349f4e9ada1b67a6ab4f6061f9c2465e` (merged #885).
**Branch/worktree:** `codex/demo-plan-nav-shell` at `/home/drakosfire/.codex/worktrees/demo-plan-nav-shell/DungeonMindBuddy`.
**PR topology:** parallel-independent from RAKE’s recap-local presentation lane; no shared paths or runtime. One implementation PR: `DEMO: stabilize Plan navigation and Edit shell`.

## 2026-10-03 lease settlement

PRIME froze #886 at exact product head `935bf04c48ff7ca0b45b8d08f4f4f433107d5fac`;
its browser geometry witness remains outstanding and the draft has not been
merged or accepted. PRIME transferred the exclusive write lease for
`PlanSurfacePage.tsx` and `PlanSurfacePage.test.tsx` to
[`HANDOFF-DEMO-world-plan-save-fidelity-guard.md`](HANDOFF-DEMO-world-plan-save-fidelity-guard.md).
This PR is not rebased or edited while the guard is active. PRIME will re-anchor
it after the guard merges, resolve both Plan-file changes, and retain the
independent visual witness gate.

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
- `apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx` — original shell/tool scope retained, but write ownership transferred to the World Plan fidelity guard until its merge and #886 re-anchor
- `apps/live-control-ui/src/planSurface/PlanSurfacePage.test.tsx` — original shell/context assertions retained, but write ownership transferred to the World Plan fidelity guard until its merge and #886 re-anchor
- `apps/live-control-ui/src/planSurface/WorldPlanEditHost.integration.test.tsx`
- `apps/live-control-ui/src/planSurface/PlanSurfaceGraphInformation.integration.test.tsx` — repair its AppChrome provider harness and assert the existing projection-backed EditHost search remains discoverable; no Graph/product behavior changes
- `apps/live-control-ui/src/ui/VisualContract.stories.tsx` — the existing `EditHostDockResponsive` fixture only; add the production `WorldPlanSurfaceContext` contribution and required providers without changing product/runtime behavior
- `apps/live-control-ui/tests/ui-visual.pw.ts` — assert stable nav/context geometry, desktop workspace-only inset, Edit containment, and mobile overlay/full-width behavior for the existing mounted EditHost dock story
- this handoff

PRIME approved the Graph integration harness path and, on 2026-10-03, the two visual-fixture paths above as test-only lease extensions. They do not authorize a new product surface or runtime behavior.

The fetched base includes the unrelated corpus merges #884 (`4509433ce6758f1c852afed68cf18a10d5ae7cb0`) and #885 (`1ded2275349f4e9ada1b67a6ab4f6061f9c2465e`). PR #885 changed only `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/IronVeilHouse.md`. The current open PR inventory is #869, #865, #844, #826, #798, #781 and #763. PRIME checked those PRs for the shell paths; none overlap. #865 conversation files remain excluded. `apps/live-control-ui/src/planSurface/planSurface.css` is exclusively leased to RAKE and will not be edited. RAKE’s concurrent recap lane owns the nine paths named in its activation message: IngestionModule and test, WorldGraphRecapProjection and test, GraphReviewAuthorNodeDrawer/Host, PublishedRecapLocalAuthoring and test, and `planSurface.css`, plus its handoff. No shared port, database, provider or runtime is leased here; DOGFOOD owns live UI 5202/API 7866 and its current route/draft.

## Required verification and acceptance

- Mounted tests at the AppChrome and real World Plan/EditHost boundary prove measured shared chrome bounds, stable navigation/context composition, Edit open/close, one canonical accessible page title, concise local-save guidance, and no repeated visible title in the canvas frame. The Graph objects/search panel is covered at its existing mounted projection boundary with an actual Graph projection; do not assert it from a fixture that does not provide that projection.
- Browser geometry at desktop 1280×800 and narrow 390×844 checks Edit open and closed, header/context and workspace alignment, Edit width/top/bottom against the shared shell, inspector/tool containment and absence of horizontal overflow. Graph search discoverability is covered at the mounted projection integration boundary. Use the mounted `EditHostDockResponsive` story with the production World Plan context component and no API/DB/live data. Never change DOGFOOD’s route or draft.
- Run focused AppChrome, EditHost, PlanSurfacePage, WorldPlan EditHost integration and PlanSurfaceShell tests. Preserve inherited failures explicitly.

## Current verification state

- `git diff --check` passes. The focused eight-file Vitest run at the current head completed with 171 passed and 13 failed. All 13 failures were present in the fetched `main` comparison: 11 `AppChrome.surfaceInteraction.test.tsx` cases fail because their harnesses omit `PeekRegionProvider`, and two `PlanSurfaceShell.test.tsx` cases cannot find the `Open` button. The repaired projection-backed Graph integration test passes 4/4, including the `Find objects` search assertion. The seven-file baseline run was 166 passed/13 failed; the corresponding head run was 167 passed/13 failed before adding the four passing Graph integration cases. `tsc --noEmit --pretty false -p tsconfig.app.json` reports the same inherited `TS2503: Cannot find namespace 'JSX'` at `src/statblocks/publication/ThreatPublicationPanel.tsx:553` on both fetched `main` and this head; no changed-file type error was reported.
- The approved visual TypeScript check reports no errors for `VisualContract.stories.tsx` or `tests/ui-visual.pw.ts`. The full app typecheck still reports only the inherited JSX namespace error noted above.
- The isolated static visual fixture at `/tmp/demo-plan-nav-shell-fixture/index.html` is not an AppChrome witness. Initial in-app navigation to `http://127.0.0.1:18765/` timed out after 31.392 seconds; blank-tab creation and `getState()` calls timed out after 33.049 and 31.698 seconds, with no denial reason in their tool results. Host `curl -I` returned HTTP 200. The mounted Ladle story now includes the production World Plan surface context, and `tests/ui-visual.pw.ts` contains the approved geometry assertions. The in-app browser attempt to open `http://127.0.0.1:5184/?story=visual-contract--edit-host-dock-responsive&mode=preview` returned `net::ERR_BLOCKED_BY_CLIENT`. The Ladle/Vite server also reported that `/tmp/demo-plan-nav-shell-deps/node_modules/@ladle/react/typings-for-build/app/index.html` was outside its serving allowlist. No screenshot or browser geometry was obtained; no alternate browser, endpoint or route was tried. No DOGFOOD UI/API port or route was used.
- DOGFOOD’s live route and draft were not opened or changed.

No API, schema, graph/state mutation, Plan conversation, Canvas package, shared contract redesign or runtime restart is in scope. If the fix needs a path outside this lease, return the exact path and reason to PRIME before editing it.
