# CI: cover local World and balance ordinary Build ownership tests

Status: ACTIVE implementation under Alan's explicit CI-first instruction, delegated
2026-11-09. Publication is one draft PR; merge requires coordinator confirmation.
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
