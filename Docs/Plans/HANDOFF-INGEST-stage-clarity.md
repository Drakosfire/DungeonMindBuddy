# INGEST: distinguish ready source from unrun graph extraction

**Status:** ACTIVE — PRIME explicitly authorized this bounded Ingest presentation correction on 2026-10-17.
**Base:** `origin/main@e71d751b0bfbcc96260995c4487aa27bcd26de40`.
**Branch:** `codex/ingest-stage-clarity` in the existing `996b` checkout.
**Topology:** one serial Ingest UI PR for PRIME review; no runtime or retained-data lane.

## Mission

Make the primary Graph evidence panel distinguish a source that is ready but has not been extracted from a partial, failed, blocked, or completed extraction. Today status inspection can return `graph_preview.status = "missing"` with zero counts and `next_actions = ["build_graph_preview_bundle"]`; the UI renders that as “Graph incomplete”, “status: missing”, “nodes: 0”, and “edges: 0”. Those values describe that no extraction result exists, not an empty graph, and make the first-run experience look like a failed result.

For a current, verified source with no extraction run, say plainly that the source is ready and the operator can choose **Process** in the Ingest navigation to extract graph candidates. If source proof is incomplete or unverified, do not call it ready; retain the existing source proof and next-action guidance. Do not claim extraction is active, failed, or empty when no run/manifest exists.

## Contract and invariants

- A missing preview with no run/manifest/step evidence and no current error or block means “not extracted yet”, not extraction failure or an empty graph.
- Say “Source ready” only when the current selected target has the source proof required by the existing `canProcessRecap` gate. Keep the existing Process action as the explicit operator choice.
- Do not fabricate `0` by substituting for an absent node/edge count. Hide counts when no graph run produced them; show only fields actually reported for partial or completed work.
- Preserve truthful partial/source-bundle, blocked, source-unverified, failed, candidate-ready, and preview-union-ready states, their run identity, current step, evidence, and recovery details. An actual error or block must never be disguised as not-yet-run.
- Preserve campaign/session/World identity and the existing mounted-route and A→B→A response guards.
- Do not process, repair, publish, or otherwise mutate the operator’s real Session 10 recap or World Graph in this slice.

## Exact write lease

- `Docs/Plans/HANDOFF-INGEST-stage-clarity.md` — this bounded contract and truthful implementation/verification evidence.
- `apps/live-control-ui/src/modules/IngestionModule.tsx` — derive the no-run display from explicit graph-run evidence and the existing source readiness gate; do not change Process, source loading, extraction, route identity, Graph Review, API, or persistence behavior.
- `apps/live-control-ui/src/modules/IngestionModule.test.tsx` — add owner-bound display regressions for verified source/no run, unverified source/no run, partial run, and failed/blocked run; keep existing route and response-generation regressions.

No server/API/schema, extraction/materializer, candidate interpretation, graph publication, source/corpus, database, provider, environment, deployment/build output, Combat, Plan/Play, shared registry, lockfile, or 5202 service/runtime paths are leased. The process-local user draft, saved recap, and current serving assets remain untouched.

## Verification and acceptance

- Run the complete `IngestionModule.test.tsx` suite and UI typecheck.
- Run the production build only to a disposable output outside the serving `dist`; verify serving asset hashes are unchanged.
- Inspect the exact cumulative `origin/main@e71d751b…` to PR-head diff and run `git diff --check`.
- Open one PR for PRIME review. Do not merge or change 5202 from this slice.
- After review/build availability, inspect the Session 10 surface without triggering Process and confirm its ready-to-process state. The operator alone chooses Process. Real extraction, candidate/evidence inspection, rerun/recovery behavior, and persistence readback remain open acceptance gates for the overall ingestion goal.

### Current implementation evidence

- `apps/live-control-ui/src/modules/IngestionModule.test.tsx`: **70 tests passed** including verified source/no run, unverified source/no run, partial extraction, failed extraction, blocked extraction, and the existing selected-session/route-fencing regressions.
- `npm run typecheck`: passed.
- `npm run build -- --outDir /tmp/dmb-ingest-stage-clarity-20261017`: passed; the existing Vite large-chunk warning remains. The build output was written outside the app's `dist`.
- `git diff --check`: passed.
- The operator's real Session 10 recap was not processed. No browser acceptance against current 5202 assets has been claimed; the operator should choose Process after this change is reviewed and available to dogfood.

## Predecessor settlement

- PR #1324 settled the earlier status-label lease at merge `2b284ff96dea8bd42cf1e3dd6f3a647ab0a4f4f5` (head `c3df3d8384a205b28ffbe6c2f5d88d7bd2c04ea8`). This successor addresses the separate misleading “Graph incomplete”/zero-count presentation for an unrun graph.
- PR #1333 settled the earlier campaign/session-affinity lease at merge `6531f0038d79431c6265afb3fd01e6d99458cd2b` (head `88510a3d8aeaff0caf9b84b674ee63e1b49836a5`). Its route/session generation guards are preserved and covered by the existing owning tests.
- PR #1336 settled Process idempotency/recovery; PR #1339 settled exact Graph Review routing. Both are part of the current main base and are outside this presentation-only change.
