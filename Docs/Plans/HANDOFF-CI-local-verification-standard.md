# CI: local exact-source verification and bounded hosted pause

Status: ACTIVE under Alan's explicit local-standard/GitHub-pause request. Branch
codex/ci-local-frontend-verification, isolated checkout from actual main
c93fe15abeb3b19adf3fd901ca8ec5ae558d43ab. This contains no retained2288/2298 edits.
Their denied commits800a/550975 remain on their original local branches; no retry
or laundering through this branch. No product/graph/ADV/source changes.

Exclusive lease: scripts/ci_local_frontend.py; tests/test_ci_local_frontend.py;
.github/workflows/local-verifier.yml; only automatic PR trigger blocks in
.github/workflows/hosted-validation.yml and world-ownership-core.yml; AGENTS.md
local verification policy; this handoff; ci/test-classification.json only new local
guard entry. Main/openness and related CI leases inspected; no concurrent writer
owns these policy/local-runner paths. Existing CI command-extraction fixture is
untouched. PR2302 remains a short report-only shadow lane; no selector consumer.
Qualification/safety denied branches are not modified by this implementation.

Invariant: isolate the requested immutable full SHA in a newly owned detached Git
worktree; use the shared frontend CI manifest's install/test/build commands and
pinned Node/npm, fresh npm ci, eight configurable workers. Default full discovery
removes hosted allowlist selectors, not tests. --suite hosted exactly preserves
shared manifest filters and is explicitly named as a safety sample. Retain discovery
and JSON results, exact SHA, runner/caller/source dirty states, versions, lock/contract
hashes, worker/resources, logs, test/build exit codes, durations and cleanup outcome.
Failure is never coerced to success; build still runs after test assertion failures.
Validate exact source/suite, artifact hashes, freshness and actual case parity.
Dirty tool source labels working-tree-diagnostic and cannot qualify exact evidence.

One persistent per-user flock inode prevents competing local verifier runs; all
agents must honor it for other Vitest tools. Memory/CPU and visible competing Vitest
checks fail closed before install. Process visibility is namespace-limited, so this
is not a claim to stop unrelated external processes. Cancellation stops the child
process group and removes only the newly owned temporary worktree. Outputs survive.
No shared node_modules, output overwrite, worktree/profile deletion or live DB.

Cutover scope: pause automatic PR triggers for two long test workflows only;
retain workflow_dispatch and all job/step bytes, short Rules/import regressions,
and new quick verifier guard CI. Actual main protections inspected: protected=false,
required contexts empty, branch rules empty. No protection/security change is needed
or performed. Rollback is restoring the exact parent trigger blocks, not rewritten
jobs/tests. No workflow is deleted and no self-hosted runner is installed.

Full regression/qualification remains an explicitly red diagnostic with owning
backlog, not release-qualified. Applicable local tests and independent exact-head
review remain mandatory; newly introduced failures or unproven baseline comparisons
block acceptance. Backend isolation and auth/CAS/rollback/history/graph draft safety
are not replaced by frontend-only evidence. Full discovered diagnostics remain
available and required at meaningful frontend checkpoints; avoid duplicate full-load
benchmarks. Benchmark worker01a1c105's reported8/16trial is context (about120s at8,
no meaningful16improvement), not exact-current-source evidence collected by this lane.

Before reporting cutover complete: independent cumulative review, verifier regression
and cleanup/lock tests, actual clean pinned-source execution, short hosted guard CI,
publication/remote verification, then explicit merge authority. Local branch policy
is not active on main before merge. Hosted manual checks remain available, and local
success is not a GitHub check or deployment/selector/qualification claim.

## Evidence/cleanup hardening from independent review

Initial dac2 review reproduced header relabelling and a surviving grandchild; it
was REQUEST_CHANGES, not approval. Successor binds the report to retained hashed
source provenance and completion receipt, re-derives commands/lock/catalog from
the requested Git object, and rejects header-only SHA/suite edits. Case parity
counts existing hosted -t unselected skips separately, never permits extra cases
in default discovery. Cleanup checks the process group independently of parent
exit and escalates TERM to KILL; a real subprocess-tree regression covers a
TERM-ignoring grandchild. Receipt hashes detect mismatched artifacts; this is
source-bound audit evidence, not cryptographic remote attestation of a local user.
