# CLEANUP: retire historical PR41/PR42 C1S4 report payloads

Status: ACTIVE. Cleanup steward adopts this artifact demolition under the standing
cleanup goal's design, implementation, review and merge authority. Serial one PR;
branch `codex/retire-c1s4-pr41-pr42-reports`, base
`e25edf9017aeb6716eb84c1f97d966cfc2307378`, reused isolated checkout. No unmerged
dependency or runtime/provider/database/operator-state write.

## Exclusive write lease

- this handoff
- `evals/c1s4_preplanning_vertical_slice/artifacts/pr41/README.md`
- `evals/c1s4_preplanning_vertical_slice/artifacts/pr41/pr41_step2c_expected_context_multimode_report.json` (delete)
- `evals/c1s4_preplanning_vertical_slice/artifacts/pr42/README.md`
- `evals/c1s4_preplanning_vertical_slice/artifacts/pr42/pr42_step2c_expected_context_multimode_report.json` (delete)

The two READMEs explicitly classify these as PR-scoped diagnostics rather than
canonical benchmark truth. Steward chooses exact-Git historical retention, not
deletion of unique evidence or a new archive copy. Preserve the generator,
canonical/latest outputs, gold, neighboring artifacts and all tests. Historical
generation commands are context, not verified current regeneration instructions;
new runs belong in owned external output, not the retired paths.

## Caller/ownership audit

All58active PR head trees were available and scanned: no references outside each
report's own artifact directory. Current C1S4 code/tests have no directory-glob
readers. All207registered worktrees were checked for target-path changes,206had
target files and none were dirty/unreadable. No checkout/branch is removed.
All52pinned open-head handoffs have no C1S4/broad-eval lease. Current open PR file
paths have no overlap, including the complete102paths for unchanged#3824.

## Verification

Original JSON bytes total678579: PR41=332194, PR42=346385. Record SHA256 and exact
base Git links in the retained READMEs; verify JSON parsing, byte recovery and
path removal. Read every current/incoming reference before deletion; do not infer
operator usage or re-creation of old benchmark values from an old README command.
Run affected benchmark/Canvas contracts in isolated exact-source locked Python;
record baseline failures if any and prove no new failure. Check focused/current
docs links, export checker, cumulative five-path diff and unchanged runtime/
fixtures. Exact-head hosted/build/validator and independent review before merge.
No new extraction, provider calls, full UI diagnostic or release qualification.

Predecessor#4165 merged e25edf90; original52/#4156 closed with reproducible models,
required-nullable/scalar interface preserved and captured DTOs verified. The18
other original residuals and separate diagnostic/ownership followups remain open.
