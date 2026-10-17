# INGEST: keep selected session and run lineage coherent

**Status:** ACTIVE — implementation is complete and awaiting PRIME review. The operator stays on Build; no operator Ingest dogfood is required for this slice.
**Base:** current GitHub `main@9020dc459b78c49f3aaea01bd5594ffb0f266e3b`.
**Branch:** `codex/ingest-selected-session-run-lineage`.
**Checkout:** reuse the assigned `/home/drakosfire/.codex/worktrees/996b/DungeonMindBuddy`; do not create a worktree or change the running app.
**Topology:** parallel-independent from open PR #1235. Its exact files are Graph Review/API observation-review paths and do not overlap this lease. Combat PR #1327 is separate. PR #1324 (status presentation) merged at `c3df3d8384a205b28ffbe6c2f5d88d7bd2c04ea8`; PR #1318 (session-affinity selector) and #1244 (candidate evidence refs) are also merged, so their old ACTIVE handoffs no longer lease implementation paths. No live runtime or data owner is introduced.
**Runtime boundary:** no 5202/API/DB changes, no recap processing, no retained source/candidate writes. Use only synthetic UI fixtures.

## Mission

Keep every displayed source text, processing result, graph candidate, evidence list, and failure attached to the active Ingest target as the selected campaign/session and extraction run change. A prior recap may remain available as explicitly labeled context, but it is not the active source until the operator explicitly loads it. Deliberately preserved drafts must remain labeled with their original session.

## Root-cause audit

Reproduced the mounted-route seam. Route-derived session and fresh-entry selection were captured on mount, while later navigation synchronized local selection asynchronously. In-flight status or saved-reader results could therefore outlive the route target; a local campaign/session key also could not distinguish A→B→A generations. The module now derives route identity on each render, invalidates the prior selection in a layout effect, binds hydration and displayed results to a generation-scoped target, and rejects mismatched status responses before adopting them.

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
- Change a route session while a saved-reader run projection is deferred. The old run’s projection clears immediately and its late completion cannot appear under the new session; the test confirms the new session/run is the only rendered projection.
- Keep a prior-session artifact in the selector while the active source is blank/new. Assert it remains labeled prior context and does not populate the editor, proof panel, or Process request without explicit Load. Verify an explicitly loaded matching artifact becomes the active source only after its status/source checks pass.
- Verify preserved mismatched drafts stay explicitly labeled and returnable, not mistaken for the active recap.
- Use deferred API mocks and synthetic fixtures only; no real recap Process, live graph access, source write, or runtime action.
- Run the IngestionModule suite, UI typecheck, production UI build, and `git diff --check`. Inspect the exact cumulative current-main-to-head diff and publish one PR for PRIME review. Do not merge or touch 5202.

## Completion evidence

Implemented only the leased Ingest module and synthetic test paths. The module now tracks route selection across mounted navigation, invalidates old asynchronous work across A→B→A, masks unverified prior status, verifies campaign/session on inspection responses, and preserves a draft under its original session when the selected session changes. Test coverage includes deferred status races, a deferred saved-reader projection across a route-session change, and manual session-change draft recovery.\n\nVerification: **61/61 IngestionModule tests passed**, UI `npm run typecheck` passed, production `npm run build` passed (708 modules; Vite emitted its existing >500 kB chunk warning), and `git diff --check` passed. The suite also printed existing React `act(...)` warnings in unrelated tests.\n\nEvidence limits: all behavior was checked with synthetic fixtures and deferred API mocks. No live recap was processed, no source/candidate or World Graph data was changed, and 5202/API/database were untouched. Real ingestion and operator acceptance remain open; this slice does not establish full ingestion readiness.
