# INGEST: preserve Process evidence through exact-run review reload

**Status:** ACTIVE — PRIME explicitly authorized this serial synthetic owning-boundary proof on 2026-10-17.
**Base:** Buddy `main@e63131e1ebbc012bfd4f266036779e64ec0c5aff` (merged #1357).
**Branch:** `codex/ingest-process-review-persistence` (remote ref; the assigned checkout's shared Git metadata is read-only).
**Checkout:** `/home/drakosfire/.codex/worktrees/996b/DungeonMindBuddy`; reuse the existing checkout, dependencies, and disposable test fixtures. Do not create a new checkout, environment, or service.
**Topology:** serial Ingest successor after #1357. PRIME explicitly transferred the dormant Process-idempotency lease to this slice. Open #1235 remains on separate Graph Review/source-observation paths and is not a dependency. PRIME retains review and merge authority.

## Mission

Prove that one ordinary Process of a newly supplied recap produces a reviewable graph candidate with source-bound evidence, and that the exact run, candidate, and source remain recoverable for review after a fresh API client is created. Preserve World, campaign, session, source artifact, source digest, run, and evidence-span identity through that path.

This is an owning-boundary test slice, not a new product capability. Do not modify route, schema, extraction, API, or persistence behavior unless the test exposes a concrete failure at this boundary.

## Starting evidence

- `tests/test_live_recap_ingest_graph_preview_api.py::test_recap_ingest_generate_recap_memory_with_graph_extraction_fake_client` already exercises ordinary Process, a fake extraction, source registration, candidate/manifest creation, and an exact World projection. It validates most work in one client and does not reopen the exact run's durable source through a fresh API client.
- `GET /api/live/graph-preview/extraction-runs/{run_id}` reloads the canonical exact run from APP-STATE. `GET /api/live/graph-preview/extraction-runs/{run_id}/recap-inspection` reloads the exact source prose from APP-STATE. Candidate and source-span components remain addressable from the immutable graph-ingest manifest.
- The durable Session 29 normalized recap named by the gold manifest is available outside this checkout at `/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy/out/graph_memory/runs/longmont-c2/session-29/20261015T204654Z/normalized_recap_source.md`; its SHA-256 matches the manifest (`4f963656828b553f7919ee00d3304725ddff892a13651b989f99b9b649933796`). It may be copied into a disposable fixture for local verification only. Never commit its text or reuse the stale `f43e48e6-c775-4960-824f-fb398fe50bb9` candidate/run.
- The existing owning fixture creates a unique disposable APP-STATE database through the configured test PostgreSQL service on `127.0.0.1:54329`. That service was unavailable in this checkout during the initial baseline attempt, which failed at fixture setup before the test ran. Do not start a server or redirect this test to a retained database; use an already available disposable test service or report the verification gate honestly.

## Exact write lease

- `Docs/Plans/HANDOFF-INGEST-process-review-persistence.md` — this contract and truthful evidence.
- `Docs/Plans/HANDOFF-INGEST-process-idempotency-recovery.md` — factual settlement that PRIME transferred its dormant lease here; preserve its observed failures and do not imply they were fixed.
- `tests/test_live_recap_ingest_process_review_persistence.py` — one portable synthetic Process→candidate/evidence→fresh-client review reload owning test. Prefer the existing fake extractor and isolated fixture helpers; keep the default test input synthetic and do not commit private recap text.
- `apps/live_control_server/services/recap_graph_preview_ingest.py` — conditional only if the new test reproduces a concrete service-level defect in this exact persistence path; retain all source/run/digest gates. Stop and ask PRIME before any other path or behavior changes.

No Graph Review UI/API paths owned by #1235, other test modules, schemas/migrations, provider configuration, credentials, corpus, retained source/candidate/run files, World publication, live databases, runtime services, served assets, or 5202 writes are leased.

## Invariants and proof

- Process exactly one explicit World/campaign/session source. The test uses synthetic recap text and a deterministic fake extractor; no model or external provider call.
- The response's exact ExtractionRun is reviewable and its candidate, validation report, source artifact, and span index are present and digest-bound in the disposable root.
- Candidate evidence references resolve to the exact SourceArtifact and source span generated from the Process input; the run/source identities agree on `world:elderwyld`, `longmont-c2`, and the selected `session-N`.
- Close the first API client, construct a fresh `TestClient(create_app())` against the same disposable roots/APP-STATE database, then retrieve the exact run and `recap-inspection` by that run ID. Assert the source status, digest, prose, World/campaign/session, candidate evidence, and identity are unchanged.
- Any inspect/status operation stays read-only. No Graph Review confirmation, publication, World Graph mutation, rerun, or “latest” substitution.
- If the boundary fails, retain the complete failure. A service repair is allowed only at the conditional service path above and only for a defect demonstrated by this proof.

## Verification

- Run the new owning test with the repository's Python test runtime and the already available disposable PostgreSQL fixture service; do not launch a service or use user data in place of the fixture.
- Run relevant ingestion tests, lint/type checks for changed paths, and `git diff --check` once the test runtime is available.
- Inspect the exact cumulative `main@e63131e1...` to head diff, publish one serial PR, and present it to PRIME. No merge authority.

## Handoff transfer

PRIME explicitly transferred the dormant lease from `HANDOFF-INGEST-process-idempotency-recovery.md` to this serial successor on 2026-10-17. That handoff's two historical idempotency/recovery failures remain unresolved observations unless separately proven and fixed. This slice does not claim to repair retry reuse or provider-free recovery.
