# REFERENCE: qualify current Plan opening and retained recovery

Status: ACTIVE bounded PRIME test-only slice. Base341218a5819ccd9bd7cf279c3cf1348f77f0fb4d;
branch codex/plan-opening-qualification-fixtures, existing buddy-context-loop checkout.
Serial successor to merged PR2325; no unmerged parent or runtime resource lease.
Original API/UI hold, surviving database protections and coordination-off remain.

## Outcome and critique

The current native Plan opening combines semantic work and retrieval votes in one
actual SDK request. Its test transport still demanded the historical work-only wire.
Two native codec tests omitted the real execution component required for choosing
the current codec. A storage-conservation test expected an older downgrade refusal
phrase even though the newer reader fence correctly refuses forward-only recovery.
These are the seven retained failures at the base, not runtime fixes.

Update fixtures at their own boundaries: identify the actual stored admission,
assert the full closed field/question sets for that codec, return a choice for each
real question and assert one real combined call. Keep request intent, edit target,
SDK-entered state, no action/proposal for discussion, routing refusal, replay and
content-conservation checks. Supply real typed execution in the codec fixture;
never add malformed-adapter fallback to production. Assert forward-only refusal
without coupling to one migration's prose; retain before/after row snapshots.

## Expected writes and ownership

Tests: test_plan_jev_authoring.py, test_native_object_retrieval.py,
application_state/test_native_storage_owner_migration.py. Documentation: this handoff
and truthful settlement of HANDOFF-REFERENCE-retained-plan-opening.md.
No runtime, migration, CI selector/runner, lockfile, user data or provider changes.
Current open Surface2326/2313/2262, Storage2308 and CI2302/2299/2298/2288 leases were
checked; none owns these backend test files. Existing CI integration fixture lease
is separate and its files remain untouched.

## Verification and delivery

Use disposable APP test databases and synthetic transports only. Focused seven
failures and the broader semantic-authoring helper callers; full exact-source
query-and-answer contract must pass. Exact-source hosted frontend/build verifier
and independent Bugbot review remain required. Preserve the red base and earlier
attempts. Review cumulative diff, push/open PR, merge under PRIME standing authority,
then qualify protected delivery separately. No green test proves browser behavior
or whole-goal completion.
