# BUDDY — historical manual migration compatibility proof

Status: ACTIVE. Owner/designer: Elderwyld vNext completion lane. Operator authorized
implementation/review/merge. Basec9681d35cc9290f425bbc54f9aa5ab4e1b8f2bbc,
accepted4068 head (merge414852082115039148184fbba18cf235eae8336e;
review5970045779). Serial historical fixture repair→remaining V9 repairs→4041.
Branch codex/v9-historical-manual-fixture; existing isolated Buddy checkout.

## Two-path lease and invariant

Only this handoff and tests/application_state/test_manual_combat_postgres.py.
The historical0160→0166 experiment must retain raw-row preservation after every
migration, exact stored schema0166, downgrade refusal and unchanged data afterward.
The repository's current migration head is0168; it must not be spoofed or confused
with this historical database's version. Never upgrade the historical target just
to satisfy the current application schema guard.

Add the existing current application_state_dsn fixture. Read the migrated record
through repository.get_encounter on the historical connection and compare with
legacy. Transfer that returned record using repository.insert_encounter into the
separate current-schema fixture database, explicitly select its DSN, then call
normal public get_encounter with real schema/access/integrity guards intact.
Historical byte preservation and current semantic compatibility are distinct
proofs; do not claim byte equality across the typed cross-database transfer.
No runtime/migration/auth/provider/serving change; no replacement of old data with
a freshly reconstructed fixture. Independent read-only design critique approved.

Current main/open PRs/narrow instructions inspected; no overlapping exclusive
lease found on this test. No canary/worker uses checkout. No later floating-main
runtime is implicitly adopted; final bounded candidate starts from acceptedc968.

## Validation and remaining goal

Run the historical case and complete owning combat-manual-persistence contract at
frozen exact SHA on owned32903 unique disposable APP databases, preserving cleanup
and all failure logs. Scoped lint compares inherited debt without unrelated edits.
Unmodified exact-head hosted frontend verifier/canonical validation/shared lock,
independent cumulative review and normal checks before authorized merge.

4068 closes ten source fixture errors and PG extension proof:137pass0skips, owned
extension DB dropped after exit/zero connections; frontend/checks/review passed.
4067 fixed Play helper/cancellation authority; its inherited migration-test red is
this slice.4041 remains HOLD for auth specialized-guard inventory, registered World/
local-mode fixtures and durable-page APP-down contract reconciliation. Actual V9.B
activation, V10 retirement and V11 baseline remain. No classic baseline rerun.

Use existing taskroot /home/drakosfire/Projects/.codex/v7-elderwyld-scope, verified
UUID48fa5d10-fe99-4557-9fc9-d8a2a4b41ac8/writable; existing venv without sync,
scratch/v9-buddy/cache, owned test server only. No manual worktree/container/global
configuration or deletion. Retain refs/evidence owner Elderwyld lane for later
qualification with scoped cleanup followup after process/mount/dirty/unique checks.
