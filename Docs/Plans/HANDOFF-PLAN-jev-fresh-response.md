# PLAN — fresh Jev delivery and pending completion

ACTIVE serial slice under the operator's preparation/play goal (2026-10-21).
Base `95506406796f74a89cf0029abbcec4b51bc90611`; branch
`codex/plan-jev-fresh-response`; existing buddy-context-loop checkout. PRIME owns
implementation/merge/delivery; Bugbot reviews exact cumulative head. PR1566 is
merged; current other open lanes do not own these paths. One implementation PR.

Invariant: a newly completed governed Jev Plan reply returns the exact committed
content basis used by its frozen receipt. True durable replay retains its existing
null-basis/replay semantics. The UI must accept the fresh reply, settle only its
unchanged saved request, unlock the composer and allow a follow-up. On confirmed
history recovery, exact completed client-request correlation must also release
the matching shared pending lock. No weakening of evidence, receipt, scope,
revision or replay validation; unrelated/stale/replaced pending records stay locked.

Exclusive expected writes: this handoff; plan_jev_harness.py;
tests/test_plan_jev_harness.py; WorldPlanAgentConversation.tsx and its
WorldPlanAgentConversation.worldHistory.test.tsx; ROADMAP-demo.md and
HANDOFF-SURFACE-plan-root-world-entry.md for backward-looking settlement. Paths
are under their existing services/planSurface directories. No schema, provider
configuration, model/prompt, publication or unrelated surface mutation.

Verify fresh response serialization versus actual resolved basis and frozen
receipt, true replay with no second provider dispatch, UI fresh reply/follow-up
and exact completed-history recovery, including unrelated/replacement failures.
Use disposable PostgreSQL for tests; preserve operator APP/native data. Run
owning tests/typecheck/build, inspect cumulative diff, obtain Bugbot review,
commit/push/open PR, merge and guarded API/UI delivery to8000/5202. Identify owned
immutable services and preserve retained data/drafts; rollback on failed health.
Prove ordinary fresh rendered grounding→follow-up and Debug/citation inspection;
image flow is subsequent goal work, not inferred from this fix.

Predecessor: PR1566 merged955064067. UI955064067 is running5202, API71db547c
unchanged. Actual original root→World chooser→Elderwyld→Session29 navigation
passed without manual IDs. Guarded rollout preserved all1458 APP rows.
