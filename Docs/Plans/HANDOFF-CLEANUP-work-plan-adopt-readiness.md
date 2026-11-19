# CLEANUP: saved-review adoption readiness

Status: ACTIVE under the standing cleanup goal's implementation, independent
review and merge authority. One bounded prerequisite PR, base
`259a570495b1e4ba9d4aaad20504b62d811c631d`, branch
`codex/work-plan-adopt-readiness`, reused isolated checkout. No ports/services.

## Serial order and ownership

Navigation PR #4128 is parked on acceptance HOLD at
`d3b76cab58654fb8fa63657bca7de5d5e164600a`: its intended case passes, but full
discovery exposed the separate saved-review variant. Review/merge this readiness
repair first; then rebase and requalify #4128. Do not absorb navigation changes
or merge it through an unresolved observation.

Exclusive writes: this handoff and only the adoption readiness wait in
`apps/live-control-ui/src/surface/workPlans/StagedWorkPlan.test.tsx`. All59open
PRs and all paginated #3824 paths were checked; no overlapping test writes.
No runtime, placement storage, API, classification, dependencies or fixture change.

## Invariant and failure witness

Save publishes its comparison before asynchronous failure bookkeeping finishes;
its adoption button remains disabled until Save settles. The old test finds the
button, then fireEvent clicks without waiting for enabled state. A controlled
100ms lock-settlement delay on current source reproduces exactly the old-wording
failure. Waiting for enabled state passes the same scenario; the complete module
with that wait passes10cases. The delay is diagnostic only, not shipped.

Critique: existence is not readiness. Await the actual enabled control before
the real click, retaining both normal/notes-failure cases, IDs, wording, exact
saved V3 references, retired local wording, reload and no duplicate-write checks.
No sleeps, forced events or bypassed disabled guards in the shipped test.

## Verification

Retain original red full-run and controlled old/new evidence externally. Verify
an explicit disabled-state control, full module, exact-head hosted/build/validator
and full discovered diagnostic; independently review source and raw comparisons.
Compare against the retained109-failure baseline and prove current frontend and
verifier inputs unchanged by the intervening backend-only main merges. A passing
rerun alone does not establish cause. This repairs an observed variant, not an
additional permanent failure-count reduction or release qualification.
