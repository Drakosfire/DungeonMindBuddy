# INGEST: offline study baseline freeze

Status: ACTIVE. Authorized by the user's ingestion simplification study goal.

Outcome: retain a byte-verified, write-once baseline through the existing evaluator
CLI without initializing providers or databases. Missing evidence stays unknown;
freezing evidence does not certify semantic quality or publication.

Topology: stacked on PR #2146, exact parent
f640d6ba340b48762a297ca9832c25c3d4302fdb. Merge/rebase #2146 before this slice.
Branch: codex/ingest-study-baseline-freeze; current isolated checkout. No runtime,
port, provider, database, publication or primary-data writes. Baseline output is a
private artifact directory supplied explicitly by the operator.

Exclusive expected write set:
- src/ingestion_evaluation/baseline.py
- scripts/evaluate_ingestion.py (offline baseline dispatch only)
- tests/test_ingestion_evaluation_baseline.py
- Docs/Guides/ingestion-study-baseline.md
- this handoff

Invariants: exact hashes before retention; copied bytes independent of historical
paths; unknown groups have explicit reasons; all required evidence categories are
represented; no overwrite/replay; verification checks every retained member and
the sealed inventory. Partial failures never produce a completed baseline.

Validation: CLI-level offline freeze/verify; mutation and missing-byte rejection;
unknown handling; output replay rejection; existing evaluator regression tests;
independent subagent review of cumulative parent-to-head diff.

Assessment normalization and controlled experiments are serial successors, not
implemented here. No obsolete runtime path is removed based on an evidence freeze.
Historical runner versions remain pinned evidence, not an alternate live default.

Validation observed: 8 baseline tests and 21 existing runner tests pass (29 total).
The sandboxed combined run stalled after 17 tests in a synthetic ASGI fixture;
the identified pytest process was stopped, and the same suite completed outside
the sandbox in 1.67 seconds. No product process was stopped. Independent subagent
review approved the five-file slice and independently injected a partial-copy
failure; that failure case is now also a permanent regression test.
