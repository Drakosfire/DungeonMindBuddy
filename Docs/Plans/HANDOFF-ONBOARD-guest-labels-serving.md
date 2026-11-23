# ONBOARD: carry readable guest labels to serving

Status: ACTIVE for preparation only. The owner-authorized onboarding goal
includes Bugbot review, merge and deployment. This successor carries merged
main PR #4565 (`ebb710512f0e9d67568f2d28cdbb562207635c7b`) on the exact
unmerged Winter serving parent #4564 at
`4451cff66e0f5d0e66ddf1739156fdd668d0dc49`. Branch
`codex/onboard-guest-labels-serving-4451` uses the isolated
build-status-baseline checkout. This records stacked preparation; actual
delivery remains serial: #4557 merges and activates, then #4564 re-anchors,
merges and activates, then this successor re-anchors, verifies, merges and
activates. No production runtime is leased during preparation.

Write lease: the merged label handoff and guest page/test files carried from
#4565, plus this handoff. No backend, schema, guest snapshot, auth or runtime
configuration changes. Preserve the actual serving guest configuration. Review
the exact parent-to-head diff and verify the combined exact source with the
required hosted and discovered frontend checks; document inherited failures.
Any parent or runtime change requires re-anchoring rather than overwriting it.
After activation verify signed-out graph labels, source roles and temporary
additions on the deployed site.
