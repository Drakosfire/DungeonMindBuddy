# CLEANUP: preserve first-World authorization through the service facade

Status: ACTIVE under the user's cleanup goal and standing review/merge authority.
Base: 4b2bc1451f7a9f0a3e3cdbc82aaae29b2b557c0d.
Branch: codex/first-world-auth-forwarding; reuse buddy-bounded-production-logs checkout.
Topology: serial, one repair PR before continuing original finding 106 / #3534.

Scope: only prepare_first_world and confirm_first_world in
apps/live_control_server/services/extract_promote.py, the dedicated
 tests/test_first_world_authorization_facade.py, and this handoff. Forward the
existing keyword-only authorization callback to its current owner without
changing route policy, publication semantics, or internal optional-call behavior.
The callback must retain identity and any denial must propagate.

Ownership: inspected all 62 open PR file lists on activation. No open PR modifies
the facade file. #2288 owns the existing native initialization test file; do not
edit it. #3824 retains hosted route authorization ownership; do not edit routes.
Historical handoffs mentioning the service do not expand this bounded assignment.
No deployment, provider, operator database or retained World writes.

Evidence: #3534 comment 7002007270 records exact-source native prepare HTTP 500:
the facade rejects authorize_world although the publication owner supports it.
Disposable APP and native PostgreSQL migrations succeeded before that failure.

Verification: dedicated facade callback/denial tests; existing native prepare,
confirm and evidence read-pin tests against migrated, uniquely owned disposable
PostgreSQL with APP template/per-test clones; affected repo-owned backend contract;
exact-commit hosted frontend verifier and validator. Preserve any inherited failures.
Independent exact-head Bugbot review before merge. No claim that this repair alone
completes the synthetic Recap publication/Plan walkthrough.

Runtime: no listening application ports. Disposable PostgreSQL uses an ephemeral
loopback port and task-owned tmpfs data; stop/remove it after each verification.
Evidence and caches remain outside source on the verified Projects filesystem.
