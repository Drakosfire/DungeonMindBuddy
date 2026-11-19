# CLEANUP: derive verifier outcome from final source observation

Status: ACTIVE. Cleanup steward adopts original finding63 under the standing
cleanup goal's implementation, independent review and merge authority. Serial,
one PR; branch `codex/verifier-final-source-outcome`, fetched main base recorded
in Git. No unmerged dependency; reused isolated checkout.

Exclusive write lease: this handoff, `scripts/ci_local_frontend.py`, and
`tests/test_ci_local_frontend.py`. Fresh open-PR changed-path scan found no overlap,
including complete102paths for unchanged#3824. No workflow, selector, dependency,
branch protection, deployment, provider or operator-database changes.

Original63's aggregate simplification landed, but the final source inspection
still overwrites source facts after calculating the exit code. A disposable real
Git-worktree probe demonstrates exit0 with source_dirty_after=true; the evidence
validator correctly refuses it. Correct the command outcome from final facts.
Preserve nonzero test/build results, source identity, exception/cleanup evidence,
and all existing publication guards. Do not weaken the validator.

Verification: dirty and committed late-source regressions with real disposable
Git fixtures, full lightweight verifier module, exact-source official hosted/build
and evidence validation; independent cumulative exact-head review before merge.
Scratch/evidence remain outside source; no competing frontend run around the
global lock. No frontend code change or duplicate full diagnostic. Passing these
checks does not establish release qualification.

Predecessor#4159 merged e0f9fb079273eeb88e31b057269d3f02ef09a88f; current
statblock fingerprint is corrected. Original52/#4156 remains open for semantic
model-regeneration drift. This slice does not modify or close that contract.
