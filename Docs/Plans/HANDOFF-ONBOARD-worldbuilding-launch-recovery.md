# ONBOARD: recover timed-out Worldbuilding launches

Status: ACTIVE under the owner's Sizzek onboarding goal and explicit authority
to review, merge, and deploy. Serial product slice based on `769632f94`, branch
`codex/onboard-worldbuilding-launch-recovery`. The deployed Winter Gazetteer
request returned an HTML error while the exact run completed; the UI lost that
run identity. The old run and the new completed run remain retained.

Outcome: both supported Build Worldbuilding approaches reserve a durable,
request-bound run before provider dispatch. A lost response can recover that
exact request without launching a duplicate. Preserve World ownership, exact
committed document revision and digest, profile, source identity, and existing
model policy. An uncertain or in-progress run must not be silently relaunched.
Request reuse with altered inputs or another World/document must fail closed.
Keep compatibility for existing extraction callers and existing recap recovery.

Write lease: this handoff; Build Worldbuilding launch/recovery model, service,
routes and focused tests; the worldbuilding-only functions in
`apps/live_control_server/services/graph_preview_runner.py` and
`apps/live_control_server/services/worldbuilding_ge_execution.py`; and the
Build extraction UI, same-origin API client and focused tests, including the
shared test inventory entry required for the new backend regression file. The open #2087
lane changes the recap-only function in the former file and shared extraction
runner internals; this lease excludes those functions and shared internals,
consistent with the owner's instruction to split the lease. No World, runtime,
port, or live provider is leased for implementation.

Verify duplicate/concurrent reservation, exact World/document/profile/digest
binding, changed-input and cross-owner denial, interrupted and completed recovery,
both Worldbuilding profiles, preserved recap behavior, and UI recovery after a
lost response at the actual route and component boundaries. Run applicable
exact-SHA backend and hosted/frontend diagnostics, inspect the cumulative diff,
and obtain independent Bugbot review before merge. Live Sizzek acceptance is a
separate, explicitly authorized deployment step.
