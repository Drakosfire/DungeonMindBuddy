# CI: preserve skipped tests in frontend collection parity

Status: ACTIVE. The owner's Sizzek delivery objective authorizes bounded fixes
needed for exact-source release evidence. Branch `codex/ci-collection-parity`,
base `89e24746136b6bf7bf04e9f8fc16e1820f45c24b`, checkout
`/home/drakosfire/Projects/.codex/ci-collection-parity/DungeonMindBuddy`.
Topology: parallel-independent of ONBOARD PR #4393: this lane changes only the
local verification tool and its tests, owns no product/runtime/database state,
and uses the global frontend lock for any frontend execution. #4393 stays pinned
to its own serving base and head; no outcome of it is inferred from this PR.
Historical verifier lease PRs #2303 and #2392 are merged; recheck open work and
exact write ownership before publishing. No live services or provider calls.

Expected exclusive write set: `scripts/ci_local_frontend.py`, a new narrow
Vitest collector under `scripts/`, `tests/test_ci_local_frontend.py`, and this
handoff, plus required CI inventory classification if a new test file requires
it. No test exclusions, selector changes, product changes or policy changes.

Invariant: retain independently collected identities and multiplicities of all
reported cases, including explicitly and conditionally skipped cases, and
preserve the existing hosted selected-case and full-discovery semantics. Reject
missing/extra/duplicated cases, collection failures, failed suites, ambiguous
filters, malformed or tampered receipts and source/command drift; never infer
success from a red run. Inventory must remain bound to the exact SHA and be
recomputed by validation using hashed evidence and the declared commands.
Vitest 3.2.4 `list --json` excludes skips, while the JSON reporter includes
them. An isolated Node 22 fixture showed `createVitest().collect()` retains
skips and duplicates, but also marks filter-excluded cases skipped; a throwing
suite has `suite.errors()` and nonzero exit even if unhandled errors are empty.
Any design must handle these explicitly and fail closed on unknown modes.

Validate with targeted Python guards, real Vitest fixture integration for
conditional/suite skips, duplicate names, name/file filters, missing/extra
cases, failed suite/import, collection failures, tampering and validation; run
an exact-head hosted verifier and a meaningful discovered comparison when the
global resource lock permits. Run independent cumulative review before merge.
Retain inherited red diagnostics truthfully; this does not authorize release or
change frontend qualification. Do not claim parity merely from matching counts.
