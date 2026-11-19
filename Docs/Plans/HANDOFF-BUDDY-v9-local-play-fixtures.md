# BUDDY — explicit local Runbook and rebase fixtures

Status: ACTIVE. Owner/designer: Elderwyld vNext completion lane; operator authorized
implementation/review/merge. Base293a78e2019060c722a109a82a5fb27f3afa53f3,
accepted4071 head (mergebd4429ebceda536c0150179bd04baf693aebbca4;
review5970210195). Serial local fixtures→remaining World/page contracts→4041.
Branch codex/v9-local-play-fixtures; existing isolated Buddy checkout.

## Three-path lease and invariant

Only this handoff; tests/application_state/test_runbook_work_object_postgres.py;
tests/test_live_play_run_rebase.py. Their client fixtures construct the full app
without selecting local deployment/auth mode, causing503 before intended behavior.
Set DMB_DEPLOYMENT_ENVIRONMENT=local and DMB_AUTH_MODE=local_operator explicitly
inside each fixture, with an explicit unproxied loopback TestClient peer. The local
boundary correctly rejects TestClient's default non-IP peer. Preserve actual auth
guards, DSN ownership, requests, replay,
conflict and corrupt-manifest assertions. If a route needs credentials, use real
fixture credentials rather than bypassing its guard. No runtime/schema/provider/
serving change. No migration-head spoofing or broad test exemption.

Full Runbook module currently includes two separate obsolete file-backed
worldbuilding assumptions. Keep those failures visible for their owning durable-
page/APP-down contract repair; this scope changes only fixture configuration.
Current main/open PRs/narrow instructions inspected; no exclusive bounded lease on
these client fixtures. No canary/worker uses checkout. Do not adopt later floating-
main runtime into the deliberately bounded release candidate.

## Validation and remaining goal

Run both complete owning modules at frozen exact SHA on uniquely owned disposable
APP databases on32903, retaining all outcomes. Explicitly prove formerly blocked
create/rebase/replay/manifest cases; independently classify any unchanged page
contract failures instead of labeling the full module green. Scoped lint/diff/
inventory, exact-head unmodified hosted frontend/canonical/shared lock, independent
cumulative review and normal checks before authorized merge.

4071 closed auth inventory:auth262passed,hosted1passed; frontend/review/checks
passed.4069 combat116passed;4068 source137passed0skips with real PostgreSQL
extensions;4067 Play route/cancellation repair accepted.4041 remains HOLD for
registered World fixture authority and durable-page APP-down contract after this
slice. Actual V9.B activation,V10 retirement,V11 baseline remain in full goal.
No frozen classic baseline or ingestion experiment rerun.

Use existing taskroot /home/drakosfire/Projects/.codex/v7-elderwyld-scope UUID
48fa5d10-fe99-4557-9fc9-d8a2a4b41ac8/write verified; venv without sync, task
scratch/cache, owned test DBs only. No manual worktree/container/global config or
deletion. Retain refs/evidence owner Elderwyld lane for qualification with scoped
cleanup followup after process/mount/dirty/unique checks; no reclaimed-byte claim.
