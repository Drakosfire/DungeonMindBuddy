# SURFACE: public local guest entry

Status: ACTIVE under Alan's standing instruction to continue the Buddy front-door plan through PRIME-led merges. This is a bounded route/auth composition slice; it does not relax hosted auth or API authority.

Topology: stacked successor to PR #2219. Exact implementation base is corrected PR #2219 head `3ab42f7f9728e506f107a7c7fa134389bf2569a7` on branch `codex/phase2a6-local-world-document-editing`; predecessor order remains #2213 → #2219 → this slice. PR #2219 is OPEN/DRAFT and still needs its predecessor stack reconciled and current-main qualification. This successor cannot merge ahead of its parents. PRIME retains sole merge authority; no deployment is authorized.

Checkout: `/home/drakosfire/Projects/.codex/blank-surface-phase1-20261107/worktrees/DungeonMindBuddy-phase2a7-guest-entry`.

Current remote default branch was fetched at `main@1a19895fd3978fcb00900bb3fc0b328d32b6781e`. Phase 1 PR #2198 merged as `dcc3d7b6b906c46edef31c9c942dbb2f99ee9ea6`; Phase 2A1 PR #2202 merged as `6712cf07d22383e72cd3085c41fec515267c8743`. PRs #2204, #2207, #2209, #2210, #2213, and #2219 remain open; #2213 remains non-mergeable on the superseded #2210 base `cd2bd138c9657487ba6ecf56f3c739ef1dc7b51d`. PR #2219 remains open/draft at exact head `3ab42f7f9728e506f107a7c7fa134389bf2569a7` and base #2213 at `02d79ceb0e767a67872e4c8c83c2a539ce6829bf`. The repository remote is `https://github.com/Drakosfire/DungeonMindBuddy.git`.

Main has an `App.tsx` path overlap from merged #2198: that commit composes the Phase 1 `BlankSurface`, while this draft depends on #2219's later LocalWorldSurface composition and adds the guest route around it. The overlap is resolved by the declared ancestry, not by rebasing this slice directly onto main: keep #2262 based on #2219, then qualify the exact cumulative tree after #2219 and its predecessors are integrated. Do not retarget #2262 to main while the parent is open. No direct `AppChrome.tsx` or `CompactAppNavigation.tsx` path change was found on current main. This is not review/acceptance of other PRs.

The corrected #2219 head passed an independent scoped review for its dual-draft recovery correction. The reviewer could not run tests in its read-only checkout (`EROFS` creating Vite temp files); the owning worktree reports 76/76 localWorld tests, typecheck, build, and diff checks. No GitHub PR-check rollup exists for that exact head. The root route change below must not start before this pinned #2219 review result; that gate is now clear for this preparatory successor.

## User outcome and security boundary

An unauthenticated visitor opening only the canonical bare root URL `/` reaches the same Buddy local World Surface and can create/resume a local World, write notes, save in IndexedDB, reload/reopen and export a validated package without signing in. The root entry performs no `/api/auth/session`, selected-World, hosted World, graph retrieval, or model request. It never makes the local World look like a published World or account save.

The public condition is deliberately strict: pathname `/` with an empty query and hash. Root URLs carrying selectors/auth-return parameters, every other path, and unknown/malformed paths remain in the existing `HostedAuthGate` → `SelectedWorldProvider` composition. Existing hosted pages and server/API guards are unchanged. Clicking primary navigation toward Plan/Play/Ingest/Build/Combat leaves the local shell and enters that protected flow; Back to canonical `/` returns to the guest Surface.

Guest composition reuses `AppChrome` primary navigation and the Buddy edit/context hosts, plus the existing `LocalWorldSurface`. Its navigation hides the hosted World chooser and published Graph launcher, which could otherwise issue hosted World reads when opened. It omits `IndexAgentConversation`, graph/retrieval/projection providers and hosted agent/tool hosts. A local note edit/export therefore remains browser-local and does not call a paid/model path. No new server access, public API, guest account, route wildcard, or auth bypass is introduced.

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
- Guest view does not display World switcher, published-graph launch, hosted agent conversation, or agent assistant. The existing local World UI does not issue model/hosted API requests, and its save/export status remains explicitly browser-local.
- Run the new focused guest App tests, relevant `App.test.tsx`, `App.surfaceInteraction.test.tsx`, `App.commandAccepted.test.tsx`, `chrome/AppChrome.test.tsx`, `src/test/appNavigation.test.tsx`, auth tests, full localWorld suite, typecheck, production build, exact base→head diff and independent exact-head review. Capture a browser verification on an isolated profile/database; do not inspect/delete/alter any disclosed user World.

This change does not provide account persistence, sync, collaboration, graph node/edge authoring, or a claim of browser storage durability against eviction/private-mode/quota/crash. The foundation chain remains serially unmerged; no successor integration/deployment is authorized here.

## Verification recorded for this implementation head

- Guest integration suite: `src/App.guestEntry.test.tsx`, 6/6 passing. It creates/saves a local World, edits/saves notes, remounts/resumes the same in-memory test repository, downloads a real ZIP and decodes it, checks the package title and note bytes, confirms no fetch calls on the guest root, and verifies hosted navigation/sign-in/Back plus query/hash/unknown-path protection. The repository is intentionally in-memory in this component test; it proves composition and package/export wiring, not IndexedDB durability.
- Production browser smoke on the unique origin `http://127.0.0.1:4178/`: created “Phase 2A7 Smoke World,” wrote a note, observed it save in IndexedDB, reloaded, resumed the World, and saw the note restored. The browser profile is isolated from existing app origins by the dedicated port. Native export download was not completed in this smoke; ZIP export/decode is covered by the component integration test.
- Focused app/chrome/navigation/auth cohort on this head: 80 passed, 7 failed. The exact same 7 failures reproduced on pinned parent `3ab42f7f9728e506f107a7c7fa134389bf2569a7` with 37 passed, 7 failed; all are in `App.test.tsx` and `src/test/appNavigation.test.tsx` and retain the same failure points/reasons. Failures concern existing selected-World fetches under this runner and route shell expectations, not the new production-only guest branch. Modified/non-primary click interception coverage remains in `src/test/appNavigation.test.tsx` and passed where selected.
- `tsc -b` passed. Production `vite build` passed; it reports the existing dynamic/static import warnings for `connectedPageApi.ts` and `localWorldPackageV1.ts`, plus the existing >500 kB chunk warning. `git diff --check` passed.
- Verification used the already-installed Phase 2A5 dependency tree by temporary ignored symlinks; no packages or lockfiles were changed. The production build output is ignored build output, not part of the diff.
- Independent exact-working-tree review against pinned parent `3ab42f7f9728e506f107a7c7fa134389bf2569a7` returned PASS. The reviewer checked the production-only canonical route guard, protected route composition, omitted hosted World/graph/agent/tool hosts, shared chrome reuse, test coverage, and scope. The reviewer did not rerun tests. Current GitHub CI is pending after publication; this review does not mark the predecessor stack accepted or authorize merge/deployment.
