# CLEANUP: preserve first-World authorization through the service facade

Status: SETTLED. PR #4077 merged at a488b2c9870e2c57efc3c47fcb4a49ad8c2acdc8
from independently approved head bcb5020ce2d9eb99dd1c9b965578c8e4d1ab81e7.
The facade lease is closed; #3532 owns the next candidate-recovery slice.
Base: 4b2bc1451f7a9f0a3e3cdbc82aaae29b2b557c0d.
Branch: codex/first-world-auth-forwarding; reuse buddy-bounded-production-logs checkout.
Topology: serial, one repair PR before continuing original finding 106 / #3534.

Scope: only prepare_first_world and confirm_first_world in
apps/live_control_server/services/extract_promote.py, the dedicated
tests/test_database_first_world_publication.py, and this handoff. Forward the
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

Verification adjustment: facade regressions extend the existing classified database
first-World test module; no shared classification/contract registry edits.

Settlement evidence: exact-head hosted verifier 1,411 selected passes/build/validator;
world-and-content contract 444 passes, one skip, 74 deselected. Actual native
prepare/confirm and source read-pin checks pass. Two database locator fixture
failures reproduce on the exact parent and remain red. This does not complete
#3534 or prove the full synthetic Recap/tutorial or release qualification.
