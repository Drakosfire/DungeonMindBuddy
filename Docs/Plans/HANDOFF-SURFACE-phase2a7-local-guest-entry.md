# SURFACE: public local guest entry

Status: ACTIVE under Alan's explicit authorization to reconcile, review, and merge this guest-entry slice after all applicable gates. It is a bounded route/auth composition change; hosted authentication and API authority remain unchanged.

Topology: replacement for stale draft PR #2262, whose original stacked base predates the merged graph-route work. Graph-route PR #2276 merged at `a22b77a406c6575eea7cc073139fb0774191cf50`; current remote main at re-anchor is that same SHA. This replacement applies only the five guest-owned files from the prior candidate `907f287f3c54169f6078f696d291d7b58801998d` onto merged graph main. Leave stale #2262 unchanged.

Branch / isolated checkout: `codex/guest-after-graph-20261109` / `/media/drakosfire/Projects/.codex/2026-11-08/task/buddy-graph-integration`. The old #2262 branch stays an open draft until the replacement PR is reviewed; no automatic closure is planned.

Current exact guest patch is five files: this handoff, `App.tsx`, `AppChrome.tsx`, `CompactAppNavigation.tsx`, and `App.guestEntry.test.tsx`. Do not pull inherited stack changes into the replacement. The old #2262 PR and branch remain untouched. This task-owned candidate must receive exact-head review and verification before publication.

## User outcome and security boundary

An unauthenticated visitor opening only the canonical bare root URL `/` reaches Buddy’s local World Surface and can create/resume a local World, author a small graph, write notes, save in IndexedDB, reload/reopen and export a validated package without signing in. The root entry performs no `/api/auth/session`, selected-World, hosted World, graph retrieval, or model request. It never makes the local World look like a published World or account save.

The public condition is deliberately strict: pathname `/` with an empty query and hash. Root URLs carrying selectors/auth-return parameters, every other path, and unknown/malformed paths remain in the existing `HostedAuthGate` → `SelectedWorldProvider` composition. Existing hosted pages and server/API guards are unchanged. Clicking primary navigation toward Plan/Play/Ingest/Build/Combat leaves the local shell and enters that protected flow; Back to canonical `/` returns to the guest Surface.

Guest composition reuses `AppChrome` primary navigation and the existing `LocalWorldSurface`. That Surface includes the local graph editor from the separately reviewed #2276 slice; the guest route does not add a second graph store or launcher. Navigation hides the hosted World chooser and published Graph launcher, which could otherwise issue hosted World reads when opened. It omits `IndexAgentConversation`, graph retrieval/projection providers and hosted agent/tool hosts. Local graph, note, save, and export operations remain browser-local and do not call model/provider endpoints. No new server access, public API, guest account, route wildcard, or auth bypass is introduced.

## Exclusive write set

- `Docs/Plans/HANDOFF-SURFACE-phase2a7-local-guest-entry.md`
- `apps/live-control-ui/src/App.tsx`
- `apps/live-control-ui/src/chrome/AppChrome.tsx`
- `apps/live-control-ui/src/chrome/CompactAppNavigation.tsx`
- `apps/live-control-ui/src/App.guestEntry.test.tsx` (new)

No `SelectedWorldContext` or API server change, hosted auth policy change, global API client change, database/schema/lockfile/dependency change, editor/package implementation, production deployment, user-data manipulation, graph renderer, or model/provider work. The path allowlist is exclusive for this slice. If an additional shared auth/navigation path becomes necessary, stop and obtain a revised handoff instead of widening this lease silently.

## Acceptance and verification

- Canonical `/` in production mode mounts local storage and shared local chrome without mounting HostedAuthGate, SelectedWorldProvider, IndexAgentConversation, the hosted World chooser, or Graph launcher. A fetch spy records no network requests during guest create/write/save/reopen/export. The guest entry is production-only; development retains its existing hosted route composition for local developer workflows and tests.
- Component integration regression performs guest create → start notes → edit/autosave → unmount/remount → local resume → export and parse the real ZIP/package contents; the record and notes remain local and unchanged. Test IndexedDB through the existing native repository harness where feasible; an in-memory repository proves route composition only, not browser persistence.
- Navigation regression opens Plan from guest root, verifies that route enters HostedAuthGate, a signed-out response shows the existing login link with correct return path, and a browser Back/popstate to `/` returns to guest without a session or World fetch. Modified/native link gestures remain owned by existing navigation logic.
- Root with a query, hash, World selector, auth-error return marker, or malformed path does not enter guest mode. Existing route tests cover protected auth and World admission; add or run the focused App/navigation/auth cohort and compare inherited failures at the exact base if failures appear.
- Guest view does not display World switcher, published-graph launch, hosted agent conversation, or agent assistant. Once a local World exists, its same local Surface exposes create/rename/connect/move graph operations; tests and isolated browser verification must confirm those writes remain local. Save/export status remains explicitly browser-local.
- Run the new focused guest App tests, relevant `App.test.tsx`, `App.surfaceInteraction.test.tsx`, `App.commandAccepted.test.tsx`, `chrome/AppChrome.test.tsx`, `src/test/appNavigation.test.tsx`, auth tests, full localWorld suite, typecheck, production build, exact base→head diff and independent exact-head review. Capture a browser verification on an isolated profile/database; do not inspect/delete/alter any disclosed user World.

This change does not provide account persistence, sync, collaboration, or a claim of browser storage durability against eviction/private-mode/quota/crash. Local graph authoring is supplied by #2276, not reimplemented here. No deployment or public exposure is authorized.

## Verification recorded for this implementation head

The original #2262 component/browser evidence below applies only to its old base and head. It is historical evidence, not qualification for the current-main replacement. The replacement adds a regression that creates a local World, seeds the four-node graph, renames and adds an object, connects them, moves a node with the keyboard, unmounts/reopens the World, and verifies graph semantics/layout in repository state and exported package while asserting no fetch calls. This component test uses the existing in-memory repository harness and does not prove IndexedDB persistence; that is checked only in the explicitly authorized isolated browser run after final integration.

Exact current-main hosted safety verification, full discovered diagnostics at an appropriate checkpoint, independent current-tree review, and isolated browser interaction are pending for this replacement candidate. Do not reuse the old #2262 run/review as current evidence. Local verifier evidence is not a GitHub workflow check. The guest route must be exercised in production mode and the protected navigation/sign-in/Back and query/hash/unknown-path regressions must continue to pass.
