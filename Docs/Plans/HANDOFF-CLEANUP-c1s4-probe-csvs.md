# CLEANUP: retire historical C1S4 direct-probe CSV copies

Status: ACTIVE. Cleanup steward adopts this bounded demolition under the user's
standing cleanup goal, including implementation, independent review and merge.
Serial single PR; branch `codex/retire-c1s4-probe-csvs`, base `b69e7d712b50251f0a07d1ecf6aa827451df5cba`,
reused isolated checkout. No unmerged dependency or runtime/state allocation.

## Exclusive write lease

- this handoff
- `evals/c1s4_preplanning_vertical_slice/artifacts/pr59/README.md`
- `evals/c1s4_preplanning_vertical_slice/artifacts/pr60/README.md`
- `evals/c1s4_preplanning_vertical_slice/artifacts/pr61/README.md`
- `evals/c1s4_preplanning_vertical_slice/artifacts/pr62/README.md`
- `evals/c1s4_preplanning_vertical_slice/artifacts/pr63/README.md`
- each directory's matching `prNN_direct_probe_results.csv` (delete)

## Invariant and failure cases

These five historical generated CSVs have identical bytes:10530 each,33 rows.
Retire checkout payloads using exact Git links, SHA256 and byte counts in their
existing READMEs. Preserve all neighboring matrices/summaries, generators, gold,
corpus, tests and runtime. No claim of current regeneration from historical
inputs or disk/image savings follows from tracked-byte removal.

All58open PR heads were available: no target-directory changes. Targeted code
searches found only the producer write, not reads; consumers read different
matrix CSVs and must stay. All209registered worktrees checked;208contain targets,
none has target changes/errors. Batched active-handoff inspection across58heads
identified131unique candidate blobs; potential eval leases cover other named
labs, not C1S4 artifacts. A per-file scan was stopped for inefficiency and replaced
with this completed batched scan. Full generic-reader and remote-recovery checks
remain required before deletion; historical evidence must remain recoverable.

## Verification and delivery

Verify five payload hashes/CSV rows and pinned remote bytes. Run affected C1S4
retrieval-audit, benchmark and Canvas contracts before/after in fresh locked exact
source; retain failures and refuse any new regression. Review cumulative diff,
focused README links, exact-head hosted/build/validator, then independent review.
No frontend source change or new full discovered diagnostic is implied. Open/push
one PR and merge only after qualifying evidence. Existing operator, UI diagnostic,
backend preview and scaffold ownership followups remain unchanged.
