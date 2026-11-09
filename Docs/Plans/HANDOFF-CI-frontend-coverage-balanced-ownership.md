# CI: cover local World and balance ordinary Build ownership tests

Status: SETTLED. PR #2281 merged at
643480036a0e8f79ab84dce330b06b7dcae27c08 after independent exact-head approval of
88d1ca2df7389fd40c25b424566c9cdbadd0fa5d and all seven hosted checks passed.
Alan explicitly authorized ready/merge; no deployment or protection change occurred.
The exclusive write lease is released. The additive CI transition is a new serial
capability; existing gates remain authoritative during its proof stages.
Historical implementation base and branch follow.
Base: eb0eb9a093b275e8e8282d6c749309f2bdd687a6. Branch:
`codex/ci-frontend-coverage-balanced-ownership`.

## Authority and ownership

Parallel-independent CI-only capability: restore missing frontend coverage and
reduce the measured ownership critical path without losing any test. Open PRs
2276/2279/2280 and the existing Surface/ingestion lanes were inspected before edits;
none owns these workflows. Prior CI handoffs duplicate-test-invocations and
migrated-test-template are SETTLED with their leases released. No predecessor
state-authority correction is necessary. This record documents the explicitly
assigned scope; it does not grant product delivery or merge authority.

## Write lease

- `.github/workflows/hosted-validation.yml`
- `.github/workflows/world-ownership-core.yml`
- `scripts/ownership_ci_partition.py`
- `tests/test_ownership_ci_partition.py`
- `tests/fixtures/ownership_ci_selectors.json`
- This handoff.

Do not edit Surface/canvas/product files, database fixtures, branch protection,
timeouts, required gate names, PostgreSQL configuration or production state.
No database service or shared runtime is allocated for collection/unit checks.
Dependencies and outputs belong to the task-owned Projects worktree/cache/scratch.

## Implementation and evidence

The frontend gate selects `src/localWorld` recursively, including its Surface and
canvas suites and future tests. Every previous frontend selector remains.

Only `test_surface_native_build_ordinary.py` is partitioned. SHA-256 of each full
pytest ID modulo four has owners World/Content, ingestion, saved-page, World/Content.
Other modules retain their owners. New cases deterministically receive one owner.
Default local pytest remains unfiltered. Every job retains its own PostgreSQL
service and existing migrated-template/per-test-clone isolation; no fixtures change.

Run42554631643 measured111 ordinary Build cases totaling504.36s (rounded phase
sums). Buckets total104.88/127.22/118.98/153.28s, with23/29/26/33 cases.
Against approximately148/276/435/809s group baselines, projected test totals are
406/403/435/424s. These are estimates from one prior run, not new hosted results;
setup/queue/runner times are excluded and splitting repeats session setup.
Raw timing logs and collection evidence remain in task-owned `scratch/`.

## Required verification and delivery

```bash
uv run --locked pytest -q tests/test_ownership_ci_partition.py
uv run --locked ruff check scripts/ownership_ci_partition.py tests/test_ownership_ci_partition.py
cd apps/live-control-ui && npm test -- src/localWorld
```

Compare actual collected definitions plus parameter-index identities for all four
old/new commands: preserve every original case exactly once, adding only the guard.
The checked-in selector snapshot and guard protect every original selector and
exercise complete/disjoint partitioning, non-target preservation and frontend
coverage. Preserve all existing gates and independent exact-head review. Commit,
push, open one draft PR, run hosted CI and report actual measurements separately
from projections. No merge or deployment. Further main commits alone do not require
a rebase; re-anchor only if integration/repository policy requires it.

## Settlement evidence

Actual collection retained all 2,560 original cases exactly once plus three guards.
Hosted ownership run42560926259 passed2,561 with the same two skips; test steps
were392/444/558/580s versus prior approximately148/276/435/809s. Hosted validation
run42560926240 passed frontend1,211 plus retained targeted4+1 cases, auth/app and
production Docker build without publishing. The longest step fell approximately28%
in this single before/after comparison; different source revisions/runners mean
these two runs are not controlled performance proof. No repeatable speed guarantee.
Raw and normalized evidence remains in the task-owned ci-stage predecessor scratch.
