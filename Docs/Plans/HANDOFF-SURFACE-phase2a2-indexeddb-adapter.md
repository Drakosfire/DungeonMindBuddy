# SURFACE: local World IndexedDB adapter

Status: ACTIVE — bounded browser-storage adapter slice.
Authority: Alan's explicit continuation instruction authorizes this local adapter implementation. It does not authorize publication, Phase 1 acceptance, merge, deployment, account adoption, or renderer work.
Flow: SURFACE. Topology: stacked; branch `codex/phase2a2-indexeddb-local-world` was created from published Phase 2A1 head `d2421f9821a1a8fc60b127b28ce425aa5921ae27` (PR #2202). Its current corrective successor must include the latest #2202 fix head and remain based on `codex/phase2a1-local-world-repository`; integrate/rebase serially after #2202 and #2198 settle. Preserve both predecessor branches. Alan's standing authorization covers publishing plan branches and updating/opening draft PRs in this repository; this repair updates existing PR #2204 only. No merge or deployment is authorized.
Checkout: `/home/drakosfire/Projects/.codex/blank-surface-phase1-20261107/worktrees/DungeonMindBuddy`.
Design input: OverMind PR #106 exact draft head `7db578897e0eb40ab3672d26826eb3bbbee6007c`, `Docs/architecture/CONTRACT-local-world-execution-adoption-phase2.md`, blob `9ceb00c005a7e1a3e22c76bed22a01f501e8cb28`, supplied verbatim in the coordination thread. This implementation consumes only Buddy's Phase2A1 port; it does not import OverMind files.

## Re-anchor and ownership

Fetched current origin/main and confirmed Buddy PR #2198 remains OPEN/DRAFT at `64f166f4fceff56e238292886bf932eb6b30e367`, mergeable. PR #2202 remains OPEN/DRAFT at `d2421f9821a1a8fc60b127b28ce425aa5921ae27`, mergeable, based on #2198. GitHub currently lists no submitted reviews for #2202; the coordinating independent review is pending, so implementation must pause if it identifies a contract blocker. Open PR path lists inspected show no unrelated overlap with the new adapter/harness paths. The shared A1 contract test file is intentionally touched only to extract/reuse its test fixtures; this is the explicitly requested successor use of the completed predecessor's test evidence, with no edits to the predecessor branch.

Repository instructions are `AGENTS.md`; `.agents/skills` is absent, and repository policy says legacy `.cursor` skills are not required. Current app test/build commands are from `apps/live-control-ui/package.json`. Dexie, `idb`, and `fake-indexeddb` are not installed. Choose the browser's native IndexedDB API to avoid a new runtime dependency: this port needs one atomic database transaction across a `worlds` store and a `conflicts` store, built-in version upgrades, and expected-revision serialization. This is one IndexedDB database, not multiple persistence systems. A bounded v1→v2 migration adds the conflict lookup index. The isolated browser harness uses the system Chrome binary with a temporary profile and unique test database names; it never opens or clears a user's existing database.

## Exclusive expected write paths

- `Docs/Plans/HANDOFF-SURFACE-phase2a2-indexeddb-adapter.md`
- `apps/live-control-ui/src/localWorld/indexedDbLocalWorldRepository.ts`
- `apps/live-control-ui/src/localWorld/localWorldContractFixtures.ts`
- `apps/live-control-ui/src/localWorld/localWorldRepository.test.ts`
- `apps/live-control-ui/src/localWorld/indexedDbLocalWorldRepository.browserHarness.html`
- `apps/live-control-ui/src/localWorld/indexedDbLocalWorldRepository.browserHarness.ts`
- `apps/live-control-ui/src/localWorld/localWorldRepository.ts` (shared snapshot identity/reference validator)
- `apps/live-control-ui/src/localWorld/inMemoryLocalWorldRepository.ts` (consume the same validator as the IndexedDB adapter)

No package/lockfile, product UI, other adapter, owner service, app routes, or test-runner config changes are allowed under this lease. If tests require installing a dependency or expanding this allowlist, return to the steward first.

## Acceptance

- Implement the Phase2A1 asynchronous `LocalWorldRepository` port using native IndexedDB, preserving its local ID/revision distinction, explicit missing/error/conflict results, complete current-shape losing candidates, immutable inputs/outputs, and independent layout revision.
- Store Worlds and conflict candidates in a single named database and in object stores that participate together in the semantic transaction. Persist each semantic snapshot plus its bounded history entry atomically. Conflicts leave the committed World unchanged while saving the candidate. Do not merge objects by name.
- Create isolated unique test DB names with cleanup. Share the four-node and same-name contract fixture builders with the existing in-memory contract tests. Prove two concurrent writes at one expected revision commit once and preserve one complete losing candidate.
- Exercise actual browser reopen/reload persistence, v1→v2 schema upgrade, fail-closed incompatible future schema and recovery/readback, blocked/unavailable IndexedDB, abort preservation, layout-only writes, and alias isolation in an isolated browser context/profile. A synthetic `QuotaExceededError` may test abort/error handling, but must be labeled simulated; do not claim actual quota exhaustion unless safely and truly observed. Document that browser success does not defeat browser eviction and is not a backup.
- If the test-only `beforeWrite` hook simulates failure, keep it a test-only seam. No status may claim a durable save from the in-memory adapter, and no model/provider, WorldKeeper, DungeonMind, user database, account, or live runtime is contacted.
- The current port stores its history array in the World record and defines no retention/coverage range. This adapter preserves the full current array and does not silently prune. Long-lived authoring must settle bounded-history/coverage semantics before treating quota handling as sufficient for indefinite use.

## Deliberately excluded

No Dexie/`idb` or second store dependency, editor/UI wiring, package ZIP/import/export, source/document/assets, conflict resolution/discard UX, account adoption, semantic operation mapping, WorldKeeper/DungeonMind calls, graph renderer, demo data, production migration, merge, or deployment. The authorized publication is limited to this existing #2204 draft branch/PR.

## Verification plan and evidence limits

Run the shared in-memory contract test and bundle the browser harness with installed esbuild, serving it from an ephemeral loopback server in system Chrome with a temporary profile and test-specific databases. Run focused typecheck and production build. Inspect exact cumulative diff from `d2421f9821a1a8fc60b127b28ce425aa5921ae27`; obtain independent read-only review and fix in-scope findings. Record exact browser/version and whether assertions ran against the real system browser or an emulator. The browser harness cannot establish power-loss/crash durability, browser quota limits, private-mode support across browsers, or cross-device/account recovery. Do not push or open a PR in this slice.

Local verification completed:
- Shared in-memory repository contract suite: 8/8 pass.
- `npm --prefix apps/live-control-ui run typecheck`: pass.
- `npm --prefix apps/live-control-ui run build`: pass. Existing dynamic/static import and >500 kB main-chunk warnings remain.
- Browser harness: 32 assertions pass against native IndexedDB on system Chrome `150.0.7871.186` (headless). The runner served a bundle from an ephemeral loopback server with a fresh temporary Chrome profile; all database names use a random `dmb-local-world-test-*` prefix and are deleted after the run. It exercises CAS from two repository connections, conflict retention, layout separation, alias isolation, connection close/reopen, v1→v2 upgrade/data preservation, malformed/current and future schema refusal, blocked upgrade retry, and unavailable storage.
- `QuotaExceededError` was injected at the pre-write seam to exercise abort and previous-snapshot preservation. Actual quota exhaustion and private browsing were not induced. Close/reopen was tested; abrupt process/power loss, browser eviction, and cross-browser support were not.
- The four-node and same-name entities remain shared test fixtures only; no product World data was introduced.
- No new package dependency was added. Direct IndexedDB was selected because browser-native readwrite transactions cover the two required stores atomically and native version upgrades support the exercised migration, while Dexie, `idb`, and fake IndexedDB are absent from the installed app dependencies. This does not prove the choice is best for a future larger schema.

At final re-anchor, #2202 was OPEN/DRAFT/mergeable at exact head `d2421f9821a1a8fc60b127b28ce425aa5921ae27` with no GitHub review submissions; no contract blocker was reported. This successor remains local and unpublished pending final independent cumulative-diff review. It has no hosted CI because it has not been published.

## Corrective review: request snapshot and schema identity

The coordinating steward reported independent HOLD on #2202 at `d2421f9…` and #2204 at `c5751ba…`. The native-browser reproduction in `scratch/independent-a2/` showed mutable semantic request headers could change during an IndexedDB request await and that a wrong `worldId` index keyPath was accepted, hiding persisted conflict candidates. The #2202 request-capture fix is now on its existing branch at `15ce6c14cccf6985297a43aa7628ef476d827966`; the A2 corrective branch must be rebased/advanced to include that exact head before push/review. A2 captures IDs and expected semantic/layout revisions before awaiting IndexedDB requests; it also captures `createWorld` title and open options at invocation.

`hasCurrentSchema` now needs exact v2 store and index validation: `worlds.keyPath === "snapshot.worldId"`, `conflicts.keyPath === "id"`, both stores `autoIncrement === false`, and `conflicts.index("worldId")` has keyPath `worldId`, `unique === false`, and `multiEntry === false`. Same-version malformed databases with each wrong schema property must be refused while their seeded world and candidate records remain readable and unchanged. No database upgrade/delete/repair may be attempted on a malformed current-version schema.

Permanent regressions belong in the existing native IndexedDB browser harness: mutate semantic worldId/expected-revision and layout worldId/expected-layout-revision immediately after method invocation; verify stale CAS remains a conflict and cannot redirect writes; mutate create title; seed wrong store keyPaths/autoIncrement and wrong index keyPath/unique/multiEntry plus missing index; assert each is refused and preserves stored records. Record exact corrected heads and browser/test evidence below after completing the repair. Previous head reviews do not apply to either corrected head; no merge/deployment or package runtime work is authorized by this correction.

The #2202 owning branch contains the request-capture correction at `e8cf5b1091abd8c0b8c0ed4e33d009a03563c737` and evidence sync at `15ce6c14cccf6985297a43aa7628ef476d827966`. The A2 branch includes that exact parent through merge commit `300bde8ee7eaa42bb1bbed1c6660b0285962967a`.

## Corrected A2 implementation verification (2026-11-08)

The local A2 branch is now based on `codex/phase2a1-local-world-repository` at `15ce6c14cccf6985297a43aa7628ef476d827966`. A merge commit carries that exact #2202 head into the original #2204 branch ancestry; the reviewed `c5751ba…` predecessor remains preserved. The correction adds synchronous request-header capture to every asynchronous IndexedDB write (`createWorld`, semantic edit, and layout write), validates the complete current schema shape (both store key paths and autoIncrement flags; index keyPath, unique, and multiEntry flags), and refuses malformed same-version databases without schema changes, data deletion, or repair. Open options are also captured before async open completion. The in-memory contract tests carried into this checkout now use the correct shared fixture helpers.

Verification on the cumulative A1→A2 checkout:
- `npm --prefix apps/live-control-ui test -- --run src/localWorld/localWorldRepository.test.ts`: 12/12 passed.
- `npm --prefix apps/live-control-ui run typecheck`: passed.
- `npm --prefix apps/live-control-ui run build`: passed, retaining the existing dynamic/static import and >500 kB main-chunk warnings.
- Bundled `indexedDbLocalWorldRepository.browserHarness.ts` with the installed esbuild and ran it in native system Headless Chrome 150 with a fresh temporary profile: 51/51 checks passed. This includes the post-invocation semantic world/revision, layout world/revision, and title mutation cases; concurrent CAS; reopen; and eight malformed same-version schema shapes. For each malformed schema, the harness compares the original database version, store keyPaths and autoIncrement values, index keyPath/unique/multiEntry metadata, and seeded World/candidate records after fail-closed refusal.
- Browser notes: synthetic `QuotaExceededError` only; actual quota exhaustion, private mode, abrupt termination/power loss, browser eviction, and cross-browser durability remain untested. Reopen proves only persistence within this Chrome profile.
- `git diff --check`: passed before commit. Existing hosted checks and an independent review of the corrected cumulative head remain pending; prior exact-head reviews do not apply.

The stale initial-handoff statements above saying “do not push” or describing the former 32/51-check state are historical records superseded by the coordinator's later explicit standing publication authorization and this correction section. Correction commit `b8cd8ba7176324a8562c2a79d0fb2ae7414ef302` is published on the existing `codex/phase2a2-indexeddb-local-world` branch and updates existing PR #2204 only. GitHub confirms #2204 OPEN/DRAFT/mergeable at that head, based on #2202 exact head `15ce6c14cccf6985297a43aa7628ef476d827966`; #2202 remains OPEN/DRAFT/mergeable at that head. Combined commit status queries returned no hosted status checks for either current head. Independent corrected-head reviews are pending; the previous exact-head reviews do not apply. No new PR is to be created; no merge/deployment or package/runtime work is authorized.
