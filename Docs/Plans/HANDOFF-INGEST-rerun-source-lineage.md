# INGEST: source-aware derivative reruns

**Status:** ACTIVE under the user-authorized Ingest-first goal: preserve source provenance and make rerun effects understandable.
**Base:** fetched `origin/main@d2df98ff7d7be67658d4705f3879dd1ddb6a1700` after #1254 merged. The merged reviewed-observation batch read changes agent retrieval files; its cumulative file list does not overlap this Ingest lease.
**Branch:** `codex/ingest-rerun-provenance`.
**Checkout:** `/home/drakosfire/.codex/worktrees/ingest-rerun-provenance/DungeonMindBuddy`.
**Topology:** parallel-independent from open #1237 (local-navigation UI), #1235 (source-observation review), #1244 (candidate graph evidence references), and #1251 (candidate readiness). The changed-path lists for those PRs and merged #1253/#1254 were rechecked against this lease; none overlap. This remains a server-side pipeline contract and does not amend those PRs.
**Runtime/data boundary:** disposable test corpus only. Do not write to retained Session 29 files, live Corpus, World Graph, database, 5202, or 5204. No provider call except a mocked breadcrumb generator in tests.

## Objective

Make each recap-derived stage report whether its output is current, stale, edited, or unverified against its inputs. An unchanged rerun must be a no-op. A changed-source rerun must not silently reuse stale work or overwrite edits. Explicit refresh must archive the prior output and report the archive path.

Stages: canonical recap, normalized recap, frontmatter seed, routing-only breadcrumb, and session-memory JSONL/meta. The canonical recap remains the prose authority; an explicit `force_recap` replacement must archive the prior recap and surface its path.

## Contract and invariants

- Deterministic normalized recap and session-memory output are current when recomputing from the exact current inputs produces byte-identical output. Existing mismatching bytes are preserved by default and reported as edited/stale; same-path presence alone never means current.
- A canonical recap with different existing content is a conflict unless `force_recap` is explicit. Explicit replacement archives the prior prose before installing the new version.
- The frontmatter seed is deterministic but reviewable. Its `dmb_recap_derivative_provenance_v1` sidecar records the normalized-recap digest and the deterministic generated-seed digest. If the seed was hand-edited while those inputs remain current, report `edited_current_inputs` and allow the reviewed seed to feed breadcrumb routing. If the normalized recap changed, report stale and require an explicit seed refresh/review before routing.
- Routing-only breadcrumb generation is non-deterministic. Its sidecar records the exact normalized-recap digest, active (possibly reviewed) seed digest, output path/digest, stage identity, campaign, and session. A breadcrumb without valid lineage is `provenance_unknown`; preserve it and do not spend on or overwrite it automatically.
- Default reruns do not rewrite current artifacts. Stale, edited, unknown, partial, or corrupt outputs stop dependent stages and return concise states, warnings, exact paths/digests, and a next action.
- Optional per-stage refresh flags (`force_normalize`, `force_seed`, `force_breadcrumb`, `force_session_memory`) are backward-compatible. An explicit refresh first builds/validates the replacement, copies all prior stage outputs and lineage into a collision-safe sibling `_archive`, installs the replacement atomically where possible, and reports archived paths. Failure must leave the previous bytes recoverable.
- Memory JSONL/meta are compared against computed expected bytes before any write. `--check` is not the first validation after overwrite.
- A stale or invalid upstream artifact blocks downstream materialization; a successful refresh updates only the requested stage and leaves downstream outputs visibly stale until separately refreshed.
- Keep request status summaries free of raw recap text and registry contents. Preserve existing response compatibility.
- No UI files are leased: #1237 owns `IngestionModule.tsx` exclusively. The API must expose understandable status through the current response fields; a follow-up UI control for explicit refresh can be added after #1237’s lease settles. Do not claim full end-to-end Ingest completion here.

## Write lease

- `Docs/Plans/HANDOFF-INGEST-rerun-source-lineage.md`
- `src/live_play/recap_derivative_provenance.py` (new hash, lineage, archive, and atomic-write helpers)
- `src/live_play/recap_ingest_pipeline.py`
- `src/live_play/recap_ingest_status.py` (PRIME explicitly authorized this status-mapping amendment on 2026-10-16 after a lease omission was identified)
- `src/agent/corpus_writer.py` (allowlist for provenance sidecars)
- `scripts/build_recap_frontmatter_seed.py` (same lineage/refresh behavior for the CLI entry point)
- `apps/live_control_server/routes/recap_ingest.py`
- `scripts/materialize_session_memory.py`
- `tests/test_recap_derivative_provenance.py` (new)
- `tests/test_live_recap_ingest_pipeline.py`
- `tests/test_live_recap_ingest_api.py`
- `tests/test_recap_frontmatter_seed.py`
- `tests/test_corpus_writer.py` (sidecar allowlist)

No UI, graph extraction/packaging, unrelated readiness APIs, corpus, database, World Graph, or deployment files are leased.

## Failure cases to prove

- Repeating unchanged normalization, seed, breadcrumb, and materialization reuses current bytes and makes no data writes.
- Changed canonical/normalized/seed/breadcrumb inputs make only their downstream outputs stale.
- Existing legacy breadcrumb without sidecar remains untouched, reports unknown provenance, and does not trigger an LLM call.
- Corrupt sidecar, wrong stage/session/path, or output digest mismatch fails closed.
- Hand-edited normalized/breadcrumb/memory output is detected and preserved without explicit refresh. A hand-edited seed remains usable when its provenance proves the normalized input is still current; its edit is visible in status.
- Explicit canonical or derivative refresh archives old bytes before replacement; generation/write failure leaves old bytes recoverable.
- Memory drift is detected before write.
- A refresh does not silently mark downstream stages current.

## Verification and release boundary

- The focused provenance, pipeline, seed, materializer, and corpus-writer suites pass: 110 tests. The owning tests/test_live_recap_ingest_api.py suite passes: 25 tests. These use the existing matching project venv and disposable test corpora.
- The new regression verifies that an explicit breadcrumb refresh with either a wrong source_recap_path or breadcrumb text that differs from the normalized recap returns HTTP 422 before archiving and leaves both the installed breadcrumb and provenance sidecar byte-identical. A direct call through the route orchestration independently confirms the same invariant and that no archive is created.
- Ruff on every changed Python module/test and git diff --check pass.
- Additional direct route checks proved: a three-stage explicit refresh returns ready_for_planning_activation and reports all six prior artifacts; an edited seed is preserved until explicit refresh; and a legacy breadcrumb without lineage remains unchanged and triggers zero routing-model calls.
- Tests use disposable corpora only. No retained recap, live Corpus, provider, database, World Graph, 5202, or 5204 state was changed. No rendered UI or full ingestion acceptance is claimed.

Merge, deployment, and rendered end-to-end acceptance remain separate gates.