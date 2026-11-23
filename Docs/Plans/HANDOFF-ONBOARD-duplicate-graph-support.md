# ONBOARD: retain distinct Graph support in answers

Status: ACTIVE. The owner authorized the Sizzek onboarding lane, Bugbot review,
merge and deployment. Serial, independently reviewable repair on branch
`codex/onboard-deduplicate-graph-support`, based on fetched main
`3ff1d14d316a0f9f89dfdb1c4421fd8e5cc771c1`. The #4477 serving integration is
merged into the serving branch; its activation remains separately blocked by
the deployment account. This slice has no serving or database write lease.

A real private Sizzek question reached writer validation and failed the
`NativeAssertionClaimV1` distinct-support check. The retained diagnostic does
not identify the particular duplicate. Synthetic calls against the serving
image show that distinct read handles can resolve to the same assertion ID and
trigger that exact validation error. The fix must preserve each selected read's
exact source citations and qualifications while emitting each assertion ID once.
Repeated or foreign handles remain rejected. Do not deduplicate by weakening the
citation validator, changing assertion content, inventing support, or altering
model-visible context. Verify the actual shared completion/citation owning
boundary, including multi-read duplicate IDs, distinct IDs, conflicting or
missing evidence, and negative controls.

Expected write set: this handoff, `src/application_state/agent_conversation/
surface_evidence_answer.py` for assertion support projection only, and focused
`tests/test_surface_native_completion.py` or a new adjacent focused test. No
schema, prompts, provider, migrations, deployment or unrelated World changes.
Open #2462 was checked: it leases `native_plan_assertions.py` and several writer
tests, but not the scoped files above. The older #1927 handoff names this file
for instruction wording only; its PR merged and that lane's write is complete.
Recheck remote main and active PRs before review. Run affected locked Python
contracts on exact source, retain failures and isolation, review cumulative diff,
obtain Bugbot review, and run the repository-required exact-source hosted frontend
verification before merge. A passing synthetic reproduction is not proof that the
specific Sizzek turn selected duplicate assertion IDs or that its final answer is
correct; real retest is a separate deployed witness.
