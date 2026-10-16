# INGEST: distinguish saved graph candidates from current source

**Status:** ACTIVE under the user-authorized Ingest-first goal: present source, extracted candidates, evidence, review, and rerun behavior with truthful provenance.
**Base:** `main@3b5752204a4e54372096345fb2b17d29541051da`, verified on GitHub before rebasing.
**Branch:** `codex/ingest-recap-source-status`.
**Checkout:** `/home/drakosfire/Projects/.codex/ingest-source-lineage-status/DungeonMindBuddy` (local validation snapshot at `6c892f691d6d0fc83c37c6ba67402b9e3c6d3785`; the service and test blob hashes match current PR head `19d165210367953e6d6e9970586655210acf6108`).
**Topology:** Parallel-independent from open PR #1276 (graph-first Ingest UI). Its UI/route/test paths and this service/test/handoff write set are disjoint; PR #1259 is merged and there is no stacked parent.
**Runtime/data boundary:** tests use temporary directories. No source, candidate, corpus, database, World Graph, provider/model call, publication, 5202, or 5204 mutation. Live surfaces remain read-only.

## Objective

Separate the persisted state of a graph-ingest run from proof that it belongs to the normalized recap currently selected in Ingest. A retained candidate must remain inspectable when its source file is missing, but the current screen must not call it ready for the selected source based on a path-only match.

## Evidence and invariant

The read-only 5204 Session 29 surface reports canonical and normalized recaps missing while also showing a graph candidate (59 nodes / 33 edges) as `candidate_validation_ready`. Current main explains the mismatch: `_lineage_for_normalized_recap` returns a relative path with no digest for a missing file, and graph-run discovery permits path-only matching when no source digest is supplied.

- A graph run is current for a selected normalized recap only when the current readable recap digest matches the run manifest or its proven SourceArtifact lineage.
- A path-only or unfiltered run discovered while the current source is unavailable remains preserved as a saved artifact, but its response status becomes `source_unverified`. Preserve the original persisted state separately as `artifact_status`; return `source_match_mode`, a concise recovery reason, counts, run identity, validation summary, and artifact paths for inspection.
- Unverified saved artifacts must not advertise a current review/rerun action. The response should direct the user to restore or load verified source first.
- An exact-digest match preserves its existing status and next actions. A changed source digest, unusable source, or mismatched lineage must never downgrade to path-only matching.
- Do not rewrite or delete manifests or candidates. This is a read-only classification of status.
- The existing UI treats `blocked_reason` as blocked and renders the dynamic status string; no shared UI/API-type path is included in this slice.

## Exclusive write set

- `Docs/Plans/HANDOFF-INGEST-candidate-evidence-readiness.md` (settle the merged #1251 lease)
- `Docs/Plans/HANDOFF-INGEST-graph-candidate-source-status.md`
- `apps/live_control_server/services/recap_graph_preview_ingest.py`
- `tests/test_recap_graph_preview_source_status.py` (new owning service-boundary regression)

No route, `types.ts`, UI module, graph-run registry, extraction/packaging, source/corpus data, database, or deployment paths are leased.

## Failure cases and verification

- A missing normalized recap whose path matches an existing candidate returns the candidate details as preserved, `source_unverified`, the original `artifact_status`, and recovery guidance; it never says ready or suggests review/rerun.
- No current source path with a retained session candidate is likewise unverified, not current-ready.
- A present normalized recap with an exact digest match keeps the persisted artifact status and next actions.
- A changed digest or unusable source does not select a same-path candidate.
- The regression writes a valid candidate manifest in a temporary repository and exercises both `discover_graph_ingest_runs` and `inspect_recap_graph_preview_status`: a path-only candidate is preserved but marked unverified, a candidate with the exact current normalized digest remains ready, and a changed digest does not fall back to the same path.
- Post-rebase verification on `origin/main@52e3ddfc5fb847080569832b1ae5c7951d1d870d`: source-status plus candidate-validation summary tests, 17 passed; Ruff on both changed Python files passed; Python compileall and `git diff --check` passed.

- No live ingestion action is part of this slice. Full rendered recap ingestion, persistence readback, and any real rerun remain separate gates in the parent goal.

- Re-anchored to `main@3b5752204a4e54372096345fb2b17d29541051da` after #1259 merged at `70c894a25ab64a0b08dd2e7a4f293f5e262eff4b`. GitHub confirms the 43 paths changed between the former base and main do not overlap this four-file write set. PR #1276 remains parallel-independent on disjoint paths.
