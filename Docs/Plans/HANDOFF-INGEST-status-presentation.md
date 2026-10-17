# INGEST: show truthful processing status

**Status:** SETTLED — PR #1324 (`INGEST: show truthful processing status`) merged at `2b284ff96dea8bd42cf1e3dd6f3a647ab0a4f4f5` from head `c3df3d8384a205b28ffbe6c2f5d88d7bd2c04ea8`. The merge is present in current `main@7cf6b81f54c57898bb235ffe89913bc296059abe`.
**Base:** `main@c2b18ebd980fcc154e94f19b7e7338de1505007e` (verified as current GitHub main before branch creation).
**Branch:** `codex/ingest-status-presentation`.
**Checkout:** `/home/drakosfire/.codex/worktrees/996b/DungeonMindBuddy` (reuse assigned checkout).
**Topology:** parallel-independent from draft PR #1235. Rechecked GitHub: #1235 is `codex/ingest-source-observation-review@ffc2276ae9b3e7feac220a1cfff2ea18ced5a414`, based on `main@fc1daff4b7fc8f6ba7d35445dd22e9fca15f6d49`; its pinned handoff is `Docs/Plans/HANDOFF-DOGFOOD-ingest-source-observation-review.md`. Its ten-file lease is disjoint from this lane's three paths: API types/client/tests and Graph Review workbench/projection/review UI/tests plus its handoff. #1235's handoff excludes backend/source/candidate/database/serving and 5202 writes; this lane also excludes processing and runtime/deployment changes. Neither lane depends on the other's behavior, and neither writes shared runtime state. The recorded #1235 checkout `/tmp/dmb-ingest-source-observation-refresh-sparse` was absent when checked; its remote draft PR and pinned lease remain open, so the lane is recorded rather than assumed settled.
**Serving baseline:** 5202 remains on the previously matched `cb11bf86c69b7dbe96063753660fda7b829620b4` built UI. Its ignored `apps/live-control-ui/dist` contains 9 files / 4.3 MB with aggregate SHA-256 `4fd6557cba12f0bcf58823d649ece073f7ebbfd767c5c192301fd7679dd5e43e`; preserve these bytes. Do not rebuild into or replace the serving output.

## Mission

Make the Ingest status label tell the operator what actually happened. A blank draft must not imply that work is running, and incomplete or unverified evidence must not be presented as progress. Keep the source/review surface and processing behavior unchanged.

## Settlement

PR #1324 implemented this status-only correction in the leased Ingest module and its existing test. It passed the recorded 58-test component suite, UI typecheck, and `git diff --check`; its body records the existing React `act(...)` warnings and the absence of a new production build or serving-asset change. The rendered 5202 state and real Session 29 ingestion remained unverified at merge. The historical implementation evidence below is retained as-is.

## Observed failure

On the blank Session 29 route, the editor is empty and the page reports “No ingestion result yet” with graph extraction `pending`, but the evidence header still displays “Processing result · in progress.” On the saved Session 10 route, the same label appears while graph extraction is missing and only 2 of 3 recap proof artifacts are verified. The historical `f43e48e6-c775-4960-824f-fb398fe50bb9` Session 29 run is `source_unverified`, has no current World binding, and proves 0/3 recap files; it is not a source for rerun or publication.

The current status badge in the Ingest evidence header maps every graph state other than the two ready states to “in progress,” including idle, missing and source-unverified states. The component already tracks explicit pane states (`idle`, `running_full_ingest`, `building_graph_preview`, `materializing_preview_supergraph`, ready, and error) and graph preview status, so this correction should use those existing signals.

## Exact write lease

- `apps/live-control-ui/src/modules/IngestionModule.tsx` — derive a user-facing status label/tone from the actual pane state, latest result, and graph preview status. Distinguish at least: not run/idle, actively processing, graph ready, failed, and source-unverified. Missing graph output after a saved recap must not be called active work. Active retry state takes precedence over a prior failed result; an explicit graph block takes precedence over a ready-shaped graph status. Do not change source loading/saving, graph extraction, publication, or evidence selection behavior.
- `apps/live-control-ui/src/modules/IngestionModule.test.tsx` — regress blank Session 29, saved Session 10 with missing graph preview, source-unverified result, active processing, ready result, failure presentation, retry-after-failure, and blocked graph results using the existing component/API fixtures.
- `Docs/Plans/HANDOFF-INGEST-status-presentation.md` — record implementation and verification evidence; do not mark this in-flight slice settled before merge.

No server/API/schema, source files, extraction/materializer, candidate interpretation, Graph writes, retained records, databases, environment, shared registries, dependencies, deployment configuration, or 5202 build assets are leased. No recap should be processed during this slice.

## Implementation evidence (in flight)

- The header now reads “Ingestion status.” The badge derives from the current pane state, current-target result, and graph preview: `Not run`, `Processing`, `Graph ready`, `Failed`, `Source unverified`, `Blocked`, `Graph incomplete`, or `Graph unavailable`. Only explicit active operation states say “Processing.”
- Owning component tests cover blank/inspected, saved recap without graph preview, source-unverified, ready, failed, deferred active processing, retry while a prior failure remains in the result, and blocked graph results that otherwise have a ready-shaped status.
- `npm test -- --reporter=dot src/modules/IngestionModule.test.tsx`: **58 passed**. The output includes React `act(...)` warnings from the existing “keeps the empty local navigation focused on recap identity” test; that unrelated warning was not changed in this slice.
- `npm run typecheck`: passed.
- The initial production build passed before the status-priority regressions were added. The isolated follow-up changes were verified with the owning test suite and typecheck; a new production build was not run, and no bundle output or serving asset was modified.
- Serving `apps/live-control-ui/dist` checksum remains `4fd6557cba12f0bcf58823d649ece073f7ebbfd767c5c192301fd7679dd5e43e` (9 files, 4.3 MB). No ingestion request or retained data mutation was made.
- Rendered 5202 still serves the previous `cb11` build. Post-merge rendered acceptance remains open; do not move 5202 to this branch before review.

## Verification and completion

- Run the focused `IngestionModule.test.tsx` suite and UI typecheck; preserve inherited failures accurately.
- Inspect exact cumulative `main@c2b18...` to head diff and run `git diff --check`.
- If production build evidence is needed, direct Vite output to a temporary directory and verify the recorded serving `dist` checksum is unchanged; never write the build to the serving output.
- Commit, push, open one PR for PRIME review, and report the exact head. Do not merge or move 5202 to this branch. PRIME owns the independent review and merge decision.
- After merge, verify the labels on a fresh blank Session 29 view and the current incomplete Session 10 view without changing their data. The real Session 29 ingestion still requires the operator’s actual recap source and a separate save/process/persistence verification.
