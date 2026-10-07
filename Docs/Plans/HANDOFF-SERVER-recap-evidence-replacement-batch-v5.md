# HANDOFF — SERVER: recap evidence replacement batch V5

**Status:** ACTIVE — implementation authorized by the ARCHITECTURE ruling relayed by PRIME.
**Base:** Buddy `main@74dc8c45a8f6bc6220a2c7d3ad5545afc0e68805` (#1006 merged).
**Branch:** `codex/recap-correction-batch-v1`.
**Topology:** One independent PR against `main`; no merge authority.
**Lease check:** Open #1008 changes no recap-correction or APP-STATE ingest paths. This slice stays in the #1006 correction seam.

## Contract

Add request/response V5 for at most seven exact-preimage evidence replacements on one pinned parent. A target is unique by `(record_kind, record_id, evidence_index)`; duplicates reject the entire request. Each operation pins source ref, source artifact, current span, and current quote list, then supplies the replacement span and quote list. Same-span quote-only edits are supported. Historical V4 remains a one-operation span relocation with its original behavior.

Replay all operations against the frozen parent in memory. Only after every preimage passes, run the existing complete child quote/source, candidate document integrity, and typed graph validation. Write one ordinary held child only when all checks pass. No held invalid intermediate child is created. The new manifest, derivation, semantic basis, assessment, effect binding, and APP-STATE structural CAS are versioned together; no lifecycle or generic correction framework is added.

## Write set

- `apps/live_control_server/models/extract_promote.py`
- `apps/live_control_server/routes/extract_promote.py`
- `apps/live_control_server/services/extract_promote.py`
- `apps/live_control_server/services/recap_semantic_candidate_correction.py`
- `apps/live_control_server/services/recap_semantic_disposition.py`
- `src/application_state/ingest/service.py`
- `tests/test_recap_semantic_candidate_correction.py`
- `tests/application_state/test_ingest_run_postgres.py`
- `Docs/Plans/HANDOFF-RAKE-plan-mounted-harness-repair.md` — remove one stale forbidden-path row per the operator's direct request.
- This handoff.

No provider calls, live registry/Graph/source writes, runtime rollout, or private-corpus check-in. Tests use synthetic fixtures.

## Local S14 request packet

The complete five-operation request is local only at `/tmp/c1s14-edge013-reanchor-265stynz/s14-correction-request-v5-local.json`, SHA-256 `bf8121855ab38046c2789e57465de319bf232294b99d28783ea314fcb9c7c5a4`. It combines the proven `edge:session14:013` line 45→47 relocation with the four literal-supported corrections. Original parent candidate SHA-256: `bed10af6c4ab8c43fc510b79088f5080b7c4c1ecac53e47074851f6537fd5e10`; source SHA-256: `e10679f7fe09d7f8a267730684702157ca08caa928bdfc246a4b8d03573f8e96`; span-index SHA-256: `bb620272aece20b73188f2bd5ec307354af7f9cfb0090ea844153485891d159c`.

## Verification and handback

Direct tests cover a full-valid synthetic four-operation held child, stale-operation all-or-nothing rejection, inherited invalid-anchor rejection before child write, duplicate request target rejection, V5 route behavior, V5 basis/assessment/CAS structure, and unchanged V4 singleton behavior. On 2026-10-07, the focused correction suite passed **32 tests** and semantic-disposition tests passed **17 tests**; one full-app test in the correction suite and two full-app disposition tests were excluded because the installed DungeonMind package lacks `dungeonmind.application.vnext`. Scoped Ruff and `git diff --check` pass. The new real disposable PostgreSQL V6 CAS test is implemented, but the fixture could not connect to `127.0.0.1:54329`, so owning-database CAS remains unverified here. Inspect the exact base-to-head diff, then commit, push, and open one PR for independent PRIME and APP-STATE review. No acceptance token until exact-head review is complete.

## Post-review validation (2026-10-07)

Independent review found that the APP-STATE span-manifest validator had applied V6's same-span quote-only allowance to the historical V5 basis used by the V4 relocation route. The validator now requires a span change for `RecapSemanticBasisV5`; `RecapSemanticBasisV6` continues to allow quote-only edits. A direct PostgreSQL CAS regression verifies that the V5 request is rejected without advancing the child revision, while the V6 test verifies acceptance and exact retry reconstruction.

The owning tests ran against a temporary PostgreSQL 16 Alpine container bound only to `127.0.0.1:54329`, with its data directory on tmpfs and no persistent volume. The fixture created and dropped its uniquely named test database; the temporary container was stopped and removed afterward. The focused correction, semantic-disposition, literal-correction, V5 regression, and V6 CAS command passed **64 tests** with 11 existing Pydantic field-name warnings using the previously corrected isolated dependency environment. Changed-path Ruff and `git diff --check` passed. No live database, runtime, registry, corpus, or Graph was touched.
