# REFERENCE: qualify current Plan opening and retained recovery

Status: SOURCE SETTLED. PR2327 merged at 77006af9a813cf74dde12e35a29341b1d450087e
from independently approved head be5b5587c1e201f4d0699924f1d42374ff12656b.
Exact query-and-answer: 1195 passed; exact hosted frontend/build passed and evidence
validated. The broader Rules diagnostic remains red as recorded below. No live
service replacement occurred. The implementation lease is released.

Historical bounded PRIME test-only slice. Base 341218a5819ccd9bd7cf279c3cf1348f77f0fb4d;
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
Current open Surface 2326/2313/2262, Storage 2308 and CI 2302/2299/2298/2288 leases were
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

Broader diagnostic checkpoint: exact base has 104 passed / 24 failed across the
three affected test files; the repair's working-tree diagnostic has 119 passed /
nine failed, with no newly failing IDs. The nine retained Rules cases are separate:
five already reject their synthetic writer schema, and four shared cases now reach
that later boundary after their opening fixture is corrected. No Rules output or
runtime code changed. Keep those failures red; this slice does not establish Rules
qualification or full release readiness. Exact-SHA query and frontend checks follow.
