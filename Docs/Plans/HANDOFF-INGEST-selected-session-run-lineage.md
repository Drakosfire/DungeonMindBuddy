# INGEST: keep selected session and run lineage coherent

**Status:** ACTIVE — PRIME assigned the DOGFOOD steward to execute this bounded Ingest lineage audit and repair on 2026-10-17. The operator stays on Build; no operator Ingest dogfood is required for this slice.
**Base:** current GitHub `main@6e7ee2e3d228a5b30277542ecd013779046a03c9`.
**Branch:** `codex/ingest-selected-session-run-lineage`.
**Checkout:** reuse the assigned `/home/drakosfire/.codex/worktrees/996b/DungeonMindBuddy`; do not create a worktree or change the running app.
**Topology:** parallel-independent from open PR #1235. Its exact files are Graph Review/API observation-review paths and do not overlap this lease. Combat PR #1327 is separate. PR #1324 (status presentation) merged at `c3df3d8384a205b28ffbe6c2f5d88d7bd2c04ea8`; PR #1318 (session-affinity selector) and #1244 (candidate evidence refs) are also merged, so their old ACTIVE handoffs no longer lease implementation paths. No live runtime or data owner is introduced.
**Runtime boundary:** no 5202/API/DB changes, no recap processing, no retained source/candidate writes. Use only synthetic UI fixtures.

## Mission

Keep every displayed source text, processing result, graph candidate, evidence list, and failure attached to the active Ingest target as the selected campaign/session and extraction run change. A prior recap may remain available as explicitly labeled context, but it is not the active source until the operator explicitly loads it. Deliberately preserved drafts must remain labeled with their original session.

## Root-cause audit

Existing code guards many asynchronous responses against a local campaign/session key and draft epoch, and existing tests cover session-input changes, stale list results, late Process results, and exact-run projection checks. The likely remaining seam is route/parent selection changes while `IngestionModule` remains mounted: `requestedRecapSession` and `freshRecapEntry` are captured only on mount, local `recapSession` is synchronized later by an effect, and some evidence UI derives directly from `latestResult` before proving it belongs to the current route target. Reproduce or reject this hypothesis before changing behavior.

## Invariants

- A response, error, source, candidate, or evidence row may be rendered as active only when its complete identity matches the current selection. Include World/campaign/session and exact extraction run/source identity wherever the operation has one.
- A route/prop target change must invalidate prior async work synchronously, including A→B→A changes. A late response or rejection from A cannot repopulate B or the later A selection.
- The selected session and route session have explicit, consistent ownership when the component remains mounted across navigation. Fresh mounts begin from the current route, not a mount-time snapshot from an earlier route.
- Prior recap choices can remain in a selector with clear prior-recap labeling. They do not become source text, proof, candidate, or Process input until explicitly loaded and verified for the active selection.
- A saved draft preserved from another session stays available only with its original session clearly shown; it must not be presented as active source for the new selection.
- Save/Process/Graph extraction semantics and backend contracts remain unchanged.

## Exact write lease

- `Docs/Plans/HANDOFF-INGEST-selected-session-run-lineage.md` — this bounded contract and truthful evidence.
- `apps/live-control-ui/src/modules/IngestionModule.tsx` — route/selection identity, stale-display masking, and response invalidation only.
- `apps/live-control-ui/src/modules/IngestionModule.test.tsx` — synthetic tests for the acceptance cases below.

No `liveApi`, API/server, MEDIA, APP-STATE, schema, Graph, extraction/materializer, corpus, database, shared registry, other UI module, dependency, deployment or served-output paths are leased. Return to PRIME before expanding the path set.

## Owning proof

- Reproduce the route/prop change seam without unmounting: A→B while A status is pending, then B→A while the first A response or failure is still pending. Only the latest selection may show status, paths, candidate/evidence, source text, or error.
- Change a route session while a saved-reader run projection is deferred. The old run’s projection must disappear immediately and its late completion must not appear under the new session. Verify URL/run identity remains bound to the exact current run.
- Keep a prior-session artifact in the selector while the active source is blank/new. Assert it remains labeled prior context and does not populate the editor, proof panel, or Process request without explicit Load. Verify an explicitly loaded matching artifact becomes the active source only after its status/source checks pass.
- Verify preserved mismatched drafts stay explicitly labeled and returnable, not mistaken for the active recap.
- Use deferred API mocks and synthetic fixtures only; no real recap Process, live graph access, source write, or runtime action.
- Run the focused IngestionModule suite, UI typecheck, and `git diff --check`; build only to the existing ignored `.pytest_cache` path if needed. Inspect exact cumulative `main@6e7ee2e3d228a5b30277542ecd013779046a03c9` → head diff and publish one PR for PRIME review. Do not merge or touch 5202.

## Completion evidence

Pending implementation. Keep the exact observed root cause, changed behavior, test results, and remaining rendered/API limits recorded here. This lease does not claim full ingestion readiness or operator acceptance.
