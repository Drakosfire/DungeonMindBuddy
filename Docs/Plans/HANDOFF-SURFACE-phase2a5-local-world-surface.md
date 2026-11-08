# SURFACE: first functional local World surface

Status: ACTIVE — both independent exact-head HOLD findings are fixed in the current worktree; corrected implementation awaits commit/push and exact-head re-review on existing draft PR #2213. Branch `codex/phase2a5-local-world-surface` remains based on corrected Phase 2A4 PR #2210 exact head `cd2bd138c9657487ba6ecf56f3c739ef1dc7b51d`; PR base is `codex/phase2a4-local-package-restore`. Order: #2210, then this successor. This is development authority only; no product completion, PR merge, deployment, public guest access or account adoption is implied.

Checkout: `/home/drakosfire/Projects/.codex/blank-surface-phase1-20261107/worktrees/DungeonMindBuddy-phase2a5-surface`.

## Re-anchor

`AGENTS.md` is current repository policy; `.agents/skills` is absent and legacy `.cursor` instructions are not required. Current open plan stack was checked: #2198, #2202, #2204, #2207, #2209 and #2210. #2210 remains OPEN/DRAFT at `cd2bd138c9657487ba6ecf56f3c739ef1dc7b51d`, base `codex/phase2a3-zip-transport` at `10e3f59f1187e5d4f7d65b17e0809ae992549be7`; no hosted checks were reported at activation. The independent exact-head review passed. This lane intentionally stacks on #2210 without merging it.

Read-only next-surface assessment: `/media/drakosfire/Projects/.codex/2026-11-07/task/phase2a5-local-world-surface-assessment.md`.

## Exclusive write lease

- `Docs/Plans/HANDOFF-SURFACE-phase2a5-local-world-surface.md`
- `apps/live-control-ui/src/App.tsx`
- `apps/live-control-ui/src/App.test.tsx`
- `apps/live-control-ui/src/localWorld/localWorldRepository.ts`
- `apps/live-control-ui/src/localWorld/inMemoryLocalWorldRepository.ts`
- `apps/live-control-ui/src/localWorld/indexedDbLocalWorldRepository.ts`
- `apps/live-control-ui/src/localWorld/localWorldPackageV1.ts`
- `apps/live-control-ui/src/localWorld/localWorldPackageV1.test.ts`
- `apps/live-control-ui/src/localWorld/localWorldSurface/LocalWorldSurface.tsx`
- `apps/live-control-ui/src/localWorld/localWorldSurface/localWorldSurface.css`
- `apps/live-control-ui/src/localWorld/localWorldSurface/LocalWorldSurface.test.tsx`
- `apps/live-control-ui/src/localWorld/localWorldSurface/localWorldSurface.browserHarness.html`
- `apps/live-control-ui/src/localWorld/localWorldSurface/localWorldSurface.browserHarness.tsx`
- `apps/live-control-ui/src/localWorld/localWorldSurface/localWorldSurface.browserHarness.css`

No dependency/lockfile, hosted auth/API or server routes, selected-World ownership, WorldKeeper/DM authority, account adoption, graph renderer, model/provider implementation, unrelated authoring route, merge or deployment. Return to the steward if another path or owner seam becomes necessary.

## Product outcome and boundary

On the current index/Buddy Surface, a person can explicitly create a local World, resume one from browser storage, edit its title, see truthful local save/conflict/error state, and download a validated ZIP package. A blank visit performs no local create/write. Title mutation uses the existing expected-local-revision semantic edit and records a Buddy-local history event. It preserves local identity, layout, history and any package supplemental references/assets. Package export includes the sidecar instead of silently dropping restored data.

Use shared AppChrome and Surface Interaction hosts where suitable; keep navigation and editor focus continuity. No graph entities or renderer are in this slice. Rich document body editing is deferred because the local record has no document-body model and `useWorkspaceDocumentAuthoring` directly invokes hosted snapshot/prepare/commit APIs and treats server revisions/receipts as authority. Do not adapt that hook by passing IndexedDB or a local revision into server API fields.

The aspirational product remains a guest-first, playful editable World canvas with a prominent title pencil, eventual People/Location/Event graph, local autosave, Save menu, and the same World model across surfaces. This intermediate slice does not deliver anonymous production access, graph editing, or hosted adoption. Current `HostedAuthGate` remains enabled in production; do not remove or relax it, bypass server authorization, or describe this as the finished no-account experience. Current global `SelectedWorldProvider` remains the hosted selection authority; do not map local IDs into hosted `?world=` identities. No automatic model/graph query or paid action is added.

## Contract and UX rules

- Add only the minimum `listWorlds()` capability to the existing package repository interface. Enumeration returns explicit found/empty/error semantics and stable records; no silent auto-create. Existing v2→v3 upgrade and schemas remain unchanged.
- Use one explicit app-owned IndexedDB database name. Open/list failure is an error state with retry; create and save are disabled unless storage opened. Report “Saved in this browser” only after repository success. Do not promise backup/recovery after browser eviction, private-mode restrictions or storage failure.
- Create is user initiated and uses the entered non-empty title. Resume selects exact local ID; same-name Worlds remain distinct. Keep local IDs separate from hosted World IDs.
- Title editor is keyboard-accessible with pencil/rename affordance, labelled input, Enter save, Escape cancel, and a narrow-screen layout. Capture full immutable request before awaits. Disable repeated submits while a write is pending. On CAS conflict, retain current committed record and the proposed title candidate, show conflict state, and require explicit resolution/retry. Never overwrite silently.
- Export uses codec → ZIP. It reads current World plus supplemental data, includes all supported document/asset references and bundled bytes, and downloads only after validation succeeds. External locators are metadata only; no fetch. Export error is visible and does not claim success. Save menu language is local browser save/export only, not account persistence.
- Actual test databases use unique names and are deleted by harness cleanup only. The production app uses the fixed product name and never deletes it.

## Acceptance and evidence

- Browser: empty visit causes no writes; explicit create → rename/save → reload/resume → ZIP download → validated decode yields the same local ID, title, revisions and history.
- Restore a package with bundled document and binary asset, rename it, export it, and validate exact references/bytes still exist.
- Exercise missing/unavailable/blocked IndexedDB, failed commit and export errors with no false saved/success status; retry behavior remains clear.
- Open same World through two repository connections/tabs, race title writes from one expected revision, prove one winner and retained losing candidate; no same-name identity merge.
- Repeated title-save activation yields one commit; stale completion/unmount/navigation does not mark another World saved or replace newer UI state. Pending edit navigation/reload behavior is explicit and tested.
- Verify keyboard rename/save/cancel, accessible labels/status announcements, and a narrow viewport. Capture screenshot evidence from the actual rendered UI.
- Run component/repository/package tests, all applicable `src/localWorld` tests, `App.test.tsx`, typecheck, production build, native browser harness, exact cumulative diff check and independent review. State native browser/storage limits; do not infer crash, actual quota exhaustion, eviction or cross-browser durability from this harness.

### Current implementation evidence

- `npm run typecheck` passes. The complete `src/localWorld` suite passes 54/54, including 11 Surface tests and 15 package codec tests. The new navigation regression proves an unsaved title survives selecting another World, creating a different World, and a route-style component unmount/remount; the prior World remains unchanged until an explicit save/retry. The new 2 MiB attachment regression restores repository package data, re-exports it through the codec, parses it, and compares binary bytes and references. An over-limit attachment is rejected before `structuredClone` is called. Root index Surface integration still passes.
- Cumulative cohort `npm test -- --run src/localWorld src/App.test.tsx src/App.surfaceInteraction.test.tsx src/App.commandAccepted.test.tsx src/chrome/AppChrome.test.tsx src/test/appNavigation.test.tsx --reporter=dot` passes 109 tests and fails 7 (two files). The same seven failures were reproduced at the exact parent commit `cd2bd138c9657487ba6ecf56f3c739ef1dc7b51d` in a disposable checkout: three `App.test.tsx` hosted route tests and four `src/test/appNavigation.test.tsx` hosted navigation tests. In jsdom, Node fetch cannot parse relative `/api/live/...` URLs, so existing hosted World/plan/play APIs fail. No new Phase2A5-specific failures were observed in this cohort.
- Production `npm run build` and TypeScript pass. Exact-parent JS baseline measured 86 files / 3,309,749 raw bytes / 947,204 gzip bytes. Current build: 87 files / 3,533,148 raw / 1,034,195 gzip-9 bytes. The initial index chunk changes from 547,146 raw / about 155.7 KB Vite-reported gzip to 596,041 raw / 169.5 KB Vite-reported gzip (about +49 KB raw / +13.8 KB gzip). ZIP code remains a separate 174,498-byte / 73,334-byte-gzip-9 chunk; codec validation remains in the initial graph because repository modules use it. Package imports are deferred until export, but the route is not cheaper by aggregate chunk-byte comparison. This measures build outputs, not transfer behavior, cold-start latency, idle CPU, or weak-laptop performance. Existing Vite warnings about `connectedPageApi.ts` and the package codec being both statically and dynamically imported remain; the index still exceeds 500 KB raw.
- Native Chrome on the actual app route created a local World, then the lazy-loaded Save-menu export completed and reported the validated package download. A prior native Chrome Playwright run before the lazy-import-only change exercised create, rename, reload/resume, package decode with a bundled document and binary asset, failed-save messaging, two-connection expected-revision conflict and explicit retry, at a 390×844 viewport with no horizontal overflow. It captured `/tmp/phase2a5-local-world-surface-mobile.png`. The separate harness's database was unique and cleaned up. The direct post-change check used the app's fixed browser database and created `Lazy Loaded Export Check`; it was verified as an empty-start user test browser, but the app has no World-delete affordance, so that verification record remains in that browser's local store. This is test data, not a seeded/demo World or product fixture.
- Native Chrome on a fresh isolated harness database confirmed an unsaved Alpha title survived switching to Beta, returning to Alpha, closing/remounting the Surface, and reopening Alpha. It also restored a World carrying a bundled document and 2 MiB binary asset, renamed it, then ran IndexedDB read → codec → ZIP → decode; exact references and binary bytes were preserved. Harness database `local-world-surface-test-ad84bae4-f7ec-4e03-a3b8-c73c736bd6cf` was isolated and deleted after the run. No user data was modified.
- Independent review of prior head `279c48680cce178d404c7186b25df5c41d1d3085` found two blockers: draft loss across in-app World selection/create/route transition, and re-export rejection of a valid 2 MiB restored attachment because binary bytes were JSON-stringified. The current worktree fixes both with per-local-ID volatile draft retention and pre-copy, per-member shape/size validation; component/package/native browser regressions pass. Corrected exact-head independent re-review and current hosted checks are required before closing the HOLD.
- Draft PR: https://github.com/Drakosfire/DungeonMindBuddy/pull/2213. Before these fixes GitHub confirmed `OPEN`/`DRAFT`, exact base OID `cd2bd138c9657487ba6ecf56f3c739ef1dc7b51d`, head `279c48680cce178d404c7186b25df5c41d1d3085`, and `MERGEABLE`. No hosted checks or PR reviews were present at that check. Refresh exact head/check state after publishing the corrections.

### Learning and Phase 2 follow-up

The title-only vertical slice fits the existing local repository without copying the shared editor. A title edit is an expected-local-revision mutation with a Buddy-local history entry; it preserves layout and supplemental package data. Listing local IDs and data stays inside the local repository and does not enter `SelectedWorldProvider` or hosted API authority. ZIP and validation code are not needed for the first render, though the general package codec remains in the eager dependency graph through existing repository validation imports.

The shared document editor is hosted-snapshot/prepare/commit coupled. A guest-first body-editing slice still needs an explicitly isolated anonymous route that does not relax hosted APIs/auth, an async authoring/document port with local revision identity, and an owner-defined local document/history model. It should not be achieved by mapping local IDs to hosted World IDs or passing local revisions into server fields. Continue to defer graph content/renderer, semantic entity editing, automatic model calls and account adoption until those contracts and a bounded handoff exist. Current evidence does not establish real quota exhaustion, blocked/private-mode browser behavior, abrupt-crash recovery, storage eviction guarantees, cross-tab/browser durability beyond the tested two-connection race, or low-end device performance.

## Exclusions and remaining gates

No prose/body document model, shared TipTap authoring-hook refactor, graph objects/relationships/renderer, account adoption, server/provider mutation, guest-route exception, removal of auth, automatic default World creation, or data/schema migration. Separate future design must define anonymous route isolation from selected hosted-World reads and prove server endpoints remain protected. The user-facing workflow here is an authenticated/local-operator development milestone, not the complete anonymous product. Product acceptance, stack integration, merge and deployment remain external gates.
