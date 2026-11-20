# BUDDY — database-owned page contract proof

Status: ACTIVE. Owner/designer: Elderwyld vNext completion lane; operator authorized
implementation/review/merge. Basea3d927b3ab44e9059c496e242b44eba43b6112e7,
accepted4075 head (mergef65c5ed66586725f51737d454c727938892bd61b;
review5970411974). Serial final fixture reconciliation→4041 final qualification.
Branch codex/v9-durable-page-contract-proof; existing isolated Buddy checkout.

## Two-path lease and explicit contract reconciliation

Only this handoff and tests/application_state/test_runbook_work_object_postgres.py.
Canonical tests/test_authored_page_database_cutover.py already specifies ordinary
workspace Pages have one database owner and no file mirror. Current Page creation
requires a registered World and APP persistence. The old outage test's file-backed
fallback expectation was superseded by that accepted contract; replace it with
negative coverage rather than restoring a nonexistent fallback or dropping tests.

Create a real World/page while APP is available; verify its snapshot/no Markdown
mirror. Remove APP DSN and independently require503 for valid create, scoped list,
and existing-page snapshot; assert no file fallback/output. Keep IDs and metadata
valid so failure is persistence unavailability, not missing World/input validation.

The old latency control is now also a PostgreSQL Page. Supply real registered World
ownership and rename test/variables/output labels to current durable Page/runbook.
Preserve prepare/commit/load, current/historical reads, existing-run admission,
exact Markdown and every nonnegative timing assertion. This is current storage
smoke coverage, NOT the retained classic retrieval benchmark, a replacement
baseline, or an optimization/speed claim. No provider/ingestion experiment.

No runtime/auth/schema/dependency/serving changes or edits to the repaired client
fixture. Existing V1 Tiptap API supports the canonical Page workflow. Independent
read-only design critique approved both replacement proof boundaries. Current main/
open PRs/narrow instructions and old named-selector references checked; none requires
additional paths. No active conflicting lease or worker/canary on this checkout.
Do not adopt later floating-main runtime into the bounded candidate.

## Validation and remaining goal

Target both reconciled cases, then complete Runbook/rebase modules plus canonical
page-cutover module at frozen exact SHA using owned32903 disposable APP fixtures.
Scoped lint/diff/inventory, unmodified exact-head hosted frontend/canonical/shared
lock, independent cumulative review and normal checks before authorized merge.
Preserve failures and exact synthetic-vs-serving proof limits.

4075 full hosted366passed;4072 local create/rebase pass;4071auth262;4069combat116;
4068source137withrealPG accepted.4041 still requires final exact candidate consumer/
frontend/source/config/browser/write/process-rollback qualification and review.
V9.B actual live readiness/activation,V10 retirement,V11 deployed baseline remain.
No frozen classic baseline rerun or live Elderwyld mutation.

Use existing taskroot /home/drakosfire/Projects/.codex/v7-elderwyld-scope verified
UUID48fa5d10-fe99-4557-9fc9-d8a2a4b41ac8/writable, venv without sync, task scratch/
cache and owned test DBs only. No manual worktree/container/global configuration/
deletion. Retain refs/evidence owner Elderwyld lane for qualification and scoped
cleanup followup after process/mount/dirty/unique checks; no reclaimed-byte claim.
