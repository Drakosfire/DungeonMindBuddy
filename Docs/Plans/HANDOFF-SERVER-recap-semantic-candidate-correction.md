# SERVER: immutable recap semantic-candidate correction

**Status:** MERGED as Buddy PR #976 at `4599888d3cbcf7c28170d10ba03b6497837e1502`; V1 candidate correction is current source behavior. Independent review and merge were settled before the separate V2 session-action handoff activated.
**Pinned base:** Buddy `origin/main@6fbf87f7035b6d17ffeb2d7aa8b35b2bc670cba8` after #975.
**Branch:** `codex/recap-semantic-candidate-correction`; isolated checkout `/tmp/dmb-recap-semantic-candidate`.
**Topology:** serial, independent source PR against `main`; no merge authority.
**Predecessor:** #975 quote-only child and #973 held semantic gate are merged.
**Authority:** PRIME accepted ARCHITECTURE's distinct immutable correction ruling and explicitly assigned this one source slice, including the enumerated APP-STATE basis/CAS implementation, to SERVER. APP-STATE retains contract/review ownership and must independently review before merge.

## Primary question

Can a GM derive a new, immutable recap child from one exact frozen reviewable candidate by replacing at most one named node description and omitting at most one named edge, with a reconstructable bounded manifest and a distinct whole-child semantic basis, while retaining every unrelated candidate field and the existing source/span/evidence authority?

The operation is a distinct route, schema and derivation. It must not broaden the literal-quote endpoint. Corrections are described by exact node ID, original and replacement description, and exact edge ID; at least one action is required. The server reconstructs the complete child from the exact parent candidate and manifest; callers never submit arbitrary candidate JSON. Any dependency on the omitted edge fails closed; do not cascade a second edit. No hardcoded Session 27 IDs. PRIME clarified these bounds after the initial handoff pin.

The new child starts `reviewable` and `held`. Its canonical APP-STATE basis binds parent and child candidate SHAs, source and span SHAs, manifest SHA, scope/profile, and derivation. The existing one-shot CAS decision works on the whole child, with exact retry behavior. Prepare refuses held/rejected children; accepted prepare seals this basis, and confirm re-proves it before the World writer. Existing quote-only V1 basis and behavior remain unchanged.

## Expected write lease

- New `apps/live_control_server/services/recap_semantic_candidate_correction.py` and focused `tests/test_recap_semantic_candidate_correction.py`.
- `apps/live_control_server/models/extract_promote.py`, `apps/live_control_server/routes/extract_promote.py`.
- `apps/live_control_server/services/extract_promote.py`, `apps/live_control_server/services/recap_semantic_disposition.py`.
- `src/application_state/ingest/service.py`; `src/application_state/ingest/repository.py` only if a genuine CAS gap appears.
- Focused `tests/test_recap_semantic_disposition.py`, `tests/application_state/test_ingest_run_postgres.py` only for boundary proof.
- This handoff.

No UI, runtime deployment, real S27 POST/decision/publication, source artifact edit, provider call, DungeonMind/native Graph writer, table, or migration. No shared ports or database writes except isolated test PostgreSQL fixture state.

## Failure cases and acceptance witness

Refuse stale parent/candidate/source/span, missing or duplicate IDs, stale original text, no-op or empty correction, arbitrary field edits, dependent edge references not handled by the bounded manifest, wrong campaign/session/profile, non-reviewable source, child identity collision, malformed manifest or digest, stale CAS revision, and changed candidate/proposal/World head. Refusal must not mutate parent or publish WorldGraph.

Focused service and HTTP tests must prove deterministic replay/idempotency, exact parent preservation and source evidence, held/rejected prepare and confirm refusal, accepted sealed basis at prepare/confirm, and unchanged literal child path. APP-STATE real PostgreSQL tests must prove V2 whole-child CAS, exact retry, stale/conflicting decision refusal and V1 parity. Run relevant full repository test/lint/type gates, inspect cumulative `origin/main..HEAD` diff, then record exact evidence and implementation head here. Synthetic fixtures only; no real S27 actions.

**Acceptance token:** `SERVER_RECAP_SEMANTIC_CANDIDATE_CORRECTION_SOURCE_READY` only after exact-head checks and independent PRIME + APP-STATE review. Implementation may hand back a PR before reviews; token is then pending.

## Implementation evidence (2026-10-06)

Source implementation commit: `f09469def83a4c666c5f074ec9c0d7495fb6fede`, based on the pinned `6fbf87f7035b6d17ffeb2d7aa8b35b2bc670cba8`. This commit adds only the enumerated owner paths. The candidate operation is limited to one description replacement and one edge omission. Its manifest is replayed at creation, decision, prepare, and confirm against exact parent/child/source/span bytes. The whole child starts held; the existing APP-STATE single-use decision CAS now accepts the distinct V2 basis. No World writer was called in correction tests.

The exact three previously excluded full-app HTTP tests were run at the pinned base `6fbf87f7` and PR head `ac2d2e6b` with the same shared virtual environment and command. Both runs failed before assertions at `apps/live_control_server/integrations/dungeonmind/native_world_source_admission.py:20`: the installed `dungeonmind.application.vnext` lacked `initialize_empty_knowledge_space`. That base/head comparison establishes the dependency mismatch as inherited. It did not exercise HTTP auth, CSRF, or review readability.

The repository's `scripts/prepare_patched_hermes.py` prepared the pinned ignored Hermes source in this isolated checkout, then `UV_CACHE_DIR=/tmp/dmb-uv-cache uv sync --locked` installed the exact locked dependencies, including DungeonMind at `7c69e447f6d4acc963ac09c6fb9cb48cc1c5b9cc`. No tracked dependency pin or running service changed. The same three HTTP tests then passed. The complete focused command, `.venv/bin/python -m pytest -q tests/test_recap_semantic_candidate_correction.py tests/test_recap_semantic_disposition.py tests/test_recap_literal_evidence_correction.py tests/application_state/test_ingest_run_postgres.py::test_semantic_candidate_basis_cas_is_distinct_and_single_use tests/application_state/test_ingest_run_postgres.py::test_recap_disposition_cas_preserves_run_and_exact_retry`, passed **36 tests** with 11 nonfatal Pydantic field-name warnings. The two APP-STATE tests used disposable real PostgreSQL on port 54329. Focused Ruff on all changed Python files and cumulative `git diff --check` passed. Full repository Ruff still reports 1,434 pre-existing errors outside this write lease; changed Python paths pass.

PRIME and APP-STATE exact-head source review was settled before PR #976 merged at `4599888d3cbcf7c28170d10ba03b6497837e1502`. The V1 source capability is established. No real S27 correction request, semantic decision, native publication, runtime deployment, or WorldGraph readback occurred in that source slice.
