# HANDOFF-INGEST-graph-first-experience

**Status:** SETTLED — PR #1276 merged at `448e88d9006b19cfb607d4ac5afde14d6d44d856`; implementation lease released.
**Objective:** Make graph enrichment the primary Ingest result, collapse recap processing to one clear action, and retire the breadcrumb-exploration product path.
**Base:** `main@3b5752204a4e54372096345fb2b17d29541051da`, verified from GitHub before rebasing.
**Parent:** Former stacked parent PR #1259 merged at `70c894a25ab64a0b08dd2e7a4f293f5e262eff4b`.
**Branch:** `codex/ingest-graph-first-cleanup` (existing PR #1276).
**Topology:** This PR targets `main`. PR #1266 is also rebased onto the current main and parallel-independent; its source-status adapter/test/handoff paths do not overlap this UI/route/test write set.
**Latest re-anchor check (2026-10-16):** GitHub confirms `main@3b5752204a4e54372096345fb2b17d29541051da`; #1259 is merged at `70c894a25ab64a0b08dd2e7a4f293f5e262eff4b`. PR #1276 and the parallel-independent PR #1266 now target this main; #1266 is at `d003bc7b6fab43f0e324cb56914292f832a76a93`. Their changed paths do not overlap. Verify current remote heads before the next review cycle.
**Runtime/data:** No real Prepare, Process, Extract, Graph admission, corpus, or database writes for verification. Do not edit or restart 5202 during implementation. Render after review approval if requested. Existing artifacts remain intact; this removes their obsolete workflow from the active product path, not user data from disk.

## Product contract

- A new recap has one visible happy path: write/paste the recap, then choose **Process**. The server owns normalization and graph extraction; users do not step through packaging stages.
- Once a saved or processed recap is loaded, the primary canvas is the graph-enriched recap projection, with linked World nodes in the prose. Raw Markdown is not shown in the primary view. Raw source may be exposed only by an intentional Advanced/source disclosure.
- The graph-enriched recap is the view, not a secondary review pane. Keep explicit Graph Review/admission as the authority boundary for committing extracted candidates; do not imply Process publishes graph facts.
- Keep technical evidence and correction controls in Advanced, but remove the breadcrumb/frontmatter-seed exploration UI, its user-facing recovery language, and its Ingest API request operations. No compatibility path for that obsolete user flow.
- Shared corpus status presentation must not restore the retired breadcrumb-routing or session-memory rows or missing-breadcrumb headline.
- Do not delete existing corpus artifacts or disable the session-memory query reader used by the planner; those are separate data/runtime ownership. The graph-first Process path must not depend on breadcrumb or session-memory generation.

## Critique and failure cases

- Reusing `generate_recap_memory` gives one server-owned path. It already stages raw input, applies/normalizes the recap, and requests graph extraction without the legacy branch.
- Existing graph projection is World-revision-bound and may contain no new candidate nodes before explicit Graph admission. The UI must label/route candidate state honestly and never claim admission. If a processed recap has no projection, show a clear unavailable state and source recovery affordance; do not silently fall back to a raw-Markdown canvas.
- Stale or missing normalized-source proof must continue to block extraction. A single button must not bypass source identity, duplicate reconciliation, title validation, session selection, or graph replacement confirmation.
- Processing existing saved text must not accidentally overwrite it with stale editor text. Send raw text only when the composer is the active source; preserve explicit replacement controls in Advanced.
- Removing old API operation literals is an intentional breaking change under the user's no-backwards-compatibility direction. Existing on-disk breadcrumbs are not deleted and are not readiness prerequisites.

## Exclusive write set

- This handoff
- `apps/live-control-ui/src/modules/IngestionModule.tsx`
- `apps/live-control-ui/src/modules/IngestionModule.test.tsx`
- `apps/live-control-ui/src/App.test.tsx` (Ingest route contract only)
- `apps/live-control-ui/src/test/appNavigation.test.tsx` (Ingest navigation assertions only)
- `apps/live-control-ui/src/modules/ingestReadiness.ts`
- `apps/live-control-ui/src/modules/IngestionStatusPanel.tsx`
- `apps/live-control-ui/src/modules/corpusIngestDisplay.ts`
- `apps/live-control-ui/src/modules/SourcesModule.test.tsx`
- `apps/live-control-ui/src/api/types.ts`
- `apps/live-control-ui/src/ingestSurface/MemoryIngestPage.css` (Ingest selectors only)
- `apps/live-control-ui/src/styles.css` (Ingest selectors only)
- `apps/live_control_server/routes/recap_ingest.py`
- `tests/test_live_recap_ingest_api.py`
- `tests/test_live_recap_ingest_graph_preview_api.py`

The parent PR #1259 is the only overlapping active UI lease and is an explicit stacked parent. PR #1266 owns disjoint candidate-source adapter and tests. No other active Ingest PR in the current open list owns these route or UI files.

## Acceptance

- Loading an existing processed recap opens the graph-linked recap as the main canvas; no raw normalized Markdown textarea or duplicate side-by-side source view appears.
- New recap text has one clear **Process** action. It invokes the graph-first server operation once, reports concise progress/errors, and on success opens the node-bearing recap projection when available.
- Raw Markdown is available only behind an Advanced/source disclosure. If projection is missing or fails, explain why and offer the appropriate recovery path without showing raw source by default.
- Graph candidates remain distinguishable from admitted World facts; a candidate-ready response offers Graph Review without asserting publication.
- Breadcrumb/frontmatter-seed/session-memory exploration actions, breadcrumb-specific visible recovery/status copy, the `include_legacy_breadcrumb` switch, and old breadcrumb API operation variants are removed from the active Ingest route/client contract. Existing source/candidate/artifact files are preserved.
- Shared corpus status presentation does not render the retired breadcrumb-routing or session-memory steps, even if an older status record contains those states.
- Graph-first Process validates the recap identity and managed-World context before staging pasted source; inspection must recommend **Process recap**, not the removed normalize step.
- Focused UI tests prove Process uses the combined operation, does not call deprecated operations, and hides raw source after loading or successful processing. Route tests prove old operations are rejected and graph-first Process does not invoke breadcrumb/session-memory generators.
- Run focused UI/API tests, UI typecheck/build, relevant Python tests, and cumulative `git diff --check`. Rendered verification is read-only at desktop and narrow widths after review.
- Inspect the exact cumulative base-to-head diff and keep the PR stacked on #1259; do not merge either PR without separate user authorization.

## Verification update — 2026-10-16

- Re-anchored against GitHub after the Build merge: current main is `3b5752204a4e54372096345fb2b17d29541051da`, including merged PR #1259 at `70c894a25ab64a0b08dd2e7a4f293f5e262eff4b`. PR #1276 and parallel-independent #1266 target this main on disjoint paths.
- Addressed the three review findings: explicit recap replacement now refreshes its normalized derivative before extraction; reconciliation/source-integrity refusals preserve the editable draft and stay out of reader mode; a selected extraction run now loads only its exact historical recap projection through the existing run endpoint, verifies run/source/world/revision identity, and has no fallback to the current session projection. The view identifies the exact run and digest-bound source and clarifies that graph links are from the admitted World Graph while candidates remain in Graph Review.
- `IngestionModule.test.tsx`: 39 passed, including exact-run loading without current-session fallback and preserving editable source after refusal. UI app/node TypeScript checks pass. The `npm run build` wrapper could not write its default cache under read-only `node_modules`; `vite build --configLoader runner` passes (688 modules, existing large-chunk warning).
- Direct route-helper test for explicit replacement and normalized derivative refresh: 1 passed. Python TestClient route tests could not be completed in this sandbox because the client/portal hangs even on an unrelated invalid-operation case; this is an unavailable boundary check, not a pass. `compileall` passed, and whitespace checks on every repaired file comparison emitted no findings.
- No real Process/extraction, graph admission, publication, durable source readback, 5202 change, or rendered acceptance was performed. The PR is not ready to claim full ingestion readiness until the combined rendered flow and durable readback are verified at the owning boundary.

## Stop condition

If the loaded graph projection cannot render candidate nodes before admission using existing contracts, keep the UI honest and record the missing projection contract. Do not silently mutate the World Graph or invent a second graph representation inside this UI slice.

## Settlement — 2026-10-17

PR #1276 merged at `448e88d9006b19cfb607d4ac5afde14d6d44d856`. The graph-enriched recap is now the primary Ingest projection, with raw Markdown behind Advanced and Graph Review remaining the candidate-admission boundary. The PR did not claim real Process, durable source readback, publication, or rendered end-to-end acceptance; those remain in the active Ingest goal. The next source-binding implementation is tracked in `HANDOFF-INGEST-recap-source-world-binding.md`.
