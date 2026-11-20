# PERF: Reopen deferred Build receipts and their verified citations

ACTIVE serial successor to merged and deployed #4191. The hosted first-dispatch
goal authorizes the bounded repair. Base 2230cb80d. Branch
codex/jev-build-pending-receipt-ui; worktree and evidence on Projects.
Qualification uses disposable APP fixtures and local frontend verification.
No migration, provider prompt, authority, or primary data changes.

Reproduction: warm empty Corrupted Edge conversation on hosted 0133b38d
dispatched to Jev in 2316 ms. Its durable Build turn completed with 84
execution events and the exact NativeBuildQuerySettledV1 event. The browser
could not reopen its history details because it does not recognize the
pending admission pin. Browser Send-to-wire bound was approximately
2173–2508 ms under the desktop-clock assumption.

The admission receipt is immutable and its digest binds the originally
pending query. A final browser response must not substitute the settled
catalog into that receipt. The SERVER shared native response owner should
project a closed, minimal citation-membership view of the actual retained
settlement only when needed. A browser pending receipt must remain confined
to ordinary Build with the same GM World/source/revision/epoch and exact
question. Native assertion/clause citations still require actual matching
identities under that bound settlement. Receipts admitted with a full query
keep their existing validation and wire shape. No wholesale catalog transfer.

Write scope: SERVER shared native response model and projection, its existing
ordinary Build tests, UI wire types, shared native receipt validator and
existing browser history consumer/tests, and this handoff. Verify a real
provider-free ordinary Build response and its history projection, then exact
receipt-reopen and citation rejection on changed scope/digest/membership.
Retain independent review and local hosted/discovered diagnostics before
merge. Verify the saved original opening conversation after rollout without
rerunning its model requests. Continue first-dispatch measurements separately.
