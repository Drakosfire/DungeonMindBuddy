# BUDDY — historical storage-owner comparison fixture

Status: ACTIVE. Owner/designer: Elderwyld vNext completion lane.
Authority: operator finish-vNext implementation/review/merge authorization.
Base803e95912511f7692ec044ca5333ba73cc4818a0 (accepted4059); branch
codex/v9-historical-storage-fixture. Serial fixture repair→merge→resume4041.

## Outcome and exclusive two-path lease

Only this handoff and tests/application_state/test_native_storage_owner_migration.py.
The historical update comparison deliberately qualifies0138→0139. Current
_fresh_case now reads content.page_presentation, introduced0158, so running that
current application against0139 is invalid fixture setup. Do not add later DDL,
upgrade the historical target to head, fake its schema version around current
content operations, or substitute an unavailable-context workload.

Build the same completed native workload on the existing fully migrated
application_state_dsn. Capture its actual persisted agent.turn row. Copy required
world/conversation parents and explicit destination-compatible columns into the
0139 target, preserving JSON payloads/IDs/scalar values and letting historical
constraints validate insertion. Assert exact equality of the represented row.
Keep old/single-owner alternating constraints, rollback-only UPDATE measurements,
row equality and final restoration unchanged. Preserve all migration failure,
rollback and legacy-row tests. No runtime/migration/provider/serving change.

Independent diagnosis supports actual-row transfer rather than later tables or
retained unavailable-context substitution. Relevant open storage/hosted/retrieval
own diffs were checked; no lease on this test path. Source-inspection fixture4059
is merged separately; auth contract261passed. No owned canary/worker uses checkout.

## Validation and remaining goal

Run the specific comparison then full owning module/query contract at frozen
published SHA with uniquely owned disposable databases and exact historical
versions. Scoped lint records inherited debt without broad cleanup. Independent
cumulative exact-head review, unmodified hosted frontend verifier/canonical
validation/shared lock, normal checks before merge. This synthetic storage test
is not a rerun of the frozen classic retrieval baseline or new serving timing.

V9 browser and governed new-write rollback passed at0274. Owned restore retains
head48384a4b/602revisions/sourceepoch195; live sources unchanged. Final4041 evidence
assembly/review, actual V9.B activation, V10 retirement and V11 baseline remain.
No storage optimization or broader performance claim is authorized by this fix.

Storage: existing /home/drakosfire/Projects/.codex/v7-elderwyld-scope, UUID
48fa5d10-fe99-4557-9fc9-d8a2a4b41ac8/write access verified. Scratch/v9-buddy,
existing cache/venv without sync, existing test server32903/unique fixture DBs
only; never retained restores or live data. No new worktree/container, no manual
deletion. Retain refs/receipts owner Elderwyld lane for qualification with scoped
cleanup followup after active process/mount/dirty/unique-data checks.
