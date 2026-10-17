# INGEST: make Process retries reuse the exact graph run

**Status:** ACTIVE — PRIME authorized this serial successor after PR #1333 merged at `6531f0038d79431c6265afb3fd01e6d99458cd2b`.
**Base:** Buddy `main@6531f0038d79431c6265afb3fd01e6d99458cd2b` (verified on GitHub after PRs #1334 and #1333 merged).
**Branch:** `codex/ingest-process-idempotency-recovery`.
**Checkout:** `/home/drakosfire/.codex/worktrees/996b/DungeonMindBuddy` (reuse the assigned checkout; no new worktree or environment).
**Topology:** serial, one successor PR after merged #1333. PRIME owns review and merge; ARCHITECTURE performs independent review.

## Mission

Make repeated identical Process requests reuse the correct already-reviewed extraction run, and make recovery from an existing reviewable candidate avoid replaying provider work. Preserve explicit force-rerun behavior and exact source/World lineage. A retry must never silently reuse a candidate from changed source text, another session, or a different World binding.

## Observed failure and starting evidence

The synthetic owning suite `tests/test_live_recap_ingest_graph_preview_api.py` ran against local code whose leased service and test files were byte-identical to merged Buddy main. It completed with **25 passed, 2 failed**:

- `test_generate_recap_memory_reuses_preview_graph_without_force`: the second identical request created a suffixed `...-2` manifest rather than returning the first manifest.
- `test_unmocked_candidate_completion_recovers_without_provider_replay`: the recovery contract assertion failed. Capture the full failure before implementation using only the no-`/tmp` temporary-path setup below.

The earlier import-collection failure was an environment issue. Use the existing pinned rollout sources without changing them: `/home/drakosfire/.local/state/dungeonmindbuddy/rollout-candidates/buddy-main-01980f14/ge-site` (GenerationEngine `7e3ed2202684316c6d426462f4928824bb2e99ca`) and `/home/drakosfire/.codex/worktrees/corpus-identity-binding/DungeonMind/src` (DungeonMind `632468ac43d8b321bf5379589a737aede9d7327c`).

The provider-free recovery failure is a product defect, not a fixture mismatch. The retry discovers the exact candidate run, its ExtractionRun is still `REVIEWABLE`, and the known-entity and SourceSpanIndex validators pass. However, `src/graph_memory/extraction/graph_ingest_packaging.py::_write_validation_report` adds `diagnostics.evidence_reference_repair_count = 0` and serializes the candidate again even when validation changes nothing. That makes the packaged candidate digest differ from the immutable ExtractionRun candidate, so the exact production-lineage gate rejects it and Process starts extraction again. The first identical-Process failure is the same gate.

PRIME amended this ACTIVE lease to include the shared packaging implementation and its focused existing test. Keep the lineage gate strict: a validation pass with no repairs must preserve the immutable candidate bytes; actual evidence repair behavior must remain explicit and covered.

## Invariants

- Reuse requires the exact normalized recap lineage (source identity and digest), selected campaign/session, and managed World binding/head snapshot.
- `force_graph_run=true` continues to create a new extraction run.
- Recovery of a reviewable candidate performs no provider call and invokes no retired materialization path; it returns the original run and candidate identities.
- Changed source or World context cannot inherit the prior candidate. Failed, incomplete, or mismatched runs do not become reviewable through reuse.
- Process remains a preparation path. It does not publish facts to the World Graph.

## Exact write lease

- `apps/live_control_server/services/recap_graph_preview_ingest.py` — precise run matching/recovery only.
- `tests/test_live_recap_ingest_graph_preview_api.py` — the two focused regression tests and necessary adjacent lineage/force assertions.
- `src/graph_memory/extraction/graph_ingest_packaging.py` — preserve candidate bytes and digest when packaging makes no semantic change; retain actual repair behavior.
- `tests/test_graph_memory_category_graph_preview_runner.py` — focused exact-byte/no-op packaging regression alongside existing real-repair coverage.
- `Docs/Plans/HANDOFF-INGEST-process-idempotency-recovery.md` — this contract and evidence.
- `Docs/Plans/HANDOFF-INGEST-session-affinity-default.md` — factual settlement of merged PR #1333.

No UI, other API routes, schema/migration, extraction producer, provider settings, source/candidate files, retained recap/corpus, World Graph, or serving runtime is leased. The shared packaging edit is limited to preserving accepted ExtractionRun bytes when GraphIngest validation makes no candidate change; it does not weaken digest checks or suppress genuine repairs.

## Runtime and test boundaries

- The owning fixture creates a uniquely named disposable APP PostgreSQL database and drops it in `finally`; no retained APP data is used.
- Pytest temporary directories must remain inside the existing workspace `.pytest_cache`; set `TMPDIR="$PWD/.pytest_cache"` before the Python process, and if pytest does not honor it, pass `--basetemp="$PWD/.pytest_cache/ingest-process-idempotency-<unique>"`. Do not create any `/tmp` directories.
- Use synthetic extractor/provider responses only. No paid/live provider request, real recap processing, 5202/API mutation, retained database, candidate write, or World publication.
- Preserve all unrelated dirty Combat changes in the assigned checkout; do not stage or commit them.

## Verification and PR

1. Reproduce both failures with full traces and establish whether each is a product defect or fixture mismatch.
2. Run the packaging no-op byte-preservation regression and actual-repair regression, the two API regressions, and complete owning Ingest API suite; verify identical retry reuse, provider-free recovery, force creates a new run, and changed source/World context does not cross-reuse.
3. Run scoped Ruff/format checks, Python compile checks, and cumulative diff check. Inspect the exact `main@6531f003` to head diff.
4. Update this handoff with exact results and limitations, and mark the predecessor handoff settled without claiming rendered/real-recap acceptance.
5. Commit only the leased paths, push the branch, and open one review-ready PR. PRIME merges after ARCHITECTURE review.

### Current implementation evidence

- Root cause reproduced: exact run discovery returns the existing run and its ExtractionRun remains REVIEWABLE; the known-entity and SourceSpanIndex validators pass. GraphIngest added a zero-count repair diagnostic and reserialized the candidate anyway, changing its digest and causing the strict production-lineage check to reject it. No fixture mismatch was found.
- The packager now skips candidate writes when identity/evidence validation makes no semantic change, does not add a zero repair count, and only writes diagnostic fields that actually change. Real evidence repairs still update the packaged candidate and validation report.
- Verification passed: focused packaging no-op, actual-repair, and warning tests (3 passed); both API regressions (2 passed); the complete Ingest API suite (27 passed, 10 existing Pydantic warnings); Python compile checks; Ruff on the two changed test files and Ingest service; and `git diff --check`.
- The complete `tests/test_graph_memory_category_graph_preview_runner.py` file had one unrelated pre-existing failure (42 passed, 1 failed): `test_runner_canonical_line_only_index_reaches_category_prompt` reported `party enrichment incomplete for 1 nodes`. The same failure reproduced against the unmodified packager from `main@6531f003`.
- The shared packager has an existing Ruff F401 for `FixtureCategoryGraphPassClient` at line 38, unchanged from the base. Whole-file Ruff format check also flags all three large Python files for formatting; no broad reformat was included. Changed test/service Ruff checks passed.
- No 5202, live provider, retained recap, or rendered Ingest flow was used. This proves synthetic retry/recovery behavior only. Real Session 29 ingestion and persistence acceptance remain open for later dogfooding.
- Only the leased server/package/tests and the two handoff records are included; Combat changes and 5202 remain untouched.

## Predecessor settlement

PR #1333 (`INGEST: reset prior recap selection on route change`) passed independent ARCHITECTURE review and merged at `6531f0038d79431c6265afb3fd01e6d99458cd2b` from head `88510a3d8aeaff0caf9b84b674ee63e1b49836a5`. It fixed mounted same-campaign session-route changes and passed 63 UI tests with typecheck and diff-check. The operator's 5202 page is still on the Session 10 route with Session 27 selected; this is read-only observation of the currently served build and does not verify that merged code has been deployed. The predecessor did not claim live source load/process/save, real recap, or rendered PR acceptance. This settlement does not assert the remaining acceptance gates are complete.
