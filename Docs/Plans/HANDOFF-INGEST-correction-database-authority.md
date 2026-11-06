# INGEST: database-owned candidate correction

Status: ACTIVE — user-authorized owning defect removal; no evaluator or provider effects.

## Outcome and invariant

Ordinary correction creation, exact retry and semantic replay use canonical source
records and immutable APP component bytes. Local package files, directories and
locks confer no authority and are neither required nor written. Preserve exact
parent/source/profile/manifest bindings, deterministic child IDs, held semantic
state and fail-closed replay. Existing locator strings remain provenance only;
this slice does not migrate historical rows or introduce a producer/schema.

## Lane and topology

Branch `codex/ingest-correction-database-authority`; base parent PR #2144 head
`71652b262ec7a7e4e859fa0028b267fe5be448d6`. Stacked delivery: merge/rebase #2144
before this successor. The evaluation tooling stack #2137 is independent and
unchanged. No merge/deployment authority. Root owns design and implementation;
subagent reviews the cumulative change. PRIME coordination only for overlap.

## Expected write lease

- apps/live_control_server/services/recap_semantic_candidate_correction.py
- src/application_state/ingest/components.py (database correction serialization)
- tests/test_recap_semantic_candidate_correction.py
- tests/test_correction_source_order.py
- tests/test_database_semantic_replay.py
- tests/test_correction_database_authority.py
- this handoff

No schema, extraction prompt, Gold, runner, native graph or primary-data writes.
Tests may create disposable synthetic APP databases only. Runtime evaluator 55447
and primary remain untouched. Retained C1 actual outputs remain immutable.

## Failure cases and validation

Replace host-local serialization with APP database serialization across hosts.
Refresh parent authority under the lock; retain existing CAS and child identity
checks. DRAFT exact owned output persistence may recover interruption; frozen
children require exact existing database bytes and must not be repaired from
files. Historical child reuse requires DB replay, never a package or URI shape.
Orphan files must neither block a valid operation nor rescue missing DB evidence.

Prove current V8 creation and retry without package access, exact held lineage,
source/candidate/index drift rejection, partial failure recovery, and database
lock serialization/release. Run existing semantic correction/source order and
DB replay regressions; inspect cumulative diff and obtain independent review.
Broader evaluation runner work follows this slice and is not part of it.

## Observed validation and limits

- Current V8 correction/source-order/semantic regressions: 185 passed, one
  known auth setup test deselected (expected401/actual503 independently
  reproduced before this slice).
- Actual disposable APP tests cover file-free create/retry, type-only exact
  delta, interruption recovery, immutable evidence refusal, historical reuse,
  recorded/concurrent disposition preservation and advisory lease contention.
- Legacy `test_database_semantic_replay` manually constructed V2 basis digest
  test fails identically on the untouched parent frozen runtime; no all-green
  legacy/auth claim. Missing/corrupt DB replay tests passed.
- No evaluator 55447, primary, native graph, provider or publication effects.
- Existing V9 explicit roster-file authority is outside this generic package
  removal; it has not been weakened or represented as database-owned here.
