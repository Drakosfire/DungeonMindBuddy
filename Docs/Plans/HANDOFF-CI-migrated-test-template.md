# CI: reuse a migrated database template with isolated test clones

Status: SETTLED by #2203, merge 2f41ff02417f52e6ff5d358959803d2d3c0cbb91.
PRIME owned the measured CI setup bottleneck under the operator's
CI-first goal and explicit CI-demolition gate waiver. Independent review and
local owning-boundary verification remain required. Larger coherent slice allowed.

## Evidence and topology

Parallel-independent from mainc8d2b596d2a1dbb323b85d73f500b13c4e2e622a;
branch codex/ci-reuse-migrated-test-template in the existing checkout/dependencies.
PR2201 is merged at that ref, independently reviewed6d2f18ab6;167 repeated selections
were removed while2240 distinct cases remain. Its baseline runs42420353355 and
42420354928 stay frozen; no cancellation/restart or source alteration.

Completed World/Content baseline:181passed,811.68s pytest,761.11s setup,17.24s call,
22.18s teardown (console-rounded),849s job. Local unchanged-fixture probe:three
fresh databases cost1.63–1.69s setup each; all three removed. One idle migration
connection remains before cleanup. Keep local and hosted observations separate.
Other ownership groups still measure the full baseline; no full CI gain claimed.

## Outcome and invariants

Run the real migration chain once per pytest session on a new owned test database.
Every test still gets its own freshly cloned database and its existing environment
binding, cleanup and head verification. No transactions shared across tests, no
shared mutable test data, no migration skipping/fake schema marker, and no fallback
to operator databases. Existing explicit unmigrated/predecessor databases and
migration tests remain unchanged. One admin target per session; changing it must
fail clearly instead of reusing a template from another server.

The migration environment must dispose its own Engine after success or failure,
otherwise PostgreSQL cannot clone a source with an idle pooled connection. This
is the necessary owning-boundary resource fix, not changed schema/data semantics.
No new migration, provider, runtime deployment, cache framework or dependency.

## Exclusive write set

- This handoff.
- Docs/Plans/HANDOFF-CI-duplicate-test-invocations.md (truthful predecessor settlement).
- tests/application_state/conftest.py (existing disposable DB owner).
- src/application_state/migrations/env.py (owned migration Engine lifecycle only).
- tests/test_application_state_database_fixture.py (real isolation/resource/failure proof).
- .github/workflows/world-ownership-core.yml (include owning fixture tests).

Local write lease: generated disposable-test databases only on54329; noAPP54331,
Core54330, benchmark55447, running5202, corpus, sources or user draft/state changes.
Keep product2196/2197/2199/2200 and heldPlay/citation/INGEST/SURFACE separate.

## Verification and delivery

Prove real migration/head, no idle template connection, distinct clone identities,
row/schema mutation isolation, failed-test cleanup, failed-migration cleanup and
refusal after template/admin mismatch. Exercise existing World/Content, migration,
concurrent allocation/CAS, retry/recovery and native writer cases on clones. Compare
setup phases against the frozen baseline; label local probes independently.
Inspect cumulative diff, independently review exact head, commit/push/open one PR,
merge with the explicit CI gate waiver after local proof/review, then deliberately
measure the same hosted groups. Preserve all failures and original baseline logs;
repeat measurements before claiming robust full-CI improvement.

## Local verification at candidate

- World/Content exact existing selection plus nine fixture cases: 190 passed in
  22.18 seconds locally. This is validation, not a hosted speedup comparison.
- Native ordinary authoring, Plan assertions and selected migration checks:
  120 passed; one historical migration test failed. The same failure reproduces
  with both modified Python files restored to exact parent c8d2b596d2a1dbb323b85d73f500b13c4e2e622a:
  test_upgrade_retains_historical_row_and_closed_predicates_exactly upgrades to
  its fixed historical 0103 revision, then invokes a reader requiring current head.
  No test exclusion or product behavior change was made to conceal it.
- Collection preserves all 2,240 pre-existing distinct cases; nine new cases give
  2,249 total. No original definition/parameter-index case is removed.
- Ruff and cumulative diff whitespace checks pass. Original failed attempts,
  parent reproduction and full collection evidence remain in private runtime
  evidence under ci-template-*. The initial in-memory parent probe did not replace
  pytest's reloaded fixture and failed at setup; it is retained as an invalid probe,
  not counted as the successful exact-parent reproduction.
- CI merge gates are explicitly waived for this demolition slice by the operator.
  Independent exact-head review is still required. No hosted speedup or complete
  CI improvement is claimed before post-merge measurement.

## Settlement

Independent review approved exact head 2e6c7da64287a7dc2f6eef08474a63bff8e9ec45.
Merged with the explicit CI waiver; no product runtime was changed. Two complete
measurements at identical trees passed: ownership 1081/1043 seconds. World/Content
190 cases: 64.51/63.06 seconds; ingestion 580 passed + one skip: 261.93/264.65;
query 780 passed: 315.62/315.31; saved-page 479 passed: 1033.39/999.10 seconds.
The original saved-page run timed out at 45 minutes and remains retained, not
counted as a completed baseline. Both hosted auth/Docker workflows also passed.
Private ci-template-* artifacts retain raw logs, phase data, source/attempt pins,
coverage and queue/dependency timing. No billing/CPU or broad product-goal
completion is inferred. No further CI change is active in this lane.
