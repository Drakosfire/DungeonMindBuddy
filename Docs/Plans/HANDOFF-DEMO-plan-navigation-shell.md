# HANDOFF — DEMO: Plan navigation shell

**Status:** SETTLED — PR #886 merged at `4efada56aa93d529bf49128d82ba2d097b074af1` from reviewed/tested head `502b54d713e32e48f160182170c87b4f41fca990`. The focused suite passed 187/187, the isolated desktop/mobile geometry gate passed 1/1, and the Page/shell lease is closed.
**Owner:** DEMO.
**Original activation base:** Buddy `origin/main@1ded2275349f4e9ada1b67a6ab4f6061f9c2465e` (merged #885).
**Current branch/worktree:** `codex/demo-plan-nav-shell-geometry-head` at `/home/drakosfire/.codex/worktrees/plan-nav-shell-restack/DungeonMindBuddy`.
**Assigned PR:** #886, `DEMO: stabilize Plan navigation and Edit shell`.
**PR topology:** serial. PRIME reviewed and merged #886 before successor work; the first saved-Plan card projection remains BLOCKED on RAKE's parser-conformance gate and a fresh ACTIVE handoff.

## 2026-10-04 lease reconciliation

The earlier #889 fidelity-guard freeze ended when #889 merged at
`8dc639f06e05cf1809f42ecaba4c791ef21af66b`; #886 then owned the bounded Page
and shell geometry slice. Current Buddy main is
`4efada56aa93d529bf49128d82ba2d097b074af1`.
It includes #904 at `fb1c48d622c9d8d404b1dddb5d5f618e03cc7ef0`, #906 at
`6feb3059b2da4d2ec29966ce9723f0effc70108f`, #907 at
`d8e861661716d2fa8c1fb1e3e56ef08268d32da8`, and #905 plus its follow-up
authority sync at `cafbe54c` and `de9e2a1e`. #904's six-path lease is settled;
#906's mounted-test repair is merged and its lease is closed.

PRIME's 2026-10-04 sequencing decision was serial: rebase #886 onto current main,
drop the duplicate #906 blank-Plan wait repair, preserve the #904 composer
integration, and prove desktop/mobile geometry on the isolated synthetic Ladle
story. #886 merged at `4efada56aa93d529bf49128d82ba2d097b074af1` from tested
head `502b54d713e32e48f160182170c87b4f41fca990`. The focused eight-file suite
passed 187/187 and the mounted geometry gate passed 1/1. `PlanSurfacePage.tsx`
and the shell/test paths are released from this lease. The first-card handoff is
still BLOCKED: PRIME assigned RAKE the editor/server parser-conformance repair
after a v2 duplicate-edge mismatch was found; no card code is active.

At the start of final publication, remote #886 was Draft at
`717727c33fe70fc154aee291e4397e2d53ac425c` and its body described an earlier
candidate. The body was replaced with exact-head evidence before PRIME's review
and merge. No allocation here authorizes use of the operator's UI 5202/API 8000
or DOGFOOD 5203. SERVER owns the operator runtime; all geometry evidence below
is from an isolated synthetic preview.

## Blocked action and reproduction

On the Elderwyld Plan document `9811d105-b075-4674-8358-0111bd458ce2`, DOGFOOD reports that opening Edit shifts the workspace and primary navigation, the panel starts below the top edge, and node search is not discoverable. I have not changed or used the live route. Source inspection found a fixed `--app-chrome-top` fallback (5.5rem/8rem/10.5rem) while navigation and context can wrap; this is a candidate geometry cause to validate in the isolated browser witness, not a live-confirmed diagnosis.

The current Plan toolbar already registers `World Graph objects` in the EditHost with its panel open by default. Preserve that existing Graph search location and make it discoverable through the composed shell; do not add a second search or navigation contract.

DOGFOOD also reports repeated Plan identity on saved document `d96904d1-d20d-4b78-8d22-c2c84d81cdc3`: the selector, a large `WORLD PLAN`/title/draft-help heading, the Edit frame identity, and the document content repeat the same context. Keep the document content and one canonical accessible page title; keep the World/document selector and its existing actions in the composed context bar; remove the redundant visible page heading/kicker and shorten the save guidance; do not repeat the selected title in the editor frame. The rapid-scroll papyrus flash is a separate, lower-priority finding and is excluded.

## Invariant

The primary navbar and surface context/subnav stay horizontally stable when Edit opens. The Plan workspace below that shared chrome reserves exactly the docked EditHost width and starts at the rendered chrome boundary. Navigation/context wrapping may change the measured drawer top, but must not move the navbar or leave a stale offset after the header scrolls above the viewport. Tools and inspectors remain within their host bounds and do not cover the chrome. On narrow screens Edit overlays the workspace, which retains its full width. The document’s canonical content and accessible page title remain; redundant visible page-level and editor-frame titles are removed, while the context bar carries the World/document selector and existing actions. Save/local-draft meaning stays visible and accurate. Existing route, World/document identity, graph and navigation contracts remain unchanged.

## Historical exclusive write lease — closed at merge

The following paths were exclusive during #886. The lease ended when #886
merged at `4efada56aa93d529bf49128d82ba2d097b074af1`; this list grants no
current write authority.

Modify only the paths needed from this allowlist:

- `apps/live-control-ui/src/chrome/AppChrome.tsx`
- `apps/live-control-ui/src/chrome/AppChrome.test.tsx`
- `apps/live-control-ui/src/chrome/AppChrome.surfaceInteraction.test.tsx`
- `apps/live-control-ui/src/surfaceInteraction/editHost/EditHost.tsx`
- `apps/live-control-ui/src/surfaceInteraction/editHost/EditHost.test.tsx`
- `apps/live-control-ui/src/styles.css` — AppChrome/EditHost shell selectors only
- `apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx` — #886 retains shell/tool write ownership after #889 settlement
- `apps/live-control-ui/src/planSurface/WorldPlanEditHost.integration.test.tsx`
- `apps/live-control-ui/src/planSurface/PlanSurfaceGraphInformation.integration.test.tsx` — repair its AppChrome provider harness and assert the existing projection-backed EditHost search remains discoverable; no Graph/product behavior changes
- `apps/live-control-ui/src/ui/VisualContract.stories.tsx` — the existing `EditHostDockResponsive` fixture only; add the production `WorldPlanSurfaceContext` contribution and required providers without changing product/runtime behavior
- `apps/live-control-ui/tests/ui-visual.pw.ts` — assert stable nav/context geometry, desktop workspace-only inset, Edit containment, and mobile overlay/full-width behavior for the existing mounted EditHost dock story
- this handoff

PRIME approved the Graph integration harness path and, on 2026-10-03, the two visual-fixture paths above as test-only lease extensions. They do not authorize a new product surface or runtime behavior.

`PlanSurfacePage.test.tsx` is outside the current #886 write set. Its bounded
#906 repair is merged, and this branch drops the duplicate wait assertion rather
than retaining a second copy of that fix.

Before #886 publication, the open-PR list was refreshed after fetching main.
That inventory is historical and must be refreshed before a successor lane.
Adjacent file lists were checked: #887 remains prototype-only under `prototypes/plan-play-cards/`;
#869 changes statblock editor/workbench paths; #781 changes semantic-action
projection paths; #844, #760, and #761 are handoff/design docs; #826 is
WorldSpace server/lockfile code; #798 is backlog-only; #765 and #763 are Rules
Lawyer server/UI paths; #764 changes Rules Lawyer plus Plan projection catalog
registration. None overlaps this lease's AppChrome, EditHost, Plan Page, shell
CSS, mounted integration, or visual-story paths. Recheck before the serial card
successor. The old RAKE recap-lane inventory and its `planSurface.css` hold are
historical; this #886 candidate still does not edit `planSurface.css` or any
shared UI package. No port, database, provider, or runtime is shared here.

## Required verification and acceptance

- Mounted tests at the AppChrome and real World Plan/EditHost boundary prove measured shared chrome bounds, stable navigation/context composition, Edit open/close, one canonical accessible page title, concise local-save guidance, and no repeated visible title in the editor frame. The Graph objects/search panel is covered at its existing mounted projection boundary with an actual Graph projection; do not assert it from a fixture that does not provide that projection.
- Browser geometry at desktop 1280×800 and narrow 390×844 checks Edit open and closed, header/context and workspace alignment, Edit width/top/bottom against the shared shell, inspector/tool containment and absence of horizontal overflow. Graph search discoverability is covered at the mounted projection integration boundary. Use the mounted `EditHostDockResponsive` story with the production World Plan context component and no API/DB/live data. Never change DOGFOOD’s route or draft.
- Run focused AppChrome, EditHost, PlanSurfacePage, WorldPlan EditHost integration and PlanSurfaceShell tests. Preserve inherited failures explicitly.

## Current verification evidence

- `origin/main` was freshly fetched at `de9e2a1ea16adb2703353f54813758ade33857ab` before final verification. `git diff --check origin/main...HEAD` passes for the rebased candidate.
- The focused eight-file Vitest run passed: 8 files, 187 tests. A parallel run briefly timed out in two `PlanSurfaceShell` cases while the visual build/typecheck ran; the isolated rerun passed all 187. Existing React `act(...)` and duplicate-key warnings remain non-failing.
- `npm run ui:visual -- --grep "keeps Plan chrome stable while Edit docks"` passed 1/1 on the mounted `EditHostDockResponsive` Ladle story, built from this branch with the production `WorldPlanSurfaceContext`, a valid local-draft identity, and matching Plan publication/EditHost targets. The run used bundled Node v24; the shell default Node v18.19.0 is below Playwright 1.63's Node 20 minimum. At desktop 1280×800, the drawer measures 380px wide at x=0, aligns within 1px of the rendered header bottom, ends at y=800, and contains its tool body. The Plan workspace shifts and shrinks by exactly 380px between open and closed states; nav/context bounds stay identical and document width remains 1280px. At mobile 390×844, the drawer is at least 360px wide and stays inside viewport bounds; its top tracks the header, the workspace retains more than 75% of viewport width, nav/context/workspace geometry stays stable on close/reopen, drawer content stays contained, and document width never exceeds 390px.
- The first geometry attempt found a fixture-only 336px desktop overflow: an inline `width: 100%` overrode the production dock sizing. The Plan fixture now uses the actual World/local-draft identity and publication target and leaves width to production shell CSS; the test now asserts the declared 380px inset relative to closed state, rather than an unrelated absolute outer margin.
- `npx tsc --noEmit --pretty false -p tsconfig.app.json` reports one error on both this head and a detached checkout of exact current main: `src/statblocks/publication/ThreatPublicationPanel.tsx(553,77): error TS2503: Cannot find namespace 'JSX'.` This path is outside the #886 diff; no new type error was reported. The Playwright/Ladle build completed successfully.
- No DOGFOOD route, operator Plan, API, or user state was opened or changed. Ports 5202, 8000, and 5203 were not used. All responsive evidence came from the isolated synthetic story and local browser automation.

No API, schema, graph/state mutation, Plan conversation, shared UI package, shared contract redesign or runtime restart was in scope. This #886 lease is settled and grants no current write authority; a successor needs its own pinned ACTIVE handoff.
